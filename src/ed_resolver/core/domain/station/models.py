"""Station domain state models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StationState:
    """Station services, controlling factions, and market context."""

    station_name: str | None = None
    station_type: str | None = None
    market_id: int | None = None
    controlling_faction: str | None = None
    has_market: bool = False
    has_shipyard: bool = False
    has_outfitting: bool = False

    def __post_init__(self) -> None:
        """Enforces domain invariants on station state."""
