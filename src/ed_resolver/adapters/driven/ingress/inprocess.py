"""In-process listener adapter consuming directly from ed-telemetry's in-memory stream buffer."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from ed_resolver.core.ports.envelope import RawTelemetryEnvelope
from ed_resolver.core.ports.ingress import TelemetryIngressPort

try:
    from ed_telemetry.core.ports.driving.telemetry_port import (  # type: ignore[import-not-found, import-untyped]
        GetTelemetryStreamPort,
    )
except ImportError:
    GetTelemetryStreamPort = None  # type: ignore[assignment, misc]


class EdTelemetryInProcessAdapter(TelemetryIngressPort):
    """Passive listener adapter connecting to an in-process ed-telemetry stream buffer."""

    def __init__(self, stream_source: Any) -> None:
        if GetTelemetryStreamPort is not None and not isinstance(
            stream_source, GetTelemetryStreamPort
        ):
            # Check protocol or duck typing
            if not hasattr(stream_source, "stream_events"):
                type_name = type(stream_source).__name__
                raise TypeError(
                    f"stream_source must implement GetTelemetryStreamPort, got {type_name}"
                )
        self._stream = stream_source
        self._is_closed: bool = False

    async def stream_envelopes(self) -> AsyncIterator[RawTelemetryEnvelope]:
        """Yields envelopes by polling the in-process stream buffer in a worker executor thread."""
        loop = asyncio.get_running_loop()

        def _get_next_event() -> Any:
            try:
                for event_dto in self._stream.stream_events(timeout=0.2):
                    return event_dto
            except Exception:
                return None
            return None

        while not self._is_closed:
            event_dto = await loop.run_in_executor(None, _get_next_event)
            if event_dto is not None:
                payload = getattr(event_dto, "payload_json", None) or str(event_dto)
                ts = getattr(event_dto, "timestamp", None) or datetime.now()
                if not isinstance(ts, datetime):
                    ts = datetime.now()
                yield RawTelemetryEnvelope(
                    raw_payload=payload,
                    received_at=ts,
                    source_uri="in-process:ed-telemetry",
                )
            else:
                await asyncio.sleep(0.05)

    async def aclose(self) -> None:
        """Closes adapter listener."""
        self._is_closed = True
