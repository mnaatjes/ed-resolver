"""Diagnostic and operational metrics for TelemetryIngressWorker."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class IngressWorkerMetrics:
    """Read-only operational metrics for TelemetryIngressWorker."""

    envelopes_received: int
    events_reduced: int
    quarantined_count: int
    last_event_at: datetime | None
