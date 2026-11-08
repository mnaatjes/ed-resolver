"""Unit and concurrency tests for InMemoryDomainStateStore."""

from __future__ import annotations

import dataclasses
from concurrent.futures import ThreadPoolExecutor

from ed_resolver.adapters.driven.state_store import InMemoryDomainStateStore
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
from ed_resolver.core.ports.driven import (
    DomainStateReaderPort,
    DomainStateWriterPort,
)


def test_state_store_fulfills_reader_and_writer_protocols() -> None:
    """Verifies that InMemoryDomainStateStore fulfills both port contracts."""
    store = InMemoryDomainStateStore()
    assert isinstance(store, DomainStateReaderPort)
    assert isinstance(store, DomainStateWriterPort)


def test_state_store_cold_start_defaults() -> None:
    """Verifies all 9 domain projections return valid non-null default state instances."""
    store = InMemoryDomainStateStore()

    assert store.get_location() == LocationState()
    assert store.get_vessel() == VesselState()
    assert store.get_flight() == FlightState()
    assert store.get_cargo() == CargoState()
    assert store.get_commander() == CommanderState()
    assert store.get_station() == StationState()
    assert store.get_carrier() == CarrierState()
    assert store.get_exploration() == ExplorationState()
    assert store.get_powerplay() == PowerplayState()


def test_state_store_atomic_pointer_swap() -> None:
    """Verifies atomic pointer replacement for each domain projection."""
    store = InMemoryDomainStateStore()

    initial_loc = store.get_location()
    updated_loc = dataclasses.replace(initial_loc, system_name="Sol", docked=True)
    store.set_location(updated_loc)

    assert store.get_location() is updated_loc
    assert store.get_location().system_name == "Sol"
    assert store.get_location().docked
    # Initial snapshot remains unaffected
    assert initial_loc.system_name is None
    assert not initial_loc.docked

    # Vessel
    vessel = VesselState(ship_name="Python", is_in_srv=True)
    store.set_vessel(vessel)
    assert store.get_vessel() is vessel

    # Flight
    flight = FlightState(fuel_main=16.0, night_vision=True)
    store.set_flight(flight)
    assert store.get_flight() is flight

    # Cargo
    cargo = CargoState(count=4, inventory={"Gold": 4})
    store.set_cargo(cargo)
    assert store.get_cargo() is cargo

    # Commander
    commander = CommanderState(name="Jameson", credits=500_000)
    store.set_commander(commander)
    assert store.get_commander() is commander

    # Station
    station = StationState(station_name="Shinrarta Dezhra", has_market=True)
    store.set_station(station)
    assert store.get_station() is station

    # Carrier
    carrier = CarrierState(callsign="V1Z-99Y", fuel_level=800)
    store.set_carrier(carrier)
    assert store.get_carrier() is carrier

    # Exploration
    exploration = ExplorationState(system_name="Beagle Point", body_count=12)
    store.set_exploration(exploration)
    assert store.get_exploration() is exploration

    # Powerplay
    powerplay = PowerplayState(power="Felicia Winters", merits=1200)
    store.set_powerplay(powerplay)
    assert store.get_powerplay() is powerplay


def test_concurrent_reads_and_writes_are_thread_safe() -> None:
    """Verifies concurrent multi-threaded writes and reads execute without torn reads."""
    store = InMemoryDomainStateStore()
    iterations = 200

    def writer_task() -> None:
        for i in range(iterations):
            new_cargo = CargoState(count=i, inventory={"Tritium": i})
            store.set_cargo(new_cargo)

    def reader_task() -> list[CargoState]:
        observed = []
        for _ in range(iterations):
            cargo = store.get_cargo()
            # Invariant: Cargo count must equal Tritium count
            assert cargo.count == cargo.inventory.get("Tritium", 0)
            observed.append(cargo)
        return observed

    with ThreadPoolExecutor(max_workers=4) as executor:
        writer_future = executor.submit(writer_task)
        reader_futures = [executor.submit(reader_task) for _ in range(3)]

        writer_future.result()
        for f in reader_futures:
            results = f.result()
            assert len(results) == iterations
