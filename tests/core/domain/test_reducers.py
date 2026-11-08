"""Unit tests for pure domain reducers across all 9 domains."""

from __future__ import annotations

from types import SimpleNamespace

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
from ed_resolver.core.domain.cargo.reducers import reduce_cargo
from ed_resolver.core.domain.carrier.reducers import reduce_carrier
from ed_resolver.core.domain.commander.reducers import reduce_commander
from ed_resolver.core.domain.exploration.reducers import reduce_exploration
from ed_resolver.core.domain.flight.reducers import reduce_flight
from ed_resolver.core.domain.location.reducers import reduce_location
from ed_resolver.core.domain.powerplay.reducers import reduce_powerplay
from ed_resolver.core.domain.station.reducers import reduce_station
from ed_resolver.core.domain.vessel.reducers import reduce_vessel


def test_location_reducer() -> None:
    current = LocationState()

    # Irrelevant event returns current instance
    assert reduce_location(current, SimpleNamespace(__class__=type("Music", (), {}))) is current

    # FSDJump event
    class FSDJump:
        star_system = "Shinrarta Dezhra"
        system_address = 123456789
        star_pos = SimpleNamespace(x=55.7, y=-17.2, z=27.1)
        body = "Founders World"
        body_id = 1
        docked = False

    new_loc = reduce_location(current, FSDJump())
    assert new_loc.system_name == "Shinrarta Dezhra"
    assert new_loc.star_pos == (55.7, -17.2, 27.1)
    assert not new_loc.docked

    # Docked event
    class Docked:
        station_name = "Jameson Memorial"
        station_type = "Orbis"

    docked_loc = reduce_location(new_loc, Docked())
    assert docked_loc.docked
    assert docked_loc.station_name == "Jameson Memorial"

    # Undocked event
    class Undocked:
        pass

    undocked_loc = reduce_location(docked_loc, Undocked())
    assert not undocked_loc.docked
    assert undocked_loc.station_name is None


def test_vessel_reducer() -> None:
    current = VesselState()

    class Loadout:
        ship_name = "Enterprise"
        ship_ident = "NCC-1701"
        ship = "Anaconda"
        hull_value = 150_000_000
        modules_value = 250_000_000

    vessel = reduce_vessel(current, Loadout())
    assert vessel.ship_name == "Enterprise"
    assert vessel.ship_type == "Anaconda"

    class Disembark:
        pass

    on_foot = reduce_vessel(vessel, Disembark())
    assert on_foot.is_on_foot
    assert not on_foot.is_in_srv


def test_flight_reducer() -> None:
    current = FlightState()

    class Status:
        # bit 2 (gear), bit 6 (hardpoints), bit 4 (supercruise)
        flags = (1 << 2) | (1 << 6) | (1 << 4)
        fuel = SimpleNamespace(fuel_main=30.5, fuel_reservoir=0.6)

    flight = reduce_flight(current, Status())
    assert flight.landing_gear_down
    assert flight.hardpoints_deployed
    assert flight.in_supercruise
    assert flight.fuel_main == 30.5


def test_cargo_reducer() -> None:
    current = CargoState()

    class Cargo:
        count = 10
        inventory = [SimpleNamespace(name="Gold", count=10)]
        vessel = "Ship"

    c1 = reduce_cargo(current, Cargo())
    assert c1.count == 10
    assert c1.inventory["Gold"] == 10

    class CollectCargo:
        type = "Gold"

    c2 = reduce_cargo(c1, CollectCargo())
    assert c2.count == 11
    assert c2.inventory["Gold"] == 11

    class EjectCargo:
        type = "Gold"
        count = 5

    c3 = reduce_cargo(c2, EjectCargo())
    assert c3.count == 6
    assert c3.inventory["Gold"] == 6


def test_commander_reducer() -> None:
    current = CommanderState()

    class Commander:
        name = "Jameson"
        fid = "F998877"

    cmdr = reduce_commander(current, Commander())
    assert cmdr.name == "Jameson"

    class LoadGame:
        commander = "Jameson"
        fid = "F998877"
        credits = 5_000_000
        loan = 0

    cmdr2 = reduce_commander(cmdr, LoadGame())
    assert cmdr2.credits == 5_000_000


def test_station_reducer() -> None:
    current = StationState()

    class Docked:
        station_name = "Jaques Station"
        station_type = "Ocellus"
        market_id = 98765
        station_faction = "Colonia Council"
        station_services = ["commodities", "shipyard", "outfitting"]

    station = reduce_station(current, Docked())
    assert station.station_name == "Jaques Station"
    assert station.has_market
    assert station.has_shipyard
    assert station.has_outfitting

    class Undocked:
        pass

    assert reduce_station(station, Undocked()) == StationState()


def test_carrier_reducer() -> None:
    current = CarrierState()

    class CarrierStats:
        carrier_id = 1234
        callsign = "H1Z-99K"
        balance = 50_000_000
        fuel_level = 500

    carrier = reduce_carrier(current, CarrierStats())
    assert carrier.callsign == "H1Z-99K"
    assert carrier.fuel_level == 500

    class CarrierDepositFuel:
        amount = 100

    carrier2 = reduce_carrier(carrier, CarrierDepositFuel())
    assert carrier2.fuel_level == 600


def test_exploration_reducer() -> None:
    current = ExplorationState()

    class FSSDiscoveryScan:
        system_name = "Beagle Point"
        body_count = 14

    explo = reduce_exploration(current, FSSDiscoveryScan())
    assert explo.system_name == "Beagle Point"
    assert explo.body_count == 14
    assert not explo.all_bodies_found

    class FSSAllBodiesFound:
        system_name = "Beagle Point"

    explo2 = reduce_exploration(explo, FSSAllBodiesFound())
    assert explo2.all_bodies_found


def test_powerplay_reducer() -> None:
    current = PowerplayState()

    class Powerplay:
        power = "Aisling Duval"
        merits = 1500
        votes = 50

    pp = reduce_powerplay(current, Powerplay())
    assert pp.power == "Aisling Duval"
    assert pp.merits == 1500
    assert pp.is_pledged

    class PowerplayLeave:
        pass

    assert reduce_powerplay(pp, PowerplayLeave()) == PowerplayState()
