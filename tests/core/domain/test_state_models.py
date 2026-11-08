"""Unit and immutability tests for the 9 core domain state models."""

from __future__ import annotations

import dataclasses
from types import MappingProxyType

import pytest

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
from ed_resolver.core.domain.exceptions import DomainValidationError


def test_location_state_instantiation_and_immutability() -> None:
    """Verifies LocationState defaults, immutability, and coordinate validation."""
    state = LocationState()
    assert state.system_name is None
    assert state.star_pos == (0.0, 0.0, 0.0)
    assert not state.docked

    with pytest.raises(dataclasses.FrozenInstanceError):
        # pyright: ignore [reportGeneralTypeIssues]
        state.docked = True  # type: ignore[misc]

    # Coordinate validation guard
    with pytest.raises(DomainValidationError, match="3-dimensional coordinate"):
        LocationState(star_pos=(1.0, 2.0))  # type: ignore[arg-type]


def test_vessel_state_instantiation_and_mutual_exclusivity() -> None:
    """Verifies VesselState defaults and on-foot/SRV mutual exclusivity."""
    state = VesselState(ship_name="Cobra Mk III", is_on_foot=True)
    assert state.ship_name == "Cobra Mk III"
    assert state.is_on_foot
    assert not state.is_in_srv

    with pytest.raises(dataclasses.FrozenInstanceError):
        state.is_on_foot = False  # type: ignore[misc]

    with pytest.raises(DomainValidationError, match="simultaneously be on foot and in an SRV"):
        VesselState(is_on_foot=True, is_in_srv=True)


def test_flight_state_instantiation_and_validation() -> None:
    """Verifies FlightState non-negative fuel validation and replace derivation."""
    state = FlightState(fuel_main=32.0, fuel_reservoir=0.5)
    assert state.fuel_main == 32.0
    assert not state.landing_gear_down

    # Replace derivation
    updated = dataclasses.replace(state, landing_gear_down=True, fuel_main=31.2)
    assert updated.landing_gear_down
    assert updated.fuel_main == 31.2
    assert not state.landing_gear_down

    with pytest.raises(DomainValidationError, match="fuel_main cannot be negative"):
        FlightState(fuel_main=-1.0)

    with pytest.raises(DomainValidationError, match="fuel_reservoir cannot be negative"):
        FlightState(fuel_reservoir=-0.1)


def test_cargo_state_mapping_proxy_immutability() -> None:
    """Verifies CargoState wraps inventory in MappingProxyType and enforces non-negative count."""
    inventory_dict = {"Gold": 10, "Palladium": 5}
    state = CargoState(count=15, inventory=inventory_dict)

    assert state.count == 15
    assert isinstance(state.inventory, MappingProxyType)
    assert state.inventory["Gold"] == 10

    # Mutating original dictionary does not affect MappingProxyType copy if copied
    inventory_dict["Gold"] = 99
    assert state.inventory["Gold"] == 10

    with pytest.raises(TypeError):
        state.inventory["Gold"] = 20  # type: ignore[index]

    with pytest.raises(dataclasses.FrozenInstanceError):
        state.count = 20  # type: ignore[misc]

    with pytest.raises(DomainValidationError, match="Cargo count cannot be negative"):
        CargoState(count=-1)


def test_commander_state_validation() -> None:
    """Verifies CommanderState credit and loan validation."""
    state = CommanderState(name="Jameson", fid="F12345", credits=100_000_000)
    assert state.name == "Jameson"
    assert state.credits == 100_000_000
    assert not state.is_wanted

    with pytest.raises(DomainValidationError, match="Credits balance cannot be negative"):
        CommanderState(credits=-500)

    with pytest.raises(DomainValidationError, match="Loan balance cannot be negative"):
        CommanderState(loan=-100)


def test_station_state_defaults_and_immutability() -> None:
    """Verifies StationState defaults and frozen behavior."""
    state = StationState(station_name="Jameson Memorial", has_market=True, has_shipyard=True)
    assert state.station_name == "Jameson Memorial"
    assert state.has_market
    assert state.has_shipyard
    assert not state.has_outfitting

    with pytest.raises(dataclasses.FrozenInstanceError):
        state.has_outfitting = True  # type: ignore[misc]


def test_carrier_state_fuel_validation() -> None:
    """Verifies CarrierState non-negative fuel validation."""
    state = CarrierState(callsign="X1Y-Z2A", fuel_level=500)
    assert state.fuel_level == 500

    with pytest.raises(DomainValidationError, match="Carrier fuel level cannot be negative"):
        CarrierState(fuel_level=-10)


def test_exploration_state_sample_validation() -> None:
    """Verifies ExplorationState sample count validation."""
    state = ExplorationState(system_name="Sol", organic_sample_count=3)
    assert state.organic_sample_count == 3

    with pytest.raises(DomainValidationError, match="organic_sample_count cannot be negative"):
        ExplorationState(organic_sample_count=-1)


def test_powerplay_state_merits_and_votes_validation() -> None:
    """Verifies PowerplayState non-negative merits and votes validations."""
    state = PowerplayState(power="Aisling Duval", merits=750, is_pledged=True)
    assert state.power == "Aisling Duval"
    assert state.merits == 750
    assert state.is_pledged

    with pytest.raises(DomainValidationError, match="Powerplay merits cannot be negative"):
        PowerplayState(merits=-1)

    with pytest.raises(DomainValidationError, match="Powerplay votes cannot be negative"):
        PowerplayState(votes=-5)
