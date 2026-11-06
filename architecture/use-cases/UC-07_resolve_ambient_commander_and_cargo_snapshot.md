---
title: "Use-Case Specification: UC-07 Resolve Ambient Commander and Cargo Snapshot"
use_case_id: "UC-07"
status: "draft"
version: "1.0.0"
level: "sea_level"
primary_actor: "Downstream Consumer (Trader Copilot / Inara Exporter / EDDN Dispatcher)"
created_at: "2026-11-06"
last_updated_at: "2026-11-06"
---

# Use-Case Specification: UC-07 Resolve Ambient Commander and Cargo Snapshot

## 1. Description & Goal
Allows a downstream client (via Python in-process facade `facade.commander` / `facade.cargo` or HTTP REST API) to synchronously retrieve the commander's profile, credits, and legal standing (`CommanderSnapshot`) and commodity inventory (`CargoInventorySnapshot`) in $O(1)$ time.

## 2. Actors & Scope
* **Primary Actor:** Downstream consumer application (e.g. trading optimizer, cargo manifest monitor, reputation exporter).
* **System Boundary:** `ed-resolver` driving adapter surfaces (`facade.commander.snapshot()`, `facade.cargo.snapshot()`, or REST `/api/v1/state/commander`, `/api/v1/state/cargo`).

## 3. Preconditions
* The `ed-resolver` state core is initialized and running.
* Journal ingress has processed startup records (`Commander`, `Cargo`) or active telemetry.

## 4. Postconditions
* Caller receives immutable `CommanderSnapshot` and/or `CargoInventorySnapshot` instances or `None` if unseeded.
* The state core remains unmutated by the read operation.

## 5. Main Success Scenario (Basic Flow)
1. Actor invokes `facade.commander.snapshot()` or `facade.cargo.snapshot()`.
2. The domain sub-facade queries the internal `StateStore` for the active snapshot.
3. The `StateStore` returns the active frozen snapshot instance in $O(1)$ non-blocking time.
4. The caller accesses strongly typed properties (e.g. `commander.credits`, `commander.is_wanted`, `cargo.inventory`).

## 6. Extensions (Alternative Flows)
* **3a. State Core Unseeded:**
  1. No `Commander` or `Cargo` event has been observed in the stream.
  2. The sub-facade returns `None` (or HTTP 204 No Content for REST).
  3. Processing completes cleanly without error.
