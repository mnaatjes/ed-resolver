---
title: "Use-Case Specification: UC-01 Resolve Ambient Location Snapshot"
use_case_id: "UC-01"
status: "draft"
version: "1.0.0"
level: "sea_level"
primary_actor: "Downstream Consumer (TUI Dashboard / Copilot / EDDN Engine)"
created_at: "2026-11-06"
last_updated_at: "2026-11-06"
---

# Use-Case Specification: UC-01 Resolve Ambient Location Snapshot

## 1. Description & Goal
Allows a downstream client (whether via Python in-process facade, HTTP REST API, or operator CLI) to synchronously retrieve the commander's current spatial location and environmental context (`LocationSnapshot`) in $O(1)$ time without parsing journal event histories.

## 2. Actors & Scope
* **Primary Actor:** Downstream consumer application (e.g. TUI overlay, itinerary copilot, EDDN contract accumulator, or human operator via CLI).
* **System Boundary:** `ed-resolver` driving adapter surfaces (`AmbientTelemetryFacade`, REST controller `GET /api/v1/state/location`, or `ed-resolver status`).

## 3. Preconditions
* The `ed-resolver` state core is initialized and running (in-process or via standalone daemon).
* Ingress file watchers have completed startup back-replay hydration or are listening to active journal streams.

## 4. Postconditions
* The caller receives an immutable `LocationSnapshot` containing system name, coordinates, address, station name, and body, or `None` if unseeded.
* The state core remains unmutated by the read operation.

## 5. Main Success Scenario (Basic Flow)
1. Actor invokes `facade.get_location()` (or requests `GET /api/v1/state/location` or runs `ed-resolver location`).
2. The driving adapter queries the internal state store for the active location snapshot.
3. The state store returns the current atomic, frozen `LocationSnapshot` instance.
4. The driving adapter delivers the snapshot to the actor:
   * As a typed dataclass (in-process facade).
   * As a serialized JSON response (REST API).
   * As formatted human-readable terminal output (CLI).

## 6. Extensions (Alternative Flows)
* **3a. State Core Unseeded (Cold Start Without Prior Milestone):**
  1. The state store indicates that no `Location`, `FSDJump`, or `CarrierJump` milestone has been observed in the journal stream or historical log.
  2. The driving adapter returns `None` (in-process facade), returns HTTP `204 No Content` / `null` payload (REST API), or displays `"Location: Unknown (Unseeded)"` (CLI).
  3. The caller handles the unseeded state without encountering a runtime crash or uncaught exception.
