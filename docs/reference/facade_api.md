---
title: "Ambient Telemetry Facade API Reference"
tags: ["reference", "facade", "api", "ed-resolver", "domain-state"]
created_at: "2026-11-08"
last_updated_at: "2026-11-08"
---

# Ambient Telemetry Facade API Reference

This reference documents the public API exposed by `ed-resolver` for in-process consumers, visualizers, copilots, and integration test suites.

---

## 1. Composition Root: `create_resolver`

**Module:** `ed_resolver.bootstrap`

```python
def create_resolver(
    ingress_port: TelemetryIngressPort | None = None,
    state_store: InMemoryDomainStateStore | None = None,
    quarantine_capacity: int = 100,
) -> AmbientTelemetryFacade:
    """Instantiates and wires the complete ed-resolver runtime pipeline."""
```

### Parameters

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `ingress_port` | `TelemetryIngressPort \| None` | `MemoryQueueAdapter()` | Driven adapter streaming raw envelopes. |
| `state_store` | `InMemoryDomainStateStore \| None` | `InMemoryDomainStateStore()` | In-memory store holding the 9 active domain states. |
| `quarantine_capacity` | `int` | `100` | Maximum capacity of the dead-letter queue ring buffer. |

### Returns
* `AmbientTelemetryFacade`: The configured driving facade.

---

## 2. Root Driving Adapter: `AmbientTelemetryFacade`

**Module:** `ed_resolver` or `ed_resolver.adapters.driving.facade`

The root coordinator exposing domain sub-facades, convenience predicates, and async runtime lifecycle controls.

### 2.1 Lifecycle Methods

* **`async def start() -> None:`**
  Starts the supervised background `TelemetryIngressWorker` task.
* **`async def stop(timeout: float = 5.0) -> None:`**
  Signals worker cancellation, awaits task termination, and closes the ingress port.
* **`async with facade:`**
  Async context manager protocol. Automatically starts the worker on entry and cleanly stops on exit.

### 2.2 Root Convenience Predicates

Macro-level boolean projections evaluated directly over the underlying state models:

| Method | Return Type | Sub-Facade Target | Description |
| :--- | :--- | :--- | :--- |
| `is_docked()` | `bool` | `location.is_docked()` | True if commander is docked at a starport, outpost, or fleet carrier. |
| `is_on_foot()` | `bool` | `vessel.is_on_foot()` | True if commander has disembarked in Odyssey on-foot mode. |
| `in_supercruise()` | `bool` | `location.in_supercruise()` | True if vessel is traveling in supercruise. |
| `is_in_srv()` | `bool` | `vessel.is_in_srv()` | True if commander is driving an SRV. |
| `is_wanted()` | `bool` | `commander.is_wanted()` | True if commander has an active bounty or wanted legal standing. |

---

## 3. Domain Sub-Facades

Accessed as properties on `AmbientTelemetryFacade`:

### 3.1 `facade.location` (`LocationSubFacade`)

Spatial position, star system, docking, and planetary surface truth.

* **`.state() -> LocationState`**: Returns the active immutable `LocationState`.
* **`.is_docked() -> bool`**: Is commander docked at a station, outpost, or carrier.
* **`.in_supercruise() -> bool`**: Is vessel in supercruise.
* **`.on_surface() -> bool`**: Is vessel or commander landed on a planetary body surface.

### 3.2 `facade.vessel` (`VesselSubFacade`)

Active ship, loadout, suit, and SRV operational truth.

* **`.state() -> VesselState`**: Returns the active immutable `VesselState`.
* **`.is_on_foot() -> bool`**: Is commander disembarked on foot.
* **`.is_in_srv() -> bool`**: Is commander driving a Surface Reconnaissance Vehicle.

### 3.3 `facade.flight` (`FlightSubFacade`)

Continuous flight parameters, gear, hardpoints, and fuel levels.

* **`.state() -> FlightState`**: Returns the active immutable `FlightState`.
* **`.landing_gear_down() -> bool`**: Is landing gear deployed.
* **`.hardpoints_deployed() -> bool`**: Are weapons/hardpoints deployed.
* **`.flight_assist_off() -> bool`**: Is Flight Assist disabled.
* **`.night_vision() -> bool`**: Is cockpit night vision enabled.

### 3.4 `facade.cargo` (`CargoSubFacade`)

Commodity inventory and hold quantities.

* **`.state() -> CargoState`**: Returns the active immutable `CargoState`.
* **`.count() -> int`**: Total commodity tonnage currently held.
* **`.has_item(item_name: str) -> bool`**: Checks if at least 1 unit of the named commodity is held.

