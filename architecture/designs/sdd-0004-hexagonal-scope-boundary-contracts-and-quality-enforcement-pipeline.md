---
title: "SDD 0004: Hexagonal Scope Boundary Contracts and Quality Enforcement Pipeline"
tags: ["sdd", "architecture", "hexagonal", "boundaries", "import-linter", "archon", "ci", "ed-resolver"]
created_at: "2026-11-06"
last_updated_at: "2026-11-06"
---

# SDD 0004: Hexagonal Scope Boundary Contracts and Quality Enforcement Pipeline

* **Status:** Proposed
* **Governing ADR:** [ADR 0004: Hexagonal Scope Boundary Contracts and Automated Quality Gate Enforcement](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0004_hexagonal_scope_boundary_contracts_and_quality_gates.md)
* **Author:** Antigravity Pair Programmer
* **Version:** 1.0.0
* **Target Package:** `ed-resolver`

---

## 1. Introduction & Context

### 1.1 Purpose
This Software Design Document (SDD) specifies the concrete implementation architecture for enforcing hexagonal boundaries, static type safety, and code quality across `ed-resolver`. It provides the technical blueprint for the automated 5-tier verification pipeline, layer contract configurations, and CI gating required to permanently mitigate `RISK-04` (Hexagonal Core Boundary Leakage) and `RISK-11` (Unverified Scope Drift).

### 1.2 System Boundary & Scope
The system boundary comprises the entire `ed-resolver` codebase (`src/ed_resolver/`), test harnesses (`tests/`), helper tooling (`scripts/`), pre-commit hooks (`.pre-commit-config.yaml`), import boundary contracts (`.importlinter`), and GitHub Actions workflows (`.github/workflows/ci.yml`).

---

## 2. Architectural Blueprint & Layer Decomposition

### 2.1 The Four Concentric Hexagonal Rings

```
+─────────────────────────────────────────────────────────────────────────────+
| RING 4: COMPOSITION ROOT & DAEMON ENTRYPOINT                                |
| Path: `src/ed_resolver/bootstrap/`, `src/ed_resolver/daemon/`               |
| Invariant: Only layer allowed to instantiate concrete implementations.     |
+─────────────────────────────────────────────────────────────────────────────+
                                       │ imports inward
                                       ▼
+─────────────────────────────────────────────────────────────────────────────+
| RING 3: DRIVING & DRIVEN ADAPTERS                                            |
| Path: `src/ed_resolver/adapters/`                                           |
| Driving: `AmbientTelemetryFacade`, REST / WebSocket controllers.            |
| Driven: `TelemetryIngressWorker`, file tailing, direct queue adapters.      |
| Invariant: May import Ports and Domain; NEVER imported by Core.             |
+─────────────────────────────────────────────────────────────────────────────+
                                       │ imports inward
                                       ▼
+─────────────────────────────────────────────────────────────────────────────+
| RING 2: USE CASES & PORTS (Application Boundary)                            |
| Path: `src/ed_resolver/core/use_cases/`, `src/ed_resolver/core/ports/`      |
| Invariant: Abstract Protocols / ABCs defining interaction boundaries.       |
| Free of framework, OS, or transport imports.                                |
+─────────────────────────────────────────────────────────────────────────────+
                                       │ imports inward
                                       ▼
+─────────────────────────────────────────────────────────────────────────────+
| RING 1: HEXAGONAL DOMAIN CORE (Pure Business & State Engine)                |
| Path: `src/ed_resolver/core/domain/`                                        |
| Components: Archetypes, IngressClassifier, Reducers, Frozen Snapshots.      |
| Invariant: 100% PURE PYTHON STANDARD LIBRARY. Zero I/O, zero async.         |
+─────────────────────────────────────────────────────────────────────────────+
```

### 2.2 Layer Invariants Table

| Ring | Package Path | Allowed Imports | Forbidden Imports | Enforcement Mechanism |
| :--- | :--- | :--- | :--- | :--- |
| **Ring 1: Domain Core** | `ed_resolver.core.domain` | Python standard library, local domain siblings | Outer adapters, use cases, ports, bootstrap, external I/O | `.importlinter` (`core_domain_isolation`), `pytest-archon` |
| **Ring 2: Ports** | `ed_resolver.core.ports` | `core.domain`, `typing.Protocol`, standard library | `adapters`, `bootstrap`, web frameworks (`fastapi`, etc.) | `.importlinter` (`domain_port_isolation`), AST checks |
| **Ring 2: Use Cases** | `ed_resolver.core.use_cases` | `core.domain`, `core.ports`, standard library | `adapters`, `bootstrap`, web frameworks (`fastapi`, etc.) | `.importlinter` (`use_case_transport_isolation`) |
| **Ring 3: Adapters** | `ed_resolver.adapters` | `core.domain`, `core.ports`, `core.use_cases`, external libraries | `ed_resolver.bootstrap` | `.importlinter` (`composition_root_isolation`) |
| **Ring 4: Composition** | `ed_resolver.bootstrap`, `daemon` | All internal packages, external frameworks | None (serves as the composition root) | Monitored via module graph |

---

## 3. Detailed Component Design & Configurations

### 3.1 Layer Boundary Contract Engine (`.importlinter`)

The root configuration file `.importlinter` enforces five deterministic contracts:

