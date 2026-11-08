"""Universal carrier contract for incoming telemetry across boundary adapters."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class RawTelemetryEnvelope:
    """Universal carrier for incoming telemetry data across all adapters."""

    raw_payload: str
    received_at: datetime
    source_uri: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
