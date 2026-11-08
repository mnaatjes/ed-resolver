---
title: "SDD 0006: Core Domain State Models and Immutability Subsystem"
tags: ["sdd", "architecture", "domain", "state", "immutability", "hexagonal", "ed-resolver"]
created_at: "2026-11-08"
last_updated_at: "2026-11-08"
---

# SDD 0006: Core Domain State Models and Immutability Subsystem

* **Status:** Proposed
* **Governing ADRs:** [ADR 0001](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0001_core_domain_state_architecture_and_unified_ingress_lifecycle.md), [ADR 0002](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0002_archetype_classification_subsystem_and_registry.md), [ADR 0003](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0003_ambient_telemetry_facade_query_contracts_and_governance.md), [ADR 0004](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0004_hexagonal_scope_boundary_contracts_and_quality_gates.md), [ADR 0005](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0005_telemetry_ingress_worker_runtime_lifecycle.md), [ADR 0006](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0006_core_domain_state_model_taxonomy_and_immutability.md)
* **Author:** Antigravity Pair Programmer
* **Version:** 1.0.0
* **Target Package:** `ed-resolver`

---

## 1. Introduction & Context

### 1.1 Purpose
This Software Design Document specifies the concrete dataclass contracts, properties, nullability rules, and validation invariants for the 9 core domain state models in `ed-resolver`. It translates the approved compound snapshot matrix (`facade_compound_snapshots_v1.0.0.yaml`) into immutable, slotted Python dataclasses under the hexagonal `src/ed_resolver/core/domain/` sub-packages.

### 1.2 System Boundary & Scope
The implementation is strictly confined to:
* `src/ed_resolver/core/domain/location/models.py` (`LocationState`)
* `src/ed_resolver/core/domain/vessel/models.py` (`VesselState`)
* `src/ed_resolver/core/domain/flight/models.py` (`FlightState`)
* `src/ed_resolver/core/domain/cargo/models.py` (`CargoState`)
* `src/ed_resolver/core/domain/commander/models.py` (`CommanderState`)
* `src/ed_resolver/core/domain/station/models.py` (`StationState`)
* `src/ed_resolver/core/domain/carrier/models.py` (`CarrierState`)
* `src/ed_resolver/core/domain/exploration/models.py` (`ExplorationState`)
* `src/ed_resolver/core/domain/powerplay/models.py` (`PowerplayState`)
* Companion unit and immutability tests under `tests/core/domain/`.

---

## 2. Architectural Blueprint & Model Hierarchy

Each domain sub-package exposes its primary state entity as a frozen, slotted dataclass with a post-init validation guard enforcing type safety and domain bounds:

```
src/ed_resolver/core/domain/
├── location/models.py      --> LocationState
├── vessel/models.py        --> VesselState
├── flight/models.py        --> FlightState
├── cargo/models.py         --> CargoState
├── commander/models.py     --> CommanderState
├── station/models.py       --> StationState
├── carrier/models.py       --> CarrierState
├── exploration/models.py   --> ExplorationState
└── powerplay/models.py     --> PowerplayState
```

---

## 3. Concrete State Model Specifications

### 3.1 `LocationState` (`src/ed_resolver/core/domain/location/models.py`)

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LocationState:
    """Consolidated spatial position, star system, and docking truth."""

    system_name: str | None = None
    system_address: int | None = None
    star_pos: tuple[float, float, float] = (0.0, 0.0, 0.0)
    body_name: str | None = None
    body_id: int | None = None
    station_name: str | None = None
    station_type: str | None = None
    docked: bool = False
    in_supercruise: bool = False
    on_surface: bool = False

    def __post_init__(self) -> None:
        if len(self.star_pos) != 3:
            raise ValueError("star_pos must be a 3-dimensional coordinate tuple (x, y, z)")
```

### 3.2 `VesselState` (`src/ed_resolver/core/domain/vessel/models.py`)

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VesselState:
    """Current vessel, active loadout, suit, and SRV operational truth."""

    ship_name: str | None = None
    ship_ident: str | None = None
    ship_type: str | None = None
    hull_value: int | None = None
    modules_value: int | None = None
    is_on_foot: bool = False
    is_in_srv: bool = False

    def __post_init__(self) -> None:
        if self.is_on_foot and self.is_in_srv:
            raise ValueError("Commander cannot simultaneously be on foot and in an SRV.")
```

