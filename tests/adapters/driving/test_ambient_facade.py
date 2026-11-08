"""End-to-end integration and query tests for AmbientTelemetryFacade and create_resolver."""

from __future__ import annotations

import asyncio
from datetime import datetime

import pytest

from ed_resolver import AmbientTelemetryFacade
from ed_resolver.adapters.driven.ingress.memory import MemoryQueueAdapter
from ed_resolver.adapters.driven.state_store import InMemoryDomainStateStore
from ed_resolver.bootstrap import create_resolver
from ed_resolver.core.domain import LocationState
from ed_resolver.core.ports.envelope import RawTelemetryEnvelope


def test_sub_facades_and_root_predicates_defaults() -> None:
    """Verifies all 9 sub-facades return default models and predicates evaluate false."""
    store = InMemoryDomainStateStore()
    facade = AmbientTelemetryFacade(reader=store)

    # Sub-facade states
    assert facade.location.state() == LocationState()
    assert not facade.location.is_docked()
    assert not facade.location.in_supercruise()
    assert not facade.location.on_surface()

    assert not facade.vessel.is_on_foot()
    assert not facade.vessel.is_in_srv()

    assert not facade.flight.landing_gear_down()
    assert not facade.flight.hardpoints_deployed()
    assert not facade.flight.night_vision()

    assert facade.cargo.count() == 0
    assert not facade.cargo.has_item("Gold")

    assert not facade.commander.is_wanted()
    assert not facade.station.has_market()
    assert not facade.carrier.has_pending_jump()
    assert not facade.exploration.all_bodies_found()
    assert not facade.powerplay.is_pledged()

    # Root convenience aliases
    assert not facade.is_docked()
    assert not facade.is_on_foot()
    assert not facade.in_supercruise()
    assert not facade.is_in_srv()
    assert not facade.is_wanted()


@pytest.mark.asyncio
async def test_end_to_end_resolver_pipeline() -> None:
    """Verifies that envelopes pushed to ingress port are reduced into the facade."""
    queue = MemoryQueueAdapter()
    facade = create_resolver(ingress_port=queue)

    async with facade:
        # 1. Enqueue FSDJump
        fsd_jump_json = (
            '{"timestamp": "2026-11-08T01:00:00Z", "event": "FSDJump", '
            '"StarSystem": "Sol", "SystemAddress": 10477373803, '
            '"StarPos": [0.0, 0.0, 0.0], "Body": "Sol", "BodyID": 0, "Docked": false}'
        )
        await queue.put(RawTelemetryEnvelope(raw_payload=fsd_jump_json, received_at=datetime.now()))

        # Allow worker task to process
        await asyncio.sleep(0.05)

        assert facade.location.state().system_name == "Sol"
        assert not facade.is_docked()

        # 2. Enqueue Docked event
        docked_json = (
            '{"timestamp": "2026-11-08T01:05:00Z", "event": "Docked", '
            '"StationName": "Mars High", "StationType": "Coriolis", '
            '"StationServices": ["Commodities", "Shipyard"]}'
        )
        await queue.put(RawTelemetryEnvelope(raw_payload=docked_json, received_at=datetime.now()))

        await asyncio.sleep(0.05)

        assert facade.is_docked()
        assert facade.location.state().station_name == "Mars High"
        assert facade.station.has_market()
        assert facade.station.has_shipyard()
        assert not facade.station.has_outfitting()
