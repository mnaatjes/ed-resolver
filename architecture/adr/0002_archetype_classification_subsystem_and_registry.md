---
title: "ADR 0002: Archetype Classification Subsystem and Registry"
tags: ["adr", "ed-resolver", "architecture", "classification", "registry", "archetypes", "hexagonal"]
created_at: "2026-11-06"
last_updated_at: "2026-11-06"
---

# ADR 0002: Archetype Classification Subsystem and Registry

* **Status:** Accepted
* **Date:** 2026-11-06
* **Deciders:** Michael Naatjes, Antigravity Agent
* **Consulted:** [ADR 0001](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0001_core_domain_state_architecture_and_unified_ingress_lifecycle.md), ADR 0003 (`ed-integration-smoke`)

---

## 1. Context and Problem Statement

`ed-resolver` transforms continuous and discrete telemetry emitted by Frontier's *Elite Dangerous* client into consolidated state snapshots (`LocationSnapshot`, `VesselSnapshot`, `FlightMode`, `QuantizedFuelState`).

As established in ADR 0001, incoming raw JSON payloads are deserialized into strongly typed `ed-models` dataclasses (`FsdJumpEvent`, `LocationEvent`, `StatusFlags`, `LoadoutEvent`, `CargoEvent`). Over 260 distinct event and status models exist across the game taxonomy.

To avoid authoring hundreds of brittle, bespoke reduction handlers, events are mapped into the four mathematical Behavioral Archetypes defined in ADR 0003:
1. **`EPOCH_MILESTONE`:** Idempotent point-in-time state replacements (`Location`, `FSDJump`).
2. **`CONTEXT_MUTATOR`:** Set differentials on inventories and equipment (`Loadout`, `MarketBuy`).
3. **`EDGE_TRANSITION`:** Bitmask delta toggles on continuous 1 Hz flags (`StatusFlags`, `StatusFlags2`).
4. **`METRIC_QUANTIZER`:** Hysteresis threshold band evaluations on scalar gauges (`Fuel`, `HullDamage`).

However, the architecture requires an explicit, deterministic mechanism governing:
* **When** classification occurs.
* **Where** the taxonomy mappings reside.
* **How** the classification subsystem is instantiated, accessed, and overridden across in-process libraries, daemon runtimes, and test harnesses.

How should `ed-resolver` architect the classification subsystem to deliver sub-microsecond routing while preserving static type safety and allowing runtime test overrides?

---

## 2. Decision Drivers

* **Sub-Microsecond Dispatch Performance ($O(1)$):** During high-frequency bursts (such as hyperspace entry emitting dozens of events concurrently), event classification must execute in instantaneous $O(1)$ time without regex parsing or JSON string sniffing.
* **Strict Type Safety:** Classification must operate on Python types (`type[JournalEvent]`), leveraging `ed-models` dataclasses rather than unstructured string matching.
* **Hexagonal Decoupling & Immutability:** `ed-models` must remain passive and unopinionated; no archetype metadata or classification protocols may leak into upstream model packages.
* **Testability & Extensibility:** Test suites and downstream consumers must be able to inject custom classification overrides (e.g. treating a custom event as a milestone during integration scenarios) without modifying global package state.
* **Zero-I/O Domain Purity:** The classification service must remain 100% synchronous, stateless, and free of external framework dependencies.

---

## 3. Considered Options

* **Option 1: Container Registration Only (Dynamic DI).** Require the bootstrap container to register every single model and archetype pair procedurally during application startup. Rejected because manual registration of 260+ models introduces startup boilerplate and risks inconsistent mapping if multiple containers are configured.
* **Option 2: Hardcoded Static Mapping Dict Only.** Define a global frozen dictionary mapping types to archetypes. Rejected because consumers and unit tests cannot override or extend classifications for experimental event flows without mutating global state.
* **Option 3: Dynamic JSON String Sniffing at Ingress.** Inspect raw JSON strings (e.g., parsing the `"event"` key) before deserialization. Rejected because it throws away static type safety, duplicates string matching, incurs continuous serialization overhead on 1 Hz ticks, and bypasses `ed-models`.
* **Option 4: Static Defaults with Bootstrap Injection (The Canonical Fleet Solution - Selected).** Provide an immutable, pre-compiled default mapping registry (`DEFAULT_ARCHETYPE_REGISTRY`), wrapped by an injectable domain service (`IngressClassifier`) instantiated at bootstrap with optional override support.

