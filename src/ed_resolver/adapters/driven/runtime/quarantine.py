"""Quarantine Dead-Letter Queue bounded ring buffer."""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime

from ed_resolver.core.ports.envelope import RawTelemetryEnvelope

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class QuarantinedPayload:
    """Record of an unparseable or rejected raw telemetry envelope."""

    envelope: RawTelemetryEnvelope
    error_message: str
    error_type: str
    quarantined_at: datetime


class QuarantineDeadLetterQueue:
    """Bounded FIFO ring buffer isolating malformed payloads to prevent memory leaks."""

    def __init__(self, max_capacity: int = 500) -> None:
        self._max_capacity = max_capacity
        self._buffer: deque[QuarantinedPayload] = deque(maxlen=max_capacity)

    def put(self, envelope: RawTelemetryEnvelope, error: Exception) -> None:
        """Appends quarantined payload, evicting the oldest entry if max_capacity is reached."""
        record = QuarantinedPayload(
            envelope=envelope,
            error_message=str(error),
            error_type=type(error).__name__,
            quarantined_at=datetime.now(),
        )
        self._buffer.append(record)
        logger.warning(
            "Telemetry payload quarantined: source=%s error=%s: %s",
            envelope.source_uri,
            record.error_type,
            record.error_message,
        )

    def get_recent(self, limit: int = 50) -> list[QuarantinedPayload]:
        """Returns recent quarantined payloads up to limit."""
        return list(self._buffer)[-limit:]

    def __len__(self) -> int:
        return len(self._buffer)
