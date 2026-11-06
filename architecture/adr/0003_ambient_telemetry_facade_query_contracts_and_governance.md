---
title: "ADR 0003: Ambient Telemetry Facade Query Contracts and Architectural Matrix Governance"
tags: ["adr", "ed-resolver", "architecture", "facade", "dto", "predicates", "snapshots", "hexagonal"]
created_at: "2026-11-06"
last_updated_at: "2026-11-06"
---

# ADR 0003: Ambient Telemetry Facade Query Contracts and Architectural Matrix Governance

* **Status:** Proposed
* **Date:** 2026-11-06
* **Deciders:** Michael Naatjes, Antigravity Agent
* **Consulted:** [ADR 0001](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0001_core_domain_state_architecture_and_unified_ingress_lifecycle.md), [ADR 0002](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0002_archetype_classification_subsystem_and_registry.md)

---

## 1. Context and Problem Statement

`AmbientTelemetryFacade` (established in ADR 0001) serves as the primary driving adapter for in-process library consumers of `ed-resolver` (such as `ed-connector`, TUI visualizers, copilots, and integration smoke tests).

Consumers exhibit two distinct operational querying patterns:
1. **Compound Snapshot Pattern:** Rich consumers (e.g., navigation copilots, EDDN contract accumulators, and dashboard overlays) require atomic, multi-property state representations (`LocationSnapshot`, `VesselSnapshot`, `FlightModeSnapshot`) frozen at a specific instant in time to prevent "torn read" state skew across separate getter calls.
2. **Atomic Predicate Pattern:** Reactive event triggers, guard clauses, and simple UI indicators require instantaneous boolean evaluations (e.g., `is_on_foot()`, `is_docked()`, `in_supercruise()`) without having to inspect, unpack, or null-check complex composite dataclasses.

Uncontrolled expansion of both patterns poses significant architectural risks:
* **Facade Bloat & Method Explosion:** Emitting ad-hoc getter or boolean methods for dozens of game variables leads to unmaintainable API sprawl.
* **Semantic State Drift:** If atomic predicates calculate their answers independently of compound snapshots, divergent answers may be returned during concurrent state transitions.
* **Unregulated Domain Contracts:** Without an explicit, pre-negotiated consensus matrix, developers may arbitrarily introduce conflicting DTO shapes or duplicate boolean queries.

How should `ed-resolver` structure the `AmbientTelemetryFacade` query API to support both querying patterns while guaranteeing absolute consistency and establishing a formalized architectural consensus process before implementation?

---

## 2. Decision Drivers

* **Ergonomic Flexibility (Dual Query Modalities):** The facade must natively support both rich compound snapshots and ergonomic atomic predicates to eliminate caller boilerplate.
* **Zero Semantic Drift (Non-Divergent Projection):** Every atomic predicate method must strictly project its answer from the exact same underlying frozen snapshot instance queried by the compound methods.
* **API Surface Boundary Governance:** A clear criterion must demarcate which operational states qualify for dedicated top-level facade methods versus requiring property inspection on snapshots.
* **Formal Consensus Before Code Generation:** All proposed compound snapshots, property fields, and atomic predicates must be codified and agreed upon in version-pinned Markdown matrices under `architecture/designs/` before any code generation or implementation begins.
* **Sub-Microsecond $O(1)$ Non-Blocking Execution:** All queries must execute synchronously in sub-microsecond time via pointer reads over immutable frozen dataclasses without locking delays.

---

## 3. Considered Options

* **Option 1: Compound Snapshots Only.** Provide only compound dataclass getters (`get_location()`, `get_vessel()`). All boolean checks must be performed by callers (e.g. `facade.get_vessel().is_on_foot if facade.get_vessel() else False`). Rejected due to excessive boilerplate and null-checking repetition across downstream callers.
* **Option 2: Flat Atomic Predicates and Getters Only.** Provide individual methods for every scalar property and flag (`get_system_name()`, `is_docked()`, `is_on_foot()`, `get_hull_health()`). Rejected due to massive facade method bloat (50+ methods) and severe risk of torn reads across rapid successive calls.
* **Option 3: Hybrid Dual-Pattern Facade Governed by Architectural Consensus Matrices (Selected).** Implement both patterns in `AmbientTelemetryFacade`, enforcing that all atomic predicates are non-divergent 1-line projections over canonical frozen snapshots. Require all compound DTO schemas and approved predicates to be cataloged in versioned Markdown consensus matrices under `architecture/designs/` prior to implementation.

---

## 4. Decision Outcome

**Chosen Option:** **Option 3: Hybrid Dual-Pattern Facade Governed by Architectural Consensus Matrices**.

### 4.1 Facade Structural Architecture

The facade acts as a synchronous, ergonomics-first projection layer over the internal `StateStore`:

```
                             CALLER QUERY
                                  │
         ┌────────────────────────┴────────────────────────┐
         │ (Compound Snapshot)                             │ (Atomic Predicate)
         ▼                                                 ▼
   facade.get_location()                            facade.is_docked()
         │                                                 │
         │ (atomic read)                                   │ (reads underlying snapshot)
         ▼                                                 ▼
   +─────────────────────────────────────────────────────────────+
   |                  INTERNAL STATE STORE                       |
   |  - _location: LocationSnapshot (frozen, immutable)          |
   |  - _vessel: VesselSnapshot (frozen, immutable)              |
   |  - _flight: FlightModeSnapshot (frozen, immutable)          |
   +─────────────────────────────────────────────────────────────+
         │                                                 │
         ▼                                                 ▼
   returns LocationSnapshot | None                   returns bool (snapshot.docked)
```