---

## 4. Decision Outcome

**Chosen Option:** **Option 4: Static Defaults with Bootstrap Injection**.

### 4.1 Subsystem Architecture & Access Pattern

```
                            COMPILE / MODULE LOAD TIME
+─────────────────────────────────────────────────────────────────────────────+
|  STATIC TAXONOMY REGISTRY (`DEFAULT_ARCHETYPE_REGISTRY`):                    |
|  dict[type[JournalEvent | StatusFlags], TelemetryArchetype]                 |
|  - Pre-compiled mapping table covering all 260+ ed-models dataclasses.      |
+─────────────────────────────────────────────────────────────────────────────+
                                      │
                                      ▼ injected at application bootstrap
+─────────────────────────────────────────────────────────────────────────────+
|  BOOTSTRAP CONTAINER (`Container.build_ingress_classifier()`):               |
|  - Merges DEFAULT_ARCHETYPE_REGISTRY with optional caller overrides.        |
|  - Produces immutable IngressClassifier domain service instance.            |
+─────────────────────────────────────────────────────────────────────────────+
                                      │
                                      ▼ injected into Ingress Pipeline
+─────────────────────────────────────────────────────────────────────────────+
|  DOMAIN SERVICE (`IngressClassifier`):                                      |
|  - Method: `classify(event: object) -> TelemetryArchetype | None`            |
|  - Performance: Instantaneous O(1) memory lookup via `type(event)`.         |
+─────────────────────────────────────────────────────────────────────────────+
                                      │
                                      ▼ routes typed object to reducer
+─────────────────────────────────────────────────────────────────────────────+
|  ARCHETYPE REDUCTION PIPELINES:                                             |
|  - EPOCH_MILESTONE  ──> EpochMilestoneAggregator                            |
|  - CONTEXT_MUTATOR  ──> ContextMutator                                      |
|  - EDGE_TRANSITION  ──> EdgeTransitionDetector                              |
|  - METRIC_QUANTIZER ──> MetricQuantizer                                     |
+─────────────────────────────────────────────────────────────────────────────+
```

### 4.2 Subsystem Components and Locations

1. **The Archetype Enumeration (`src/ed_resolver/core/domain/archetypes.py`):**
   ```python
   class TelemetryArchetype(Enum):
       EPOCH_MILESTONE = "epoch_milestone"
       CONTEXT_MUTATOR = "context_mutator"
       EDGE_TRANSITION = "edge_transition"
       METRIC_QUANTIZER = "metric_quantizer"
   ```

2. **The Static Registry Table (`src/ed_resolver/core/domain/classification/registry.py`):**
   * Pre-compiles the definitive mapping of `ed-models` dataclasses into their respective archetypes:
   ```python
   DEFAULT_ARCHETYPE_REGISTRY: Mapping[type, TelemetryArchetype] = MappingProxyType({
       # Epoch Milestones (Spatial, Travel, Session)
       FsdJumpEvent: TelemetryArchetype.EPOCH_MILESTONE,
       LocationEvent: TelemetryArchetype.EPOCH_MILESTONE,
       CarrierJumpEvent: TelemetryArchetype.EPOCH_MILESTONE,
       DockedEvent: TelemetryArchetype.EPOCH_MILESTONE,
       UndockedEvent: TelemetryArchetype.EPOCH_MILESTONE,
       SupercruiseEntryEvent: TelemetryArchetype.EPOCH_MILESTONE,
       SupercruiseExitEvent: TelemetryArchetype.EPOCH_MILESTONE,
       TouchdownEvent: TelemetryArchetype.EPOCH_MILESTONE,
       LiftoffEvent: TelemetryArchetype.EPOCH_MILESTONE,

       # Context Mutators (Loadout, Equipment, Cargo, Accounts)
       LoadoutEvent: TelemetryArchetype.CONTEXT_MUTATOR,
       ModuleBuyEvent: TelemetryArchetype.CONTEXT_MUTATOR,
       ModuleSellEvent: TelemetryArchetype.CONTEXT_MUTATOR,
       ShipyardSwapEvent: TelemetryArchetype.CONTEXT_MUTATOR,
       CollectCargoEvent: TelemetryArchetype.CONTEXT_MUTATOR,
       EjectCargoEvent: TelemetryArchetype.CONTEXT_MUTATOR,

       # Continuous Bitfield Flags (Edge Transitions)
       StatusFlags: TelemetryArchetype.EDGE_TRANSITION,
       StatusFlags2: TelemetryArchetype.EDGE_TRANSITION,

       # Continuous Metrics (Quantized Bands)
       FuelTelemetry: TelemetryArchetype.METRIC_QUANTIZER,
       HullDamageEvent: TelemetryArchetype.METRIC_QUANTIZER,
   })
   ```

