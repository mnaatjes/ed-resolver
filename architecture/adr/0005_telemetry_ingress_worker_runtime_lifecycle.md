---
title: "ADR 0005: TelemetryIngressWorker Runtime and Ingress Lifecycle"
tags: ["adr", "ed-resolver", "architecture", "worker", "runtime", "ingress", "hexagonal", "ports-and-adapters", "asyncio"]
created_at: "2026-11-06"
last_updated_at: "2026-11-06"
---

# ADR 0005: TelemetryIngressWorker Runtime and Ingress Lifecycle

* **Status:** Accepted
* **Date:** 2026-11-06
* **Deciders:** Michael Naatjes, Antigravity Agent
* **Consulted:** [ADR 0001](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0001_core_domain_state_architecture_and_unified_ingress_lifecycle.md), [ADR 0002](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0002_archetype_classification_subsystem_and_registry.md), [ADR 0003](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0003_ambient_telemetry_facade_query_contracts_and_governance.md), [ADR 0004](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0004_hexagonal_scope_boundary_contracts_and_quality_gates.md)

---

## 1. Context and Problem Statement

Frontier Developments' *Elite Dangerous* telemetry streams arrive as asynchronous, continuous event sequences across journal files, status bitfield snapshots, and network streams. In the hexagonal architecture of `ed-resolver`:

1. The **Domain Core** (`core/domain/`) is strictly passive, synchronous, and pure. It contains domain entities, state snapshots, archetypes, and state reducers that mutate internal snapshots when given structured domain events.
2. The **Ports** (`core/ports/`) define clean boundary interfaces for telemetry ingress (`TelemetryIngressPort`), state queries, and notification emissions.
3. The **Driving Adapters** (`adapters/driving/`) provide client-facing entrypoints, such as `AmbientTelemetryFacade` (for in-process programmatic consumers like `ed-connector`) and REST/WebSocket API controllers (for external clients).

However, a fundamental runtime problem exists: **What executes the continuous asynchronous consumption loop that bridges the driven telemetry stream port to the domain core reducers?**

If `ed-resolver` provides only a passive facade with synchronous methods like `feed(event)`, every downstream consumer (e.g., `ed-connector`, TUI dashboards, copilot tools, and standalone services) must write its own `asyncio` task, implement exponential-backoff stream reconnects, handle raw JSON parsing, deserialize payloads with `ed-models`, catch validation errors, and dispatch events. This replicates fragile loop infrastructure across every client application in the fleet.

Conversely, if that background execution loop is implemented only inside a standalone OS daemon process (`ed-resolver-daemon`), in-process Python tools, copilot scripts, and smoke test suites would be forced to deploy and manage a standalone operating system daemon just to observe resolved game state.

Furthermore, confusion often arises regarding the architectural identity of this loop:
* Is it a "daemon"?
* Is it a "driving adapter"?
* Or is it an internal driven runtime worker?

A definitive architectural decision is required to formalize the role, taxonomy, lifecycle, and failure-containment boundaries of `TelemetryIngressWorker`.

---

## 2. Decision Drivers

* **Zero Duplication across Consumers:** The asynchronous event-reading loop, reconnection heuristics, raw envelope validation, and reducer dispatch must be written once and reusable anywhere in the fleet.
* **Architectural Role Clarity:** Strictly demarcate `TelemetryIngressWorker` within the Ports & Adapters hierarchy. Clarify why it is an internal driven runtime component rather than a driving adapter or a standalone daemon.
* **Passive Domain Purity:** The domain core must never instantiate event loops, background threads, or network sockets. The worker mediates between asynchronous external streams and synchronous core reducers.
* **Dual Ingress Lifecycles (Embedded vs. Standalone):** Both the embedded `AmbientTelemetryFacade(auto_connect=True)` and the CLI executable `ed-resolver-daemon` must utilize the exact same `TelemetryIngressWorker` engine.
* **Permissive Deserialization & Quarantine DLQ (Fault Isolation):** Malformed payloads, unknown Frontier events, or schema drift (Frontier game updates) must be quarantined to a Dead Letter Queue without crashing the worker task or halting state tracking.
* **Controlled Task Lifecycle:** The worker must support deterministic startup (`start()`), graceful cancellation (`stop()`), and backpressure control without orphaned coroutines or memory leaks.

