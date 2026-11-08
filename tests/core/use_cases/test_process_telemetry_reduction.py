"""Unit tests for ProcessTelemetryReductionUseCase."""

from __future__ import annotations

from ed_resolver.adapters.driven.state_store import InMemoryDomainStateStore
from ed_resolver.core.domain.archetypes import TelemetryArchetype
from ed_resolver.core.ports.driving import ReduceTelemetryEventPort
from ed_resolver.core.use_cases import ProcessTelemetryReductionUseCase


def test_use_case_fulfills_driving_port() -> None:
    store = InMemoryDomainStateStore()
    use_case = ProcessTelemetryReductionUseCase(reader=store, writer=store)
    assert isinstance(use_case, ReduceTelemetryEventPort)


def test_use_case_skips_passive_archetype() -> None:
    store = InMemoryDomainStateStore()
    use_case = ProcessTelemetryReductionUseCase(reader=store, writer=store)

    class Music:
        music_track = "Supercruise"

    initial_loc = store.get_location()
    use_case.reduce(Music(), archetype=TelemetryArchetype.PASSIVE)

    # State in store remains unchanged
    assert store.get_location() is initial_loc


def test_use_case_orchestrates_multiple_domain_updates() -> None:
    store = InMemoryDomainStateStore()
    use_case = ProcessTelemetryReductionUseCase(reader=store, writer=store)

    class FSDJump:
        star_system = "Lave"
        system_address = 998877
        star_pos = (10.0, 20.0, 30.0)
        body = "Lave Station"
        body_id = 4
        body_count = 10
        docked = False

    use_case.reduce(FSDJump(), archetype=TelemetryArchetype.EPOCH_MILESTONE)

    # 1. LocationState updated
    assert store.get_location().system_name == "Lave"
    assert store.get_location().star_pos == (10.0, 20.0, 30.0)

    # 2. ExplorationState updated
    assert store.get_exploration().system_name == "Lave"
    assert store.get_exploration().body_count == 10
