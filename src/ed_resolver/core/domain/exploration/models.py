"""Exploration domain state models."""

from __future__ import annotations

from dataclasses import dataclass

from ..exceptions import DomainValidationError


@dataclass(frozen=True, slots=True)
class ExplorationState:
    """Exploration survey progress, discovered bodies, and organic bio discoveries."""

    system_name: str | None = None
    body_count: int | None = None
    all_bodies_found: bool = False
    organic_sample_count: int = 0

    def __post_init__(self) -> None:
        """Validates biological sample counters."""
        if self.organic_sample_count < 0:
            raise DomainValidationError("organic_sample_count cannot be negative.")
