"""Unit and lifecycle tests for TelemetryIngressWorker."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import pytest

from ed_resolver.adapters.driven.ingress.memory import MemoryQueueAdapter
from ed_resolver.adapters.driven.runtime.quarantine import QuarantineDeadLetterQueue
from ed_resolver.adapters.driven.runtime.worker import TelemetryIngressWorker
from ed_resolver.core.domain.archetypes import TelemetryArchetype
from ed_resolver.core.domain.classification.classifier import IngressClassifier
from ed_resolver.core.errors import (
    WorkerAlreadyRunningError,
    WorkerNotRunningError,
)
from ed_resolver.core.ports.envelope import RawTelemetryEnvelope


class FakeReducerPipeline:
    """Mock state reducer pipeline capturing event dispatches."""

    def __init__(self) -> None:
        self.reduced_events: list[tuple[Any, TelemetryArchetype | None]] = []

    def reduce(self, event: Any, archetype: TelemetryArchetype | None) -> None:
        self.reduced_events.append((event, archetype))


@pytest.mark.asyncio
async def test_worker_lifecycle_and_processing() -> None:
    queue_adapter = MemoryQueueAdapter()
    classifier = IngressClassifier()
    pipeline = FakeReducerPipeline()
    quarantine = QuarantineDeadLetterQueue(max_capacity=10)

    worker = TelemetryIngressWorker(
        ingress_port=queue_adapter,
        classifier=classifier,
        reducer_pipeline=pipeline,
        quarantine_queue=quarantine,
    )

    assert not worker.is_running
    await worker.start()
    assert worker.is_running

    # Duplicate start raises WorkerAlreadyRunningError
    with pytest.raises(WorkerAlreadyRunningError):
        await worker.start()

    # 1. Enqueue valid FSDJump event
    valid_env = RawTelemetryEnvelope(
        raw_payload=(
            '{"timestamp": "2026-11-06T20:00:00Z", "event": "FSDJump", "StarSystem": "Achenar"}'
        ),
        received_at=datetime.now(),
        source_uri="memory://valid",
    )
    await queue_adapter.put(valid_env)

    # 2. Enqueue malformed JSON (quarantine target)
    bad_env = RawTelemetryEnvelope(
        raw_payload="corrupted_not_json",
        received_at=datetime.now(),
        source_uri="memory://bad",
    )
    await queue_adapter.put(bad_env)

    # Allow worker loop to process queue items
    await asyncio.sleep(0.1)

    # Stop worker gracefully
    await worker.stop()
    assert not worker.is_running

    # Stopping an inactive worker raises WorkerNotRunningError
    with pytest.raises(WorkerNotRunningError):
        await worker.stop()

    # Assert metric counters
    metrics = worker.metrics
    assert metrics.envelopes_received == 2
    assert metrics.events_reduced == 1
    assert metrics.quarantined_count == 1

    # Assert pipeline reduction
    assert len(pipeline.reduced_events) == 1
    reduced_event, archetype = pipeline.reduced_events[0]
    assert getattr(reduced_event, "StarSystem", "") == "Achenar"
    assert archetype == TelemetryArchetype.EPOCH_MILESTONE

    # Assert quarantine queue captured bad payload
    assert len(quarantine) == 1
    quarantined = quarantine.get_recent()[0]
    assert quarantined.envelope.source_uri == "memory://bad"
    assert "JSONDecodeError" in quarantined.error_type