---

## 3. Considered Options

* **Option 1: Consumer-Managed Loops (Passive Core Only).** `ed-resolver` exports only reducers and `AmbientTelemetryFacade.feed(event)`. Consumers are responsible for managing their own async streaming tasks and reconnection logic.
  * *Disadvantage:* High code duplication across fleet tools; divergent error handling; difficult fleet-wide updates.
* **Option 2: Standalone Daemon Only.** `TelemetryIngressWorker` exists only as part of an external CLI daemon (`ed-resolver-daemon`). All consumers must talk to the daemon over HTTP/WebSocket IPC.
  * *Disadvantage:* Heavy operational overhead for in-process libraries, CLI tools, and automated smoke tests; prevents zero-latency in-memory query facades.
* **Option 3: Reusable Driven Runtime Worker (Selected).** Implement `TelemetryIngressWorker` inside `src/ed_resolver/adapters/driven/runtime/` as an asynchronous worker class that consumes from `TelemetryIngressPort`, deserializes and classifies payloads, routes to core reducers, and handles quarantine. Both `AmbientTelemetryFacade` and `ed-resolver-daemon` instantiate and manage this worker.

---

## 4. Decision Outcome

**Chosen Option:** **Option 3: Reusable Driven Runtime Worker**.

### 4.1 Taxonomic Classification in Hexagonal Architecture

`TelemetryIngressWorker` is categorized as an **Internal Driven Runtime Worker** located under `src/ed_resolver/adapters/driven/runtime/worker.py`:

```
                       +---------------------------------------+
                       |           DRIVING BOUNDARY            |
                       |  AmbientTelemetryFacade / Daemon CLI  |
                       +-------------------+-------------------+
                                           |
                    controls lifecycle     |  queries state
                      (start / stop)       |  (get_snapshot)
                                           v
+------------------------------------------+------------------------------------------+
|                                      APPLICATION                                    |
|                                                                                     |
|   +-----------------------------------------------------------------------------+   |
|   |                  TelemetryIngressWorker (Driven Runtime)                    |   |
|   |                                                                             |   |
|   |   1. Stream Ingestion: Pulls RawTelemetryEnvelope from TelemetryIngressPort   |   |
|   |   2. Deserialization: Maps JSON to ed-models DTO with quarantine DLQ         |   |
|   |   3. Classification: Resolves TelemetryArchetype via IngressClassifier      |   |
|   |   4. State Reduction: Calls pure synchronous reducers in Domain Core        |   |
|   +-------------------+-------------------------------------+-------------------+   |
|                       |                                     |                       |
+-----------------------|-------------------------------------|-----------------------+
                        | consumes stream                     | mutates state
                        v                                     v
         +-----------------------------+       +-----------------------------+
         |     TelemetryIngressPort    |       |      Domain State Store     |
         |    (Driven Adapter Port)    |       |        (Domain Core)        |
         +-----------------------------+       +-----------------------------+
```

1. **Why it is NOT the Daemon:**
   The daemon (`ed-resolver-daemon`) is an operational OS-level process boundary—a CLI executable script that initializes logging, loads environment configuration, boots an HTTP/WebSocket server, and hosts the worker. The worker itself is pure Python code with no network listener, daemonization, or signal-handling lock-in.

2. **Why it is NOT a Driving Adapter:**
   A driving adapter initiates commands or queries against the application boundary in response to human or external client requests (e.g., `AmbientTelemetryFacade.get_location()`, HTTP `GET /api/v1/state/location`). The worker does not accept user queries; it runs in the background, consuming from driven ingress ports and pumping data downward into the domain state store.

