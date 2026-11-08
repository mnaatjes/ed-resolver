"""Pure domain reduction functions for StationState."""

from __future__ import annotations

import dataclasses
from typing import Any

from .models import StationState


def _get_val(obj: Any, *keys: str, default: Any = None) -> Any:
    for k in keys:
        if hasattr(obj, k):
            v = getattr(obj, k)
            if v is not None:
                return v
    return default


def reduce_station(current: StationState, event: Any) -> StationState:
    """Derives updated StationState from docking events."""
    event_type = type(event).__name__

    if event_type == "Docked":
        services = _get_val(event, "StationServices", "station_services", default=[]) or []
        services_set = {str(s).lower() for s in services}

        return dataclasses.replace(
            current,
            station_name=_get_val(
                event, "StationName", "station_name", default=current.station_name
            ),
            station_type=_get_val(
                event, "StationType", "station_type", default=current.station_type
            ),
            market_id=_get_val(event, "MarketID", "market_id", default=current.market_id),
            controlling_faction=_get_val(
                event, "StationFaction", "station_faction", default=current.controlling_faction
            ),
            has_market="commodities" in services_set or "market" in services_set,
            has_shipyard="shipyard" in services_set,
            has_outfitting="outfitting" in services_set,
        )

    if event_type == "Undocked":
        return StationState()

    return current
