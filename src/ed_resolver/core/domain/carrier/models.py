"""Carrier domain state models."""

from __future__ import annotations

from dataclasses import dataclass

from ..exceptions import DomainValidationError


@dataclass(frozen=True, slots=True)
class CarrierState:
    """Fleet carrier finances, fuel capacity, and pending jump state."""

    carrier_id: int | None = None
    callsign: str | None = None
    balance: int | None = None
    fuel_level: int | None = None
    pending_jump_target: str | None = None

    def __post_init__(self) -> None:
        """Validates carrier fuel capacity is non-negative."""
        if self.fuel_level is not None and self.fuel_level < 0:
            raise DomainValidationError("Carrier fuel level cannot be negative.")
