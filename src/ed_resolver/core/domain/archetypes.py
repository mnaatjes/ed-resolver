"""Behavioral reduction archetypes for Elite Dangerous telemetry events."""

from __future__ import annotations

from enum import Enum


class TelemetryArchetype(str, Enum):
    """Behavioral reduction archetypes for Elite Dangerous telemetry events."""

    EPOCH_MILESTONE = "EPOCH_MILESTONE"
    CONTEXT_MUTATOR = "CONTEXT_MUTATOR"
    EDGE_TRANSITION = "EDGE_TRANSITION"
    METRIC_QUANTIZER = "METRIC_QUANTIZER"
    PASSIVE = "PASSIVE"
