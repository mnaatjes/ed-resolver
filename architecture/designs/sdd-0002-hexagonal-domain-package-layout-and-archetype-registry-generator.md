---
title: "SDD 0002: Hexagonal Domain Package Layout and Archetype Classification Registry Generator"
tags: ["sdd", "architecture", "domain", "hexagonal", "classification", "registry", "codegen", "ed-resolver"]
created_at: "2026-11-06"
last_updated_at: "2026-11-06"
---

# SDD 0002: Hexagonal Domain Package Layout and Archetype Classification Registry Generator

* **Status:** Proposed
* **Governing ADRs:** [ADR 0002](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0002_archetype_classification_subsystem_and_registry.md), [ADR 0003](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0003_ambient_telemetry_facade_query_contracts_and_governance.md), [ADR 0004](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0004_hexagonal_scope_boundary_contracts_and_quality_gates.md)
* **Author:** Antigravity Pair Programmer
* **Version:** 1.0.0
* **Target Package:** `ed-resolver`

---

## 1. Introduction & Context

### 1.1 Purpose
This Software Design Document specifies:
1. The formal directory taxonomy and module structure for the 9 hexagonal domain sub-packages under `src/ed_resolver/core/domain/`.
2. The core domain archetype enumeration `TelemetryArchetype` (`src/ed_resolver/core/domain/archetypes.py`).
3. The offline code generator tool (`scripts/generate_archetype_registry.py`) that parses the approved structured YAML matrix (`architecture/designs/matrix/archetype_taxonomy_v0.2.1.yaml`), performs AST reconciliation against `ed-models`, and deterministically outputs the static Python lookup registry (`src/ed_resolver/core/domain/classification/registry.py`).

### 1.2 System Boundary & Scope
The implementation is strictly confined to:
* `src/ed_resolver/core/domain/archetypes.py`
* `src/ed_resolver/core/domain/classification/`
* `src/ed_resolver/core/domain/{location, vessel, flight, cargo, commander, station, carrier, exploration, powerplay}/`
* `scripts/generate_archetype_registry.py`
* `tests/scripts/test_generate_archetype_registry.py`

---

## 2. Architectural Blueprint & Domain Package Structure

### 2.1 Domain Ring Decomposition

```
src/ed_resolver/core/domain/
├── __init__.py
├── archetypes.py                  # TelemetryArchetype enum
├── classification/                # Ingress classification subsystem
│   ├── __init__.py
│   ├── classifier.py              # IngressClassifier domain service
│   └── registry.py                # Generated static DEFAULT_ARCHETYPE_REGISTRY
├── location/                      # Spatial coordinates, bodies, stars, docking
│   └── __init__.py
├── vessel/                        # Active ship, loadout, suit, SRV
│   └── __init__.py
├── flight/                        # 1 Hz flags, gear, hardpoints, fuel gauges
│   └── __init__.py
├── cargo/                         # Commodity inventory, materials, transfers
│   └── __init__.py
├── commander/                     # Credits, ranks, reputations, bounties, crimes
│   └── __init__.py
├── station/                       # Market, shipyard, outfitting, station services
│   └── __init__.py
├── carrier/                       # Fleet carrier finances, jumps, crew, packs
│   └── __init__.py
├── exploration/                   # FSS scans, DSS maps, bio samples, codex
│   └── __init__.py
└── powerplay/                     # Pledges, merits, voting, power commodities
    └── __init__.py
```

### 2.2 Core Archetype Definition (`archetypes.py`)

```python
from enum import Enum


class TelemetryArchetype(str, Enum):
    """Behavioral reduction archetypes for Elite Dangerous telemetry events."""

    EPOCH_MILESTONE = "EPOCH_MILESTONE"
    CONTEXT_MUTATOR = "CONTEXT_MUTATOR"
    EDGE_TRANSITION = "EDGE_TRANSITION"
    METRIC_QUANTIZER = "METRIC_QUANTIZER"
    PASSIVE = "PASSIVE"
```

---

## 3. Detailed Design: Offline Code Generator (`scripts/generate_archetype_registry.py`)

### 3.1 Pipeline Flow & Execution Logic

```
   `uv run python scripts/generate_archetype_registry.py`
                             │
                             ▼
  [Step 1: Ingest YAML Consensus Matrix]
  Reads: `architecture/designs/matrix/archetype_taxonomy_v<version>.yaml`
  Validates: Schema keys (`version`, `categories`, `models`, `archetype`)
                             │
                             ▼
  [Step 2: Package Introspection & AST Reconciliation]
  Crawls: Released `ed-models` package hierarchy via `inspect_ed_models_taxonomy.py`
  Validates: Every discovered class exists in YAML matrix (Error Gate: Exit 1 on drift)
                             │
                             ▼
  [Step 3: Deterministic Source Code Synthesis]
  Generates Python AST / formatted source declaring:
  - Strongly typed imports from `ed_models.core.domain.events.*`
  - `MappingProxyType` dictionary `DEFAULT_ARCHETYPE_REGISTRY`
  - Explicit slot-based type annotations: `Mapping[type[Any], TelemetryArchetype]`
                             │
                             ▼
  [Step 4: Output File Emission & Ruff Formatting]
  Writes: `src/ed_resolver/core/domain/classification/registry.py`
  Executes: `ruff format` and `ruff check --fix`
                             │
                             ▼
  [Step 5: Exit 0 & Report Compiled Statistics]
```

### 3.2 Generated Code Specification (`registry.py`)

The generated file adheres strictly to the following contract:
```python
"""Autogenerated default archetype taxonomy registry.

Generated by scripts/generate_archetype_registry.py from:
architecture/designs/matrix/archetype_taxonomy_v0.2.1.yaml

DO NOT EDIT MANUALLY.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Mapping

from ed_models.core.domain.events.travel import FSDJump, Location, ...
# ... other domain category imports ...

from ed_resolver.core.domain.archetypes import TelemetryArchetype

DEFAULT_ARCHETYPE_REGISTRY: Mapping[type[Any], TelemetryArchetype] = MappingProxyType(
    {
        FSDJump: TelemetryArchetype.EPOCH_MILESTONE,
        Location: TelemetryArchetype.EPOCH_MILESTONE,
        # ... 398 mapped classes ...
    }
)
```

---

## 4. Error Handling & Discrepancy Gate

1. **Unmapped Class Gate:** If an event class exists in `ed-models` but is absent from the YAML matrix, the script aborts immediately with code 1, printing:
   `ERROR: Discrepancy Gate Failed: N uncataloged models detected in ed-models.`
2. **Phantom Class Gate:** If the YAML matrix references an event class no longer in `ed-models`, the script aborts with code 1, printing:
   `ERROR: Discrepancy Gate Failed: N phantom models declared in YAML matrix.`
3. **Invalid Archetype Gate:** If an archetype string does not match `TelemetryArchetype`, aborts with code 1.

---

## 5. Verification & Acceptance Criteria

1. **Deterministic Codegen:** Re-running the generator script without YAML modifications produces zero git diff on `registry.py`.
2. **Quality Gates:** Generated `registry.py` passes `ruff`, `mypy src/`, and `import-linter`.
3. **Parity Compliance:** `tests/architecture/test_archetype_parity.py` passes cleanly against generated registry.
4. **Unit Tested Tooling:** Generator script logic is verified via unit tests in `tests/scripts/test_generate_archetype_registry.py`.
