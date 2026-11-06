"""Introspects the released ed-models package to discover all event classes and fields.

Outputs structured information used to author and validate the taxonomy and facade matrices.
"""

from __future__ import annotations

import dataclasses
import importlib
import inspect
import pkgutil
from dataclasses import dataclass, field
from types import ModuleType
from typing import Any

import ed_models.core.domain.events as events_pkg
import ed_models.core.domain.status as status_pkg


@dataclass(frozen=True, slots=True)
class DiscoveredModel:
    """Represents a discovered model class and its type-annotated fields."""

    name: str
    module: str
    fields: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DiscoveredDomain:
    """Represents a domain package category containing discovered models."""

    category: str
    module_path: str
    models: list[DiscoveredModel] = field(default_factory=list)


def _extract_model_fields(cls: type[Any]) -> dict[str, str]:
    """Extract type annotations for fields on a dataclass or model class."""
    if dataclasses.is_dataclass(cls):
        return {f.name: str(f.type) for f in dataclasses.fields(cls)}
    if hasattr(cls, "__annotations__"):
        return {name: str(typ) for name, typ in cls.__annotations__.items()}
    return {}


def _crawl_package_classes(package: ModuleType) -> dict[str, list[DiscoveredModel]]:
    """Walk all submodules in a package and discover event model classes."""
    results: dict[str, list[DiscoveredModel]] = {}
    if not hasattr(package, "__path__"):
        return results

    for module_info in pkgutil.walk_packages(package.__path__, prefix=f"{package.__name__}."):
        try:
            mod = importlib.import_module(module_info.name)
        except Exception:
            continue

        # Extract top-level category under package
        # e.g. ed_models.core.domain.events.travel.fsd_jump -> travel
        rel_path = module_info.name[len(package.__name__) :].strip(".")
        parts = rel_path.split(".")
        category = parts[0] if parts else "general"
        discovered_in_mod: list[DiscoveredModel] = []

        for name, obj in inspect.getmembers(mod, inspect.isclass):
            # Restrict to classes defined within this module or package
            if obj.__module__ != mod.__name__:
                continue
            if name.startswith("_") or name.endswith("Base"):
                continue

            fields_dict = _extract_model_fields(obj)
            discovered_in_mod.append(
                DiscoveredModel(
                    name=name,
                    module=mod.__name__,
                    fields=fields_dict,
                )
            )

        if discovered_in_mod:
            results.setdefault(category, []).extend(discovered_in_mod)

    return results


def crawl_ed_models_taxonomy() -> list[DiscoveredDomain]:
    """Systematically discover all event and status model classes in released ed-models."""
    domains: list[DiscoveredDomain] = []

    # 1. Crawl events sub-packages
    events_by_category = _crawl_package_classes(events_pkg)
    for category, models in sorted(events_by_category.items()):
        sorted_models = sorted(models, key=lambda m: m.name)
        domains.append(
            DiscoveredDomain(
                category=category,
                module_path=f"ed_models.core.domain.events.{category}",
                models=sorted_models,
            )
        )

    # 2. Crawl status sub-packages
    status_by_category = _crawl_package_classes(status_pkg)
    # Combine status into a single "status" domain or individual sub-modules
    all_status_models: list[DiscoveredModel] = []
    for models in status_by_category.values():
        all_status_models.extend(models)

    # Also inspect status_pkg directly
    for name, obj in inspect.getmembers(status_pkg, inspect.isclass):
        if obj.__module__ == status_pkg.__name__ and not name.startswith("_"):
            all_status_models.append(
                DiscoveredModel(
                    name=name,
                    module=status_pkg.__name__,
                    fields=_extract_model_fields(obj),
                )
            )

    if all_status_models:
        deduped = {m.name: m for m in all_status_models}
        domains.append(
            DiscoveredDomain(
                category="status",
                module_path="ed_models.core.domain.status",
                models=sorted(deduped.values(), key=lambda m: m.name),
            )
        )

    return domains


