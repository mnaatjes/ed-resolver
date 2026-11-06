---
title: "SDD 0005: TelemetryIngressWorker Runtime and Ingress Lifecycle Subsystem"
tags: ["sdd", "architecture", "worker", "runtime", "ingress", "hexagonal", "asyncio", "ports-and-adapters", "ed-resolver"]
created_at: "2026-11-06"
last_updated_at: "2026-11-06"
---

# SDD 0005: TelemetryIngressWorker Runtime and Ingress Lifecycle Subsystem

* **Status:** Proposed
* **Governing ADRs:** [ADR 0001](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0001_core_domain_state_architecture_and_unified_ingress_lifecycle.md), [ADR 0002](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0002_archetype_classification_subsystem_and_registry.md), [ADR 0003](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0003_ambient_telemetry_facade_query_contracts_and_governance.md), [ADR 0004](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0004_hexagonal_scope_boundary_contracts_and_quality_gates.md), [ADR 0005](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0005_telemetry_ingress_worker_runtime_lifecycle.md)
* **Author:** Antigravity Pair Programmer
* **Version:** 1.0.0
* **Target Package:** `ed-resolver`

---

## 1. Introduction & Context

### 1.1 Purpose
This Software Design Document specifies the technical blueprint for the `TelemetryIngressWorker` runtime subsystem in `ed-resolver`. It defines the concrete interfaces, class structures, lifecycle states, data envelopes, error models, and driven adapter implementations that bridge external telemetry feeds to synchronous domain core reducers without duplicating fleet streaming logic.

### 1.2 System Boundary & Scope
The implementation is strictly confined to:
* **Port Envelope & Interface:** `src/ed_resolver/core/ports/envelope.py` and `src/ed_resolver/core/ports/ingress.py`.
* **Runtime Worker Engine:** `src/ed_resolver/adapters/driven/runtime/worker.py` and `src/ed_resolver/adapters/driven/runtime/metrics.py`.
* **Operational Exceptions:** `src/ed_resolver/core/errors.py`.
* **Driven Ingress Adapters:** `src/ed_resolver/adapters/driven/ingress/{network.py, inprocess.py, memory.py}`.
* **Architectural Boundary Tests:** `tests/architecture/test_ingress_worker_boundaries.py`.

---

## 2. Architectural Blueprint & Subsystem Decomposition

```
                                  +---------------------------------------+
                                  |           DRIVING BOUNDARY            |
                                  |  AmbientTelemetryFacade / Daemon CLI  |
                                  +-------------------+-------------------+
                                                      |
                               controls lifecycle     |  queries state
                                 (start / stop)       |  (get_snapshot)
                                                      v
+-----------------------------------------------------+-----------------------------------------------------+
|                                                 APPLICATION                                               |
|                                                                                                           |
|   +---------------------------------------------------------------------------------------------------+   |
|   |                        TelemetryIngressWorker (Driven Runtime Engine)                             |   |
|   |                                                                                                   |   |
|   |   1. Stream Ingestion: Pulls RawTelemetryEnvelope from TelemetryIngressPort                      |   |
|   |   2. Deserialization: Maps JSON to ed-models DTO with QuarantineDeadLetterQueue                   |   |
|   |   3. Classification: Resolves TelemetryArchetype via IngressClassifier                            |   |
|   |   4. State Reduction: Calls pure synchronous reducers in Domain Core                              |   |
|   +-------------------+---------------------------------------------------------------+---------------+   |
|                       |                                                               |                   |
+-----------------------|---------------------------------------------------------------|-------------------+
                        | consumes stream                                               | mutates state
                        v                                                               v
         +-----------------------------+                                 +-----------------------------+
         |     TelemetryIngressPort    |                                 |      Domain State Store     |
         |    (Driven Adapter Port)    |                                 |        (Domain Core)        |
         +--------------+--------------+                                 +-----------------------------+
                        |
        +---------------+---------------+
        |                               |
        v                               v
+-----------------------------+ +-----------------------------+
|  EdTelemetryNetworkAdapter  | |  EdTelemetryInProcessAdapter|
|     (Primary: LAN / SSE)    | | (Secondary: In-Memory Buffer|
+-----------------------------+ +-----------------------------+
```