3. **Why it IS a Driven Runtime Worker:**
   It is driven by the application runtime lifecycle (started and stopped by the facade or daemon host) and drives events into core reducers by consuming from external stream adapters satisfying `TelemetryIngressPort`.

---

### 4.2 Worker Interface, Lifecycle & Execution Model

The worker manages a single supervised `asyncio.Task` and implements a clean interface across configuration, state inspection, and lifecycle operations:

```python
class TelemetryIngressWorker:
    """Asynchronous driven runtime worker that continuously drains ingress streams into core reducers."""

    def __init__(
        self,
        ingress_port: TelemetryIngressPort,
        classifier: IngressClassifier,
        reducer_pipeline: StateReducerPipeline,
        quarantine_queue: QuarantineDeadLetterQueue | None = None,
    ) -> None: ...

    @property
    def is_running(self) -> bool: ...

    @property
    def metrics(self) -> IngressWorkerMetrics: ...

    async def start(self) -> None: ...

    async def stop(self, timeout: float = 5.0) -> None: ...

    async def process_envelope(self, envelope: RawTelemetryEnvelope) -> None: ...
```

#### Detailed Operations & Role Specifications

1. **Initialization Parameters (`__init__`):**
   * **`ingress_port: TelemetryIngressPort`:** The stream source to consume envelopes from (e.g., local disk journal tailer, remote WebSocket stream, or in-memory test queue).
   * **`classifier: IngressClassifier`:** The domain classifier that resolves event archetypes (`TelemetryArchetype`) via the generated registry.
   * **`reducer_pipeline: StateReducerPipeline`:** The pipeline of pure synchronous domain reducers updating the state store.
   * **`quarantine_queue: QuarantineDeadLetterQueue | None`:** Optional dead-letter queue for isolating unparseable or schema-drifted payloads without failing the stream.

2. **Observable Properties:**
   * **`is_running -> bool`:** Returns `True` if the worker's background task is actively running and processing events; `False` if stopped or unstarted.
   * **`metrics -> IngressWorkerMetrics`:** Exposes diagnostic counters (`envelopes_received`, `events_reduced`, `quarantined_count`, `last_event_at`) for observability and health checks.

3. **Public Methods:**
   * **`async def start() -> None`:**
     Validates the worker is not already running, establishes stream connection on `ingress_port`, and launches `_run_loop()` in a supervised `asyncio.Task`.
   * **`async def stop(timeout: float = 5.0) -> None`:**
     Signals cancellation to the background task, awaits clean task completion within the timeout, and gracefully closes `ingress_port` resources.
   * **`async def process_envelope(envelope: RawTelemetryEnvelope) -> None`:**
     Executes a single end-to-end processing step (deserialization, classification, reduction, quarantine on failure). Used by `_run_loop()` and available for deterministic testing or manual stepping.

4. **Internal Helper Responsibilities:**
   * **`async def _run_loop() -> None`:** The continuous stream-drain loop consuming from `ingress_port` and delegating to `process_envelope`.
   * **`def _deserialize(raw_payload: str) -> BaseEvent | None`:** Invokes `ed-models` deserializer.
   * **`def _quarantine(envelope: RawTelemetryEnvelope, error: Exception) -> None`:** Routes failed payloads to `quarantine_queue` with error context and updates error metrics.

---

### 4.3 Decoupled Ingress Envelope Contract (`RawTelemetryEnvelope`)

To prevent tight coupling to specific file systems or transmission protocols, the ingress boundary defines a universal, source-agnostic envelope DTO (`core/ports/envelope.py`):

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class RawTelemetryEnvelope:
    """Universal carrier for incoming telemetry data across all adapters."""

    # 1. The raw unparsed text (JSON)
    raw_payload: str

    # 2. Timestamp recorded when the envelope entered the application boundary
    received_at: datetime

    # 3. Optional origin identifier for debugging/observability (e.g., file path or stream URI)
    source_uri: str | None = None

    # 4. Optional adapter metadata (e.g., line numbers, stream partition, transport headers)
    metadata: Mapping[str, Any] = field(default_factory=dict)
