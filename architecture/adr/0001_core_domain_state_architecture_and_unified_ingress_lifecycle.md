---
title: "ADR 0001: Core Domain State Architecture and Unified Ingress Lifecycle"
tags: ["adr", "ed-resolver", "architecture", "facade", "daemon", "cli-daemon", "hexagonal", "archetypes"]
created_at: "2026-11-06"
last_updated_at: "2026-11-06"
---

# ADR 0001: Core Domain State Architecture and Unified Ingress Lifecycle

* **Status:** Accepted
* **Date:** 2026-11-06
* **Deciders:** Michael Naatjes, Antigravity Agent
* **Consulted:** [ADR 0002](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0002_archetype_classification_subsystem_and_registry.md), ADR 0003, ADR 0004, ADR 0005 (`ed-integration-smoke`)

---

## 1. Context and Problem Statement

Frontier Developments' *Elite Dangerous* client emits fragmented, asynchronous telemetry streams across two distinct channels:
1. Continuous 1 Hz status ticks (`Status.json`) carrying integer bitfields and scalar measurements.
2. Chronological event logs (`Journal.*.log`) emitted upon discrete in-game actions.

Downstream consumers (TUI visualizers, in-game overlays, navigation copilots, Discord bots, and third-party dispatchers like EDDN/Inara) require real-time, consolidated truths:
* *Where is the commander right now?* (`LocationSnapshot`)
* *What ship/loadout is active?* (`VesselSnapshot`)
* *Is the commander disembarked on foot?* (`is_on_foot`)
* *What is the current flight state and fuel level?* (`FlightMode`, `QuantizedFuelState`)

To prevent each consumer from repeatedly parsing raw logs, managing bitwise math, or duplicating event-reduction heuristics, a dedicated state synthesis package—`ed-resolver`—is required.

However, consumers operate under different deployment topologies:
* **Embedded Library Consumers (e.g. `ed-connector`, copilots, smoke tests):** Import `ed-resolver` as a direct Python dependency and require a zero-overhead, in-process query facade.
* **Standalone Daemon Consumers (e.g. Web UIs, Go/Rust tools, multi-app homelabs):** Connect over local HTTP/WebSockets to an always-on background service without each holding duplicate file handles to the journal logs.

A critical architectural challenge arises: **Where does the running background listener process live?**
If `ed-resolver` were only a passive data reducer, every consuming package (such as `ed-connector`) would have to write its own asynchronous background loop to connect to `ed-telemetry`, poll streams, handle reconnections, and feed events. This would result in duplicate listener logic strewn across fleet applications.

Conversely, if `ed-resolver` required a running external daemon process to function, simple in-process Python tools and integration test suites would be forced to manage background service orchestration, introducing unnecessary operational friction.

How should `ed-resolver` encapsulate the background runner logic to guarantee zero duplication across consumers while providing both an in-process Facade and an executable Daemon entrypoint?

---

## 2. Decision Drivers

* **Encapsulated Ingress Worker (Zero Logic Duplication):** The asynchronous worker logic that connects to telemetry feeds, handles reconnection, deserializes raw JSON, and feeds reducers must reside 100% inside `ed-resolver` as a reusable runtime component.
* **Passive Domain Core vs. Active Lifecycle Runner:** The hexagonal core (archetypes, classifier, state store) must remain pure and synchronous, while the async listener loop is cleanly encapsulated in an operational worker runtime (`TelemetryIngressWorker`).
* **Thin Daemon Executable:** The standalone daemon (`ed-resolver-daemon`) must be a thin CLI entrypoint that merely hosts the reusable worker and exposes an HTTP/WebSocket server.
* **Pluggable Ingress Decoupling:** The ingress pipeline must support interchangeable sources: in-memory queues (testing), local journal disk tailing (embedded), or remote WebSocket/SSE streams (`ed-telemetry` API).
* **Pure Boundary Isolation (No Foreign DTOs in Core):** The domain core must define its own internal envelope contracts (`RawTelemetryEnvelope`) without importing concrete transport DTOs from external packages.
* **Resilient Deserialization & Quarantine:** Ingress parsing must handle malformed JSON and schema drift gracefully (per `RISK-06`) via dead-letter quarantine without halting the state reducer.
* **Thread-Safe Atomic State Synchronization:** Concurrent reads and async writes must guarantee atomic snapshot replacements (`@dataclass(frozen=True)`) without torn reads or thread lock contention.
* **Deterministic Cold-Start Resilience:** Startup back-replay hydration must guarantee immediate, valid state recovery across mid-session launches, with explicit null-safe contracts for unseeded edge cases.
* **Passive Decoupling from `ed-models`:** `ed-models` dataclasses must remain pure, passive schema contracts; no behavioral archetype metadata or reduction logic may leak into `ed-models`.

