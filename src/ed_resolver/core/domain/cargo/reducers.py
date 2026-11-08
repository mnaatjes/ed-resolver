"""Pure domain reduction functions for CargoState."""

from __future__ import annotations

import dataclasses
from types import MappingProxyType
from typing import Any

from .models import CargoState


def _get_val(obj: Any, *keys: str, default: Any = None) -> Any:
    for k in keys:
        if hasattr(obj, k):
            v = getattr(obj, k)
            if v is not None:
                return v
    return default


def reduce_cargo(current: CargoState, event: Any) -> CargoState:
    """Derives updated CargoState from inventory and cargo events."""
    event_type = type(event).__name__

    if event_type == "Cargo":
        inventory_data: dict[str, int] = {}
        raw_inv = _get_val(event, "Inventory", "inventory")
        if isinstance(raw_inv, list):
            for item in raw_inv:
                name = _get_val(item, "Name", "name", default=str(item))
                qty = _get_val(item, "Count", "count", default=0)
                inventory_data[name] = qty
        elif isinstance(raw_inv, dict):
            inventory_data = dict(raw_inv)

        count = _get_val(event, "Count", "count", default=sum(inventory_data.values()))
        vessel = _get_val(event, "Vessel", "vessel", default=current.vessel_type)

        return dataclasses.replace(
            current,
            count=max(0, count),
            inventory=MappingProxyType(inventory_data),
            vessel_type=vessel,
        )

    if event_type == "CollectCargo":
        commodity = _get_val(event, "Type", "type", default="Unknown")
        inv = dict(current.inventory)
        inv[commodity] = inv.get(commodity, 0) + 1
        return dataclasses.replace(
            current,
            count=current.count + 1,
            inventory=MappingProxyType(inv),
        )

    if event_type == "EjectCargo":
        commodity = _get_val(event, "Type", "type", default="Unknown")
        count_ejected = _get_val(event, "Count", "count", default=1)
        inv = dict(current.inventory)
        if commodity in inv:
            new_qty = max(0, inv[commodity] - count_ejected)
            if new_qty == 0:
                del inv[commodity]
            else:
                inv[commodity] = new_qty
        new_count = max(0, current.count - count_ejected)
        return dataclasses.replace(
            current,
            count=new_count,
            inventory=MappingProxyType(inv),
        )

    return current
