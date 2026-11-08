"""Cargo domain state models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from ..exceptions import DomainValidationError


@dataclass(frozen=True, slots=True)
class CargoState:
    """Current commodity cargo inventory, material quantities, and capacity."""

    count: int = 0
    inventory: Mapping[str, int] = field(default_factory=dict)
    vessel_type: str | None = None

    def __post_init__(self) -> None:
        """Validates non-negative counts and wraps inventory in an immutable view."""
        if self.count < 0:
            raise DomainValidationError("Cargo count cannot be negative.")
        if not isinstance(self.inventory, MappingProxyType):
            object.__setattr__(self, "inventory", MappingProxyType(dict(self.inventory)))
