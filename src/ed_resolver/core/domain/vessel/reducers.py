"""Pure domain reduction functions for VesselState."""

from __future__ import annotations

import dataclasses
from typing import Any

from .models import VesselState


def reduce_vessel(current: VesselState, event: Any) -> VesselState:
    """Derives updated VesselState from telemetry events."""
    event_type = type(event).__name__

    if event_type in ("Loadout", "LoadGame", "ShipyardBuy", "ShipyardSwap"):
        return dataclasses.replace(
            current,
            ship_name=getattr(event, "ship_name", current.ship_name),
            ship_ident=getattr(event, "ship_ident", current.ship_ident),
            ship_type=getattr(event, "ship", getattr(event, "ship_type", current.ship_type)),
            hull_value=getattr(event, "hull_value", current.hull_value),
            modules_value=getattr(event, "modules_value", current.modules_value),
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
            is_in_srv=getattr(event, "sr_v", False),
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
