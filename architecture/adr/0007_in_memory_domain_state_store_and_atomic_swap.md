---
title: "ADR 0007: In-Memory Domain State Store and Atomic Swap Architecture"
tags: ["adr", "ed-resolver", "architecture", "state-store", "concurrency", "hexagonal"]
created_at: "2026-11-08"
last_updated_at: "2026-11-08"
---

# ADR 0007: In-Memory Domain State Store and Atomic Swap Architecture

* **Status:** Accepted
* **Date:** 2026-11-08
* **Deciders:** Michael Naatjes, Antigravity Agent
* **Consulted:** [ADR 0001](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0001_core_domain_state_architecture_and_unified_ingress_lifecycle.md), [ADR 0004](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0004_hexagonal_scope_boundary_contracts_and_quality_gates.md), [ADR 0006](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0006_core_domain_state_model_taxonomy_and_immutability.md)

---

## 1. Context and Problem Statement

`ed-resolver` aggregates asynchronous telemetry events and 1 Hz status ticks emitted by *Elite Dangerous* into 9 consolidated domain state models (`LocationState`, `VesselState`, `FlightState`, `CargoState`, `CommanderState`, `StationState`, `CarrierState`, `ExplorationState`, `PowerplayState`).

These domain projections must be consumed concurrently by external consumers (UI render loops, web facades, audio/TTS engines, MCP tools) while being continuously updated by background telemetry reduction pipelines.

Persisting these high-frequency domain projections in an external database (SQLite, Redis) introduces serialization latency, process overhead, and disk contention. Furthermore, traditional thread locking (mutexes) risks lock contention and priority inversions under high-frequency 1 Hz ticker ingress.

How should `ed-resolver` store, isolate, and provide access to the 9 active domain state models to achieve nanosecond-scale read performance, zero I/O overhead, and deterministic thread safety?

---

## 2. Decision Drivers

* **Zero-I/O & Nanosecond Read Latency:** Query consumers (e.g., status overlays or ambient query facades) require instantaneous access to the latest domain state without disk or socket bottlenecks.
* **Torn-Read Prevention & Concurrency Safety:** Multiple threads reading state models simultaneously must never observe partially written fields or corrupted state structures.
* **Separation of Read and Write Capabilities (Interface Segregation):** Ingress reducers require mutation authority, while query facades and external callers must only have read authority.
* **Cold-Start Determinism:** When the application starts and before the first game journal event is processed, every domain projection must provide valid, safe initial default representations.
* **Hexagonal Decoupling:** Port contracts must reside inside `src/ed_resolver/core/ports/driven/` with zero framework dependencies, while the concrete memory store resides under `src/ed_resolver/adapters/driven/state_store/`.

---

## 3. Considered Options

* **Option 1: Embedded Relational Database (SQLite in-memory or WAL disk).** Provides transactional persistence and SQL querying, but introduces serialization/deserialization overhead and lock contention on 1 Hz ticker updates.
* **Option 2: Mutex-Guarded Mutable Container.** Uses threading locks around a single shared dictionary of mutable objects. Vulnerable to lock contention, deadlocks, and torn reads if any caller retains an uncopied object reference.
* **Option 3: Pure In-Memory Container with Atomic Pointer Swapping (Selected).** Stores frozen dataclasses in an in-memory container. Updates derive new frozen dataclasses via `dataclasses.replace()` and replace the container pointer in a single atomic Python instruction.

---

## 4. Decision Outcome

**Chosen Option:** **Option 3: Pure In-Memory Container with Atomic Pointer Swapping**.

### 4.1 Port Segregation: Reader vs. Writer Contracts

To enforce the Principle of Least Privilege and Interface Segregation, two distinct driven port protocols are defined in `core/ports/driven/state_store.py`:

1. **`DomainStateReaderPort`:**
   Exposes read-only accessors for the 9 domain projections:
   * `get_location() -> LocationState`
   * `get_vessel() -> VesselState`
   * `get_flight() -> FlightState`
   * `get_cargo() -> CargoState`
   * `get_commander() -> CommanderState`
   * `get_station() -> StationState`
   * `get_carrier() -> CarrierState`
   * `get_exploration() -> ExplorationState`
   * `get_powerplay() -> PowerplayState`

2. **`DomainStateWriterPort`:**
   Exposes state update methods used strictly by reduction pipelines:
   * `set_location(state: LocationState) -> None`
   * `set_vessel(state: VesselState) -> None`
   * `set_flight(state: FlightState) -> None`
   * `set_cargo(state: CargoState) -> None`
   * `set_commander(state: CommanderState) -> None`
   * `set_station(state: StationState) -> None`
   * `set_carrier(state: CarrierState) -> None`
   * `set_exploration(state: ExplorationState) -> None`
   * `set_powerplay(state: PowerplayState) -> None`

### 4.2 Atomic Pointer Exchange Mechanism

In Python (CPython), assigning an object reference to an instance attribute (`self._location = new_state`) is an atomic opcode execution (`STORE_FAST` / `STORE_ATTR`).

Because all `*State` models are strictly immutable (`@dataclass(frozen=True, slots=True)`):
* Any thread fetching `store.get_location()` receives an immutable snapshot pointer.
* The consumer can inspect this object indefinitely without fear that a concurrent reducer will mutate its fields underneath them.
* When a reducer updates state, it derives a new state instance and swaps the pointer. Subsequent calls to `get_location()` immediately receive the new instance without blocking existing readers.

### 4.3 Cold-Start Defaults

Upon initialization, `InMemoryDomainStateStore` instantiates each of the 9 domain models using their default initializers (`LocationState()`, `VesselState()`, etc.). Callers querying state during cold start receive valid, deterministic default models rather than `None` pointers.

---

## 5. Consequences

### Positive

* **Nanosecond Read Latency:** Accessing domain state is a direct memory pointer dereference (~10-20 nanoseconds).
* **Zero Locking Overhead:** Lockless concurrent reads and writes eliminate deadlock risks and thread contention.
* **Strict Hexagonal Boundaries:** Port protocols decouple application use cases from the underlying storage mechanism.
* **No Torn Reads:** Immutability guarantees that consumers always observe internally consistent state projections.

### Negative

* **Non-Persistent In-Memory Lifetime:** If the application process terminates, domain state is recreated from the latest journal logs upon restart. (Persistence across sessions, if needed, belongs to an explicit persistence adapter, not the active runtime state store).

---

## 6. References

* [ADR 0001: Core Domain State Architecture and Unified Ingress Lifecycle](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0001_core_domain_state_architecture_and_unified_ingress_lifecycle.md)
* [ADR 0004: Hexagonal Scope Boundary Contracts and Automated Quality Gate Enforcement](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0004_hexagonal_scope_boundary_contracts_and_quality_gates.md)
* [ADR 0006: Core Domain State Model Taxonomy and Immutability Contracts](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0006_core_domain_state_model_taxonomy_and_immutability.md)
