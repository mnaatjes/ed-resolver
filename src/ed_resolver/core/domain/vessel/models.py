"""Vessel domain state models."""

from __future__ import annotations

from dataclasses import dataclass

from ..exceptions import DomainValidationError


@dataclass(frozen=True, slots=True)
class VesselState:
    """Current vessel, active loadout, suit, and SRV operational truth."""

    ship_name: str | None = None
    ship_ident: str | None = None
    ship_type: str | None = None
    hull_value: int | None = None
    modules_value: int | None = None
    is_on_foot: bool = False
    is_in_srv: bool = False

    def __post_init__(self) -> None:
        """Validates situational mutual exclusivity."""
        if self.is_on_foot and self.is_in_srv:
            raise DomainValidationError("Commander cannot simultaneously be on foot and in an SRV.")
