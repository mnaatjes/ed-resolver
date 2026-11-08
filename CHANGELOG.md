# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Domain Sub-Packages & Archetypes:**
  - Authored [`src/ed_resolver/core/domain/archetypes.py`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/src/ed_resolver/core/domain/archetypes.py) establishing `TelemetryArchetype` enum (`EPOCH_MILESTONE`, `CONTEXT_MUTATOR`, `EDGE_TRANSITION`, `METRIC_QUANTIZER`, `PASSIVE`).
  - Established 9 domain sub-packages (`location`, `vessel`, `flight`, `cargo`, `commander`, `station`, `carrier`, `exploration`, `powerplay`) and `classification/`.
  - Implemented offline code generator [`scripts/generate_archetype_registry.py`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/scripts/generate_archetype_registry.py) compiling 398 `ed-models` classes into [`src/ed_resolver/core/domain/classification/registry.py`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/src/ed_resolver/core/domain/classification/registry.py).
  - Authored unit test suite in [`tests/scripts/test_generate_archetype_registry.py`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/tests/scripts/test_generate_archetype_registry.py).
- **Architectural Decision Records & Specifications:**
  - [`ADR 0001: Core Domain State Architecture and Unified Ingress Lifecycle`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0001_core_domain_state_architecture_and_unified_ingress_lifecycle.md).
  - [`ADR 0002: Archetype Classification Subsystem and Registry`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0002_archetype_classification_subsystem_and_registry.md).
  - [`ADR 0003: Ambient Telemetry Facade Query Contracts and Architectural Matrix Governance`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0003_ambient_telemetry_facade_query_contracts_and_governance.md).
  - [`ADR 0004: Hexagonal Scope Boundary Contracts and Automated Quality Gate Enforcement`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0004_hexagonal_scope_boundary_contracts_and_quality_gates.md).
  - [`ADR 0005: TelemetryIngressWorker Runtime and Ingress Lifecycle`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0005_telemetry_ingress_worker_runtime_lifecycle.md).
  - [`SDD 0002: Hexagonal Domain Package Layout and Archetype Classification Registry Generator`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/designs/sdd-0002-hexagonal-domain-package-layout-and-archetype-registry-generator.md).
  - [`SDD 0004: Hexagonal Scope Boundary Contracts and Quality Enforcement Pipeline`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/designs/sdd-0004-hexagonal-scope-boundary-contracts-and-quality-enforcement-pipeline.md).
  - [`SDD 0005: TelemetryIngressWorker Runtime and Ingress Lifecycle Subsystem`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/designs/sdd-0005-telemetry-ingress-worker-runtime-lifecycle.md).
  - Consensus YAML matrices under [`architecture/designs/matrix/`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/designs/matrix/): `archetype_taxonomy_v0.2.1.yaml`, `facade_compound_snapshots_v1.0.0.yaml`, and `facade_atomic_predicates_v1.0.0.yaml`.
  - Functional Use-Case Specifications: `UC-01` through `UC-07` in [`architecture/use-cases/`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/use-cases/).
  - Introspection tool [`scripts/inspect_ed_models_taxonomy.py`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/scripts/inspect_ed_models_taxonomy.py) and test suite.
  - Architectural parity test [`tests/architecture/test_archetype_parity.py`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/tests/architecture/test_archetype_parity.py).
- **Telemetry Ingress Worker & Driven Runtime:**
  - Implemented universal carrier [`src/ed_resolver/core/ports/envelope.py`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/src/ed_resolver/core/ports/envelope.py) (`RawTelemetryEnvelope`).
  - Implemented ingress port protocol [`src/ed_resolver/core/ports/ingress.py`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/src/ed_resolver/core/ports/ingress.py) (`TelemetryIngressPort`).
  - Implemented operational error hierarchy [`src/ed_resolver/core/errors.py`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/src/ed_resolver/core/errors.py) (`TelemetryWorkerError`).
  - Implemented permissive deserializer [`src/ed_resolver/adapters/driven/runtime/deserializer.py`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/src/ed_resolver/adapters/driven/runtime/deserializer.py) (`TelemetryPayloadDeserializer`).
  - Implemented dead-letter queue ring buffer [`src/ed_resolver/adapters/driven/runtime/quarantine.py`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/src/ed_resolver/adapters/driven/runtime/quarantine.py) (`QuarantineDeadLetterQueue`).
  - Implemented runtime worker [`src/ed_resolver/adapters/driven/runtime/worker.py`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/src/ed_resolver/adapters/driven/runtime/worker.py) (`TelemetryIngressWorker`).
  - Implemented domain classifier [`src/ed_resolver/core/domain/classification/classifier.py`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/src/ed_resolver/core/domain/classification/classifier.py) (`IngressClassifier`).
  - Implemented driven adapters: `MemoryQueueAdapter`, `EdTelemetryNetworkAdapter`, and `EdTelemetryInProcessAdapter`.
  - Authored unit test suites in `tests/adapters/driven/` and automated AST boundary checks in `tests/architecture/test_boundaries.py`.
- **Session Metadata:**
  - Antigravity Conversation UUID: `0e2a3797-902e-4aba-8293-062e3271e26d`