---

## 3. Considered Options

* **Option 1: Passive Reducer Library Only (Consumer-Owned Listeners).** `ed-resolver` only provides synchronous `feed(event)` methods. Every consumer (`ed-connector`, daemon, test runner) must author their own async listener and stream reconnection loop. Rejected due to severe code duplication and fragmented error handling across consumers.
* **Option 2: Standalone Microservice Daemon Only.** Build `ed-resolver` strictly as an independent OS service. In-process consumers cannot embed the library; all tools must communicate over loopback HTTP/WebSocket sockets. Rejected due to operational complexity in unit tests, CI pipelines, and standalone Python scripts.
* **Option 3: Unified Engine Architecture with Reusable Worker Runtime (Selected).** Author `ed-resolver` as a complete library containing the domain core, the state facade, and a reusable `TelemetryIngressWorker`. Bundle a thin CLI entrypoint (`ed-resolver-daemon`) that spins up the worker and serves HTTP/WebSockets.

---

## 4. Decision Outcome

**Chosen Option:** **Option 3: Unified Engine Architecture with Reusable Worker Runtime**.

### 4.1 Architectural Hierarchy

```
+------------------------------------------------------------------------------------+
|                                PACKAGE: ed-resolver                                |
|                                                                                    |
|   +────────────────────────────────────────────────────────────────────────────+   |
|   | THIN CLI EXECUTABLE ENTRYPOINT:                                            |   |
|   | `ed-resolver-daemon` ([project.scripts] console script in cli.py)          |   |
|   |  - Parses CLI flags (--port 8989, --telemetry-url, --journal-dir)          |   |
|   |  - Starts TelemetryIngressWorker + REST / WebSocket API Server             |   |
|   +─────────────────────────────────────┬──────────────────────────────────────+   |
|                                         │ boots worker & serves HTTP/WS            |
|                                         ▼                                          |
|   +────────────────────────────────────────────────────────────────────────────+   |
|   | DRIVING ADAPTER: In-Process Ambient Facade (`AmbientTelemetryFacade`)      |   |
|   |  - Exposes get_location(), get_vessel(), is_on_foot(), get_flight_mode()   |   |
|   |  - Delegated lifecycle controls: start() / stop() via IngressWorker        |   |
|   +─────────────────────────────────────┬──────────────────────────────────────+   |
|                                         │ reads atomic state snapshots             |
|                                         ▼                                          |
|   +────────────────────────────────────────────────────────────────────────────+   |
|   |                           HEXAGONAL DOMAIN CORE                            |   |
|   |                                                                            |   |
|   |   1. IngressClassifier (ADR 0002 Static Registry + Bootstrap Overrides)    |   |
|   |      - Resolves typed event to TelemetryArchetype in O(1) time             |   |
|   |   2. Behavioral Archetype Reducers & Dispatch (ADR 0003 Mechanics):        |   |
|   |      - EpochMilestoneAggregator  (Spatial & Session milestones)            |   |
|   |      - ContextMutator            (Loadout, cargo, & equipment differentials)|   |
|   |      - EdgeTransitionDetector    (Continuous 1 Hz bitmask toggle deltas)   |   |
|   |      - MetricQuantizer           (Continuous gauge threshold hysteresis)   |   |
|   |      - PASSIVE Bypass Pipeline   (Non-mutating events / audit passthrough) |   |
|   |   3. StateStore (Atomic Reference Swap of Frozen Dataclass Snapshots)      |   |
|   +─────────────────────────────────────▲──────────────────────────────────────+   |
|                                         │ (Driven Port: TelemetryIngressPort)      |
|   +─────────────────────────────────────┴──────────────────────────────────────+   |
|   | DRIVEN INGRESS RUNTIME (`TelemetryIngressWorker`):                         |   |
|   |  - Permissive Deserializer (ed_models.parse_journal_event + Quarantine)    |   |
|   |  - Manages stream connection, auto-reconnect, and line dispatch            |   |
|   +─────────────────────────────────────▲──────────────────────────────────────+   |
|                                         │ consumes raw byte/JSON envelopes         |
|   +─────────────────────────────────────┴──────────────────────────────────────+   |
|   | PLUGGABLE INGRESS ADAPTERS:                                                |   |
|   |  - DirectQueueIngressAdapter (In-memory asyncio.Queue for tests/copilots)  |   |
|   |  - LocalJournalFileIngressAdapter (Direct disk tailing via ed-telemetry)   |   |
|   |  - RemoteTelemetryApiIngressAdapter (WebSocket/SSE client to ed-telemetry)|   |
|   +----------------------------------------------------------------------------+   |
+------------------------------------------------------------------------------------+
```

