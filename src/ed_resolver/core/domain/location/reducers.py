"""Pure domain reduction functions for LocationState."""

from __future__ import annotations

import dataclasses
from typing import Any

from .models import LocationState


def reduce_location(current: LocationState, event: Any) -> LocationState:
    """Derives updated LocationState from telemetry events."""
    event_type = type(event).__name__

    if event_type in ("FSDJump", "Location", "CarrierJump"):
        star_pos = getattr(event, "star_pos", None)
        pos_tuple = current.star_pos
        if star_pos is not None:
            if hasattr(star_pos, "x") and hasattr(star_pos, "y") and hasattr(star_pos, "z"):
                pos_tuple = (float(star_pos.x), float(star_pos.y), float(star_pos.z))
            elif isinstance(star_pos, tuple | list) and len(star_pos) == 3:
                pos_tuple = (float(star_pos[0]), float(star_pos[1]), float(star_pos[2]))

        return dataclasses.replace(
            current,
            system_name=getattr(event, "star_system", current.system_name),
            system_address=getattr(event, "system_address", current.system_address),
            star_pos=pos_tuple,
            body_name=getattr(event, "body", current.body_name),
            body_id=getattr(event, "body_id", current.body_id),
            station_name=getattr(event, "station_name", None),
            station_type=getattr(event, "station_type", None),
            docked=getattr(event, "docked", False),
            in_supercruise=False,
            on_surface=False,
        )

    if event_type == "Docked":
        return dataclasses.replace(
            current,
            station_name=getattr(event, "station_name", current.station_name),
            station_type=getattr(event, "station_type", current.station_type),
            docked=True,
            in_supercruise=False,
        )

    if event_type == "Undocked":
        return dataclasses.replace(
            current,
            station_name=None,
            station_type=None,
            docked=False,
        )

    if event_type == "SupercruiseExit":
        return dataclasses.replace(
            current,
            body_name=getattr(event, "body", current.body_name),
            body_id=getattr(event, "body_id", current.body_id),
            in_supercruise=False,
        )

    if event_type == "SupercruiseEntry":
        return dataclasses.replace(
            current,
            in_supercruise=True,
            docked=False,
            on_surface=False,
        )

    if event_type == "Touchdown":
        return dataclasses.replace(
            current,
            on_surface=True,
            body_name=getattr(event, "body", current.body_name),
            body_id=getattr(event, "body_id", current.body_id),
        )

    if event_type == "Liftoff":
        return dataclasses.replace(
            current,
            on_surface=False,
        )

    return current
