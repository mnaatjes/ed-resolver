"""Pure domain reduction functions for PowerplayState."""

from __future__ import annotations

import dataclasses
from typing import Any

from .models import PowerplayState


def reduce_powerplay(current: PowerplayState, event: Any) -> PowerplayState:
    """Derives updated PowerplayState from galactic power events."""
    event_type = type(event).__name__

    if event_type == "Powerplay":
        merits_val = getattr(event, "merits", current.merits)
        votes_val = getattr(event, "votes", current.votes)
        return dataclasses.replace(
            current,
            power=getattr(event, "power", current.power),
            merits=max(0, merits_val),
            votes=max(0, votes_val),
            is_pledged=True,
        )

    if event_type in ("PowerplayDefect", "PowerplayLeave"):
        return PowerplayState()

    return current
