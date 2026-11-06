---
title: "ADR 0001: Core Domain State Architecture and Dual-Modal Driving Adapters"
tags: ["adr", "ed-resolver", "architecture", "facade", "daemon", "hexagonal", "archetypes"]
created_at: "2026-11-06"
last_updated_at: "2026-11-06"
---

# ADR 0001: Core Domain State Architecture and Dual-Modal Driving Adapters

* **Status:** Accepted
* **Date:** 2026-11-06
* **Deciders:** Michael Naatjes, Antigravity Agent
* **Consulted:** ADR 0003, ADR 0004, ADR 0005 (`ed-integration-smoke`)

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

However, consumers operate under two distinct operational environments:
* **In-process Python applications & test suites** require a zero-overhead, zero-network, synchronous library facade.
* **Multi-client fleets & non-Python frontends (Web, Go, Rust)** require a centralized, always-on background daemon exposing a local API without opening duplicate file handles to the journal directory.

Terminal operators and shell scripts already have standard utilities (`curl`, `jq`, `websocat`) to inspect HTTP/WebSocket endpoints; a dedicated operator CLI driving adapter introduces unnecessary maintenance overhead without unique functional value.

How should `ed-resolver` be architected to resolve domain state from telemetry streams while cleanly serving both in-process and multi-client environments without duplicating core logic?

---

## 2. Decision Drivers

* **Domain Purity & Single Source of Truth:** Core reduction logic (archetypes, classifier, state store) must be 100% independent of I/O, networking, and frameworks.
* **Passive Decoupling from `ed-models`:** `ed-models` dataclasses must remain pure, passive schema contracts; no behavioral archetype metadata or reduction logic may leak into `ed-models`.
* **Zero Operational Friction for Python Callers:** Single-process Python apps must be able to import and run `ed-resolver` as a direct library dependency without requiring an external background daemon.
* **Polyglot & Multi-Client Fleet Support:** Multi-app homelab environments must be able to run `ed-resolver` as a standalone daemon to eliminate redundant disk polling and expose local endpoints.
* **Minimal Maintenance Footprint:** Avoid unnecessary operator CLI tooling where standard shell utilities (`curl`, `websocat`) provide identical inspection capabilities.
* **Deterministic Cold-Start Resilience:** Startup back-replay hydration must guarantee immediate, valid state recovery across mid-session launches, with explicit null-safe contracts for unseeded edge cases.

---

## 3. Considered Options

* **Option 1: Pure Library Package Only (Embedded Facade).** Publish `ed-resolver` strictly as an in-process Python library. Rejected because multi-client setups would duplicate disk I/O and non-Python tools could not consume resolved state.
* **Option 2: Standalone Microservice Daemon Only.** Build `ed-resolver` exclusively as an always-on OS background service (systemd / Docker) exposing REST/WebSocket APIs. Rejected because it introduces mandatory operational friction, IPC overhead, and background process management into simple Python scripts and integration test suites.
* **Option 3: Tri-Modal Adapters (Library, Daemon, Operator CLI).** Implement an embedded facade, a daemon, and a custom Click/Typer terminal CLI. Rejected because the CLI introduces redundant argument parsing, table formatting, and test overhead that standard HTTP tools (`curl`, `jq`) already provide.
* **Option 4: Dual-Modal Driving Adapter Architecture (Selected).** Structure `ed-resolver` with a pure, in-memory Hexagonal Domain Core wrapped by exactly two distinct Driving Adapters:
  1. *The In-Process Facade Adapter* (`from ed_resolver import AmbientTelemetryFacade`)
  2. *The Standalone Daemon Adapter* (`ed-resolver-daemon` exposing HTTP/WebSocket/IPC)

---

## 4. Decision Outcome

**Chosen Option:** **Option 4: Dual-Modal Driving Adapter Architecture**.

### 4.1 Architectural Component Hierarchy

