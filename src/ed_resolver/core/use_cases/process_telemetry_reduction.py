"""Telemetry event reduction use case coordinating domain reducers with state store ports."""

from __future__ import annotations

from typing import Any

from ..domain.archetypes import TelemetryArchetype
from ..domain.cargo.reducers import reduce_cargo
from ..domain.carrier.reducers import reduce_carrier
from ..domain.commander.reducers import reduce_commander
from ..domain.exploration.reducers import reduce_exploration
from ..domain.flight.reducers import reduce_flight
from ..domain.location.reducers import reduce_location
from ..domain.powerplay.reducers import reduce_powerplay
from ..domain.station.reducers import reduce_station
from ..domain.vessel.reducers import reduce_vessel
from ..ports.driven.state_store import (
    DomainStateReaderPort,
    DomainStateWriterPort,
)
from ..ports.driving.reduction import ReduceTelemetryEventPort


class ProcessTelemetryReductionUseCase(ReduceTelemetryEventPort):
    """Orchestrates pure domain reducers to update active state in DomainStateStore."""

    def __init__(
        self,
        reader: DomainStateReaderPort,
        writer: DomainStateWriterPort,
    ) -> None:
        self._reader = reader
        self._writer = writer

    def reduce(self, event: Any, archetype: TelemetryArchetype | None = None) -> None:
        """Processes event across 9 domain reducers, writing any changed state to the store."""
        if archetype == TelemetryArchetype.PASSIVE:
            return

        # 1. Location
        current_loc = self._reader.get_location()
        new_loc = reduce_location(current_loc, event)
        if new_loc is not current_loc:
            self._writer.set_location(new_loc)

        # 2. Vessel
        current_vessel = self._reader.get_vessel()
        new_vessel = reduce_vessel(current_vessel, event)
        if new_vessel is not current_vessel:
            self._writer.set_vessel(new_vessel)

        # 3. Flight
        current_flight = self._reader.get_flight()
        new_flight = reduce_flight(current_flight, event)
        if new_flight is not current_flight:
            self._writer.set_flight(new_flight)

        # 4. Cargo
        current_cargo = self._reader.get_cargo()
        new_cargo = reduce_cargo(current_cargo, event)
        if new_cargo is not current_cargo:
            self._writer.set_cargo(new_cargo)

        # 5. Commander
        current_cmdr = self._reader.get_commander()
        new_cmdr = reduce_commander(current_cmdr, event)
        if new_cmdr is not current_cmdr:
            self._writer.set_commander(new_cmdr)

        # 6. Station
        current_station = self._reader.get_station()
        new_station = reduce_station(current_station, event)
        if new_station is not current_station:
            self._writer.set_station(new_station)

        # 7. Carrier
        current_carrier = self._reader.get_carrier()
        new_carrier = reduce_carrier(current_carrier, event)
        if new_carrier is not current_carrier:
            self._writer.set_carrier(new_carrier)

        # 8. Exploration
        current_explo = self._reader.get_exploration()
        new_explo = reduce_exploration(current_explo, event)
        if new_explo is not current_explo:
            self._writer.set_exploration(new_explo)

        # 9. Powerplay
        current_pp = self._reader.get_powerplay()
        new_pp = reduce_powerplay(current_pp, event)
        if new_pp is not current_pp:
            self._writer.set_powerplay(new_pp)
