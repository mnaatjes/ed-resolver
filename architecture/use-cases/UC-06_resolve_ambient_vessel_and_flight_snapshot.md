---
title: "Use-Case Specification: UC-06 Resolve Ambient Vessel and Flight Snapshot"
use_case_id: "UC-06"
status: "draft"
version: "1.0.0"
level: "sea_level"
primary_actor: "Downstream Consumer (TUI Overlay / Copilot / Systems Monitor)"
created_at: "2026-11-06"
last_updated_at: "2026-11-06"
---

# Use-Case Specification: UC-06 Resolve Ambient Vessel and Flight Snapshot

## 1. Description & Goal
Allows a downstream client (via Python in-process facade `facade.vessel` / `facade.flight` or HTTP REST API) to synchronously retrieve the commander's active ship/suit loadout (`VesselSnapshot`) and continuous 1 Hz cockpit telemetry (`FlightModeSnapshot`) in $O(1)$ time.

## 2. Actors & Scope
* **Primary Actor:** Downstream consumer application (e.g. cockpit overlay, equipment optimizer, power distributor monitor).
* **System Boundary:** `ed-resolver` driving adapter surfaces (`facade.vessel.snapshot()`, `facade.flight.snapshot()`, or REST endpoints `/api/v1/state/vessel` and `/api/v1/state/flight`).

## 3. Preconditions
* The `ed-resolver` state core is initialized and running.
* Ingress worker is listening to active telemetry streams or back-replay has hydrated initial state.

## 4. Postconditions
* Caller receives immutable `VesselSnapshot` and/or `FlightModeSnapshot` instances or `None` if unseeded.
* The state core remains unmutated by the read operation.

## 5. Main Success Scenario (Basic Flow)
1. Actor invokes `facade.vessel.snapshot()` or `facade.flight.snapshot()`.
2. The domain sub-facade queries the internal `StateStore` for the requested snapshot.
3. The `StateStore` returns the active frozen snapshot instance in $O(1)$ non-blocking time.
4. The caller accesses strongly typed properties (e.g. `vessel.ship_name`, `flight.landing_gear_down`).

## 6. Extensions (Alternative Flows)
* **3a. State Core Unseeded:**
  1. The state store indicates that no `Loadout` or `StatusTelemetry` event has yet been observed.
  2. The sub-facade returns `None` (or HTTP 204 No Content for REST).
  3. Processing completes without raising an unhandled exception.
