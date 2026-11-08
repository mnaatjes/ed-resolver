---
title: "SDD 0007: In-Memory Domain State Store Subsystem"
tags: ["sdd", "architecture", "state-store", "concurrency", "hexagonal", "ed-resolver"]
created_at: "2026-11-08"
last_updated_at: "2026-11-08"
---

# SDD 0007: In-Memory Domain State Store Subsystem

* **Status:** Proposed
* **Governing ADRs:** [ADR 0001](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0001_core_domain_state_architecture_and_unified_ingress_lifecycle.md), [ADR 0004](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0004_hexagonal_scope_boundary_contracts_and_quality_gates.md), [ADR 0006](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0006_core_domain_state_model_taxonomy_and_immutability.md), [ADR 0007](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0007_in_memory_domain_state_store_and_atomic_swap.md)
* **Author:** Antigravity Pair Programmer
* **Version:** 1.0.0
* **Target Package:** `ed-resolver`

---

## 1. Introduction & Context

### 1.1 Purpose
This Software Design Document specifies the driven port protocols and concrete in-memory adapter implementation for `DomainStateStore` in `ed-resolver`. It defines how the 9 immutable domain state models (`LocationState`, `VesselState`, `FlightState`, `CargoState`, `CommanderState`, `StationState`, `CarrierState`, `ExplorationState`, `PowerplayState`) are held in process memory, queried by external facades, and updated atomically by telemetry reducers.

### 1.2 System Boundary & Scope
The implementation is strictly confined to:
* Port contracts: `src/ed_resolver/core/ports/driven/state_store.py` (`DomainStateReaderPort`, `DomainStateWriterPort`)
* Port exports: `src/ed_resolver/core/ports/driven/__init__.py`
* Adapter implementation: `src/ed_resolver/adapters/driven/state_store/in_memory.py` (`InMemoryDomainStateStore`)
* Adapter exports: `src/ed_resolver/adapters/driven/state_store/__init__.py`
* Unit tests: `tests/adapters/driven/test_in_memory_state_store.py`

---

## 2. Port Contracts Specification (`src/ed_resolver/core/ports/driven/state_store.py`)

In compliance with hexagonal architecture, driven ports are declared as `typing.Protocol` with runtime checkability:

```python
from typing import Protocol, runtime_checkable

from ed_resolver.core.domain import (
    CargoState,
    CarrierState,
    CommanderState,
    ExplorationState,
    FlightState,
    LocationState,
    PowerplayState,
    StationState,
    VesselState,
)


@runtime_checkable
class DomainStateReaderPort(Protocol):
    """Read-only access to the 9 active domain state projections."""

    def get_location(self) -> LocationState: ...
    def get_vessel(self) -> VesselState: ...
    def get_flight(self) -> FlightState: ...
    def get_cargo(self) -> CargoState: ...
    def get_commander(self) -> CommanderState: ...
    def get_station(self) -> StationState: ...
    def get_carrier(self) -> CarrierState: ...
    def get_exploration(self) -> ExplorationState: ...
    def get_powerplay(self) -> PowerplayState: ...


@runtime_checkable
class DomainStateWriterPort(Protocol):
    """Write/update access for telemetry event reducers."""

    def set_location(self, state: LocationState) -> None: ...
    def set_vessel(self, state: VesselState) -> None: ...
    def set_flight(self, state: FlightState) -> None: ...
    def set_cargo(self, state: CargoState) -> None: ...
    def set_commander(self, state: CommanderState) -> None: ...
    def set_station(self, state: StationState) -> None: ...
    def set_carrier(self, state: CarrierState) -> None: ...
    def set_exploration(self, state: ExplorationState) -> None: ...
    def set_powerplay(self, state: PowerplayState) -> None: ...
```

---

## 3. Driven Adapter Specification (`src/ed_resolver/adapters/driven/state_store/in_memory.py`)

The `InMemoryDomainStateStore` class implements both `DomainStateReaderPort` and `DomainStateWriterPort`:

```python
from ed_resolver.core.domain import (
    CargoState,
    CarrierState,
    CommanderState,
    ExplorationState,
    FlightState,
    LocationState,
    PowerplayState,
    StationState,
    VesselState,
)
from ed_resolver.core.ports.driven.state_store import (
    DomainStateReaderPort,
    DomainStateWriterPort,
)


class InMemoryDomainStateStore(DomainStateReaderPort, DomainStateWriterPort):
    """Thread-safe, lockless in-memory domain state store using atomic pointer swapping."""

    def __init__(self) -> None:
        self._location: LocationState = LocationState()
        self._vessel: VesselState = VesselState()
        self._flight: FlightState = FlightState()
        self._cargo: CargoState = CargoState()
        self._commander: CommanderState = CommanderState()
        self._station: StationState = StationState()
        self._carrier: CarrierState = CarrierState()
        self._exploration: ExplorationState = ExplorationState()
        self._powerplay: PowerplayState = PowerplayState()

    # --- Reader Port Accessors ---
    def get_location(self) -> LocationState:
        return self._location

    def get_vessel(self) -> VesselState:
        return self._vessel

    def get_flight(self) -> FlightState:
        return self._flight

    def get_cargo(self) -> CargoState:
        return self._cargo

    def get_commander(self) -> CommanderState:
        return self._commander

    def get_station(self) -> StationState:
        return self._station

    def get_carrier(self) -> CarrierState:
        return self._carrier

    def get_exploration(self) -> ExplorationState:
        return self._exploration

    def get_powerplay(self) -> PowerplayState:
        return self._powerplay

    # --- Writer Port Mutators ---
    def set_location(self, state: LocationState) -> None:
        self._location = state

    def set_vessel(self, state: VesselState) -> None:
        self._vessel = state

    def set_flight(self, state: FlightState) -> None:
        self._flight = state

    def set_cargo(self, state: CargoState) -> None:
        self._cargo = state

    def set_commander(self, state: CommanderState) -> None:
        self._commander = state

    def set_station(self, state: StationState) -> None:
        self._station = state

    def set_carrier(self, state: CarrierState) -> None:
        self._carrier = state

    def set_exploration(self, state: ExplorationState) -> None:
        self._exploration = state

    def set_powerplay(self, state: PowerplayState) -> None:
        self._powerplay = state
```

---

## 4. Verification & Testing Strategy

1. **Protocol Compliance:**
   * Assert `isinstance(store, DomainStateReaderPort)` is `True`.
   * Assert `isinstance(store, DomainStateWriterPort)` is `True`.
2. **Cold-Start Integrity:**
   * Verify all 9 accessors return non-null, valid initial state models with default parameters upon instant construction.
3. **Atomic Swap & Mutation Isolation:**
   * Read `loc1 = store.get_location()`.
   * Update with `store.set_location(new_loc)`.
   * Verify `store.get_location() is new_loc`.
   * Verify `loc1` remains unchanged.
4. **Boundary Compliance (`tests/architecture/test_boundaries.py`):**
   * Port protocols inherit from `Protocol` or `Port` markers.
   * Core domain does not import driven ports or adapter implementations.
