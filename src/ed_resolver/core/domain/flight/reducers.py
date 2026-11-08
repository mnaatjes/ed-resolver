"""Pure domain reduction functions for FlightState."""

from __future__ import annotations

import dataclasses
from typing import Any

from .models import FlightState


def reduce_flight(current: FlightState, event: Any) -> FlightState:
    """Derives updated FlightState from status ticks or continuous events."""
    event_type = type(event).__name__

    if event_type in ("Status", "StatusEvent"):
        flags = getattr(event, "flags", None)
        fuel = getattr(event, "fuel", None)
        fuel_main = current.fuel_main
        fuel_res = current.fuel_reservoir

        if fuel is not None:
            fuel_main = getattr(fuel, "fuel_main", fuel_main)
            fuel_res = getattr(fuel, "fuel_reservoir", fuel_res)

        gear = current.landing_gear_down
        hardpoints = current.hardpoints_deployed
        fa_off = current.flight_assist_off
        night_vis = current.night_vision
        supercruise = current.in_supercruise

        if flags is not None and isinstance(flags, int):
            # Bit 2: Landing gear, Bit 6: Hardpoints, Bit 11: FA-Off,
            # Bit 28: Night Vision, Bit 4: Supercruise
            gear = bool(flags & (1 << 2))
            hardpoints = bool(flags & (1 << 6))
            fa_off = bool(flags & (1 << 11))
            night_vis = bool(flags & (1 << 28))
            supercruise = bool(flags & (1 << 4))

        return dataclasses.replace(
            current,
            in_supercruise=supercruise,
            landing_gear_down=gear,
            hardpoints_deployed=hardpoints,
            flight_assist_off=fa_off,
            night_vision=night_vis,
            fuel_main=fuel_main,
            fuel_reservoir=fuel_res,
        )

    if event_type == "SupercruiseEntry":
        return dataclasses.replace(current, in_supercruise=True)

    if event_type == "SupercruiseExit":
        return dataclasses.replace(current, in_supercruise=False)

    return current
