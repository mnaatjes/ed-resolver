"""Permissive deserializer service converting raw telemetry JSON into typed ed-models."""

from __future__ import annotations

import json
import logging
from typing import Any

from ed_models import JournalEvent, StatusTelemetry, create_domain_facade, parse_journal_event

logger = logging.getLogger(__name__)


class TelemetryPayloadDeserializer:
    """Driven runtime service deserializing raw JSON into typed ed-models."""

    def __init__(self) -> None:
        self._facade = create_domain_facade()

    def deserialize(self, raw_payload: str) -> JournalEvent | StatusTelemetry | None:
        """Parses raw JSON string into a strongly typed ed-models event or status entity.

        Permissiveness Guarantees:
        - Extra unknown keys from new game patches are silently ignored by ed-models.
        - Raises ValueError or json.JSONDecodeError on malformed JSON or unrecognized event
          structures, triggering worker quarantine routing without halting the stream.
        """
        data: dict[str, Any] = json.loads(raw_payload)

        # 1. 1 Hz Cockpit Status Bitfields (Status.json format has 'Flags' integer)
        if "Flags" in data:
            flags = int(data.get("Flags", 0))
            flags2 = int(data.get("Flags2", 0))
            raw_pips = data.get("Pips", [4, 4, 4])
            if isinstance(raw_pips, list) and len(raw_pips) >= 3:
                pips = (int(raw_pips[0]), int(raw_pips[1]), int(raw_pips[2]))
            else:
                pips = (4, 4, 4)

            fuel = data.get("Fuel", {})
            fuel_main = float(fuel.get("FuelMain", 0.0)) if isinstance(fuel, dict) else 0.0
            fuel_reservoir = (
                float(fuel.get("FuelReservoir", 0.0)) if isinstance(fuel, dict) else 0.0
            )
            cargo = int(data.get("Cargo", 0))
            legal_state = str(data.get("LegalState", "Clean"))

            return self._facade.parse_telemetry(
                flags=flags,
                flags2=flags2,
                pips=pips,
                fuel_main=fuel_main,
                fuel_reservoir=fuel_reservoir,
                cargo=cargo,
                legal_state=legal_state,
            )

        # 2. Event-driven telemetry (Journal.*.log and snapshot files with 'event' key)
        if "event" in data:
            return parse_journal_event(data)

        raise ValueError("Payload missing recognizable telemetry markers ('event' or 'Flags').")
