"""Driven runtime worker continuously draining ingress streams into core reducers."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from ed_resolver.adapters.driven.runtime.deserializer import TelemetryPayloadDeserializer
from ed_resolver.adapters.driven.runtime.metrics import IngressWorkerMetrics
from ed_resolver.adapters.driven.runtime.quarantine import QuarantineDeadLetterQueue
from ed_resolver.core.domain.classification.classifier import IngressClassifier
from ed_resolver.core.errors import (
    WorkerAlreadyRunningError,
    WorkerLifecycleTimeoutError,
    WorkerNotRunningError,
)
from ed_resolver.core.ports.driving.reduction import ReduceTelemetryEventPort
from ed_resolver.core.ports.envelope import RawTelemetryEnvelope
from ed_resolver.core.ports.ingress import TelemetryIngressPort

logger = logging.getLogger(__name__)


class TelemetryIngressWorker:
    """Asynchronous runtime worker draining ingress streams into domain reducers."""

    def __init__(
        self,
        ingress_port: TelemetryIngressPort,
        classifier: IngressClassifier,
        reducer_pipeline: ReduceTelemetryEventPort | Any,
        deserializer: TelemetryPayloadDeserializer | None = None,
        quarantine_queue: QuarantineDeadLetterQueue | None = None,
    ) -> None:
        self._ingress_port = ingress_port
        self._classifier = classifier
        self._reducer_pipeline = reducer_pipeline
        self._deserializer = deserializer or TelemetryPayloadDeserializer()
        self._quarantine_queue = quarantine_queue

        self._task: asyncio.Task[None] | None = None
        self._is_running: bool = False
        self._envelopes_received: int = 0
        self._events_reduced: int = 0
        self._quarantined_count: int = 0
        self._last_event_at: datetime | None = None

    @property
    def is_running(self) -> bool:
        """Returns True if background consumption task is active."""
        return self._is_running and self._task is not None and not self._task.done()

    @property
    def metrics(self) -> IngressWorkerMetrics:
        """Diagnostic operational counters."""
        return IngressWorkerMetrics(
            envelopes_received=self._envelopes_received,
            events_reduced=self._events_reduced,
            quarantined_count=self._quarantined_count,
            last_event_at=self._last_event_at,
        )

    async def start(self) -> None:
        """Validates worker state and starts supervised asyncio task draining ingress stream."""
        if self.is_running:
            raise WorkerAlreadyRunningError("TelemetryIngressWorker is already running.")

        self._is_running = True
        self._task = asyncio.create_task(self._run_loop(), name="TelemetryIngressWorkerLoop")

    async def stop(self, timeout: float = 5.0) -> None:
        """Signals task cancellation, awaits completion, and cleans up ingress port."""
        if not self._is_running or self._task is None:
            raise WorkerNotRunningError("Cannot stop an inactive TelemetryIngressWorker.")

        self._is_running = False
        self._task.cancel()

        try:
            await asyncio.wait_for(self._task, timeout=timeout)
        except asyncio.CancelledError:
            pass
        except TimeoutError:
            raise WorkerLifecycleTimeoutError(
                f"Worker loop failed to terminate within {timeout} seconds."
            ) from None
        finally:
            self._task = None
            await self._ingress_port.aclose()

    async def process_envelope(self, envelope: RawTelemetryEnvelope) -> None:
        """Processes single envelope: deserialize, classify, reduce, or quarantine."""
        self._envelopes_received += 1
        try:
            event = self._deserializer.deserialize(envelope.raw_payload)
            if event is None:
                raise ValueError("Payload deserialized to empty event.")

            archetype = self._classifier.classify(event)
            self._reducer_pipeline.reduce(event, archetype)
            self._events_reduced += 1
            self._last_event_at = envelope.received_at
        except Exception as exc:
            self._quarantined_count += 1
            if self._quarantine_queue is not None:
                self._quarantine_queue.put(envelope, exc)
            else:
                logger.warning(
                    "Payload quarantined without active DLQ: %s (Error: %s)",
                    envelope.source_uri,
                    exc,
                )

    async def _run_loop(self) -> None:
        """Internal asynchronous consumption loop."""
        try:
            async for envelope in self._ingress_port.stream_envelopes():
                if not self._is_running:
                    break
                await self.process_envelope(envelope)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("Unhandled exception in TelemetryIngressWorker loop: %s", exc)
            raise
        finally:
            self._is_running = False
