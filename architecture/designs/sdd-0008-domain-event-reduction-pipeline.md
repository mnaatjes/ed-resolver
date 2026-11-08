---
title: "SDD 0008: Domain Event Reduction Pipeline and Dispatch Subsystem"
tags: ["sdd", "architecture", "reducers", "use-cases", "hexagonal", "ed-resolver"]
created_at: "2026-11-08"
last_updated_at: "2026-11-08"
---

# SDD 0008: Domain Event Reduction Pipeline and Dispatch Subsystem

* **Status:** Proposed
* **Governing ADRs:** [ADR 0001](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0001_core_domain_state_architecture_and_unified_ingress_lifecycle.md), [ADR 0002](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0002_archetype_classification_subsystem_and_registry.md), [ADR 0005](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0005_telemetry_ingress_worker_runtime_lifecycle.md), [ADR 0006](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0006_core_domain_state_model_taxonomy_and_immutability.md), [ADR 0007](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0007_in_memory_domain_state_store_and_atomic_swap.md), [ADR 0008](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0008_domain_event_reduction_pipelines_and_dispatch.md)
* **Author:** Antigravity Pair Programmer
* **Version:** 1.0.0
* **Target Package:** `ed-resolver`

---

## 1. Introduction & Context

### 1.1 Purpose
This Software Design Document specifies the architecture, contracts, and concrete implementations of domain event reduction pipelines in `ed-resolver`. It defines how deserialized telemetry event DTOs are mapped to the 9 immutable domain state models via pure functional reducers, and how the `ProcessTelemetryReductionUseCase` coordinates state reads and writes.

### 1.2 System Boundary & Scope
The implementation is strictly confined to:
* Driving Port: `src/ed_resolver/core/ports/driving/reduction.py` (`ReduceTelemetryEventPort`)
* Port Exports: `src/ed_resolver/core/ports/driving/__init__.py`
* Domain Reducer Modules:
  - `src/ed_resolver/core/domain/location/reducers.py`
  - `src/ed_resolver/core/domain/vessel/reducers.py`
  - `src/ed_resolver/core/domain/flight/reducers.py`
  - `src/ed_resolver/core/domain/cargo/reducers.py`
  - `src/ed_resolver/core/domain/commander/reducers.py`
  - `src/ed_resolver/core/domain/station/reducers.py`
  - `src/ed_resolver/core/domain/carrier/reducers.py`
  - `src/ed_resolver/core/domain/exploration/reducers.py`
  - `src/ed_resolver/core/domain/powerplay/reducers.py`
* Core Use Case: `src/ed_resolver/core/use_cases/process_telemetry_reduction.py` (`ProcessTelemetryReductionUseCase`)
* Unit & Architectural Tests:
  - `tests/core/domain/test_reducers.py`
  - `tests/core/use_cases/test_process_telemetry_reduction.py`

---

## 2. Port Contract Specification (`src/ed_resolver/core/ports/driving/reduction.py`)

The primary port implemented by the reduction use case is defined as:

```python
from typing import Any, Protocol, runtime_checkable

from ed_resolver.core.domain.archetypes import TelemetryArchetype
from ed_resolver.core.ports.base import DrivingPort


@runtime_checkable
class ReduceTelemetryEventPort(DrivingPort, Protocol):
    """Driving port for dispatching deserialized telemetry events into reduction pipelines."""

    def reduce(self, event: Any, archetype: TelemetryArchetype | None = None) -> None:
        """Processes an event DTO, computes updated domain states, and stores new projections."""
        ...
```

---

## 3. Domain Reducers Specification

Each hexagonal domain defines a dedicated `reducers.py` module containing pure functional reduction logic.

### 3.1 Location Reducer (`core/domain/location/reducers.py`)
Handles:
* `FSDJump` / `Location` / `CarrierJump`: Full spatial update (`system_name`, `system_address`, `star_pos`, `body_name`, `body_id`, `docked=False`).
* `Docked`: Sets `station_name`, `station_type`, and `docked=True`.
* `Undocked`: Clears `station_name`, `station_type`, and sets `docked=False`.
* `SupercruiseExit`: Updates `body_name`, `body_id`, and sets `in_supercruise=False`.
* `SupercruiseEntry`: Sets `in_supercruise=True`.
* `Touchdown`: Sets `on_surface=True`, updates `body_name`.
* `Liftoff`: Sets `on_surface=False`.

