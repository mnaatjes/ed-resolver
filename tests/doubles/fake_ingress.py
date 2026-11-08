"""In-memory test doubles for TelemetryIngressPort satisfying HEXA-TRUTH-27."""

from __future__ import annotations

from ed_resolver.adapters.driven.ingress.memory import MemoryQueueAdapter


class FakeTelemetryIngressAdapter(MemoryQueueAdapter):
    """Test double satisfying FakeTelemetryIngressAdapter double parity."""
