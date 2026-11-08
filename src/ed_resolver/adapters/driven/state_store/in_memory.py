"""In-memory implementation of the domain state store using atomic pointer swapping."""

from __future__ import annotations

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
    """Thread-safe in-memory domain state store using atomic pointer replacement."""

    def __init__(self) -> None:
        """Initializes the store with deterministic cold-start default states."""
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
        """Returns the active location state."""
        return self._location

    def get_vessel(self) -> VesselState:
        """Returns the active vessel state."""
        return self._vessel

    def get_flight(self) -> FlightState:
        """Returns the active flight telemetry state."""
        return self._flight

    def get_cargo(self) -> CargoState:
        """Returns the active cargo state."""
        return self._cargo

    def get_commander(self) -> CommanderState:
        """Returns the active commander state."""
        return self._commander

    def get_station(self) -> StationState:
        """Returns the active station state."""
        return self._station

    def get_carrier(self) -> CarrierState:
        """Returns the active fleet carrier state."""
        return self._carrier

    def get_exploration(self) -> ExplorationState:
        """Returns the active exploration state."""
        return self._exploration

    def get_powerplay(self) -> PowerplayState:
        """Returns the active powerplay state."""
        return self._powerplay

    # --- Writer Port Mutators ---

    def set_location(self, state: LocationState) -> None:
        """Atomically replaces the active location state."""
        self._location = state

    def set_vessel(self, state: VesselState) -> None:
        """Atomically replaces the active vessel state."""
        self._vessel = state

    def set_flight(self, state: FlightState) -> None:
        """Atomically replaces the active flight telemetry state."""
        self._flight = state

    def set_cargo(self, state: CargoState) -> None:
        """Atomically replaces the active cargo state."""
        self._cargo = state

    def set_commander(self, state: CommanderState) -> None:
        """Atomically replaces the active commander state."""
        self._commander = state

    def set_station(self, state: StationState) -> None:
        """Atomically replaces the active station state."""
        self._station = state

    def set_carrier(self, state: CarrierState) -> None:
        """Atomically replaces the active fleet carrier state."""
        self._carrier = state

    def set_exploration(self, state: ExplorationState) -> None:
        """Atomically replaces the active exploration state."""
        self._exploration = state

    def set_powerplay(self, state: PowerplayState) -> None:
        """Atomically replaces the active powerplay state."""
        self._powerplay = state
