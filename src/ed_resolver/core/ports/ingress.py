"""Driven ingress port protocol declarations."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from ed_resolver.core.ports.base import DrivenPort
from ed_resolver.core.ports.envelope import RawTelemetryEnvelope


@runtime_checkable
class TelemetryIngressPort(DrivenPort, Protocol):
    """Driven port protocol yielding continuous raw telemetry envelopes."""

    def stream_envelopes(self) -> AsyncIterator[RawTelemetryEnvelope]:
        """Asynchronously yield raw envelopes from the underlying transport stream."""
        ...

    async def aclose(self) -> None:
        """Cleanly release open stream or network resources."""
        ...
