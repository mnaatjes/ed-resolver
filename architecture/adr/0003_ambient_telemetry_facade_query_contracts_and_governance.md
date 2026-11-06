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

* **Option 1: Monolithic Flat Facade.** Provide all snapshot getters and predicate methods directly on a single `AmbientTelemetryFacade` class (`facade.get_location()`, `facade.is_docked()`, `facade.get_vessel()`, `facade.is_on_foot()`). Rejected due to namespace pollution and method bloat as the game domain expands.
* **Option 2: Segregation by Query Pattern.** Separate namespaces based strictly on return type (`facade.snapshots.*` vs. `facade.predicates.*`). Rejected as an anti-pattern: callers think domain-first (spatial location, vessel, combat), not syntax-first.
* **Option 3: External Dependency Injection Container / Service Locator.** Expose state queries via a DI container (`container.resolve(ILocationService)`). Rejected because it leaks container mechanics into consumer code (`ed-connector`, scripts, copilots) where zero-overhead Python ergonomics are required.
* **Option 4: Domain-Grouped Sub-Facades with Root Convenience Aliasing (Selected).** Structure `AmbientTelemetryFacade` into cohesive domain sub-facades (`facade.location`, `facade.vessel`, `facade.flight`, `facade.status`), where each sub-facade co-locates its compound snapshot getter alongside its related atomic predicates. Surface the most ubiquitous macro-state helpers (`facade.is_on_foot()`, `facade.is_docked()`) as root-level convenience aliases.

---

## 4. Decision Outcome

**Chosen Option:** **Option 4: Domain-Grouped Sub-Facades with Root Convenience Aliasing**.

### 4.1 Facade Structural Architecture

The facade acts as a root coordinator delegating to cohesive, domain-bounded sub-facades while surfacing high-frequency convenience aliases:

```
                             CALLER QUERY
                                  │
         ┌────────────────────────┼────────────────────────┐
         │ (Domain Sub-Facade)    │ (Domain Sub-Facade)    │ (Root Convenience Alias)
         ▼                        ▼                        ▼
   facade.location          facade.vessel            facade.is_on_foot()
         │                        │                        │
   ┌─────┴───────────────┐  ┌─────┴───────────────┐        │ (direct alias)
   ▼                     ▼  ▼                     ▼        ▼
.snapshot()  .is_docked()  .snapshot()  .is_on_foot() ────►┘
   │                     │  │                     │
   └──────────┬──────────┘  └──────────┬──────────┘
              ▼                        ▼
   +─────────────────────────────────────────────────────────────+
   |                  INTERNAL STATE STORE                       |
   |  - _location: LocationSnapshot (frozen, immutable)          |
   |  - _vessel: VesselSnapshot (frozen, immutable)              |
   |  - _flight: FlightModeSnapshot (frozen, immutable)          |
   +─────────────────────────────────────────────────────────────+
```

### 4.2 Non-Divergent Domain Sub-Facades

To guarantee state consistency, each domain sub-facade holds a reference to the atomic `StateStore` and evaluates its predicates strictly as 1-line projections over the active frozen snapshot:

```python
class LocationSubFacade:
    """Domain sub-facade for spatial coordinates, docking, and celestial context."""

    def __init__(self, state_store: StateStore) -> None:
        self._state_store = state_store

    def snapshot(self) -> LocationSnapshot | None:
        """Return the current atomic location snapshot."""
        return self._state_store.get_location()

    def is_docked(self) -> bool:
        """Predicate: Is commander docked at a station, outpost, or carrier."""
        loc = self.snapshot()
        return loc.docked if loc is not None else False

    def in_supercruise(self) -> bool:
        """Predicate: Is commander in supercruise flight."""
        loc = self.snapshot()
        return loc.in_supercruise if loc is not None else False


class VesselSubFacade:
    """Domain sub-facade for commander vessel, loadout, suit, and SRV state."""

    def __init__(self, state_store: StateStore) -> None:
        self._state_store = state_store

    def snapshot(self) -> VesselSnapshot | None:
        """Return the current atomic vessel snapshot."""
        return self._state_store.get_vessel()

    def is_on_foot(self) -> bool:
        """Predicate: Is commander disembarked on foot (Odyssey suit)."""
        vessel = self.snapshot()
        return vessel.is_on_foot if vessel is not None else False

    def is_in_srv(self) -> bool:
        """Predicate: Is commander operating a surface reconnaissance vehicle."""
        vessel = self.snapshot()
        return vessel.is_in_srv if vessel is not None else False


class AmbientTelemetryFacade:
    """Root driving facade exposing domain sub-facades and root convenience aliases."""

    def __init__(self, state_store: StateStore, ingress_worker: TelemetryIngressWorker) -> None:
        self._state_store = state_store
        self._ingress_worker = ingress_worker

        # Domain Sub-Facades
        self.location = LocationSubFacade(state_store)
        self.vessel = VesselSubFacade(state_store)
        self.flight = FlightModeSubFacade(state_store)

    # Lifecycle delegation
    async def start(self) -> None:
        await self._ingress_worker.start()

    async def stop(self) -> None:
        await self._ingress_worker.stop()

    # Root Convenience Aliases (Ubiquitous Macro-Context Predicates)
    def is_on_foot(self) -> bool:
        return self.vessel.is_on_foot()

    def is_docked(self) -> bool:
        return self.location.is_docked()
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
| PHASE 1: SYSTEMATIC INTROSPECTION & CONSENSUS MATRICES (YAML Plane)         |
|                                                                             |
| 1. Execute `scripts/inspect_ed_models_taxonomy.py`:                         |
|    - Inspects released `ed-models` package (`ed-models==v0.2.1`).           |
|    - Systematically crawls all 12 domain categories and status models.      |
|    - Discovers 100% of concrete event classes and typed field attributes.   |
|    - Validated in `tests/scripts/test_inspect_ed_models_taxonomy.py`.       |
|                                                                             |
| 2. Author and review version-pinned governance YAML matrices in             |
|    `architecture/designs/matrix/`:                                          |
|    - `architecture/designs/matrix/facade_compound_snapshots_v<version>.yaml` |
|    - `architecture/designs/matrix/facade_atomic_predicates_v<version>.yaml`  |
|    - Validated by pre-commit `check-yaml` and Pydantic schema models.       |
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

Under this decision, **no code implementation or dataclass generation may begin until both Phase 1 YAML matrices are authored, reviewed, and approved**.

### 4.5 Deterministic Domain Crawling & Generation Script

To guarantee zero omission of `ed-models` events and properties:
* The inspection script `scripts/inspect_ed_models_taxonomy.py` imports the officially released `ed-models` library dependency (pinned in `pyproject.toml` via `git+https://github.com/mnaatjes/ed-models.git@v0.2.1`), never relying on uncommitted local paths.
* It systematically visits all module paths under `ed_models.core.domain.events` (`travel`, `station`, `trade`, `startup`, `odyssey`, `carrier`, `combat`, `exploration`, `powerplay`, `squadrons`, `other`) and `ed_models.core.domain.status`.
* It extracts each class name, module hierarchy, and dataclass field annotations into structured dictionary output, ensuring full coverage.
* The script itself is unit-tested under `tests/scripts/test_inspect_ed_models_taxonomy.py` prior to operational execution.

---

## 5. Consequences

### Positive
* **Ergonomic Clarity:** Callers have clean, single-line access to major game context predicates (`if facade.is_on_foot(): ...`) without verbose unpacking.
* **Deterministic Non-Divergence:** Because predicates project directly from compound snapshots, there is zero possibility of torn reads or conflicting answers between getters and booleans.
* **Bound API Surface:** The qualification criteria in Section 4.3 prevent arbitrary method bloat across the facade.
* **Schema Validation & Tooling Ergonomics:** Storing matrices as structured YAML enables automated validation (`check-yaml`, Pydantic models) and seamless programmatic ingestion without fragile markdown table scraping.
* **Zero Omission Guarantee:** Systematic package crawling against released `ed-models` ensures all upstream domains are accounted for in the generated YAML matrix.
* **Auditability & Traceability:** YAML matrices provide an unambiguous, version-controlled ledger of all supported query properties and their provenance.

### Negative / Trade-offs
* Requires authoring and maintaining two formalized YAML consensus matrices before implementation can begin.
* Callers needing niche or minor flags (e.g. night vision) must query the compound snapshot rather than using a dedicated facade predicate.

---

## 6. Validation and Next Steps

1. Update the Master Risk Register (`architecture/risk/risk-list.md`) to capture potential predicate divergence risks.
2. Update the Use-Case catalog (`architecture/use-cases/`) to reflect predicate queries.
3. Implement and test the taxonomy inspection script:
   * Test suite: `tests/scripts/test_inspect_ed_models_taxonomy.py`
   * Tool: `scripts/inspect_ed_models_taxonomy.py`
4. Author Phase 1 Consensus Matrices under `architecture/designs/matrix/`:
   * `architecture/designs/matrix/facade_compound_snapshots_v1.0.0.yaml`
   * `architecture/designs/matrix/facade_atomic_predicates_v1.0.0.yaml`
5. Implement `AmbientTelemetryFacade` and snapshot models in `src/ed_resolver/` once matrices are approved.