3. **The IngressClassifier Service (`src/ed_resolver/core/domain/classification/classifier.py`):**
   * Encapsulates lookup logic and safe fallback handling:
   ```python
   class IngressClassifier:
       """Pure domain service classifying typed ed-models into behavioral archetypes."""

       def __init__(
           self,
           registry: Mapping[type, TelemetryArchetype] | None = None,
           overrides: Mapping[type, TelemetryArchetype] | None = None,
       ) -> None:
           base = dict(registry or DEFAULT_ARCHETYPE_REGISTRY)
           if overrides:
               base.update(overrides)
           self._registry: Mapping[type, TelemetryArchetype] = MappingProxyType(base)

       def classify(self, event: object) -> TelemetryArchetype | None:
           """Resolves archetype in O(1) time based on Python type."""
           return self._registry.get(type(event))
   ```

4. **Composition Root (`src/ed_resolver/bootstrap/container.py`):**
   * Injects the singleton `IngressClassifier` into the ingress pipeline during runtime initialization:
   ```python
   def build_ingress_classifier(
       overrides: Mapping[type, TelemetryArchetype] | None = None
   ) -> IngressClassifier:
       return IngressClassifier(overrides=overrides)
   ```

### 4.3 Classification Execution Timing

* Classification occurs strictly **at the Ingress Boundary immediately after raw deserialization**:
  1. `TelemetryIngressWorker` receives raw JSON bytes from the active `TelemetryIngressPort`.
  2. The worker invokes `ed_models.parse_journal_event(json_dict)`.
  3. The resulting typed dataclass instance is passed to `classifier.classify(event)`.
  4. The returned archetype directly routes the event to the appropriate reducer:
     * If `EPOCH_MILESTONE` $\rightarrow$ passes to `EpochMilestoneAggregator`.
     * If `CONTEXT_MUTATOR` $\rightarrow$ passes to `ContextMutator`.
     * If `None` (uncataloged or non-state event) $\rightarrow$ discarded or forwarded to audit logs.

---

## 5. Consequences

### Positive
* **Deterministic $O(1)$ Performance:** Type-based dictionary hashing eliminates repeated string parsing and regex matching on high-frequency streams.
* **Zero Model Coupling:** `ed-models` remains pure, passive, and unopinionated; archetype semantics are managed entirely within `ed-resolver`.
* **Isolated Extension Points:** Custom applications or integration test doubles can inject archetype overrides via `container.build_ingress_classifier(overrides=...)` without mutating global state.
* **Hexagonal Compliance:** The classifier is a pure, zero-I/O domain service with zero third-party dependencies, adhering strictly to architectural boundaries.

### Negative / Trade-offs
* `DEFAULT_ARCHETYPE_REGISTRY` must be maintained alongside `ed-models` releases as new game events are introduced by Frontier Developments.
* Events emitted by the game that are omitted from the registry resolve to `None` and are ignored by state reducers (mitigated by automated parity tests in `tests/architecture/test_archetype_parity.py`).

---

## 6. Validation and Next Steps

1. Implement `DEFAULT_ARCHETYPE_REGISTRY` and `IngressClassifier` in `src/ed_resolver/core/domain/classification/`.
2. Add automated architectural parity test (`tests/architecture/test_archetype_parity.py`) asserting that all milestone and loadout event models exported by `ed-models` are explicitly mapped.
