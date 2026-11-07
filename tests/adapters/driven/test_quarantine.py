"""Unit tests for QuarantineDeadLetterQueue ring buffer."""

from __future__ import annotations

from datetime import datetime

from ed_resolver.adapters.driven.runtime.quarantine import QuarantineDeadLetterQueue
from ed_resolver.core.ports.envelope import RawTelemetryEnvelope


def test_quarantine_queue_stores_and_evicts() -> None:
    queue = QuarantineDeadLetterQueue(max_capacity=3)
    assert len(queue) == 0

    for i in range(5):
        envelope = RawTelemetryEnvelope(
            raw_payload=f'{{"count": {i}}}',
            received_at=datetime.now(),
            source_uri=f"test://uri/{i}",
        )
        queue.put(envelope, ValueError(f"Error {i}"))

    # Bounded to max_capacity
    assert len(queue) == 3

    recent = queue.get_recent(limit=10)
    assert len(recent) == 3
    # FIFO: Should contain items 2, 3, 4
    assert recent[0].envelope.source_uri == "test://uri/2"
    assert recent[1].envelope.source_uri == "test://uri/3"
    assert recent[2].envelope.source_uri == "test://uri/4"
    assert recent[2].error_message == "Error 4"
    assert recent[2].error_type == "ValueError"
