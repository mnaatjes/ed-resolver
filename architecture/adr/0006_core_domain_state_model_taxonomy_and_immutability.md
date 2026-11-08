---
title: "ADR 0006: Core Domain State Model Taxonomy and Immutability Contracts"
tags: ["adr", "ed-resolver", "architecture", "domain", "state", "immutability", "hexagonal"]
created_at: "2026-11-08"
last_updated_at: "2026-11-08"
---

# ADR 0006: Core Domain State Model Taxonomy and Immutability Contracts

* **Status:** Accepted
* **Date:** 2026-11-08
* **Deciders:** Michael Naatjes, Antigravity Agent
* **Consulted:** [ADR 0001](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0001_core_domain_state_architecture_and_unified_ingress_lifecycle.md), [ADR 0002](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0002_archetype_classification_subsystem_and_registry.md), [ADR 0003](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0003_ambient_telemetry_facade_query_contracts_and_governance.md), [ADR 0004](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0004_hexagonal_scope_boundary_contracts_and_quality_gates.md), [ADR 0005](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0005_telemetry_ingress_worker_runtime_lifecycle.md)

---

## 1. Context and Problem Statement

Frontier Developments' *Elite Dangerous* telemetry client emits fragmented, asynchronous telemetry streams across two distinct channels:
1. Continuous 1 Hz status ticks (`Status.json`) carrying integer bitfields and scalar measurements.
2. Chronological event logs (`Journal.*.log`) and auxiliary disk dump files (`Market.json`, `Cargo.json`, `Shipyard.json`, `Outfitting.json`, `NavRoute.json`, `ModulesInfo.json`, `Backpack.json`).

In previous architectural discussions, the synthesized domain projections representing game truth were colloquially referred to as "Domain Snapshots" (e.g. `LocationSnapshot`, `VesselSnapshot`, `PowerplaySnapshot`).

However, this nomenclature creates acute cognitive dissonance and structural ambiguity across the codebase:
* **Frontier Raw Files:** The auxiliary files generated on the local disk by the game engine are already formally classified as "Snapshot Files" (`Cargo.json`, `Market.json`, etc.).
* **Domain Projections:** Calling synthesized in-memory models "Snapshots" confuses raw input disk files with consolidated business domain projections.

Furthermore, these domain models serve as the single source of truth across asynchronous multi-threaded runtimes. They must satisfy rigorous concurrency safety, immutability, and boundary isolation guarantees.

How should `ed-resolver` formally name, structure, and govern its core domain models across the 9 hexagonal domains to eliminate terminology collisions and guarantee deterministic, thread-safe access?

---

## 2. Decision Drivers

* **Taxonomic Disambiguation:** Strictly reserve the term "Snapshot" for raw Frontier filesystem artifacts (`Cargo.json`, etc.) and establish a distinct, industry-standard name for synthesized domain projections.
* **Deterministic Concurrency & Thread Safety:** Domain models are read concurrently by UI threads, TUI loops, or HTTP API controllers while being mutated asynchronously by `TelemetryIngressWorker` reducers. Models must eliminate "torn reads" without heavyweight locking.
* **Immutability & Integrity:** Once instantiated, a domain projection must be completely immutable (`@dataclass(frozen=True, slots=True)`). No caller or reducer may tamper with fields in-place.
* **Cold-Start Resilience:** Models must support explicit, safe defaults or nullable fields when initial game logs have not yet seeded a particular attribute.
* **Hexagonal Decoupling:** Core domain state models must reside strictly within `src/ed_resolver/core/domain/<domain>/` with zero dependencies on transport, adapters, or external libraries.

---

## 3. Considered Options

* **Option 1: Retain "Snapshot" Nomenclature (`LocationSnapshot`, `PowerplaySnapshot`).** Rejected due to persistent naming collisions with Frontier's raw disk files (`Cargo.json`, etc.).
* **Option 2: "Context" Nomenclature (`LocationContext`, `PowerplayContext`).** Highlights composite views, but "Context" is often overloaded with execution contexts, request contexts, or logging contexts.
* **Option 3: "Truth" Nomenclature (`LocationTruth`, `PowerplayTruth`).** Emphasizes factual consensus, but is non-standard in Python and enterprise domain modeling.
* **Option 4: "State" Nomenclature (Selected - `LocationState`, `PowerplayState`).** Clean, industry-standard, and universally understood. Represents the consolidated point-in-time domain entity state.

---

## 4. Decision Outcome

**Chosen Option:** **Option 4: "State" Nomenclature**.

### 4.1 Domain State Model Taxonomy Across the 9 Domains

