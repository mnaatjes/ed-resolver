"""Unit tests for TelemetryPayloadDeserializer."""

from __future__ import annotations

import pytest
from ed_models import JournalEvent, StatusTelemetry

from ed_resolver.adapters.driven.runtime.deserializer import TelemetryPayloadDeserializer


def test_deserialize_journal_event() -> None:
    deserializer = TelemetryPayloadDeserializer()
    payload = (
        '{"timestamp": "2026-11-06T20:00:00Z", "event": "FSDJump", '
        '"StarSystem": "Sol", "ExtraFutureField": 123}'
    )
    event = deserializer.deserialize(payload)
    assert isinstance(event, JournalEvent)
    assert getattr(event, "event", "") == "FSDJump"
    assert getattr(event, "StarSystem", "") == "Sol"


def test_deserialize_status_telemetry() -> None:
    deserializer = TelemetryPayloadDeserializer()
    payload = (
        '{"timestamp": "2026-11-06T20:00:00Z", "Flags": 16, "Flags2": 0, '
        '"Pips": [2, 4, 2], "Fuel": {"FuelMain": 32.0}}'
    )
    status = deserializer.deserialize(payload)
    assert isinstance(status, StatusTelemetry)
    assert status.flags.value == 16
    assert status.pips == (2, 4, 2)
    assert status.fuel_main == 32.0


def test_deserialize_invalid_payload_raises_value_error() -> None:
    deserializer = TelemetryPayloadDeserializer()
    with pytest.raises(ValueError, match="missing recognizable telemetry markers"):
        deserializer.deserialize('{"foo": "bar"}')
