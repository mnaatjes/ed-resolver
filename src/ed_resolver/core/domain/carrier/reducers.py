"""Pure domain reduction functions for CarrierState."""

from __future__ import annotations

import dataclasses
from typing import Any

from .models import CarrierState


def _get_val(obj: Any, *keys: str, default: Any = None) -> Any:
    for k in keys:
        if hasattr(obj, k):
            v = getattr(obj, k)
            if v is not None:
                return v
    return default


def reduce_carrier(current: CarrierState, event: Any) -> CarrierState:
    """Derives updated CarrierState from carrier management events."""
    event_type = type(event).__name__

    if event_type in ("CarrierStats", "CarrierFinance"):
        fuel = _get_val(event, "FuelLevel", "fuel_level", default=current.fuel_level)
        balance = _get_val(
            event,
            "CarrierBalance",
            "carrier_balance",
            "Balance",
            "balance",
            default=current.balance,
        )
        return dataclasses.replace(
            current,
            carrier_id=_get_val(event, "CarrierID", "carrier_id", default=current.carrier_id),
            callsign=_get_val(event, "Callsign", "callsign", default=current.callsign),
            balance=balance,
            fuel_level=max(0, fuel) if fuel is not None else None,
        )

    if event_type == "CarrierDepositFuel":
        fuel_deposited = _get_val(event, "Amount", "amount", default=0)
        curr_fuel = current.fuel_level or 0
        return dataclasses.replace(current, fuel_level=curr_fuel + fuel_deposited)

    if event_type == "CarrierJumpRequest":
        return dataclasses.replace(
            current,
            pending_jump_target=_get_val(
                event, "SystemName", "system_name", default=current.pending_jump_target
            ),
        )

    if event_type == "CarrierJumpCancelled":
        return dataclasses.replace(current, pending_jump_target=None)

    return current
