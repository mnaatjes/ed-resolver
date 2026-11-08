"""Pure domain reduction functions for CommanderState."""

from __future__ import annotations

import dataclasses
from typing import Any

from .models import CommanderState


def reduce_commander(current: CommanderState, event: Any) -> CommanderState:
    """Derives updated CommanderState from profile and financial events."""
    event_type = type(event).__name__

    if event_type == "Commander":
        return dataclasses.replace(
            current,
            name=getattr(event, "name", current.name),
            fid=getattr(event, "fid", current.fid),
        )

    if event_type == "LoadGame":
        credits_val = getattr(event, "credits", current.credits)
        loan_val = getattr(event, "loan", current.loan)
        return dataclasses.replace(
            current,
            name=getattr(event, "commander", current.name),
            fid=getattr(event, "fid", current.fid),
            credits=max(0, credits_val),
            loan=max(0, loan_val),
        )

    if event_type in ("CommitCrime", "Bounty"):
        return dataclasses.replace(current, is_wanted=True)

    return current
