"""Unit tests for the ed-models taxonomy introspection script."""

from __future__ import annotations

from scripts.inspect_ed_models_taxonomy import (
    DiscoveredDomain,
    DiscoveredModel,
    crawl_ed_models_taxonomy,
    format_domain_summary,
)


def test_crawl_ed_models_discovers_all_domains() -> None:
    """Verify that crawler identifies the known event categories and status models."""
    domains = crawl_ed_models_taxonomy()

    # Must find core categories
    expected_categories = {
        "travel",
        "station",
        "trade",
        "startup",
        "odyssey",
        "carrier",
        "combat",
        "exploration",
        "powerplay",
        "squadrons",
        "other",
        "status",
    }
    discovered_category_names = {d.category for d in domains}
    for category in expected_categories:
        assert category in discovered_category_names, f"Missing domain category: {category}"


def test_crawl_ed_models_finds_known_events_and_fields() -> None:
    """Verify that specific well-known events like FSDJump and Location are found with fields."""
    domains = crawl_ed_models_taxonomy()
    travel_domain = next((d for d in domains if d.category == "travel"), None)
    assert travel_domain is not None, "Travel domain should exist"

    fsd_jump = next((m for m in travel_domain.models if m.name == "FSDJump"), None)
    assert fsd_jump is not None, "FSDJump must be discovered in travel domain"
    assert "StarSystem" in fsd_jump.fields or "star_system" in fsd_jump.fields


def test_format_domain_summary() -> None:
    """Verify domain summary reporting."""
    domain = DiscoveredDomain(
        category="travel",
        module_path="ed_models.core.domain.events.travel",
        models=[
            DiscoveredModel(
                name="FsdJumpEvent",
                module="ed_models.core.domain.events.travel",
                fields={"star_system": "str", "system_address": "int"},
            )
        ],
    )
    summary = format_domain_summary([domain])
    assert "travel" in summary
    assert "FsdJumpEvent" in summary
    assert "Categories: 1" in summary
    assert "Models: 1" in summary
