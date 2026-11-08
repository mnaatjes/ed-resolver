"""Pure domain reduction functions for PowerplayState."""

from __future__ import annotations

import dataclasses
from typing import Any

from .models import PowerplayState


def _get_val(obj: Any, *keys: str, default: Any = None) -> Any:
    for k in keys:
        if hasattr(obj, k):
            v = getattr(obj, k)
            if v is not None:
                return v
    return default


def reduce_powerplay(current: PowerplayState, event: Any) -> PowerplayState:
    """Derives updated PowerplayState from galactic power events."""
    event_type = type(event).__name__

    if event_type == "Powerplay":
        merits_val = _get_val(event, "Merits", "merits", default=current.merits)
        votes_val = _get_val(event, "Votes", "votes", default=current.votes)
        return dataclasses.replace(
            current,
            power=_get_val(event, "Power", "power", default=current.power),
            merits=max(0, merits_val),
            votes=max(0, votes_val),
            is_pledged=True,
        )

    if event_type in ("PowerplayDefect", "PowerplayLeave"):
        return PowerplayState()

    return current
