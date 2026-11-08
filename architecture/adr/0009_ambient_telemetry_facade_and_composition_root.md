---
title: "ADR 0009: Ambient Telemetry Facade Implementation and Composition Root"
tags: ["adr", "ed-resolver", "architecture", "facade", "adapters", "composition-root", "hexagonal"]
created_at: "2026-11-08"
last_updated_at: "2026-11-08"
---

# ADR 0009: Ambient Telemetry Facade Implementation and Composition Root

* **Status:** Accepted
* **Date:** 2026-11-08
* **Deciders:** Michael Naatjes, Antigravity Agent
* **Consulted:** [ADR 0001](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0001_core_domain_state_architecture_and_unified_ingress_lifecycle.md), [ADR 0003](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0003_ambient_telemetry_facade_query_contracts_and_governance.md), [ADR 0005](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0005_telemetry_ingress_worker_runtime_lifecycle.md), [ADR 0006](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0006_core_domain_state_model_taxonomy_and_immutability.md), [ADR 0007](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0007_in_memory_domain_state_store_and_atomic_swap.md), [ADR 0008](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0008_domain_event_reduction_pipelines_and_dispatch.md)

---

## 1. Context and Problem Statement

`ed-resolver` provides rich domain state projection and continuous telemetry processing for *Elite Dangerous*. While previous architectural iterations established the ingress worker, classifier, domain state models, in-memory store, and reducers, external client applications (e.g. `ed-connector`, visual copilots, voice assistants, and smoke tests) require a unified, ergonomic, and thread-safe entry point.

ADR 0003 established the conceptual blueprint for `AmbientTelemetryFacade` with domain-grouped sub-facades and atomic convenience predicates. However:
1. The naming in ADR 0003 still referenced the older "Snapshot" nomenclature (`LocationSnapshot`, `VesselSnapshot`), which was superseded by ADR 0006 (`LocationState`, `VesselState`, etc.).
2. The concrete implementation of `AmbientTelemetryFacade` as a Level 4 driving adapter under `src/ed_resolver/adapters/driving/facade/` and its instantiation in the composition root (`create_resolver`) need to be formalized.

How should `ed-resolver` implement `AmbientTelemetryFacade` and wire its complete runtime pipeline within the composition root?

---

## 2. Decision Drivers

* **Taxonomic Alignment with ADR 0006:** All sub-facades expose `state()` or `get_state()` methods returning the 9 immutable `*State` models, replacing obsolete `*Snapshot` references.
* **Ergonomic Convenience & Predicate Consistency:** Ubiquitous macro-predicates (`is_docked()`, `is_on_foot()`, `in_supercruise()`, `is_wanted()`) must be non-divergent 1-line projections over the underlying state instances.
* **Full Ingress Lifecycle Supervision:** The facade manages worker lifecycle via async methods `start()` and `stop(timeout=...)` or async context manager `async with facade:`.
* **Zero Boilerplate Composition Root:** Provide a clean factory function `create_resolver(...)` in `src/ed_resolver/bootstrap/` or package root `ed_resolver` that wires all adapters, ports, and use cases out-of-the-box.

---

## 3. Decision Outcome

**Chosen Option:** **Level 4 Driving Adapter Architecture with Sub-Facades and Async Context Management**.

### 3.1 Sub-Facade Specifications Across 9 Domains

Each domain sub-facade takes a `DomainStateReaderPort` and provides state access and predicates:

1. **`LocationSubFacade`:**
   - `state() -> LocationState`
   - `is_docked() -> bool`
   - `in_supercruise() -> bool`
   - `on_surface() -> bool`
2. **`VesselSubFacade`:**
   - `state() -> VesselState`
   - `is_on_foot() -> bool`
   - `is_in_srv() -> bool`
3. **`FlightSubFacade`:**
   - `state() -> FlightState`
   - `landing_gear_down() -> bool`
   - `hardpoints_deployed() -> bool`
   - `flight_assist_off() -> bool`
   - `night_vision() -> bool`
4. **`CargoSubFacade`:**
   - `state() -> CargoState`
   - `count() -> int`
   - `has_item(item: str) -> bool`
5. **`CommanderSubFacade`:**
   - `state() -> CommanderState`
   - `is_wanted() -> bool`
6. **`StationSubFacade`:**
   - `state() -> StationState`
   - `has_market() -> bool`
   - `has_shipyard() -> bool`
   - `has_outfitting() -> bool`
7. **`CarrierSubFacade`:**
   - `state() -> CarrierState`
   - `has_pending_jump() -> bool`
8. **`ExplorationSubFacade`:**
   - `state() -> ExplorationState`
   - `all_bodies_found() -> bool`
9. **`PowerplaySubFacade`:**
   - `state() -> PowerplayState`
   - `is_pledged() -> bool`

### 3.2 Root Convenience Aliases on `AmbientTelemetryFacade`

* `facade.is_docked()` -> `facade.location.is_docked()`
* `facade.is_on_foot()` -> `facade.vessel.is_on_foot()`
* `facade.in_supercruise()` -> `facade.location.in_supercruise()`
* `facade.is_in_srv()` -> `facade.vessel.is_in_srv()`
* `facade.is_wanted()` -> `facade.commander.is_wanted()`

### 3.3 Factory Function: `create_resolver`

A composition factory in `src/ed_resolver/bootstrap/factory.py` (and exported at package root):
```python
def create_resolver(
    ingress_port: TelemetryIngressPort | None = None,
    state_store: InMemoryDomainStateStore | None = None,
) -> AmbientTelemetryFacade: ...
```

---

## 4. Consequences

### Positive
* Instant access to telemetry truth for client applications.
* Strict hexagonal compliance: `AmbientTelemetryFacade` depends solely on `DomainStateReaderPort` and `TelemetryIngressWorker`.
* Ergonomic async context management (`async with create_resolver(...) as facade:`).

### Negative
* Additional delegation layer. With Python's fast attribute access, method delegation takes under 50 nanoseconds.

---

## 5. References
* [ADR 0001: Core Domain State Architecture and Unified Ingress Lifecycle](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0001_core_domain_state_architecture_and_unified_ingress_lifecycle.md)
* [ADR 0003: Ambient Telemetry Facade Query Contracts and Architectural Matrix Governance](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0003_ambient_telemetry_facade_query_contracts_and_governance.md)
* [ADR 0006: Core Domain State Model Taxonomy and Immutability Contracts](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0006_core_domain_state_model_taxonomy_and_immutability.md)
* [ADR 0007: In-Memory Domain State Store and Atomic Swap Architecture](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0007_in_memory_domain_state_store_and_atomic_swap.md)
* [ADR 0008: Domain Event Reduction Pipelines and Dispatch Architecture](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0008_domain_event_reduction_pipelines_and_dispatch.md)
