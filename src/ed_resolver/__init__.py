"""Package root for ed-resolver."""

from ed_resolver.adapters.driving.facade import AmbientTelemetryFacade
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

__version__ = "0.2.0"

__all__ = [
    "__version__",
    "AmbientTelemetryFacade",
    "CargoState",
    "CarrierState",
    "CommanderState",
    "ExplorationState",
    "FlightState",
    "LocationState",
    "PowerplayState",
    "StationState",
    "VesselState",
]
