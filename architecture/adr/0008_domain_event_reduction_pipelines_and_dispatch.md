---
title: "ADR 0008: Domain Event Reduction Pipelines and Dispatch Architecture"
tags: ["adr", "ed-resolver", "architecture", "reducers", "use-cases", "hexagonal"]
created_at: "2026-11-08"
last_updated_at: "2026-11-08"
---

# ADR 0008: Domain Event Reduction Pipelines and Dispatch Architecture

* **Status:** Accepted
* **Date:** 2026-11-08
* **Deciders:** Michael Naatjes, Antigravity Agent
* **Consulted:** [ADR 0001](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0001_core_domain_state_architecture_and_unified_ingress_lifecycle.md), [ADR 0002](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0002_archetype_classification_subsystem_and_registry.md), [ADR 0005](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0005_telemetry_ingress_worker_runtime_lifecycle.md), [ADR 0006](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0006_core_domain_state_model_taxonomy_and_immutability.md), [ADR 0007](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0007_in_memory_domain_state_store_and_atomic_swap.md)

---

## 1. Context and Problem Statement

`ed-resolver` ingests deserialized *Elite Dangerous* telemetry events (`ed-models` DTOs) and 1 Hz status ticks from the `TelemetryIngressWorker`. These incoming payloads must be translated into updated domain projections (`LocationState`, `VesselState`, `CargoState`, etc.) and stored in `DomainStateStore`.

Allowing worker runtimes or adapters to modify domain states directly couples infrastructure to business logic and violates hexagonal architecture. Furthermore, updates must remain purely deterministic, testable in complete isolation without mocking I/O, and thread-safe.

How should `ed-resolver` structure, execute, and dispatch telemetry reduction logic across its 9 domains to ensure pure domain calculations, zero lifecycle coupling, and strict hexagonal compliance?

---

## 2. Decision Drivers

* **Pure Domain Logic:** Reduction calculations must be mathematical, stateless transforms (`State_new = reduce(State_current, Event)`). Reducers must perform zero I/O, zero network calls, and zero in-place mutations.
* **Separation of Computation and Storage:** Pure domain reducers calculate updated state models; application use cases coordinate fetching the current state from `DomainStateReaderPort` and saving the updated state to `DomainStateWriterPort`.
* **Behavioral Archetype Fast-Path:** Events classified as `PASSIVE` (e.g. `Music`, `Fileheader`) must be fast-path discarded before invoking domain reducers, minimizing CPU cycles.
* **Hexagonal Boundary Enforcement:**
  - Reducer functions reside strictly inside `core/domain/<domain>/reducers.py`.
  - The reduction use case resides in `core/use_cases/process_telemetry_reduction.py` and implements a driving port `ReduceTelemetryEventPort`.
  - Driven ports (`DomainStateReaderPort`, `DomainStateWriterPort`) are injected via constructor dependency injection.

---

## 3. Considered Options

* **Option 1: Monolithic Reducer Dispatcher in Adapter Runtime.** The `TelemetryIngressWorker` contains all event handling logic and directly mutates internal dictionaries. Rejected as it couples infrastructure to business logic and breaks hexagonal boundaries.
* **Option 2: Active Record / Mutator Methods on State Models.** Methods like `location_state.apply_fsd_jump(event)` mutate or return new states. Rejected because state models are frozen slotted data structures and should remain pure value containers without sprawling event logic.
* **Option 3: Pure Functional Domain Reducers with Hexagonal Use Case Orchestration (Selected).**
  - Pure domain reducer functions: `reduce_<domain>(current: State, event: Any) -> State`.
  - Use case: `ProcessTelemetryReductionUseCase` implements `ReduceTelemetryEventPort`, orchestrating reader/writer ports and dispatching to domain reducers.

---

## 4. Decision Outcome

**Chosen Option:** **Option 3: Pure Functional Domain Reducers with Hexagonal Use Case Orchestration**.

### 4.1 Component Architecture

```
[TelemetryIngressWorker] (Driven Runtime Adapter)
       │
       ▼ calls ReduceTelemetryEventPort.reduce(event, archetype)
[ProcessTelemetryReductionUseCase] (Core Use Case)
       │
       ├─ If archetype == PASSIVE: return (Fast-Path Skip)
       │
       ├─ Reads current state from DomainStateReaderPort
       ├─ Dispatches to pure Domain Reducers:
       │    ├── reduce_location(current_loc, event)
       │    ├── reduce_vessel(current_vessel, event)
       │    ├── reduce_flight(current_flight, event)
       │    ├── reduce_cargo(current_cargo, event)
       │    ├── reduce_commander(current_cmdr, event)
       │    ├── reduce_station(current_station, event)
       │    ├── reduce_carrier(current_carrier, event)
       │    ├── reduce_exploration(current_explo, event)
       │    └── reduce_powerplay(current_pp, event)
       │
       ▼ Writes new state to DomainStateWriterPort (Atomic Pointer Swap)
```

### 4.2 Pure Domain Reducer Invariants

1. **Deterministic Function Signatures:**
   Every domain reducer follows the signature:
   `def reduce_<domain>(current: <Domain>State, event: Any) -> <Domain>State`
2. **Immutable Returns:**
   If the event is relevant to the domain, a new instance is returned using `dataclasses.replace()`. If the event is irrelevant to the domain, `current` is returned unchanged by identity (`return current`).
3. **Zero Mutation:**
   No attributes of `current` or `event` may be modified in-place.

---

## 5. Consequences

### Positive

* **100% Isolated Unit Testability:** Domain reducers can be tested with plain Python unit tests without instantiating stores, workers, threads, or loops.
* **Lockless & Concurrent:** Pure functions operate on thread-local arguments without shared state.
* **Clean Quality Gate Alignment:** Complies strictly with hexagonal architectural AST rules (`*UseCase` class, constructor DI, `DrivingPort` interface).

### Negative

* **Multiple Dispatch Checks:** Ingress events pass through domain reducer checks. Given Python's fast type/attribute checks and our fast-path skip for `PASSIVE` archetypes, overhead is negligible (< 1 µs per event).

---

## 6. References

* [ADR 0001: Core Domain State Architecture and Unified Ingress Lifecycle](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0001_core_domain_state_architecture_and_unified_ingress_lifecycle.md)
* [ADR 0002: Archetype Classification Subsystem and Registry](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0002_archetype_classification_subsystem_and_registry.md)
* [ADR 0005: TelemetryIngressWorker Runtime and Ingress Lifecycle](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0005_telemetry_ingress_worker_runtime_lifecycle.md)
* [ADR 0006: Core Domain State Model Taxonomy and Immutability Contracts](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0006_core_domain_state_model_taxonomy_and_immutability.md)
* [ADR 0007: In-Memory Domain State Store and Atomic Swap Architecture](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0007_in_memory_domain_state_store_and_atomic_swap.md)