def format_domain_summary(domains: list[DiscoveredDomain]) -> str:
    """Format discovered domains and models into a human-readable summary table."""
    total_models = sum(len(d.models) for d in domains)
    header = (
        f"=== Discovered ed-models Domains (Categories: {len(domains)}, Models: {total_models}) ==="
    )
    lines: list[str] = [
        header,
        "",
    ]
    for d in domains:
        lines.append(f"Domain Category: [{d.category}] ({len(d.models)} models)")
        lines.append(f"  Module: {d.module_path}")
        for m in d.models[:5]:
            lines.append(f"    - {m.name} ({len(m.fields)} fields)")
        if len(d.models) > 5:
            lines.append(f"    ... and {len(d.models) - 5} more")
        lines.append("")
    return "\n".join(lines)


def emit_taxonomy_yaml(domains: list[DiscoveredDomain], version: str = "0.2.1") -> str:
    """Generate structured YAML mapping 100% of discovered ed-models classes to archetypes."""
    lines: list[str] = [
        f'version: "{version}"',
        'source_package: "ed-models"',
        "categories:",
    ]

    # Deterministic default heuristic mapping per category
    category_defaults = {
        "travel": "EPOCH_MILESTONE",
        "station": "CONTEXT_MUTATOR",
        "carrier": "CONTEXT_MUTATOR",
        "startup": "EPOCH_MILESTONE",
        "odyssey": "CONTEXT_MUTATOR",
        "trade": "CONTEXT_MUTATOR",
        "combat": "CONTEXT_MUTATOR",
        "exploration": "PASSIVE",
        "powerplay": "CONTEXT_MUTATOR",
        "squadrons": "PASSIVE",
        "other": "PASSIVE",
        "status": "EDGE_TRANSITION",
        "base": "PASSIVE",
    }

    # Known specific archetype overrides
    known_overrides = {
        "FSDJump": "EPOCH_MILESTONE",
        "Location": "EPOCH_MILESTONE",
        "CarrierJump": "EPOCH_MILESTONE",
        "Docked": "EPOCH_MILESTONE",
        "Undocked": "EPOCH_MILESTONE",
        "SupercruiseEntry": "EPOCH_MILESTONE",
        "SupercruiseExit": "EPOCH_MILESTONE",
        "Touchdown": "EPOCH_MILESTONE",
        "Liftoff": "EPOCH_MILESTONE",
        "Loadout": "CONTEXT_MUTATOR",
        "StatusFlags": "EDGE_TRANSITION",
        "StatusFlags2": "EDGE_TRANSITION",
        "StatusTelemetry": "METRIC_QUANTIZER",
    }

    for d in sorted(domains, key=lambda x: x.category):
        lines.append(f"  {d.category}:")
        lines.append(f'    module: "{d.module_path}"')
        lines.append("    models:")
        default_archetype = category_defaults.get(d.category, "PASSIVE")
        for m in sorted(d.models, key=lambda x: x.name):
            archetype = known_overrides.get(m.name, default_archetype)
            lines.append(f"      {m.name}:")
            lines.append(f'        archetype: "{archetype}"')
            lines.append(f"        fields_count: {len(m.fields)}")

    return "\n".join(lines) + "\n"


def main() -> None:
    """Main execution entrypoint."""
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(
        description="Inspect ed-models and emit consensus YAML matrices."
    )
    parser.add_argument(
        "--emit-yaml",
        action="store_true",
        help="Emit YAML matrix files to architecture/designs/matrix/",
    )
    args = parser.parse_args()

    domains = crawl_ed_models_taxonomy()
    if args.emit_yaml:
        matrix_dir = Path("architecture/designs/matrix")
        matrix_dir.mkdir(parents=True, exist_ok=True)
        taxonomy_path = matrix_dir / "archetype_taxonomy_v0.2.1.yaml"
        content = emit_taxonomy_yaml(domains, version="0.2.1")
        taxonomy_path.write_text(content, encoding="utf-8")
        print(f"Emitted: {taxonomy_path} ({len(domains)} categories)")
    else:
        print(format_domain_summary(domains))


if __name__ == "__main__":
    main()
