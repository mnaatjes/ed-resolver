"""Pure domain reduction functions for LocationState."""

from __future__ import annotations

import dataclasses
from typing import Any

from .models import LocationState


def _get_val(obj: Any, *keys: str, default: Any = None) -> Any:
    for k in keys:
        if hasattr(obj, k):
            v = getattr(obj, k)
            if v is not None:
                return v
    return default


def reduce_location(current: LocationState, event: Any) -> LocationState:
    """Derives updated LocationState from telemetry events."""
    event_type = type(event).__name__

    if event_type in ("FSDJump", "Location", "CarrierJump"):
        star_pos = _get_val(event, "StarPos", "star_pos")
        pos_tuple = current.star_pos
        if star_pos is not None:
            if hasattr(star_pos, "x") and hasattr(star_pos, "y") and hasattr(star_pos, "z"):
                pos_tuple = (float(star_pos.x), float(star_pos.y), float(star_pos.z))
            elif isinstance(star_pos, tuple | list) and len(star_pos) == 3:
                pos_tuple = (float(star_pos[0]), float(star_pos[1]), float(star_pos[2]))

        return dataclasses.replace(
            current,
            system_name=_get_val(event, "StarSystem", "star_system", default=current.system_name),
            system_address=_get_val(
                event, "SystemAddress", "system_address", default=current.system_address
            ),
            star_pos=pos_tuple,
            body_name=_get_val(event, "Body", "body", default=current.body_name),
            body_id=_get_val(event, "BodyID", "body_id", default=current.body_id),
            station_name=_get_val(event, "StationName", "station_name"),
            station_type=_get_val(event, "StationType", "station_type"),
            docked=_get_val(event, "Docked", "docked", default=False),
            in_supercruise=False,
            on_surface=False,
        )

    if event_type == "Docked":
        return dataclasses.replace(
            current,
            station_name=_get_val(
                event, "StationName", "station_name", default=current.station_name
            ),
            station_type=_get_val(
                event, "StationType", "station_type", default=current.station_type
            ),
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
            body_name=_get_val(event, "Body", "body", default=current.body_name),
            body_id=_get_val(event, "BodyID", "body_id", default=current.body_id),
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
            body_name=_get_val(event, "Body", "body", default=current.body_name),
            body_id=_get_val(event, "BodyID", "body_id", default=current.body_id),
        )

    if event_type == "Liftoff":
        return dataclasses.replace(
            current,
            on_surface=False,
        )

    return current