### 4.2 Reusable Worker Runtime vs. Thin Daemon Entrypoint

1. **`TelemetryIngressWorker` (Infrastructure Runtime Worker):**
   * Encapsulates the complete background listening, stream reconnection, raw JSON deserialization (via `ed_models.parse_journal_event`), archetype classification (via `IngressClassifier`, [ADR 0002](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0002_archetype_classification_subsystem_and_registry.md)), and archetype reduction dispatch loop.
   * **Quarantine / DLQ Policy (RISK-06):** Inbound lines that fail JSON decoding or model hydration are caught, routed to an optional quarantine logging callback, and bypassed without raising uncaught exceptions or terminating the worker loop.
   * **Classification & Pipeline Routing ([ADR 0002](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0002_archetype_classification_subsystem_and_registry.md)):** Once deserialized into a typed `ed-models` dataclass, the event is passed to `IngressClassifier.classify(event)`. If classified as state-bearing (`EPOCH_MILESTONE`, `CONTEXT_MUTATOR`, `EDGE_TRANSITION`, `METRIC_QUANTIZER`), it routes to the respective domain reducer; if classified as `PASSIVE`, it bypasses reduction state mutation and is forwarded directly to downstream observers.
   * Exposes clean lifecycle controls: `await worker.start()` and `await worker.stop()`.
   * **For Embedded Consumers (`ed-connector`, Copilot):** Consumers instantiate `AmbientTelemetryFacade(auto_connect=True)` or call `await facade.start()`. The facade delegates to an internal `TelemetryIngressWorker` running as a background `asyncio.Task` inside the caller's event loop. Zero code duplication.

2. **`ed-resolver-daemon` (Thin CLI Entrypoint):**
   * Defined as a console script in `pyproject.toml` pointing to `src/ed_resolver/daemon/cli.py`.
   * Accepts command-line parameters (e.g. `--port`, `--telemetry-host`, `--journal-dir`).
   * Instantiates `AmbientTelemetryFacade`, starts `TelemetryIngressWorker`, and exposes a lightweight Starlette/FastAPI HTTP/WebSocket server.
   * Contains zero business logic; acts strictly as an operating system process harness.

### 4.3 Pluggable Ingress Ports & Pure Domain Isolation

To preserve Hexagonal Boundary Isolation, the domain core defines its own pure driven port and envelope protocol without importing foreign transport DTOs:

