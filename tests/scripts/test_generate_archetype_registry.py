"""Unit tests for generate_archetype_registry.py code generator."""

from __future__ import annotations

from pathlib import Path

from scripts.generate_archetype_registry import (
    generate_registry_source,
    load_taxonomy_matrix,
    validate_matrix_against_models,
)
from scripts.inspect_ed_models_taxonomy import crawl_ed_models_taxonomy


def test_load_taxonomy_matrix() -> None:
    """Verifies that the YAML matrix loads and parses categories correctly."""
    matrix_path = Path("architecture/designs/matrix/archetype_taxonomy_v0.2.1.yaml")
    data = load_taxonomy_matrix(matrix_path)
    assert data["version"] == "0.2.1"
    assert "categories" in data
    assert "travel" in data["categories"]


def test_validate_matrix_against_models() -> None:
    """Verifies that reconciliation detects zero drift between YAML matrix and ed-models."""
    matrix_path = Path("architecture/designs/matrix/archetype_taxonomy_v0.2.1.yaml")
    matrix_data = load_taxonomy_matrix(matrix_path)
    domains = crawl_ed_models_taxonomy()

    # Should not raise exception
    validate_matrix_against_models(matrix_data, domains)


def test_generate_registry_source_produces_valid_syntax() -> None:
    """Verifies that code generator synthesizes syntactically valid Python code."""
    matrix_path = Path("architecture/designs/matrix/archetype_taxonomy_v0.2.1.yaml")
    matrix_data = load_taxonomy_matrix(matrix_path)
    domains = crawl_ed_models_taxonomy()

    code = generate_registry_source(matrix_data, domains)
    assert "DEFAULT_ARCHETYPE_REGISTRY" in code
    assert "from ed_resolver.core.domain.archetypes import TelemetryArchetype" in code
    assert "FSDJump: TelemetryArchetype.EPOCH_MILESTONE" in code

    # Verify compiles as valid Python AST
    compile(code, "<test_registry>", "exec")
