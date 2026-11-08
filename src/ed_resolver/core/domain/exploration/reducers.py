"""Pure domain reduction functions for ExplorationState."""

from __future__ import annotations

import dataclasses
from typing import Any

from .models import ExplorationState


def reduce_exploration(current: ExplorationState, event: Any) -> ExplorationState:
    """Derives updated ExplorationState from exploration survey events."""
    event_type = type(event).__name__

    if event_type in ("FSDJump", "Location"):
        return dataclasses.replace(
            current,
            system_name=getattr(event, "star_system", current.system_name),
            body_count=getattr(event, "body_count", None),
            all_bodies_found=False,
        )

    if event_type == "FSSDiscoveryScan":
        return dataclasses.replace(
            current,
            system_name=getattr(event, "system_name", current.system_name),
            body_count=getattr(event, "body_count", current.body_count),
        )

    if event_type == "FSSAllBodiesFound":
        return dataclasses.replace(
            current,
            system_name=getattr(event, "system_name", current.system_name),
            all_bodies_found=True,
        )

    if event_type == "ScanOrganic":
        return dataclasses.replace(
            current,
            organic_sample_count=current.organic_sample_count + 1,
        )

    return current
