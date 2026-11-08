"""Pure domain reduction functions for ExplorationState."""

from __future__ import annotations

import dataclasses
from typing import Any

from .models import ExplorationState


def _get_val(obj: Any, *keys: str, default: Any = None) -> Any:
    for k in keys:
        if hasattr(obj, k):
            v = getattr(obj, k)
            if v is not None:
                return v
    return default


def reduce_exploration(current: ExplorationState, event: Any) -> ExplorationState:
    """Derives updated ExplorationState from exploration survey events."""
    event_type = type(event).__name__

    if event_type in ("FSDJump", "Location"):
        return dataclasses.replace(
            current,
            system_name=_get_val(event, "StarSystem", "star_system", default=current.system_name),
            body_count=_get_val(event, "BodyCount", "body_count", default=None),
            all_bodies_found=False,
        )

    if event_type == "FSSDiscoveryScan":
        return dataclasses.replace(
            current,
            system_name=_get_val(event, "SystemName", "system_name", default=current.system_name),
            body_count=_get_val(event, "BodyCount", "body_count", default=current.body_count),
        )

    if event_type == "FSSAllBodiesFound":
        return dataclasses.replace(
            current,
            system_name=_get_val(event, "SystemName", "system_name", default=current.system_name),
            all_bodies_found=True,
        )

    if event_type == "ScanOrganic":
        return dataclasses.replace(
            current,
            organic_sample_count=current.organic_sample_count + 1,
        )

    return current