```
+--------------------------------------------------------------------------+
|                          PACKAGE: ed-resolver                            |
|                                                                          |
|   +───────────────────────────+     +──────────────────────────────+     |
|   | DRIVING ADAPTER 1:        |     | DRIVING ADAPTER 2:           |     |
|   | Embedded Python Facade    |     | Standalone REST/WS Daemon    |     |
|   | (In-Process Library Mode) |     | (Background Service Mode)    |     |
|   +─────────────┬─────────────+     +──────────────┬───────────────+     |
|                 │                                  │                     |
|                 └─────────────────┬────────────────┘                     |
|                                   │ drives via method invocations        |
|                                   ▼                                      |
|   +──────────────────────────────────────────────────────────────────+   |
|   |                     HEXAGONAL DOMAIN CORE                        |   |
|   |                                                                  |   |
|   |   1. IngressClassifier (Stateless Event -> Archetype Router)     |   |
|   |   2. Behavioral Archetype Reducers (ADR 0003 Mechanics):        |   |
|   |      - EpochMilestoneAggregator                                  |   |
|   |      - ContextMutator                                            |   |
|   |      - EdgeTransitionDetector                                    |   |
|   |      - MetricQuantizer                                           |   |
|   |   3. Ambient State Cache (Frozen Dataclass Snapshots)            |   |
|   +──────────────────────────────────────────────────────────────────+   |
|                                   ▲                                      |
|                                   │ (Driven Port: Telemetry Ingress)     |
|   +───────────────────────────────┴──────────────────────────────────+   |
|   | DRIVEN INGRESS ADAPTER (File Watcher & Back-Replay Hydration)    |   |
|   | (Powered by `ed-telemetry` & filesystem cursors)                 |   |
|   +------------------------------------------------------------------+   |
+--------------------------------------------------------------------------+
```

### 4.2 Core Domain Specifications

1. **IngressClassifier & Registry:**
   * Contains the authoritative mapping table associating `ed-models` dataclasses with their governing ADR 0003 behavioral archetypes.
   * `ed-models` remains passive and unopinionated; classification is an extrinsic domain responsibility of `ed-resolver`.
2. **Behavioral Reducers:**
   * **Epoch Milestone:** Idempotently overwrites spatial coordinates and star systems (`Location`, `FSDJump`).
   * **Context Mutator:** Applies set differentials to loadouts, modules, and cargo inventories.
   * **Edge Transition:** Filters 1 Hz continuous bitfields into rising/falling state toggles.
   * **Metric Quantizer:** Evaluates scalar fuel/integrity levels against hysteresis bands.
3. **Cold-Start Startup Back-Replay Hydration:**
   * Upon initialization, the ingress adapter scans backward across the active journal log to recover the most recent milestone and loadout before query methods open.
   * Query getters return explicit nullable types (`LocationSnapshot | None`, `VesselSnapshot | None`) to provide strict safety for unseeded edge cases.

### 4.3 The Two Driving Adapter Modes

| Mode | Invocation Pattern | Primary Use-Case | Consumer Profile |
| :--- | :--- | :--- | :--- |
| **1. In-Process Facade** | `from ed_resolver import AmbientTelemetryFacade`<br>`facade.get_location()` | Standalone Python apps, TUI dashboards, integration test suites. | Zero-overhead, direct memory access. |
| **2. Standalone Daemon** | Terminal / systemd:<br>`ed-resolver-daemon --port 8989`<br>`GET /api/v1/state/location` | Centralized fleet host, multi-tool setups, Web UIs, Go/Rust tools. | Decoupled HTTP, SSE, and WebSocket endpoints. |

---

## 5. Consequences

### Positive
* **Unified Core Logic:** Both interaction modes execute the identical archetype classification and state reduction algorithms.
* **Lean Surface Area:** Eliminates custom CLI parsers, terminal formatters, and CLI test fixtures; operators use universal shell tools (`curl`, `jq`, `websocat`).
* **Maximum Consumer Flexibility:** Callers choose their preferred integration level (direct library dependency vs. microservice daemon) based on their runtime requirements.
* **Zero Pollution of `ed-models`:** Preserves pure hexagonal boundaries and zero-I/O invariants in upstream model packages.
* **Resource Optimization:** Multi-tool environments can deploy a single daemon instance to eliminate redundant journal reading and disk contention.

### Negative / Trade-offs
* Standalone daemon deployments require process supervision (systemd or container lifecycle management).
* Terminal operators inspecting state must use standard HTTP tools (`curl`) rather than a bespoke formatted command line.

---

## 6. Validation and Next Steps

1. Prototype and validate the complete pipeline within `ed-integration-smoke` against live/replay journal archives.
2. Author IEEE 1016 Software Design Document (SDD-0001) specifying package layout, HTTP schema endpoints, and concurrency locking primitives.
