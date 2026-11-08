"""Architectural parity test validating that 100% of ed-models are in the taxonomy matrix."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from scripts.inspect_ed_models_taxonomy import crawl_ed_models_taxonomy


def test_archetype_taxonomy_matrix_covers_all_ed_models() -> None:
    """Asserts that 100% of event classes in ed-models are declared in the YAML matrix."""
    matrix_path = Path("architecture/designs/matrix/archetype_taxonomy_v0.2.1.yaml")
    assert matrix_path.is_file(), f"Taxonomy matrix not found: {matrix_path}"

    matrix_data: dict[str, Any] = yaml.safe_load(matrix_path.read_text(encoding="utf-8"))
    assert "categories" in matrix_data, "Matrix YAML must declare 'categories' root key"

    matrix_categories = matrix_data["categories"]
    discovered_domains = crawl_ed_models_taxonomy()

    missing_models: list[str] = []

    for domain in discovered_domains:
        assert (
            domain.category in matrix_categories
        ), f"Category '{domain.category}' discovered in ed-models but missing from matrix YAML"

        category_models = matrix_categories[domain.category].get("models", {})
        for model in domain.models:
            if model.name not in category_models:
                missing_models.append(f"{domain.category}.{model.name}")
            else:
                model_def = category_models[model.name]
                assert (
                    "archetype" in model_def
                ), f"Model '{model.name}' missing 'archetype' declaration"
                assert model_def["archetype"] in {
                    "EPOCH_MILESTONE",
                    "CONTEXT_MUTATOR",
                    "EDGE_TRANSITION",
                    "METRIC_QUANTIZER",
                    "PASSIVE",
                }, f"Invalid archetype '{model_def['archetype']}' for model '{model.name}'"

    details = "\n".join(missing_models)
    assert (
        not missing_models
    ), f"{len(missing_models)} models exist in ed-models but are missing from taxonomy:\n{details}"
