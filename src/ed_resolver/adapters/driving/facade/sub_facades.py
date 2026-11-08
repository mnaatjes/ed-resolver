"""Domain sub-facades for the AmbientTelemetryFacade driving adapter."""

from __future__ import annotations

from ....core.domain import (
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
from ....core.ports.driven.state_store import DomainStateReaderPort


class LocationSubFacade:
    """Domain sub-facade for spatial coordinates, docking, and celestial context."""

    def __init__(self, reader: DomainStateReaderPort) -> None:
        self._reader = reader

    def state(self) -> LocationState:
        """Returns the current location state."""
        return self._reader.get_location()

    def is_docked(self) -> bool:
        """Predicate: Is commander docked at a station, outpost, or carrier."""
        return self.state().docked

    def in_supercruise(self) -> bool:
        """Predicate: Is commander currently in supercruise flight."""
        return self.state().in_supercruise

    def on_surface(self) -> bool:
        """Predicate: Is commander landed on a planetary surface."""
        return self.state().on_surface


class VesselSubFacade:
    """Domain sub-facade for commander vessel, loadout, suit, and SRV state."""

    def __init__(self, reader: DomainStateReaderPort) -> None:
        self._reader = reader

    def state(self) -> VesselState:
        """Returns the current vessel operational state."""
        return self._reader.get_vessel()

    def is_on_foot(self) -> bool:
        """Predicate: Is commander disembarked on foot (Odyssey suit mode)."""
        return self.state().is_on_foot

    def is_in_srv(self) -> bool:
        """Predicate: Is commander operating a surface reconnaissance vehicle."""
        return self.state().is_in_srv


class FlightSubFacade:
    """Domain sub-facade for continuous flight parameters, gear, and hardpoints."""

    def __init__(self, reader: DomainStateReaderPort) -> None:
        self._reader = reader

    def state(self) -> FlightState:
        """Returns the current flight telemetry state."""
        return self._reader.get_flight()

    def landing_gear_down(self) -> bool:
        """Predicate: Is landing gear currently deployed."""
        return self.state().landing_gear_down

    def hardpoints_deployed(self) -> bool:
        """Predicate: Are weapons / hardpoints deployed."""
        return self.state().hardpoints_deployed

    def flight_assist_off(self) -> bool:
        """Predicate: Is flight assist disabled."""
        return self.state().flight_assist_off

    def night_vision(self) -> bool:
        """Predicate: Is night vision active."""
        return self.state().night_vision


class CargoSubFacade:
    """Domain sub-facade for commodity inventory and hold capacity."""

    def __init__(self, reader: DomainStateReaderPort) -> None:
        self._reader = reader

    def state(self) -> CargoState:
        """Returns the current cargo inventory state."""
        return self._reader.get_cargo()

    def count(self) -> int:
        """Returns total commodity tonnage in hold."""
        return self.state().count

    def has_item(self, item_name: str) -> bool:
        """Predicate: Does inventory hold at least 1 unit of named commodity."""
        return self.state().inventory.get(item_name, 0) > 0


class CommanderSubFacade:
    """Domain sub-facade for commander identity, finances, and legal reputation."""

    def __init__(self, reader: DomainStateReaderPort) -> None:
        self._reader = reader

    def state(self) -> CommanderState:
        """Returns the current commander state."""
        return self._reader.get_commander()

    def is_wanted(self) -> bool:
        """Predicate: Does commander hold active bounty or wanted standing."""
        return self.state().is_wanted


class StationSubFacade:
    """Domain sub-facade for station services and market context."""

    def __init__(self, reader: DomainStateReaderPort) -> None:
        self._reader = reader

    def state(self) -> StationState:
        """Returns the current station state."""
        return self._reader.get_station()

    def has_market(self) -> bool:
        """Predicate: Does docked starport provide commodity market services."""
        return self.state().has_market

    def has_shipyard(self) -> bool:
        """Predicate: Does docked starport provide shipyard facilities."""
        return self.state().has_shipyard

    def has_outfitting(self) -> bool:
        """Predicate: Does docked starport provide outfitting services."""
        return self.state().has_outfitting


class CarrierSubFacade:
    """Domain sub-facade for fleet carrier finances, fuel, and jump orders."""

    def __init__(self, reader: DomainStateReaderPort) -> None:
        self._reader = reader

    def state(self) -> CarrierState:
        """Returns the current carrier state."""
        return self._reader.get_carrier()

    def has_pending_jump(self) -> bool:
        """Predicate: Is fleet carrier queued for a jump countdown."""
        return self.state().pending_jump_target is not None


class ExplorationSubFacade:
    """Domain sub-facade for cartography, FSS survey scans, and exobiology."""

    def __init__(self, reader: DomainStateReaderPort) -> None:
        self._reader = reader

    def state(self) -> ExplorationState:
        """Returns the current exploration survey state."""
        return self._reader.get_exploration()

    def all_bodies_found(self) -> bool:
        """Predicate: Have all celestial bodies in the star system been surveyed."""
        return self.state().all_bodies_found


class PowerplaySubFacade:
    """Domain sub-facade for galactic power pledges, merits, and nominations."""

    def __init__(self, reader: DomainStateReaderPort) -> None:
        self._reader = reader

    def state(self) -> PowerplayState:
        """Returns the current powerplay state."""
        return self._reader.get_powerplay()

    def is_pledged(self) -> bool:
        """Predicate: Is commander actively pledged to a galactic power."""
        return self.state().is_pledged
