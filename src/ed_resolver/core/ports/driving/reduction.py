"""Driving port protocol for domain telemetry reduction pipeline."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from ed_resolver.core.domain.archetypes import TelemetryArchetype

from ..base import DrivingPort


@runtime_checkable
class ReduceTelemetryEventPort(DrivingPort, Protocol):
    """Driving port for dispatching deserialized telemetry events into reduction pipelines."""

    def reduce(self, event: Any, archetype: TelemetryArchetype | None = None) -> None:
        """Processes an event DTO, computes updated domain states, and stores new projections."""
        ...
