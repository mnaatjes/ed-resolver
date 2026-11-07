"""Network adapter streaming Server-Sent Events (SSE) from ed-telemetry."""

from __future__ import annotations

import asyncio
import json
import logging
import urllib.request
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from ed_resolver.core.ports.envelope import RawTelemetryEnvelope
from ed_resolver.core.ports.ingress import TelemetryIngressPort

logger = logging.getLogger(__name__)


class EdTelemetryNetworkAdapter(TelemetryIngressPort):
    """Primary network adapter connecting to ed-telemetry /api/v1/stream over HTTP/SSE."""

    def __init__(self, base_url: str = "http://127.0.0.1:8080") -> None:
        self.base_url = base_url.rstrip("/")
        self._is_closed: bool = False

    async def stream_envelopes(self) -> AsyncIterator[RawTelemetryEnvelope]:
        """Streams live envelopes by consuming SSE events from ed-telemetry."""
        url = f"{self.base_url}/api/v1/stream"
        loop = asyncio.get_running_loop()

        def _open_stream() -> Any:
            req = urllib.request.Request(
                url,
                headers={"Accept": "text/event-stream", "User-Agent": "ed-resolver/0.1.0"},
            )
            return urllib.request.urlopen(req, timeout=10.0)

        response = None
        try:
            response = await loop.run_in_executor(None, _open_stream)
        except Exception as exc:
            logger.error("Failed to connect to ed-telemetry stream at %s: %s", url, exc)
            return

        def _read_line() -> bytes:
            if response is None:
                return b""
            line_data = response.readline()
            return bytes(line_data) if line_data else b""

        while not self._is_closed:
            try:
                line_bytes = await loop.run_in_executor(None, _read_line)
                if not line_bytes:
                    await asyncio.sleep(0.1)
                    continue

                line = line_bytes.decode("utf-8").strip()
                if line.startswith("data:"):
                    payload_raw = line[5:].strip()
                    if not payload_raw:
                        continue

                    # Unpack ed-telemetry wire format if wrapped
                    try:
                        wrapper = json.loads(payload_raw)
                        if isinstance(wrapper, dict) and "payload_json" in wrapper:
                            inner_json = wrapper["payload_json"]
                            meta = {
                                "id": wrapper.get("id"),
                                "event_type": wrapper.get("event_type"),
                            }
                        else:
                            inner_json = payload_raw
                            meta = {}
                    except json.JSONDecodeError:
                        inner_json = payload_raw
                        meta = {}

                    yield RawTelemetryEnvelope(
                        raw_payload=inner_json,
                        received_at=datetime.now(),
                        source_uri=url,
                        metadata=meta,
                    )
            except Exception as exc:
                if self._is_closed:
                    break
                logger.warning("Error reading from stream %s: %s", url, exc)
                await asyncio.sleep(1.0)

        if response is not None:
            try:
                response.close()
            except Exception:
                pass

    async def aclose(self) -> None:
        """Closes network connection."""
        self._is_closed = True
