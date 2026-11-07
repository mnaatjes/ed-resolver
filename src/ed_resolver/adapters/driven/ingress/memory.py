"""In-memory queue adapter for deterministic unit and compliance testing."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from ed_resolver.core.ports.envelope import RawTelemetryEnvelope
from ed_resolver.core.ports.ingress import TelemetryIngressPort


class MemoryQueueAdapter(TelemetryIngressPort):
    """In-memory FIFO queue implementation of TelemetryIngressPort for testing."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[RawTelemetryEnvelope | None] = asyncio.Queue()
        self._is_closed: bool = False

    async def put(self, envelope: RawTelemetryEnvelope) -> None:
        """Pushes an envelope into the test queue."""
        if not self._is_closed:
            await self._queue.put(envelope)

    async def stream_envelopes(self) -> AsyncIterator[RawTelemetryEnvelope]:
        """Asynchronously yield envelopes until queue is closed with a sentinel None."""
        while not self._is_closed:
            item = await self._queue.get()
            if item is None:
                self._queue.task_done()
                break
            try:
                yield item
            finally:
                self._queue.task_done()

    async def aclose(self) -> None:
        """Closes queue and emits sentinel to unblock consumers."""
        self._is_closed = True
        await self._queue.put(None)
