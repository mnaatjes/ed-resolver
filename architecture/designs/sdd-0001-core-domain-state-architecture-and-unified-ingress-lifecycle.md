---
title: "SDD 0001: Core Domain State Architecture and Unified Ingress Lifecycle"
tags: ["sdd", "architecture", "ingress", "lifecycle", "state-store", "hexagonal", "ed-resolver"]
created_at: "2026-11-06"
last_updated_at: "2026-11-06"
---

# SDD 0001: Core Domain State Architecture and Unified Ingress Lifecycle

* **Status:** Proposed
* **Governing ADR:** [ADR 0001: Core Domain State Architecture and Unified Ingress Lifecycle](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0001_core_domain_state_architecture_and_unified_ingress_lifecycle.md)
* **Author:** Antigravity Pair Programmer
* **Version:** 1.0.0
* **Target Package:** `ed-resolver`

---

## 1. Introduction & Context

### 1.1 Purpose
This Software Design Document (SDD) specifies the concrete implementation architecture for the core state synthesis engine of `ed-resolver`. It provides the technical blueprints for:
1. The **`StateStore`** thread-safe in-memory state synchronization and non-blocking reader interface.
2. The reusable **`TelemetryIngressWorker`** asynchronous background lifecycle runner.
3. The driven **`TelemetryIngressPort`** boundary protocol and interchangeable ingress adapters (`DirectQueueIngressAdapter`, `LocalJournalFileIngressAdapter`, `RemoteTelemetryApiIngressAdapter`).
4. The cold-start **Startup Back-Replay Hydration** pipeline.
5. The **`ed-resolver-daemon`** thin OS CLI and HTTP/WebSocket serving harness.

### 1.2 System Boundary & Scope
The system boundary encompasses:
* `src/ed_resolver/core/ports/` (Ingress protocols and envelope contracts).
* `src/ed_resolver/core/domain/` (State store, snapshot reference management).
* `src/ed_resolver/adapters/driven/ingress/` (Ingress worker, stream tailing, queue ingestion).
* `src/ed_resolver/adapters/driving/` (In-process `AmbientTelemetryFacade`, REST controllers).
* `src/ed_resolver/daemon/` (Console script CLI entrypoint).

---

## 2. Architectural Blueprint & Component Interactions

### 2.1 Hexagonal Layer Interaction Model

```
+─────────────────────────────────────────────────────────────────────────────+
|                         APPLICATION ENTRYPOINTS                             |
|                                                                             |
|  [Embedded Library Consumer]              [Standalone OS Process Consumer]  |
|  `from ed_resolver import ...`            `ed-resolver-daemon --port 8989`  |
|              │                                           │                  |
|              ▼                                           ▼                  |
|  +─────────────────────────────+         +─────────────────────────────+    |
|  | AmbientTelemetryFacade      |         | Daemon CLI & HTTP/WS Server |    |
|  | - get_location()            |         | - GET /api/v1/state/*       |    |
|  | - is_on_foot()              |         | - WS  /api/v1/stream        |    |
|  +──────────────┬──────────────+         +──────────────┬──────────────+    |
|                 │                                       │                   |
|                 └───────────────────┬───────────────────┘                   |
|                                     ▼ reads immutable frozen snapshots      |
|  +───────────────────────────────────────────────────────────────────────+  |
|  |                         HEXAGONAL DOMAIN CORE                         |  |
|  |                                                                       |  |
|  |   StateStore                                                          |  |
|  |   - _snapshots: dict[type, object] (immutable reference swap)         |  |
|  |   - threading.RLock (atomic writer synchronization)                   |  |
|  |   - O(1) lock-free read access                                        |  |
|  +──────────────────────────────────▲────────────────────────────────────+  |
|                                     │ feed(deserialized_event)              |
|  +──────────────────────────────────┴────────────────────────────────────+  |
|  |                      DRIVEN INGRESS RUNTIME                           |  |
|  |                                                                       |  |
|  |   TelemetryIngressWorker (asyncio.Task)                               |  |
|  |   1. Reads RawTelemetryEnvelope from TelemetryIngressPort             |  |
|  |   2. Permissive Deserializer (ed_models.parse_journal_event)          |  |
|  |   3. Dead-Letter Quarantine (DLQ) Callback on parse errors            |  |
|  |   4. IngressClassifier.classify(event) -> TelemetryArchetype          |  |
|  |   5. State Reducer Pipeline Dispatch (Milestone, Mutator, etc.)       |  |
|  +──────────────────────────────────▲────────────────────────────────────+  |
|                                     │ raw envelopes                      |
|  +──────────────────────────────────┴────────────────────────────────────+  |
|  |                    PLUGGABLE INGRESS ADAPTERS                         |  |
|  |  - DirectQueueIngressAdapter: asyncio.Queue ingestion                 |  |
|  |  - LocalJournalFileIngressAdapter: Direct file tailing (ed-telemetry) |  |
|  |  - RemoteTelemetryApiIngressAdapter: WebSocket client to ed-telemetry|  |
|  +───────────────────────────────────────────────────────────────────────+  |
+─────────────────────────────────────────────────────────────────────────────+
```