### 3.3 `FlightState` (`src/ed_resolver/core/domain/flight/models.py`)

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FlightState:
    """Continuous flight parameters, gear, hardpoints, and fuel measurements."""

    in_supercruise: bool = False
    landing_gear_down: bool = False
    hardpoints_deployed: bool = False
    flight_assist_off: bool = False
    night_vision: bool = False
    fuel_main: float | None = None
    fuel_reservoir: float | None = None

    def __post_init__(self) -> None:
        if self.fuel_main is not None and self.fuel_main < 0:
            raise ValueError("fuel_main cannot be negative.")
        if self.fuel_reservoir is not None and self.fuel_reservoir < 0:
            raise ValueError("fuel_reservoir cannot be negative.")
```

### 3.4 `CargoState` (`src/ed_resolver/core/domain/cargo/models.py`)

```python
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class CargoState:
    """Current commodity cargo inventory, material quantities, and capacity."""

    count: int = 0
    inventory: Mapping[str, int] = field(default_factory=dict)
    vessel_type: str | None = None

    def __post_init__(self) -> None:
        if self.count < 0:
            raise ValueError("Cargo count cannot be negative.")
        if not isinstance(self.inventory, MappingProxyType):
            object.__setattr__(self, "inventory", MappingProxyType(dict(self.inventory)))
```

### 3.5 `CommanderState` (`src/ed_resolver/core/domain/commander/models.py`)

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CommanderState:
    """Commander profile, credit balance, loan status, and criminal reputation."""

    name: str | None = None
    fid: str | None = None
    credits: int = 0
    loan: int = 0
    is_wanted: bool = False

    def __post_init__(self) -> None:
        if self.credits < 0:
            raise ValueError("Credits balance cannot be negative.")
        if self.loan < 0:
            raise ValueError("Loan balance cannot be negative.")
```

### 3.6 `StationState` (`src/ed_resolver/core/domain/station/models.py`)

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StationState:
    """Station services, controlling factions, and market context."""

    station_name: str | None = None
    station_type: str | None = None
    market_id: int | None = None
    controlling_faction: str | None = None
    has_market: bool = False
    has_shipyard: bool = False
    has_outfitting: bool = False

    def __post_init__(self) -> None:
        pass
```

### 3.7 `CarrierState` (`src/ed_resolver/core/domain/carrier/models.py`)

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CarrierState:
    """Fleet carrier finances, fuel capacity, and pending jump state."""

    carrier_id: int | None = None
    callsign: str | None = None
    balance: int | None = None
    fuel_level: int | None = None
    pending_jump_target: str | None = None

    def __post_init__(self) -> None:
        if self.fuel_level is not None and self.fuel_level < 0:
            raise ValueError("Carrier fuel level cannot be negative.")
```

### 3.8 `ExplorationState` (`src/ed_resolver/core/domain/exploration/models.py`)

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExplorationState:
    """Exploration survey progress, discovered bodies, and organic bio discoveries."""

    system_name: str | None = None
    body_count: int | None = None
    all_bodies_found: bool = False
    organic_sample_count: int = 0

    def __post_init__(self) -> None:
        if self.organic_sample_count < 0:
            raise ValueError("organic_sample_count cannot be negative.")
```

### 3.9 `PowerplayState` (`src/ed_resolver/core/domain/powerplay/models.py`)

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PowerplayState:
    """Powerplay faction pledge, active merits, rank, and weekly nominations."""

    power: str | None = None
    merits: int = 0
    votes: int = 0
    is_pledged: bool = False

    def __post_init__(self) -> None:
        if self.merits < 0:
            raise ValueError("Powerplay merits cannot be negative.")
        if self.votes < 0:
            raise ValueError("Powerplay votes cannot be negative.")
```

---

## 4. Verification and Architectural Quality Gates

1. **AST Validation Test (`test_domain_entities_are_self_validating`):**
   * Confirms every domain state model defines a `__post_init__` method and is decorated with `@dataclass(frozen=True)`.
2. **Immutability Mutation Guard Test (`test_domain_state_models_are_frozen`):**
   * Attempts to mutate properties on each of the 9 state models and asserts that `FrozenInstanceError` is raised.
3. **Pure Zero-I/O Domain Isolation:**
   * Confirms zero imports of adapters, transport, or third-party packages in any `models.py` file.
