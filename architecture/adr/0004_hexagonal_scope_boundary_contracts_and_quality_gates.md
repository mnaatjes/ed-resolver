---
title: "ADR 0004: Hexagonal Scope Boundary Contracts and Automated Quality Gate Enforcement"
tags: ["adr", "ed-resolver", "architecture", "hexagonal", "boundaries", "import-linter", "archon", "ci"]
created_at: "2026-11-06"
last_updated_at: "2026-11-06"
---

# ADR 0004: Hexagonal Scope Boundary Contracts and Automated Quality Gate Enforcement

* **Status:** Proposed
* **Date:** 2026-11-06
* **Deciders:** Michael Naatjes, Antigravity Agent
* **Consulted:** [ADR 0001](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0001_core_domain_state_architecture_and_unified_ingress_lifecycle.md), [ADR 0002](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0002_archetype_classification_subsystem_and_registry.md), [ADR 0003](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0003_ambient_telemetry_facade_query_contracts_and_governance.md)

---

## 1. Context and Problem Statement

`ed-resolver` synthesizes multi-channel *Elite Dangerous* telemetry into consolidated, ambient state truths. Its scope spans diverse responsibilities:
1. Low-level I/O tailing, stream re-connection, line buffering, and JSON deserialization (Driven Ingress Runtime).
2. Pure, deterministic mathematical state reduction across 260+ game events (Hexagonal Domain Core).
3. Thread-safe atomic state snapshot synchronization and non-blocking reads (`StateStore`).
4. Ergonomic in-process synchronous querying across 9 domain sub-facades (`AmbientTelemetryFacade`).
5. Out-of-process REST / WebSocket service hosting (`ed-resolver-daemon`).

Without strict, automated architectural boundary enforcement, multi-layer Python packages suffer from **Architectural Degradation and Scope Drift** (captured in `RISK-04` and `RISK-11`):
* Low-level filesystem, OS, or network I/O leaking into the pure Domain Core.
* Async framework contagion (`asyncio`) invading synchronous facade query methods.
* Concrete transport DTOs or HTTP frameworks (`fastapi`, `starlette`) leaking into Use-Case interactors or domain entities.
* Upstream `ed-models` package updates introducing unmapped event classes that silently fail to update state (`RISK-08`).
* Predicate query methods drifting from compound snapshot state (`RISK-10`).

How should `ed-resolver` define its system scope boundaries, and what deterministic enforcement mechanisms should prevent architectural boundary regressions across local development and CI pipelines?

---

## 2. Decision Drivers

* **Zero Boundary Leakage (Hexagonal Purity):** Core domain state reducers, models, and classifier services must remain 100% pure Python with zero I/O, zero network, and zero external framework dependencies.
* **Inward Dependency Rule:** Outer layers (Adapters, CLI, Bootstrap) may depend on inner layers (Use Cases, Ports, Domain), but inner layers must never import or reference outer layers.
* **Deterministic Automated Gating:** Architectural boundary compliance must not rely on human memory or manual PR reviews; it must be enforced automatically via static analysis tools during pre-commit and CI execution.
* **Multi-Tier Quality Gate Pipeline:** Quality enforcement must span five distinct complementary gates:
  1. Formatting and linting (`ruff`, `ruff-format`).
  2. Syntactic validation of consensus YAML matrices (`check-yaml`).
  3. Strict static type analysis (`mypy`).
  4. Layer boundary contract verification (`import-linter`).
  5. Abstract syntax tree (AST) architectural compliance assertions (`pytest-archon` / `pytest`).
* **Single Verification Command:** Developers and CI runners must be able to run a single, deterministic command (`uv run python scripts/verify.py`) that executes 100% of quality checks with exit code 1 on any failure.

---

## 3. Considered Options

* **Option 1: Manual PR Code Review Only.** Rely on peer review checklists to catch boundary leaks and illegal imports. Rejected because manual reviews are fallible and allow subtle layer coupling to accumulate over time.
* **Option 2: Import-Linter Only.** Configure `.importlinter` contracts without AST test assertions or pre-commit hooks. Rejected because `import-linter` cannot inspect function signatures, inheritance rules, or verify that consensus YAML matrices match installed package models.
* **Option 3: Multi-Tiered Automated Boundary & Quality Gate Enforcement (Selected).** Codify all hexagonal scope boundaries into formal contracts, verified automatically by `import-linter`, `pytest-archon`, `mypy`, pre-commit hooks, and a unified `scripts/verify.py` runner wired into GitHub Actions CI.

---

## 4. Decision Outcome

**Chosen Option:** **Option 3: Multi-Tiered Automated Boundary & Quality Gate Enforcement**.

### 4.1 Canonical System Scope and Layer Boundaries

The package structure is divided into four concentric hexagonal rings with explicit responsibilities and dependency directions:

