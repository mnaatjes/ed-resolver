---
title: "SDD 0009: Ambient Telemetry Facade and Composition Root Subsystem"
tags: ["sdd", "architecture", "facade", "adapters", "composition-root", "hexagonal", "ed-resolver"]
created_at: "2026-11-08"
last_updated_at: "2026-11-08"
---

# SDD 0009: Ambient Telemetry Facade and Composition Root Subsystem

* **Status:** Proposed
* **Governing ADRs:** [ADR 0001](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0001_core_domain_state_architecture_and_unified_ingress_lifecycle.md), [ADR 0003](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0003_ambient_telemetry_facade_query_contracts_and_governance.md), [ADR 0005](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0005_telemetry_ingress_worker_runtime_lifecycle.md), [ADR 0006](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0006_core_domain_state_model_taxonomy_and_immutability.md), [ADR 0007](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0007_in_memory_domain_state_store_and_atomic_swap.md), [ADR 0008](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0008_domain_event_reduction_pipelines_and_dispatch.md), [ADR 0009](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0009_ambient_telemetry_facade_and_composition_root.md)
* **Author:** Antigravity Pair Programmer
* **Version:** 1.0.0
* **Target Package:** `ed-resolver`

---

## 1. Introduction & Context

### 1.1 Purpose
This Software Design Document specifies the concrete architecture and implementation details for the `AmbientTelemetryFacade` driving adapter and the composition root factory (`create_resolver`). It translates the 9 domain sub-facades and atomic convenience predicates into clean, fully-typed Python components under `src/ed_resolver/adapters/driving/facade/`.

### 1.2 System Boundary & Scope
The implementation is strictly confined to:
* Domain Sub-Facades & Main Facade: `src/ed_resolver/adapters/driving/facade/`
  - `sub_facades.py` (9 domain sub-facades)
  - `facade.py` (`AmbientTelemetryFacade`)
  - `__init__.py` (re-exports)
* Composition Root Factory: `src/ed_resolver/bootstrap/factory.py` (`create_resolver`)
* Package Root Exports: `src/ed_resolver/__init__.py`
* Companion Tests: `tests/adapters/driving/test_ambient_facade.py`

---

## 2. Component Blueprint

```
src/ed_resolver/
├── adapters/driving/facade/
│   ├── __init__.py
│   ├── sub_facades.py        # LocationSubFacade, VesselSubFacade, etc.
│   └── facade.py             # AmbientTelemetryFacade
├── bootstrap/
│   ├── factory.py            # create_resolver() composition root
│   └── container.py
└── __init__.py               # Re-exports create_resolver, AmbientTelemetryFacade, *State
```

---

## 3. Sub-Facade & Facade Specifications

### 3.1 Sub-Facades (`src/ed_resolver/adapters/driving/facade/sub_facades.py`)
Each sub-facade takes `DomainStateReaderPort`:

```python
class LocationSubFacade:
    def __init__(self, reader: DomainStateReaderPort) -> None:
        self._reader = reader

    def state(self) -> LocationState:
        return self._reader.get_location()

    def is_docked(self) -> bool:
        return self.state().docked

    def in_supercruise(self) -> bool:
        return self.state().in_supercruise

    def on_surface(self) -> bool:
        return self.state().on_surface
```

### 3.2 `AmbientTelemetryFacade` (`src/ed_resolver/adapters/driving/facade/facade.py`)
Provides sub-facades, convenience aliases, and async context management:

```python
class AmbientTelemetryFacade:
    def __init__(
        self,
        reader: DomainStateReaderPort,
        worker: TelemetryIngressWorker | None = None,
    ) -> None:
        self._reader = reader
        self._worker = worker

        self.location = LocationSubFacade(reader)
        self.vessel = VesselSubFacade(reader)
        self.flight = FlightSubFacade(reader)
        self.cargo = CargoSubFacade(reader)
        self.commander = CommanderSubFacade(reader)
        self.station = StationSubFacade(reader)
        self.carrier = CarrierSubFacade(reader)
        self.exploration = ExplorationSubFacade(reader)
        self.powerplay = PowerplaySubFacade(reader)

    # Lifecycle Methods
    async def start(self) -> None:
        if self._worker is not None:
            await self._worker.start()

    async def stop(self, timeout: float = 5.0) -> None:
        if self._worker is not None:
            await self._worker.stop(timeout=timeout)

    async def __aenter__(self) -> AmbientTelemetryFacade:
        await self.start()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.stop()

    # Root Convenience Predicates
    def is_docked(self) -> bool:
        return self.location.is_docked()

    def is_on_foot(self) -> bool:
        return self.vessel.is_on_foot()

    def in_supercruise(self) -> bool:
        return self.location.in_supercruise()

    def is_in_srv(self) -> bool:
        return self.vessel.is_in_srv()

    def is_wanted(self) -> bool:
        return self.commander.is_wanted()
```

---

## 4. Composition Root Factory (`src/ed_resolver/bootstrap/factory.py`)

The `create_resolver` factory connects all hexagonal layers:
1. Instantiates `InMemoryDomainStateStore` (reader & writer).
2. Instantiates `ProcessTelemetryReductionUseCase(reader, writer)`.
3. Instantiates `IngressClassifier`.
4. Instantiates `TelemetryPayloadDeserializer` & `QuarantineDeadLetterQueue`.
5. Instantiates `TelemetryIngressWorker`.
6. Wraps and returns `AmbientTelemetryFacade`.

---

## 5. Verification & Testing Strategy

1. **Sub-Facade State & Predicate Tests:**
   - Verify every sub-facade returns the latest active state and projects correct boolean values.
2. **Root Convenience Aliasing Tests:**
   - Verify `facade.is_docked()`, `facade.is_on_foot()`, etc., strictly mirror their sub-facades.
3. **End-to-End Pipeline Smoke Test:**
   - Feed raw envelopes into `create_resolver(ingress_port=MemoryQueueAdapter())`.
   - Start worker via `async with facade:`.
   - Verify raw JSON input immediately projects into updated `facade.location.state()`.
4. **Hexagonal Boundary Conformance:**
   - Assert all quality gates pass via `python scripts/verify.py`.