```

**Design Rationale:**
* **Source-Agnostic:** Does not classify file types (e.g. journal vs. snapshot). Payloads from Frontier Developments are self-describing; `ed-models` determines event structure directly from JSON content.
* **Pure Isolation:** External transport models (e.g. `ed-telemetry` envelopes) are unpacked at the adapter boundary before reaching the worker.
* **Immutability & Performance:** `frozen=True` prevents downstream mutation, while `slots=True` minimizes memory overhead during high-frequency telemetry bursts.

### 4.4 Ingress Adapter Strategy (`TelemetryIngressPort` Implementations)

To eliminate code duplication across the *Elite Dangerous* software fleet, `ed-resolver` does **not** re-implement filesystem tailing, directory polling, or journal rotation locks—those responsibilities belong strictly to `ed-telemetry`.

Instead, `TelemetryIngressPort` is satisfied by three designated driven adapters:

1. **Primary Adapter (`EdTelemetryNetworkAdapter`):**
   * **Role:** Connects across the LAN or loopback to a running `ed-telemetry` streaming service via HTTP/SSE or WebSocket.
   * **Target Endpoints (`ed-telemetry` API):**
     * `GET /api/v1/stream`: Server-Sent Events (SSE) live push stream emitting JSON event payloads as they are journaled.
     * `GET /api/v1/status/game`: Cockpit status tick snapshot (`Status.json`) for active operational flags, pips, and fuel levels.
     * `GET /api/v1/events` & `/api/v1/events/buffer`: Event history and recent ring buffer for deterministic cold-start hydration and replay.
     * `GET /api/v1/telemetry/head`: File offset, line number, and active journal filename tracking.
   * **Usage:** Default production deployment for multi-machine setups (e.g. gaming PC streaming to a Linux/Docker host) or standalone daemon operation.
   * **Mechanism:** Unpacks `ed-telemetry` wire DTOs and wraps their inner `payload_json` strings into clean `RawTelemetryEnvelope` instances.

2. **Secondary Adapter (`EdTelemetryInProcessAdapter`):**
   * **Role:** For all-in-one desktop use without requiring a standalone daemon process.
   * **Target Contracts (`ed-telemetry` Core):**
     * **Port Contract:** `GetTelemetryStreamPort` (`ed_telemetry.core.ports.driving.telemetry_port`).
     * **Use Case Implementation:** `GetTelemetryStreamUseCase.stream_events(timeout=...) -> Iterator[TelemetryPayloadDTO]` (`ed_telemetry.core.use_cases.get_telemetry_stream`).
     * **DTO Payload Target:** `TelemetryPayloadDTO.payload_json` (raw JSON string) and `TelemetryPayloadDTO.timestamp`.
   * **Distribution:** Enabled via optional extra: `pip install ed-resolver[telemetry]`.
   * **Mechanism:** Passive listener connecting directly to `ed-telemetry`'s in-memory stream buffer. It does **not** manage or control `ed-telemetry`'s filesystem lifecycle; it simply consumes from the buffer inside the same memory space.

3. **Test Adapter (`MemoryQueueAdapter`):**
   * **Role:** Lightweight in-memory queue adapter for deterministic unit and architectural compliance tests.
   * **Usage:** Provides zero-I/O test execution without network sockets, background threads, or filesystem handles.

---

### 4.5 Ingress Pipeline Operations

Inside `_run_loop()`, each incoming event traverses four sequential phases:

1. **Stream Ingestion:**
   Consumes `RawTelemetryEnvelope` items asynchronously from the configured `TelemetryIngressPort` implementation (`EdTelemetryNetworkAdapter`, `EdTelemetryInProcessAdapter`, or `MemoryQueueAdapter`).
2. **Permissive Deserialization & Quarantine (DLQ):**
   * Uses `ed-models` to deserialize payload JSON into typed event DTOs.
   * If parsing fails (unknown event structure, corrupted JSON, or schema validation error), the raw envelope is not dropped silently; it is routed directly to the `QuarantineDeadLetterQueue` with error diagnostics. The worker continues executing without crashing.
3. **Archetype Classification:**
   * Invokes `IngressClassifier.classify(event)` to map the event to its primary `TelemetryArchetype` using the generated classification registry.
4. **Domain State Reduction:**
   * Passes the classified event and archetype to the synchronous `StateReducerPipeline`.
   * Updates frozen domain snapshots atomically in the `DomainStateStore`.
   * Dispatches change notifications to registered subscribers via `TelemetryNotificationPort`.

---

### 4.6 Operational Exception Model vs. Query Null-Return Strategy

`ed-resolver` strictly decouples **state query responses** from **runtime operational failures**:

* **Downstream Query Return Strategy (ADR 0001 & ADR 0003):**
  When consumer facades query domain state (e.g., `get_location()`), unseeded or mid-flight edge cases return explicit nullable types (`LocationSnapshot | None`) or pre-populated safe defaults rather than raising exceptions.

* **Worker Operational Exceptions:**
  Unlike passive domain queries, the `TelemetryIngressWorker` controls active system plumbing and background task lifecycles. Operational mistakes (e.g. attempting to double-start a running worker) or infrastructure failures (e.g. port connection drops, shutdown timeouts) must raise explicit, structured exceptions (`core/errors.py`):

```python
class TelemetryWorkerError(Exception):
    """Base exception for all worker lifecycle and operational failures."""


