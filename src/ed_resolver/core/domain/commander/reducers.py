"""Pure domain reduction functions for CommanderState."""

from __future__ import annotations

import dataclasses
from typing import Any

from .models import CommanderState


def _get_val(obj: Any, *keys: str, default: Any = None) -> Any:
    for k in keys:
        if hasattr(obj, k):
            v = getattr(obj, k)
            if v is not None:
                return v
    return default


def reduce_commander(current: CommanderState, event: Any) -> CommanderState:
    """Derives updated CommanderState from profile and financial events."""
    event_type = type(event).__name__

    if event_type == "Commander":
        return dataclasses.replace(
            current,
            name=_get_val(event, "Name", "name", default=current.name),
            fid=_get_val(event, "FID", "fid", default=current.fid),
        )

    if event_type == "LoadGame":
        credits_val = _get_val(event, "Credits", "credits", default=current.credits)
        loan_val = _get_val(event, "Loan", "loan", default=current.loan)
        return dataclasses.replace(
            current,
            name=_get_val(event, "Commander", "commander", default=current.name),
            fid=_get_val(event, "FID", "fid", default=current.fid),
            credits=max(0, credits_val),
            loan=max(0, loan_val),
        )

    if event_type in ("CommitCrime", "Bounty"):
        return dataclasses.replace(current, is_wanted=True)

    return current