---

## 3. Data Contracts & Interfaces

### 3.1 The Ingress Envelope Contract (`core/ports/envelope.py`)

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class RawTelemetryEnvelope:
    """Universal carrier for incoming telemetry data across all adapters."""

    # Raw unparsed JSON string
    raw_payload: str

    # Boundary ingestion timestamp
    received_at: datetime

    # Optional origin debugging identifier (e.g. URI or buffer name)
    source_uri: str | None = None

    # Optional adapter metadata (line numbers, HTTP headers, stream partition)
    metadata: Mapping[str, Any] = field(default_factory=dict)
```

### 3.2 The Ingress Port Contract (`core/ports/ingress.py`)

```python
from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from .envelope import RawTelemetryEnvelope


@runtime_checkable
class TelemetryIngressPort(Protocol):
    """Driven port protocol yielding continuous raw telemetry envelopes."""

    async def stream_envelopes(self) -> AsyncIterator[RawTelemetryEnvelope]:
        """Asynchronously yield raw envelopes from the underlying transport stream."""
        ...

    async def aclose(self) -> None:
        """Cleanly release open stream or network resources."""
        ...
```

---

## 4. Subsystem Detailed Design

### 4.1 TelemetryIngressWorker (`adapters/driven/runtime/worker.py`)

```python
import asyncio
import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

from ed_resolver.core.domain.archetypes import TelemetryArchetype
from ed_resolver.core.domain.classification.classifier import IngressClassifier
from ed_resolver.core.errors import (
    WorkerAlreadyRunningError,
    WorkerLifecycleTimeoutError,
    WorkerNotRunningError,
)
from ed_resolver.core.ports.envelope import RawTelemetryEnvelope
from ed_resolver.core.ports.ingress import TelemetryIngressPort

logger = logging.getLogger(__name__)


class TelemetryIngressWorker:
    """Asynchronous driven runtime worker that drains ingress streams into core reducers."""

    def __init__(
        self,
        ingress_port: TelemetryIngressPort,
        classifier: IngressClassifier,
        reducer_pipeline: Any,  # StateReducerPipeline protocol
        quarantine_queue: Any | None = None,  # QuarantineDeadLetterQueue protocol
    ) -> None:
        self._ingress_port = ingress_port
        self._classifier = classifier
        self._reducer_pipeline = reducer_pipeline
        self._quarantine_queue = quarantine_queue

        self._task: asyncio.Task[None] | None = None
        self._is_running: bool = False
        self._envelopes_received: int = 0
        self._events_reduced: int = 0
        self._quarantined_count: int = 0
        self._last_event_at: datetime | None = None

    @property
    def is_running(self) -> bool:
        return self._is_running and self._task is not None and not self._task.done()

    @property
    def metrics(self) -> dict[str, Any]:
        return {
            "envelopes_received": self._envelopes_received,
            "events_reduced": self._events_reduced,
            "quarantined_count": self._quarantined_count,
            "last_event_at": self._last_event_at,
        }

    async def start(self) -> None:
        if self.is_running:
            raise WorkerAlreadyRunningError("TelemetryIngressWorker is already running.")

        self._is_running = True
        self._task = asyncio.create_task(self._run_loop(), name="TelemetryIngressWorkerLoop")

    async def stop(self, timeout: float = 5.0) -> None:
        if not self._is_running or self._task is None:
            raise WorkerNotRunningError("Cannot stop an inactive TelemetryIngressWorker.")

        self._is_running = False
        self._task.cancel()

        try:
            await asyncio.wait_for(self._task, timeout=timeout)
        except asyncio.CancelledError:
            pass
        except TimeoutError:
            raise WorkerLifecycleTimeoutError(
                f"Worker loop failed to terminate within {timeout} seconds."
            )
        finally:
            self._task = None
            await self._ingress_port.aclose()

    async def process_envelope(self, envelope: RawTelemetryEnvelope) -> None:
        self._envelopes_received += 1
        try:
            event = self._deserialize(envelope.raw_payload)
            if event is None:
                raise ValueError("Payload deserialized to empty event.")

            archetype = self._classifier.classify(event)
            self._reducer_pipeline.reduce(event, archetype)
            self._events_reduced += 1
            self._last_event_at = envelope.received_at
        except Exception as exc:
            self._quarantine(envelope, exc)

    async def _run_loop(self) -> None:
        try:
            async for envelope in self._ingress_port.stream_envelopes():
                if not self._is_running:
                    break
                await self.process_envelope(envelope)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("Unhandled exception in TelemetryIngressWorker loop: %s", exc)
            raise
        finally:
            self._is_running = False

    def _deserialize(self, raw_payload: str) -> Any:
        # Deserializes JSON via ed-models entrypoint
        ...

    def _quarantine(self, envelope: RawTelemetryEnvelope, error: Exception) -> None:
        self._quarantined_count += 1
        if self._quarantine_queue is not None:
            self._quarantine_queue.put(envelope, error)
        else:
            logger.warning(
                "Payload quarantined without active DLQ: %s (Error: %s)",
                envelope.source_uri,
                error,
            )
