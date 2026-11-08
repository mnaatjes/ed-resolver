"""Pure domain service classifying typed ed-models into behavioral archetypes."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from ed_resolver.core.domain.archetypes import TelemetryArchetype
from ed_resolver.core.domain.classification.registry import DEFAULT_ARCHETYPE_REGISTRY


class IngressClassifier:
    """Pure domain service classifying typed ed-models into behavioral archetypes."""

    def __init__(
        self,
        registry: Mapping[type, TelemetryArchetype] | None = None,
        overrides: Mapping[type, TelemetryArchetype] | None = None,
    ) -> None:
        base = dict(registry if registry is not None else DEFAULT_ARCHETYPE_REGISTRY)
        if overrides:
            base.update(overrides)
        self._registry: Mapping[type, TelemetryArchetype] = MappingProxyType(base)

    def classify(self, event: object) -> TelemetryArchetype | None:
        """Resolves archetype in O(1) time based on Python type."""
        return self._registry.get(type(event))