The synthesized domain models are formally designated as `*State` entities and organized across the established hexagonal sub-packages:

| Hexagonal Sub-Package | Domain State Model | Primary Responsibility |
| :--- | :--- | :--- |
| `core/domain/location/` | **`LocationState`** | Star system, SystemAddress, coordinates (`StarPos`), celestial body, starport, docking status. |
| `core/domain/vessel/` | **`VesselState`** | Active ship name, ident, hull type, suit, SRV state, on-foot mode. |
| `core/domain/flight/` | **`FlightState`** | Continuous 1 Hz flags (gear, hardpoints, FA-off, night vision), fuel main & reservoir levels. |
| `core/domain/cargo/` | **`CargoState`** | Commodity inventory counts, item mappings, cargo capacity, vessel carrier mode. |
| `core/domain/commander/` | **`CommanderState`** | Commander name, FID, credits balance, loan status, bounty/fine legal standing. |
| `core/domain/station/` | **`StationState`** | Docked starport name, type, market ID, controlling faction, available station services. |
| `core/domain/carrier/` | **`CarrierState`** | Fleet carrier ID, callsign, balance, fuel capacity, pending jump target & countdown. |
| `core/domain/exploration/` | **`ExplorationState`** | System body count, FSS discovery scan progress, organic biological sampling counts. |
| `core/domain/powerplay/` | **`PowerplayState`** | Pledged galactic power, active merits, weekly votes, rank, pledge standing. |

---

### 4.2 Immutability and Atomic State Replacement

To guarantee zero torn reads and sub-nanosecond concurrent access:

1. **Frozen Slotted Dataclasses:**
   All state models are decorated with `@dataclass(frozen=True, slots=True)`:
   * `frozen=True` prevents in-place attribute reassignment (`state.merits = 10` raises `FrozenInstanceError`).
   * `slots=True` drastically reduces memory footprint and optimizes property attribute lookup speed.
2. **Immutable Composite Types:**
   Nested attributes must use immutable collections (e.g. `MappingProxyType`, `tuple`) rather than mutable lists or dictionaries:
   * Coordinates are stored as `tuple[float, float, float]`.
   * Cargo inventory mappings are stored as immutable `Mapping[str, int]`.
3. **Atomic Swap Pattern:**
   Reducers never mutate existing state objects. When processing an event (e.g. `CollectCargo`), the reducer derives a brand-new instance of `CargoState` using `dataclasses.replace()` and swaps the reference in `DomainStateStore` via a single atomic pointer exchange.

---

### 4.3 Null-Safe Cold-Start Strategy

In accordance with ADR 0001:
* Mandatory attributes that require discrete game seeding (e.g. `system_name`, `ship_name`, `power`) are explicitly typed as nullable (`str | None`), defaulting to `None` upon cold start.
* Quantitative counters and boolean predicates provide safe default initializers (e.g. `count: int = 0`, `is_docked: bool = False`, `merits: int = 0`).

---

## 5. Consequences

### Positive

* **Eliminated Ambiguity:** Clear boundary between Frontier's raw disk "Snapshot files" and `ed-resolver`'s synthesized "State models".
* **Thread-Safe by Design:** Readers can query state references from any thread or async task without acquiring locks.
* **Strict Hexagonal Alignment:** State models have zero external dependencies and reside purely within their respective domain ring.

### Negative

* **Allocation Overhead on Reductions:** High-frequency updates (e.g. 1 Hz fuel tick updates) instantiate a new `FlightState` dataclass each second. Given Python 3.13 slotted dataclass optimizations, this allocation overhead is negligible (< 100 ns).

---

## 6. References

* [ADR 0001: Core Domain State Architecture and Unified Ingress Lifecycle](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0001_core_domain_state_architecture_and_unified_ingress_lifecycle.md)
* [ADR 0002: Archetype Classification Subsystem and Registry](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0002_archetype_classification_subsystem_and_registry.md)
* [ADR 0003: Ambient Telemetry Facade Query Contracts and Architectural Matrix Governance](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0003_ambient_telemetry_facade_query_contracts_and_governance.md)
* [ADR 0004: Hexagonal Scope Boundary Contracts and Automated Quality Gate Enforcement](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0004_hexagonal_scope_boundary_contracts_and_quality_gates.md)
* [ADR 0005: TelemetryIngressWorker Runtime and Ingress Lifecycle](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0005_telemetry_ingress_worker_runtime_lifecycle.md)
* [Facade Compound Snapshots Consensus Matrix](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/designs/matrix/facade_compound_snapshots_v1.0.0.yaml)