```

---

## 5. Driven Adapter Implementations

### 5.1 Primary Adapter: `EdTelemetryNetworkAdapter` (`adapters/driven/ingress/network.py`)
Connects to remote/local `ed-telemetry` HTTP/SSE services:
* **Endpoints:**
  * `GET /api/v1/stream`: SSE push stream yielding live events.
  * `GET /api/v1/status/game`: Cockpit status tick snapshot.
  * `GET /api/v1/events` & `/api/v1/events/buffer`: Replay and cold-start catch-up.
* **Mechanism:** Wraps `payload_json` into `RawTelemetryEnvelope`.

### 5.2 Secondary Adapter: `EdTelemetryInProcessAdapter` (`adapters/driven/ingress/inprocess.py`)
Direct passive listener connecting to in-memory buffers:
* **Target Contracts:**
  * `GetTelemetryStreamPort` (`ed_telemetry.core.ports.driving.telemetry_port`).
  * `GetTelemetryStreamUseCase.stream_events(timeout=...)`.
* **Packaging:** Optional extra via `pip install ed-resolver[telemetry]`.
* **Zero Lifecycle Ownership:** Consumes from the stream iterator without initializing or managing journal watchers.

### 5.3 Test Adapter: `MemoryQueueAdapter` (`adapters/driven/ingress/memory.py`)
Lightweight FIFO queue (`asyncio.Queue[RawTelemetryEnvelope]`) for deterministic test suites.

---

## 6. Operational Exception Hierarchy (`core/errors.py`)

```python
class TelemetryWorkerError(Exception):
    """Base exception for all worker lifecycle and operational failures."""


class WorkerAlreadyRunningError(TelemetryWorkerError):
    """Raised when start() is invoked on an active worker."""


class WorkerNotRunningError(TelemetryWorkerError):
    """Raised when an operation requires an active worker, but it is stopped."""


class WorkerLifecycleTimeoutError(TelemetryWorkerError):
    """Raised when stop() times out waiting for the background task to complete."""


class IngressPortConnectionError(TelemetryWorkerError):
    """Raised when the worker cannot connect to or initialize the IngressPort stream."""
```

---

## 7. Scope & Boundary Enforcement Verification

To safeguard fleet architecture and prevent direct file watching in `ed-resolver`:
1. **AST Compliance Test (`test_no_filesystem_watchers_in_ingress_adapters`):**
   Scans `adapters/driven/ingress/` and `adapters/driven/runtime/` to guarantee zero imports of `watchdog`, `inotify`, `win32file`, or disk polling utilities.
2. **Import-Linter Layer Verification (`.importlinter`):**
   Ensures `core/domain` and `core/ports` never import `adapters/driven/runtime`.
3. **Packaging Verification (`pyproject.toml`):**
   Ensures `ed-telemetry` is strictly quarantined to `[project.optional-dependencies]`.
