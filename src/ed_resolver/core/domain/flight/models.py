"""Flight domain state models."""

from __future__ import annotations

from dataclasses import dataclass

from ..exceptions import DomainValidationError


@dataclass(frozen=True, slots=True)
class FlightState:
    """Continuous flight parameters, gear, hardpoints, and fuel measurements."""

    in_supercruise: bool = False
    landing_gear_down: bool = False
    hardpoints_deployed: bool = False
    flight_assist_off: bool = False
    night_vision: bool = False
    fuel_main: float | None = None
    fuel_reservoir: float | None = None

    def __post_init__(self) -> None:
        """Validates fuel levels are non-negative."""
        if self.fuel_main is not None and self.fuel_main < 0:
            raise DomainValidationError("fuel_main cannot be negative.")
        if self.fuel_reservoir is not None and self.fuel_reservoir < 0:
            raise DomainValidationError("fuel_reservoir cannot be negative.")