### 3.2 Vessel Reducer (`core/domain/vessel/reducers.py`)
Handles:
* `Loadout` / `LoadGame` / `ShipyardBuy` / `ShipyardSwap`: Updates `ship_name`, `ship_ident`, `ship_type`, `hull_value`, `modules_value`.
* `SuitLoadout`: Updates suit and sets `is_on_foot=True`, `is_in_srv=False`.
* `LaunchSRV`: Sets `is_in_srv=True`, `is_on_foot=False`.
* `DockSRV`: Sets `is_in_srv=False`.

### 3.3 Flight Reducer (`core/domain/flight/reducers.py`)
Handles:
* `Status` / Status Ticks: Updates continuous flags (`landing_gear_down`, `hardpoints_deployed`, `flight_assist_off`, `night_vision`, `fuel_main`, `fuel_reservoir`).

### 3.4 Cargo Reducer (`core/domain/cargo/reducers.py`)
Handles:
* `Cargo`: Full replacement of `inventory` and total `count`.
* `CollectCargo`: Increments item count and total count.
* `EjectCargo`: Decrements item count and total count.

### 3.5 Commander Reducer (`core/domain/commander/reducers.py`)
Handles:
* `Commander`: Seeds `name` and `fid`.
* `LoadGame`: Updates `credits` and `loan`.
* `Bounty` / `CommitCrime`: Updates `is_wanted`.

### 3.6 Station Reducer (`core/domain/station/reducers.py`)
Handles:
* `Docked`: Seeds `station_name`, `station_type`, `market_id`, `controlling_faction`, service flags.
* `Undocked`: Resets station context to default `StationState()`.

### 3.7 Carrier Reducer (`core/domain/carrier/reducers.py`)
Handles:
* `CarrierStats`: Updates `carrier_id`, `callsign`, `balance`, `fuel_level`.
* `CarrierJumpRequest`: Sets `pending_jump_target`.
* `CarrierJumpCancelled`: Clears `pending_jump_target`.

### 3.8 Exploration Reducer (`core/domain/exploration/reducers.py`)
Handles:
* `FSSDiscoveryScan`: Updates `system_name`, `body_count`.
* `FSSAllBodiesFound`: Sets `all_bodies_found=True`.
* `ScanOrganic`: Increments `organic_sample_count`.

### 3.9 Powerplay Reducer (`core/domain/powerplay/reducers.py`)
Handles:
* `Powerplay`: Seeds `power`, `merits`, `votes`, `is_pledged=True`.
* `PowerplayDefect` / `PowerplayLeave`: Resets to default `PowerplayState()`.

---

## 4. Use Case Orchestration Specification (`core/use_cases/process_telemetry_reduction.py`)

`ProcessTelemetryReductionUseCase` coordinates the pipeline:
1. Fast-paths out if `archetype == TelemetryArchetype.PASSIVE`.
2. Reads the current domain states from `DomainStateReaderPort`.
3. Calls domain reducers for each domain.
4. If a domain reducer returns a new object reference (`new_state is not current_state`), it writes the updated state to `DomainStateWriterPort`.

---

## 5. Testing & Quality Gate Strategy

1. **Pure Reducer Unit Tests (`tests/core/domain/test_reducers.py`):**
   * Verifies each reducer returns derived copies without mutating input arguments.
   * Verifies that irrelevant events return the unchanged `current` object.
2. **Use Case Integration Tests (`tests/core/use_cases/test_process_telemetry_reduction.py`):**
   * Uses `InMemoryDomainStateStore` as both reader and writer port.
   * Tests multi-domain reduction (e.g. `FSDJump` updates `LocationState` and `ExplorationState`).
   * Tests `PASSIVE` event fast-path skipping.
3. **Architecture Boundary Tests:**
   * Validates `test_use_cases_follow_lexical_and_structural_conventions` and zero lifecycle leakage.
