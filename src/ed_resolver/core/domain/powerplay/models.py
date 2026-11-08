"""Powerplay domain state models."""

from __future__ import annotations

from dataclasses import dataclass

from ..exceptions import DomainValidationError


@dataclass(frozen=True, slots=True)
class PowerplayState:
    """Powerplay faction pledge, active merits, rank, and weekly nominations."""

    power: str | None = None
    merits: int = 0
    votes: int = 0
    is_pledged: bool = False

    def __post_init__(self) -> None:
        """Validates merits and votes counters."""
        if self.merits < 0:
            raise DomainValidationError("Powerplay merits cannot be negative.")
        if self.votes < 0:
            raise DomainValidationError("Powerplay votes cannot be negative.")