---

## 3. Detailed Component Design & Contracts

### 3.1 Domain Boundary Envelope & Port Protocol (`core/ports/`)

To preserve hexagonal isolation, outer transport DTOs are mapped into standard domain envelopes at the boundary:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import AsyncIterator, Protocol


@dataclass(frozen=True, slots=True)
class RawTelemetryEnvelope:
    """Pure domain boundary envelope for incoming raw telemetry slices."""

    topic: str
    timestamp: datetime
    payload_bytes: bytes


class TelemetryIngressPort(Protocol):
    """Driven port protocol through which ingress streams enter the system."""

    async def stream_envelopes(self) -> AsyncIterator[RawTelemetryEnvelope]:
        """Asynchronously yield raw telemetry envelopes from the underlying source."""
        ...

    async def connect(self) -> None:
        """Establish underlying file handles, queues, or network sockets."""
        ...

    async def disconnect(self) -> None:
        """Release file locks, cancel consumer tasks, or close sockets."""
        ...
```

### 3.2 Thread-Safe `StateStore` Architecture (`core/domain/`)

The `StateStore` encapsulates all 9 domain snapshot states, guaranteeing:
* **Zero Torn Reads:** Readers acquire instantaneous references to immutable `@dataclass(frozen=True, slots=True)` instances.
* **Writer Atomicity:** Reducer updates modify references inside a guarded critical section (`threading.RLock`), then swap the pointer instantaneously.

```python
import threading
from typing import TypeVar, Type

T = TypeVar("T")


class StateStore:
    """Thread-safe state repository holding active frozen domain snapshots."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._snapshots: dict[type, object | None] = {}

    def get_snapshot(self, snapshot_type: type[T]) -> T | None:
        """Lock-free instantaneous reference read."""
        # Python dictionary reads are pointer-atomic under GIL / RCU semantics
        return self._snapshots.get(snapshot_type)  # type: ignore[return-value]

    def set_snapshot(self, snapshot: object) -> None:
        """Atomically replaces an active snapshot reference."""
        with self._lock:
            self._snapshots[type(snapshot)] = snapshot
```

### 3.3 Reusable Ingress Worker Runtime (`adapters/driven/ingress/`)

`TelemetryIngressWorker` executes as a long-running background worker (`asyncio.Task`):

```python
class TelemetryIngressWorker:
    """Asynchronous worker managing stream consumption, deserialization, and dispatch."""

    def __init__(
        self,
        ingress_port: TelemetryIngressPort,
        classifier: IngressClassifier,
        state_store: StateStore,
        dlq_handler: Callable[[RawTelemetryEnvelope, Exception], None] | None = None,
    ) -> None:
        self._port = ingress_port
        self._classifier = classifier
        self._store = state_store
        self._dlq_handler = dlq_handler
        self._task: asyncio.Task[None] | None = None
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        await self._port.connect()
        self._task = asyncio.create_task(self._run_loop(), name="ed-resolver-ingress-worker")

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self._port.disconnect()

    async def _run_loop(self) -> None:
        async for envelope in self._port.stream_envelopes():
            try:
                event_model = self._deserialize(envelope)
                archetype = self._classifier.classify(event_model)
                self._dispatch_to_reducer(event_model, archetype)
            except Exception as exc:
                if self._dlq_handler:
                    self._dlq_handler(envelope, exc)
```

---

## 4. Cold-Start Back-Replay Hydration (`UC-02`)

To avoid unseeded `None` dereferences upon startup (`RISK-01`):
1. **Target Identification:** Ingress initializes by scanning backwards through the current journal file (`Journal.*.log`).
2. **Milestone Recovery:** Locates the most recent `Location` or `FSDJump` milestone and `Loadout` context event.
3. **State Pre-Seeding:** Feeds recovered records to the reducers before opening query interfaces.
4. **Live Tail Handoff:** Switches seamlessly to forward tailing at EOF.

---

## 5. Verification & Quality Acceptance

1. **Deterministic Testability:** `DirectQueueIngressAdapter` enables pure in-memory pipeline verification without file or network dependencies.
2. **Concurrency Safety:** Multi-threaded stress tests assert zero torn reads under 100 concurrent readers and 1000 Hz writes.
3. **Resilience Gate:** Ingress pipeline tests assert that malformed JSON strings route to the DLQ without terminating the worker loop (`RISK-06`).
