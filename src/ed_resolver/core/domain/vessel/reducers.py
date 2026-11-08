"""Pure domain reduction functions for VesselState."""

from __future__ import annotations

import dataclasses
from typing import Any

from .models import VesselState


def _get_val(obj: Any, *keys: str, default: Any = None) -> Any:
    for k in keys:
        if hasattr(obj, k):
            v = getattr(obj, k)
            if v is not None:
                return v
    return default


def reduce_vessel(current: VesselState, event: Any) -> VesselState:
    """Derives updated VesselState from telemetry events."""
    event_type = type(event).__name__

    if event_type in ("Loadout", "LoadGame", "ShipyardBuy", "ShipyardSwap"):
        return dataclasses.replace(
            current,
            ship_name=_get_val(event, "ShipName", "ship_name", default=current.ship_name),
            ship_ident=_get_val(event, "ShipIdent", "ship_ident", default=current.ship_ident),
            ship_type=_get_val(
                event, "Ship", "ship", "ShipType", "ship_type", default=current.ship_type
            ),
            hull_value=_get_val(event, "HullValue", "hull_value", default=current.hull_value),
            modules_value=_get_val(
                event, "ModulesValue", "modules_value", default=current.modules_value
            ),
            is_on_foot=False,
            is_in_srv=False,
        )

    if event_type in ("SuitLoadout", "Disembark"):
        return dataclasses.replace(
            current,
            is_on_foot=True,
            is_in_srv=False,
        )

    if event_type == "Embark":
        return dataclasses.replace(
            current,
            is_on_foot=False,
            is_in_srv=_get_val(event, "SRV", "sr_v", default=False),
        )

    if event_type == "LaunchSRV":
        return dataclasses.replace(
            current,
            is_in_srv=True,
            is_on_foot=False,
        )

    if event_type == "DockSRV":
        return dataclasses.replace(
            current,
            is_in_srv=False,
            is_on_foot=False,
        )

    return current
