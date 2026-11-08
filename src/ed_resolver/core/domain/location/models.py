"""Location domain state models."""

from __future__ import annotations

from dataclasses import dataclass

from ..exceptions import DomainValidationError


@dataclass(frozen=True, slots=True)
class LocationState:
    """Consolidated spatial position, star system, and docking truth."""

    system_name: str | None = None
    system_address: int | None = None
    star_pos: tuple[float, float, float] = (0.0, 0.0, 0.0)
    body_name: str | None = None
    body_id: int | None = None
    station_name: str | None = None
    station_type: str | None = None
    docked: bool = False
    in_supercruise: bool = False
    on_surface: bool = False

    def __post_init__(self) -> None:
        """Validates spatial coordinate integrity."""
        if len(self.star_pos) != 3:
            raise DomainValidationError(
                "star_pos must be a 3-dimensional coordinate tuple (x, y, z)"
            )