### 4.2 Non-Divergent Projection Guarantee

To ensure state consistency, atomic predicates are strictly forbidden from maintaining independent state or consulting raw bitmasks directly. They must project directly from the primary snapshot:

```python
class AmbientTelemetryFacade:
    """Synchronous driving facade exposing compound snapshots and projected predicates."""

    def __init__(self, state_store: StateStore, ingress_worker: TelemetryIngressWorker) -> None:
        self._state_store = state_store
        self._ingress_worker = ingress_worker

    # 1. Compound Snapshot Queries (Canonical Truth)
    def get_location(self) -> LocationSnapshot | None:
        return self._state_store.get_location()

    def get_vessel(self) -> VesselSnapshot | None:
        return self._state_store.get_vessel()

    def get_flight_mode(self) -> FlightModeSnapshot | None:
        return self._state_store.get_flight_mode()

    # 2. Atomic Predicates (Projected Convenience Helpers)
    def is_docked(self) -> bool:
        loc = self.get_location()
        return loc.docked if loc is not None else False

    def is_on_foot(self) -> bool:
        vessel = self.get_vessel()
        return vessel.is_on_foot if vessel is not None else False

    def in_supercruise(self) -> bool:
        flight = self.get_flight_mode()
        return flight.in_supercruise if flight is not None else False
```

### 4.3 Qualification Criteria for Atomic Predicates

To prevent API bloat, a state property qualifies as a dedicated top-level facade predicate (`is_*()`, `has_*()`, `can_*()`) **only if** it satisfies at least one of the following criteria:
1. **Primary Operational Context Shift:** Represents a macro-level alteration in commander presence or physical environment (`is_on_foot()`, `is_docked()`, `in_supercruise()`, `is_in_srv()`).
2. **Critical Behavioral Guard:** Evaluates an operational boundary condition required by downstream dispatchers or copilots (`is_alive()`, `is_hardpoints_deployed()`).

All fine-grained status indicators (such as cargo scoop, landing gear, night vision, lights, FA off) remain accessible as typed properties on the respective compound snapshot (e.g. `facade.get_flight_mode().landing_gear_down`).

### 4.4 Two-Phase Governance Process: Consensus Matrices Before Implementation

In alignment with the methodology established in ADR 0002, the implementation of facade query methods is decoupled into two strictly ordered phases:

```
+─────────────────────────────────────────────────────────────────────────────+
| PHASE 1: ARCHITECTURAL CONSENSUS MATRICES (Markdown Specification)          |
|                                                                             |
| Author and review two version-pinned governance matrices in                 |
| `architecture/designs/`:                                                    |
|                                                                             |
| 1. `architecture/designs/facade_compound_snapshots_matrix_v<version>.md`     |
|    - Defines every compound snapshot DTO (name, fields, types, sources).    |
|                                                                             |
| 2. `architecture/designs/facade_atomic_predicates_matrix_v<version>.md`      |
|    - Defines every top-level boolean helper, its projected snapshot, and    |
|      its fallback evaluation when unseeded.                                 |
+─────────────────────────────────────────────────────────────────────────────+
                                       │
                                       ▼ Architectural Approval (Review Gate)
+─────────────────────────────────────────────────────────────────────────────+
| PHASE 2: CODE IMPLEMENTATION & GENERATION                                   |
|                                                                             |
| - Implement frozen snapshot dataclasses in `src/ed_resolver/core/domain/`.  |
| - Author `AmbientTelemetryFacade` methods in `src/ed_resolver/facade.py`.   |
| - Validate complete matrix parity via Archon and unit test suites.          |
+─────────────────────────────────────────────────────────────────────────────+
```

Under this decision, **no code implementation or dataclass generation may begin until both Phase 1 Markdown matrices are authored, reviewed, and approved**.

---

## 5. Consequences

### Positive
* **Ergonomic Clarity:** Callers have clean, single-line access to major game context predicates (`if facade.is_on_foot(): ...`) without verbose unpacking.
* **Deterministic Non-Divergence:** Because predicates project directly from compound snapshots, there is zero possibility of torn reads or conflicting answers between getters and booleans.
* **Bound API Surface:** The qualification criteria in Section 4.3 prevent arbitrary method bloat across the facade.
* **Auditability & Traceability:** Markdown matrices provide an unambiguous, human-readable ledger of all supported query properties and their provenance.

### Negative / Trade-offs
* Requires authoring and maintaining two formalized Markdown consensus matrices before implementation can begin.
* Callers needing niche or minor flags (e.g. night vision) must query the compound snapshot rather than using a dedicated facade predicate.

---

## 6. Validation and Next Steps

1. Update the Master Risk Register (`architecture/risk/risk-list.md`) to capture potential predicate divergence risks.
2. Update the Use-Case catalog (`architecture/use-cases/`) to reflect predicate queries.
3. Author Phase 1 Consensus Matrices under `architecture/designs/`:
   * `architecture/designs/facade_compound_snapshots_matrix_v1.0.0.md`
   * `architecture/designs/facade_atomic_predicates_matrix_v1.0.0.md`
4. Implement `AmbientTelemetryFacade` and snapshot models in `src/ed_resolver/` once matrices are approved.
