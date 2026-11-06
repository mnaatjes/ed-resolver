---
title: "Use-Case Specification: UC-04 Classify Telemetry Event Archetype"
use_case_id: "UC-04"
status: "draft"
version: "1.0.0"
level: "sea_level"
primary_actor: "TelemetryIngressWorker"
created_at: "2026-11-06"
last_updated_at: "2026-11-06"
---

# Use-Case Specification: UC-04 Classify Telemetry Event Archetype

## 1. Description & Goal
Enables the internal ingress pipeline to deterministically categorize incoming deserialized `ed-models` telemetry events into architectural archetypes (`EPOCH_MILESTONE`, `CONTEXT_MUTATOR`, `EDGE_TRANSITION`, `METRIC_QUANTIZER`, `PASSIVE`) in $O(1)$ time to route them to the appropriate domain state reducer or bypass queue.

## 2. Actors & Scope
* **Primary Actor:** `TelemetryIngressWorker` (internal ingress processor thread / loop).
* **Supporting Actor:** State Reducer Subsystem (`DomainStateReducer`).
* **System Boundary:** `ed-resolver` core domain classification subsystem (`IngressClassifier` / `ArchetypeRegistry`).

## 3. Preconditions
* The classification registry is initialized with the compiled `DEFAULT_ARCHETYPE_REGISTRY` mapping and any optional bootstrap override map.
* A journal record has been deserialized by `ed-models` into a concrete telemetry model instance.

## 4. Postconditions
* The event is mapped to exactly one `TelemetryArchetype` enum value.
* If classified as state-bearing (`EPOCH_MILESTONE`, `CONTEXT_MUTATOR`, `EDGE_TRANSITION`, or `METRIC_QUANTIZER`), the event is dispatched to the corresponding domain state reducer.
* If classified as `PASSIVE`, the event bypasses state mutation logic and is forwarded directly to downstream observers or telemetry emission queues.

## 5. Main Success Scenario (Basic Flow)
1. `TelemetryIngressWorker` receives a deserialized `ed-models` event object from the active `TelemetryIngressPort`.
2. `TelemetryIngressWorker` passes the event instance (or type) to `IngressClassifier.classify(event)`.
3. `IngressClassifier` checks its internal lookup map (`_overrides` followed by `_defaults`).
4. `IngressClassifier` resolves the event's type to a registered `TelemetryArchetype` (e.g. `EPOCH_MILESTONE` for `Location` or `FSDJump`).
5. `IngressClassifier` returns the resolved `TelemetryArchetype` to `TelemetryIngressWorker`.
6. `TelemetryIngressWorker` routes the event to the designated pipeline (state reduction or passive bypass).

## 6. Extensions (Alternative Flows)
* **3a. Bootstrap Override Hit:**
  1. `IngressClassifier` detects a custom mapping in `_overrides` supplied during bootstrap.
  2. The override archetype takes precedence over the default registry.
  3. Processing resumes at step 5.
* **4a. Uncataloged Event (Fallback to Passive):**
  1. An event type is received that is absent from both overrides and defaults (e.g. uncataloged journal event or upstream model added without regeneration).
  2. `IngressClassifier` logs a warning identifying the uncataloged event type.
  3. `IngressClassifier` falls back to `TelemetryArchetype.PASSIVE`.
  4. Processing resumes at step 5 without halting runtime telemetry ingestion.