```
+─────────────────────────────────────────────────────────────────────────────+
| LAYER 4: COMPOSITION ROOT & DAEMON HARNESS (`bootstrap/`, `daemon/`)        |
| - `ed_resolver.daemon`: OS CLI entrypoint, HTTP/WS endpoints (Starlette).   |
| - `ed_resolver.bootstrap`: Dependency injection container and wiring.       |
| - May import all inner layers; NO inner layer may import bootstrap or daemon.|
+─────────────────────────────────────────────────────────────────────────────+
                                       │ depends inward
                                       ▼
+─────────────────────────────────────────────────────────────────────────────+
| LAYER 3: ADAPTERS (`adapters/driving/`, `adapters/driven/`)                 |
| - Driving: `AmbientTelemetryFacade`, REST controllers.                      |
| - Driven Ingress: `TelemetryIngressWorker`, pluggable tailing adapters.     |
| - May import Use Cases, Ports, and Domain Core; NEVER imported by Core.     |
+─────────────────────────────────────────────────────────────────────────────+
                                       │ depends inward
                                       ▼
+─────────────────────────────────────────────────────────────────────────────+
| LAYER 2: APPLICATION CORE / USE CASES & PORTS (`core/use_cases/`, `ports/`) |
| - `core.ports`: Pure abstract protocols (`TelemetryIngressPort`, etc.).     |
| - `core.use_cases`: Interactors orchestrating state hydration & queries.     |
| - Free of transport, filesystem, or web framework imports.                 |
+─────────────────────────────────────────────────────────────────────────────+
                                       │ depends inward
                                       ▼
+─────────────────────────────────────────────────────────────────────────────+
| LAYER 1: HEXAGONAL DOMAIN CORE (`core/domain/`)                             |
| - `domain.archetypes`: Archetype enumeration (`TelemetryArchetype`).        |
| - `domain.classification`: `IngressClassifier`, static taxonomy registry.    |
| - `domain.state`: Pure state store, reducers, frozen snapshot dataclasses.  |
| - PURE PYTHON ONLY: Zero outer imports, zero I/O, zero async contagion.     |
+─────────────────────────────────────────────────────────────────────────────+
```

### 4.2 Formal Boundary Contracts (`.importlinter`)

Five immutable boundary contracts are maintained in `.importlinter`:
1. `core_domain_isolation`: `ed_resolver.core.domain` is strictly forbidden from importing `ed_resolver.adapters`, external I/O libraries, or frameworks.
2. `inward_dependency_direction`: Enforces strict layered dependencies: `adapters` $\rightarrow$ `core.use_cases` $\rightarrow$ `core.domain`.
3. `domain_port_isolation`: `core.domain` cannot import `core.ports` or `core.use_cases`.
4. `use_case_transport_isolation`: `core.use_cases` cannot import `fastapi`, `starlette`, `flask`, `click`, or `adapters`.
5. `composition_root_isolation`: No internal layer (`core.domain`, `core.ports`, `core.use_cases`, `adapters`) may import `ed_resolver.bootstrap`.

### 4.3 Automated Quality Gate Pipeline

Every code modification must pass all five sequential gates enforced by `scripts/verify.py`:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       `uv run python scripts/verify.py`                     │
│                                                                             │
│  Gate 1: Pre-Commit Hooks                                                   │
│    - trailing-whitespace, end-of-file-fixer                                 │
│    - check-yaml (validates syntax of consensus matrices in designs/matrix/)  │
│    - check-toml (validates pyproject.toml)                                  │
│    - ruff check (linting, imports, formatting rules)                        │
│    - ruff-format (deterministic code styling)                               │
│                                                                             │
│  Gate 2: Import Linter (`lint-imports`)                                      │
│    - Enforces 5 hexagonal boundary contracts against AST import graph       │
│                                                                             │
│  Gate 3: Static Type Verification (`mypy src/`)                             │
│    - Strict static typing across all domain models, snapshots, and facades  │
│                                                                             │
│  Gate 4: Unit & Architectural Compliance (`pytest tests/`)                  │
│    - Architectural compliance rules (`tests/architecture/test_boundaries.py`)│
│    - Introspection and matrix parity (`tests/scripts/`)                     │
│    - Domain reduction logic and facade projection unit tests                │
│                                                                             │
│  Gate 5: GitHub Actions Continuous Integration (`.github/workflows/ci.yml`) │
│    - Automatically runs `verify.py` on all branch pushes and pull requests  │
│    - Merge gate: PRs cannot merge if any quality gate fails                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Consequences

### Positive
* **Deterministic Boundary Protection:** Eliminates architectural erosion; boundary leaks fail immediately in pre-commit and CI with descriptive import traces.
* **Pure Testability:** The Domain Core remains 100% decoupled from async event loops, file tailing, and HTTP engines, allowing lightning-fast unit tests.
* **Unified Developer Experience:** Developers run a single command (`scripts/verify.py`) to run all checks identically to CI.
* **Audit Compliance:** Changes to boundaries or layers require updating explicit contract definitions, producing transparent git reviews.

### Negative / Trade-offs
* Strict import rules require careful separation of interfaces (ports) from implementations (adapters).
* New dependencies must be classified and declared in `.importlinter` if they cross layer boundaries.

---

## 6. Validation and Next Steps

1. Verify existing import contracts and tests via `uv run python scripts/verify.py`.
2. Add explicit taxonomy parity test (`tests/architecture/test_archetype_parity.py`) cross-referencing `architecture/designs/matrix/archetype_taxonomy_v0.2.1.yaml` with installed `ed-models`.
3. Enforce that GitHub Actions CI gating remains mandatory for merging pull requests into `main`.
