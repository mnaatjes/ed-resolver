"""Pure domain reduction functions for CarrierState."""

from __future__ import annotations

import dataclasses
from typing import Any

from .models import CarrierState


def reduce_carrier(current: CarrierState, event: Any) -> CarrierState:
    """Derives updated CarrierState from carrier management events."""
    event_type = type(event).__name__

    if event_type in ("CarrierStats", "CarrierFinance"):
        fuel = getattr(event, "fuel_level", current.fuel_level)
        return dataclasses.replace(
            current,
            carrier_id=getattr(event, "carrier_id", current.carrier_id),
            callsign=getattr(event, "callsign", current.callsign),
            balance=getattr(event, "carrier_balance", getattr(event, "balance", current.balance)),
            fuel_level=max(0, fuel) if fuel is not None else None,
        )

    if event_type == "CarrierDepositFuel":
        fuel_deposited = getattr(event, "amount", 0)
        curr_fuel = current.fuel_level or 0
        return dataclasses.replace(current, fuel_level=curr_fuel + fuel_deposited)

    if event_type == "CarrierJumpRequest":
        return dataclasses.replace(
            current,
            pending_jump_target=getattr(event, "system_name", current.pending_jump_target),
        )

    if event_type == "CarrierJumpCancelled":
        return dataclasses.replace(current, pending_jump_target=None)

    return current
