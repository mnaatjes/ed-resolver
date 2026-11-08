"""Port contracts for the in-memory domain state store."""

from __future__ import annotations

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

from ..base import DrivenPort


@runtime_checkable
class DomainStateReaderPort(DrivenPort, Protocol):
    """Read-only access to the 9 active domain state projections."""

    def get_location(self) -> LocationState:
        """Returns the current location state."""
        ...

    def get_vessel(self) -> VesselState:
        """Returns the current vessel state."""
        ...

    def get_flight(self) -> FlightState:
        """Returns the current flight telemetry state."""
        ...

    def get_cargo(self) -> CargoState:
        """Returns the current cargo state."""
        ...

    def get_commander(self) -> CommanderState:
        """Returns the current commander state."""
        ...

    def get_station(self) -> StationState:
        """Returns the current station state."""
        ...

    def get_carrier(self) -> CarrierState:
        """Returns the current fleet carrier state."""
        ...

    def get_exploration(self) -> ExplorationState:
        """Returns the current exploration state."""
        ...

    def get_powerplay(self) -> PowerplayState:
        """Returns the current powerplay state."""
        ...


@runtime_checkable
class DomainStateWriterPort(DrivenPort, Protocol):
    """Write and mutation access for telemetry event reducers."""

    def set_location(self, state: LocationState) -> None:
        """Atomically replaces the active location state."""
        ...

    def set_vessel(self, state: VesselState) -> None:
        """Atomically replaces the active vessel state."""
        ...

    def set_flight(self, state: FlightState) -> None:
        """Atomically replaces the active flight telemetry state."""
        ...

    def set_cargo(self, state: CargoState) -> None:
        """Atomically replaces the active cargo state."""
        ...

    def set_commander(self, state: CommanderState) -> None:
        """Atomically replaces the active commander state."""
        ...

    def set_station(self, state: StationState) -> None:
        """Atomically replaces the active station state."""
        ...

    def set_carrier(self, state: CarrierState) -> None:
        """Atomically replaces the active fleet carrier state."""
        ...

    def set_exploration(self, state: ExplorationState) -> None:
        """Atomically replaces the active exploration state."""
        ...

    def set_powerplay(self, state: PowerplayState) -> None:
        """Atomically replaces the active powerplay state."""
        ...
