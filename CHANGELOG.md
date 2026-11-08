# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Thin CLI Client & Standalone Daemon (ADR 0010 / SDD 0010):**
  - Implemented command-line interface entrypoint in [`src/ed_resolver/daemon/cli.py`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/src/ed_resolver/daemon/cli.py) with `serve` and `status` subcommands.
  - Registered `ed-resolver` console script in [`pyproject.toml`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/pyproject.toml).
  - Implemented zero-dependency `TelemetryDaemonServer` in [`src/ed_resolver/daemon/server.py`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/src/ed_resolver/daemon/server.py) built on standard library `ThreadingHTTPServer`.
  - Implemented thread-safe `EventBroadcaster` in [`src/ed_resolver/daemon/broadcaster.py`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/src/ed_resolver/daemon/broadcaster.py) for SSE fan-out streaming.
  - Exposed REST endpoints for `/health`, `/predicates`, `/state`, and all 9 domain states (`/state/location`, `/state/vessel`, etc.).
  - Authored authoritative OpenAPI 3.1 contract in [`architecture/api/openapi.yaml`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/api/openapi.yaml).
  - Authored comprehensive test suite in [`tests/daemon/test_cli_and_server.py`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/tests/daemon/test_cli_and_server.py).
- **Diátaxis Documentation Suite:**
  - Authored consumer API reference in [`docs/reference/facade_api.md`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/docs/reference/facade_api.md).
  - Authored installation and setup how-to guide in [`docs/how-to/install_and_setup.md`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/docs/how-to/install_and_setup.md).
  - Authored telemetry querying recipe how-to guide in [`docs/how-to/query_ambient_telemetry.md`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/docs/how-to/query_ambient_telemetry.md).
  - Authored quickstart telemetry listener tutorial in [`docs/tutorials/quickstart_telemetry_listener.md`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/docs/tutorials/quickstart_telemetry_listener.md).

## [0.1.0] - 2026-11-08

### Added
- **Domain State Models & Immutability (ADR 0006 / SDD 0006):**
  - Implemented 9 pure, frozen, slotted domain state models under [`src/ed_resolver/core/domain/`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/src/ed_resolver/core/domain/): `LocationState`, `VesselState`, `FlightState`, `CargoState`, `CommanderState`, `StationState`, `CarrierState`, `ExplorationState`, and `PowerplayState`.
  - Enforced post-init invariant self-validations and immutable container wrappers (`MappingProxyType`).
  - Authored unit and mutation guard test suite in [`tests/core/domain/test_state_models.py`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/tests/core/domain/test_state_models.py).
- **In-Memory State Store & Atomic Swapping (ADR 0007 / SDD 0007):**
  - Defined driven port protocols [`src/ed_resolver/core/ports/driven/state_store.py`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/src/ed_resolver/core/ports/driven/state_store.py) (`DomainStateReaderPort`, `DomainStateWriterPort`).
  - Implemented thread-safe, lockless [`src/ed_resolver/adapters/driven/state_store/in_memory.py`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/src/ed_resolver/adapters/driven/state_store/in_memory.py) (`InMemoryDomainStateStore`).
  - Created test double parity in [`tests/doubles/fake_state_store.py`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/tests/doubles/fake_state_store.py).
  - Authored concurrency and multi-threaded test suite in [`tests/adapters/driven/test_in_memory_state_store.py`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/tests/adapters/driven/test_in_memory_state_store.py).
- **Domain Event Reducers & Pipeline Dispatch (ADR 0008 / SDD 0008):**
  - Defined driving port protocol [`src/ed_resolver/core/ports/driving/reduction.py`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/src/ed_resolver/core/ports/driving/reduction.py) (`ReduceTelemetryEventPort`).
  - Implemented pure functional reducers across all 9 domains under `src/ed_resolver/core/domain/<domain>/reducers.py` supporting both PascalCase and snake_case DTO attributes.
  - Implemented use case interactor [`src/ed_resolver/core/use_cases/process_telemetry_reduction.py`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/src/ed_resolver/core/use_cases/process_telemetry_reduction.py) (`ProcessTelemetryReductionUseCase`).
  - Authored unit test suites in [`tests/core/domain/test_reducers.py`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/tests/core/domain/test_reducers.py) and [`tests/core/use_cases/test_process_telemetry_reduction.py`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/tests/core/use_cases/test_process_telemetry_reduction.py).
- **Ambient Telemetry Facade & Composition Root (ADR 0009 / SDD 0009):**
  - Implemented 9 domain sub-facades in [`src/ed_resolver/adapters/driving/facade/sub_facades.py`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/src/ed_resolver/adapters/driving/facade/sub_facades.py).
  - Implemented root driving adapter [`src/ed_resolver/adapters/driving/facade/facade.py`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/src/ed_resolver/adapters/driving/facade/facade.py) (`AmbientTelemetryFacade`) with async lifecycle supervision (`start`, `stop`, `async with`) and non-divergent macro predicates.
  - Implemented composition root factory [`src/ed_resolver/bootstrap/factory.py`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/src/ed_resolver/bootstrap/factory.py) (`create_resolver`).
  - Authored end-to-end integration test suite in [`tests/adapters/driving/test_ambient_facade.py`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/tests/adapters/driving/test_ambient_facade.py).
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
  - [`ADR 0006: Core Domain State Model Taxonomy and Immutability Contracts`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0006_core_domain_state_model_taxonomy_and_immutability.md).
  - [`ADR 0007: In-Memory Domain State Store and Atomic Swap Architecture`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0007_in_memory_domain_state_store_and_atomic_swap.md).
  - [`ADR 0008: Domain Event Reduction Pipelines and Dispatch Architecture`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0008_domain_event_reduction_pipelines_and_dispatch.md).
  - [`ADR 0009: Ambient Telemetry Facade Implementation and Composition Root`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0009_ambient_telemetry_facade_and_composition_root.md).
  - [`SDD 0002: Hexagonal Domain Package Layout and Archetype Classification Registry Generator`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/designs/sdd-0002-hexagonal-domain-package-layout-and-archetype-registry-generator.md).
  - [`SDD 0004: Hexagonal Scope Boundary Contracts and Quality Enforcement Pipeline`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/designs/sdd-0004-hexagonal-scope-boundary-contracts-and-quality-enforcement-pipeline.md).
  - [`SDD 0005: TelemetryIngressWorker Runtime and Ingress Lifecycle Subsystem`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/designs/sdd-0005-telemetry-ingress-worker-runtime-lifecycle.md).
  - [`SDD 0006: Core Domain State Models and Immutability Subsystem`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/designs/sdd-0006-core-domain-state-models-and-immutability.md).
  - [`SDD 0007: In-Memory Domain State Store Subsystem`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/designs/sdd-0007-in-memory-domain-state-store.md).
  - [`SDD 0008: Domain Event Reduction Pipeline and Dispatch Subsystem`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/designs/sdd-0008-domain-event-reduction-pipeline.md).
  - [`SDD 0009: Ambient Telemetry Facade and Composition Root Subsystem`](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/designs/sdd-0009-ambient-telemetry-facade-and-composition-root.md).
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