```python
@dataclass(frozen=True, slots=True)
class RawTelemetryEnvelope:
    """Pure domain boundary envelope for inbound telemetry payloads."""
    topic: str
    timestamp: datetime
    payload_bytes: bytes


class TelemetryIngressPort(Protocol):
    """Driven port through which normalized telemetry envelopes enter the state core."""
    def feed(self, envelope: RawTelemetryEnvelope) -> None: ...
```

Concrete ingress sources map their payloads into `RawTelemetryEnvelope` via interchangeable Driven Adapters:
* **`DirectQueueIngressAdapter`:** Ingests envelopes from an in-memory `asyncio.Queue` or Python generator. Used for mock testing and deterministic replay.
* **`LocalJournalFileIngressAdapter`:** Directly monitors and tails local journal files on the OS filesystem using `ed-telemetry` as an imported library. Used by standalone in-process copilots without network daemons.
* **`RemoteTelemetryApiIngressAdapter`:** Connects as a WebSocket / SSE client to an external `ed-telemetry` HTTP server (`http://localhost:8080`), converting `ed_telemetry.TelemetryPayloadDTO` into `RawTelemetryEnvelope`.

### 4.4 Atomic Concurrency & State Synchronization

* In-memory state is maintained inside `StateStore` as immutable, frozen dataclasses (`@dataclass(frozen=True, slots=True)`: `LocationSnapshot`, `VesselSnapshot`, `QuantizedFuelState`).
* **Synchronization Contract:** The asynchronous writer thread (`TelemetryIngressWorker`) prepares new snapshots off-thread and updates the store via an atomic reference swap protected by a fine-grained reentrant lock (`threading.RLock`).
* Readers (`facade.get_location()`) acquire an instantaneous reference to the active frozen instance. This guarantees $O(1)$ sub-microsecond non-blocking reads with zero risk of torn state or reader lock starvation.

### 4.5 Cold-Start Startup Back-Replay Hydration

* Upon initialization, the selected ingress adapter scans backward across the active journal log to recover the most recent milestone (`Location` or `FSDJump`) and loadout before query methods open.
* Query getters return explicit nullable types (`LocationSnapshot | None`, `VesselSnapshot | None`) to provide strict safety for unseeded edge cases.

---

## 5. Consequences

### Positive
* **Zero Duplication:** The entire telemetry listening, reconnection, and deserialization lifecycle is packaged within `ed-resolver`. Consuming applications simply invoke `await facade.start()`.
* **Hexagonal Boundary Purity:** Core domain layers depend strictly on Python standard library and local protocols (`RawTelemetryEnvelope`); no third-party transport DTOs leak into the domain core.
* **Resilient Ingress Pipeline:** Malformed or drifting Frontier JSON lines are safely quarantined without halting the state reducer loop.
* **Thread-Safe Non-Blocking Reads:** Frozen dataclasses and atomic pointer updates provide deterministic concurrency for high-frequency readers.
* **Dual Operational Topologies:** Supports both embedded in-process execution (library dependency) and centralized fleet execution (standalone daemon).
* **Pluggable Ingress:** Seamlessly switches between in-memory mock queues, local journal file watching, or remote `ed-telemetry` API streams without changing domain reducer code.
* **Thin CLI Daemon:** `ed-resolver-daemon` is a lightweight process wrapper containing no domain rules, making it trivial to test and maintain.

### Negative / Trade-offs
* `ed-resolver` includes optional dependencies for daemon hosting (e.g., `uvicorn`, `starlette`), managed via optional dependency extras (`pip install ed-resolver[daemon]`).
* Standalone daemon deployments require process supervision (systemd or container lifecycle management).

---

## 6. Validation and Next Steps

1. Prototype the `TelemetryIngressWorker` and pluggable adapters within `ed-integration-smoke`.
2. Author IEEE 1016 Software Design Document (SDD-0001) detailing class contracts, `TelemetryIngressWorker` concurrency controls, `IngressClassifier` integration ([ADR 0002](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0002_archetype_classification_subsystem_and_registry.md)), and HTTP/WebSocket schema endpoints.