class WorkerAlreadyRunningError(TelemetryWorkerError):
    """Raised when start() is invoked on an already running worker."""


class WorkerNotRunningError(TelemetryWorkerError):
    """Raised when an operation requires an active worker, but it is stopped."""


class WorkerLifecycleTimeoutError(TelemetryWorkerError):
    """Raised when stop() times out waiting for the worker loop task to conclude."""


class IngressPortConnectionError(TelemetryWorkerError):
    """Raised when the worker cannot connect to or initialize the IngressPort stream."""
```

**What Does NOT Raise an Exception:**
Payload deserialization errors, malformed JSON, and unexpected game events are strictly non-fatal. They do **not** raise `TelemetryWorkerError`; instead, they route immediately to `QuarantineDeadLetterQueue` to maintain continuous runtime availability.

---

## 5. Consequences

### Positive

* **Uniform Behavior Across Runtimes:** Whether embedded in a copilot or running in a 24/7 background daemon, event reduction, deserialization, and quarantine rules are identical.
* **Resilience against Game Updates:** Schema changes or unrecognized journal events never crash the consumer application or loop task; unparsed events are cleanly sequestered in quarantine.
* **Clean Hexagonal Isolation:** The domain core remains completely synchronous and decoupled from `asyncio`, network sockets, or OS process lifecycles.
* **Testability:** In unit and integration smoke tests, the worker can be wired to a `MemoryQueueStreamAdapter` and stepped deterministically without spawning OS daemon processes.

### Negative

* **Asyncio Concurrency Requirement:** In-process embedded consumers must either run within an `asyncio` event loop or let the facade manage an isolated worker background thread with its own loop.
* **Quarantine Memory Management:** The in-memory dead-letter queue must enforce a bounded capacity (ring buffer or eviction policy) to prevent memory growth during prolonged periods of invalid data.

---

## 6. References

* [ADR 0001: Core Domain State Architecture and Unified Ingress Lifecycle](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0001_core_domain_state_architecture_and_unified_ingress_lifecycle.md)
* [ADR 0002: Archetype Classification Subsystem and Registry](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0002_archetype_classification_subsystem_and_registry.md)
* [ADR 0004: Hexagonal Scope Boundary Contracts and Automated Quality Gate Enforcement](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0004_hexagonal_scope_boundary_contracts_and_quality_gates.md)