```ini
[importlinter]
root_packages =
    ed_resolver
include_external_packages = True

[importlinter:contract:core_domain_isolation]
name = core_domain_isolation
type = forbidden
source_modules =
    ed_resolver.core.domain
forbidden_modules =
    ed_resolver.adapters
    external
    frameworks

[importlinter:contract:inward_dependency_direction]
name = inward_dependency_direction
type = layers
layers =
    ed_resolver.adapters
    ed_resolver.core.use_cases
    ed_resolver.core.domain

[importlinter:contract:domain_port_isolation]
name = domain_port_isolation
type = forbidden
source_modules =
    ed_resolver.core.domain
forbidden_modules =
    ed_resolver.core.ports
    ed_resolver.core.use_cases

[importlinter:contract:use_case_transport_isolation]
name = use_case_transport_isolation
type = forbidden
source_modules =
    ed_resolver.core.use_cases
forbidden_modules =
    ed_resolver.adapters
    fastapi
    starlette
    flask
    click
    typer

[importlinter:contract:composition_root_isolation]
name = composition_root_isolation
type = forbidden
source_modules =
    ed_resolver.core.domain
    ed_resolver.core.ports
    ed_resolver.core.use_cases
    ed_resolver.adapters
forbidden_modules =
    ed_resolver.bootstrap
```

### 3.2 AST Compliance & Structural Rule Assertions (`tests/architecture/test_boundaries.py`)

In addition to import graph checks, structural Python AST assertions in `tests/architecture/test_boundaries.py` enforce code-level invariants:
1. **Purity of Core Domain (`test_core_domain_has_zero_external_dependencies`):** Crawls AST import nodes in `core/domain/` to guarantee no adapter modules are referenced.
2. **Inward Flow Rule (`test_dependencies_point_strictly_inward`):** Validates that no module in `core/` imports from `adapters/`.
3. **Protocol Abstraction Rule (`test_ports_are_abstract_protocols_or_abcs`):** Asserts that all classes defined in `core/ports/` inherit from `typing.Protocol` or `abc.ABC`.
4. **Snapshot Immutability Rule (`test_snapshots_are_frozen_dataclasses`):** Asserts that all snapshot classes exported in `core.domain.models` use `@dataclass(frozen=True)`.

### 3.3 The 5-Tier Verification Runner (`scripts/verify.py`)

The verification engine sequentially runs all quality checks, aborting on the first failure:

```
                  `uv run python scripts/verify.py`
                                 │
                                 ▼
                 [Gate 1: Pre-Commit Quality Checks]
                 - trailing-whitespace, end-of-file-fixer
                 - check-yaml (validates consensus matrices)
                 - check-toml (validates pyproject.toml)
                 - ruff check (linter rules E, F, W, I, B, UP)
                 - ruff-format (line length 100)
                                 │ Passed (0)
                                 ▼
                 [Gate 2: Import Linter Contracts]
                 - lint-imports (.importlinter contracts)
                                 │ Passed (0)
                                 ▼
                 [Gate 3: Static Type Analysis]
                 - mypy src/ (strict type contracts)
                                 │ Passed (0)
                                 ▼
                 [Gate 4: Unit & Architectural Compliance]
                 - pytest tests/ (unit, script, Archon tests)
                                 │ Passed (0)
                                 ▼
                 [Exit 0: All Quality Gates Passed]
```

### 3.4 Continuous Integration Workflow (`.github/workflows/ci.yml`)

The CI workflow executes on every pull request and push to `main`:
* Installs Python 3.13 and Astral `uv`.
* Executes `uv run python scripts/verify.py`.
* Any regression in boundary imports, typing, tests, or formatting immediately fails the build, preventing pull request merge.

---

## 4. Error Handling, Failure Modes & Gating

| Failure Mode | Detection Point | Operator Diagnostic | Remediation Action |
| :--- | :--- | :--- | :--- |
| **Illegal Adapter Import in Domain Core** | Gate 2 (`lint-imports`), Gate 4 (`pytest-archon`) | `ImportLinter: Broken contract core_domain_isolation` | Move concrete logic to `adapters/` and introduce an abstract protocol in `core/ports/`. |
| **Malformed Consensus YAML Syntax** | Gate 1 (`check-yaml` pre-commit) | `check-yaml: Failed to load YAML: ...` | Fix YAML indentation or syntax error in `architecture/designs/matrix/`. |
| **Missing Model Mapping Drift** | Gate 4 (`test_inspect_ed_models_taxonomy`) | `AssertionError: Missing domain category: ...` | Update `architecture/designs/matrix/` to cover new models. |
| **Type Incompatibility on DTO Fields** | Gate 3 (`mypy src/`) | `mypy: Incompatible types in assignment ...` | Align type annotations on snapshot fields or helper methods. |

---

## 5. Verification & Acceptance Criteria

1. **Gate Parity:** Running `uv run python scripts/verify.py` locally produces the exact same execution results as GitHub Actions CI.
2. **Deterministic Exit Codes:** Any check returning non-zero immediately halts `verify.py` and returns exit code 1.
3. **Execution Performance:** Complete verification pipeline must execute in under 3.0 seconds on standard developer hardware.
4. **Zero Tolerance:** No warnings, lint suppressions (`# noqa`), or type ignores (`# type: ignore`) may be introduced in core domain layers.
