"""Pure domain reduction functions for StationState."""

from __future__ import annotations

import dataclasses
from typing import Any

from .models import StationState


def reduce_station(current: StationState, event: Any) -> StationState:
    """Derives updated StationState from docking events."""
    event_type = type(event).__name__

    if event_type == "Docked":
        services = getattr(event, "station_services", []) or []
        services_set = {str(s).lower() for s in services}

        return dataclasses.replace(
            current,
            station_name=getattr(event, "station_name", current.station_name),
            station_type=getattr(event, "station_type", current.station_type),
            market_id=getattr(event, "market_id", current.market_id),
            controlling_faction=getattr(event, "station_faction", current.controlling_faction),
            has_market="commodities" in services_set or "market" in services_set,
            has_shipyard="shipyard" in services_set,
            has_outfitting="outfitting" in services_set,
        )

    if event_type == "Undocked":
        return StationState()

    return current