### 3.5 `facade.commander` (`CommanderSubFacade`)

Commander profile, finances, and legal standing.

* **`.state() -> CommanderState`**: Returns the active immutable `CommanderState`.
* **`.is_wanted() -> bool`**: Does commander have an active fine or bounty.

### 3.6 `facade.station` (`StationSubFacade`)

Docked starport services, market, and shipyard facilities.

* **`.state() -> StationState`**: Returns the active immutable `StationState`.
* **`.has_market() -> bool`**: Does starport provide commodity market services.
* **`.has_shipyard() -> bool`**: Does starport provide shipyard facilities.
* **`.has_outfitting() -> bool`**: Does starport provide module outfitting.

### 3.7 `facade.carrier` (`CarrierSubFacade`)

Fleet carrier status, fuel, and jump orders.

* **`.state() -> CarrierState`**: Returns the active immutable `CarrierState`.
* **`.has_pending_jump() -> bool`**: Is carrier queued for a jump countdown.

### 3.8 `facade.exploration` (`ExplorationSubFacade`)

FSS survey scan progress, system bodies, and exobiology sampling.

* **`.state() -> ExplorationState`**: Returns the active immutable `ExplorationState`.
* **`.all_bodies_found() -> bool`**: Have all celestial bodies in the star system been discovered.

### 3.9 `facade.powerplay` (`PowerplaySubFacade`)

Galactic power faction pledge, merits, and voting status.

* **`.state() -> PowerplayState`**: Returns the active immutable `PowerplayState`.
* **`.is_pledged() -> bool`**: Is commander actively pledged to a galactic power.

---

## 4. Domain State Models

All domain state models reside in `ed_resolver.core.domain` (and are re-exported at package root `ed_resolver`). They are decorated with `@dataclass(frozen=True, slots=True)` and enforce invariant validation.

### 4.1 `LocationState`
* `system_name: str | None = None`
* `system_address: int | None = None`
* `star_pos: tuple[float, float, float] = (0.0, 0.0, 0.0)`
* `body_name: str | None = None`
* `body_id: int | None = None`
* `station_name: str | None = None`
* `station_type: str | None = None`
* `docked: bool = False`
* `in_supercruise: bool = False`
* `on_surface: bool = False`

### 4.2 `VesselState`
* `ship_name: str | None = None`
* `ship_ident: str | None = None`
* `ship_type: str | None = None`
* `hull_value: int | None = None`
* `modules_value: int | None = None`
* `is_on_foot: bool = False`
* `is_in_srv: bool = False`

### 4.3 `FlightState`
* `in_supercruise: bool = False`
* `landing_gear_down: bool = False`
* `hardpoints_deployed: bool = False`
* `flight_assist_off: bool = False`
* `night_vision: bool = False`
* `fuel_main: float | None = None`
* `fuel_reservoir: float | None = None`

### 4.4 `CargoState`
* `count: int = 0`
* `inventory: Mapping[str, int] = field(default_factory=dict)` *(wrapped in MappingProxyType)*
* `vessel_type: str | None = None`

### 4.5 `CommanderState`
* `name: str | None = None`
* `fid: str | None = None`
* `credits: int = 0`
* `loan: int = 0`
* `is_wanted: bool = False`

### 4.6 `StationState`
* `station_name: str | None = None`
* `station_type: str | None = None`
* `market_id: int | None = None`
* `controlling_faction: str | None = None`
* `has_market: bool = False`
* `has_shipyard: bool = False`
* `has_outfitting: bool = False`

### 4.7 `CarrierState`
* `carrier_id: int | None = None`
* `callsign: str | None = None`
* `balance: int | None = None`
* `fuel_level: int | None = None`
* `pending_jump_target: str | None = None`

### 4.8 `ExplorationState`
* `system_name: str | None = None`
* `body_count: int | None = None`
* `all_bodies_found: bool = False`
* `organic_sample_count: int = 0`

### 4.9 `PowerplayState`
* `power: str | None = None`
* `merits: int = 0`
* `votes: int = 0`
* `is_pledged: bool = False`

---

## 5. Driven Ingress Adapters

**Module:** `ed_resolver.adapters.driven.ingress`

* **`MemoryQueueAdapter`**: An in-memory queue implementing `TelemetryIngressPort`. Used for unit testing and offline simulation via `.put(envelope)`.
* **`EdTelemetryNetworkAdapter`**: An asynchronous SSE client that streams live JSON payloads from `ed-telemetry` over HTTP (`http://127.0.0.1:8080/api/v1/stream`).
* **`EdTelemetryInProcessAdapter`**: Directly consumes from an in-process `ed-telemetry` memory ring buffer.
