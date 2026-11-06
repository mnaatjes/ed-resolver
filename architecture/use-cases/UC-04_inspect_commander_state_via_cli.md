---
title: "Use-Case Specification: UC-04 Inspect Commander State via CLI"
use_case_id: "UC-04"
status: "draft"
version: "1.0.0"
level: "sea_level"
primary_actor: "Human Operator / Automation Script"
created_at: "2026-11-06"
last_updated_at: "2026-11-06"
---

# Use-Case Specification: UC-04 Inspect Commander State via CLI

## 1. Description & Goal
Allows a human operator or bash automation pipeline to query the current in-game status of the commander directly from the terminal shell via `ed-resolver` CLI commands, retrieving formatted spatial, vessel, and flight metrics.

## 2. Actors & Scope
* **Primary Actor:** Human operator or terminal script.
* **System Boundary:** `ed-resolver` CLI driving adapter (`src/ed_resolver/adapters/driving/cli.py`).

## 3. Preconditions
* `ed-resolver` package is installed and executable in the local terminal environment.
* Either a local `ed-resolver-daemon` is running, or local Frontier journal files are readable on the filesystem.

## 4. Postconditions
* Operator receives human-readable or JSON-formatted terminal output displaying active game state.
* Process exits with code `0` on success or non-zero on error.

## 5. Main Success Scenario (Basic Flow)
1. Operator executes `ed-resolver status` (or `ed-resolver status --json`).
2. The CLI driving adapter checks whether a local `ed-resolver-daemon` instance is listening on `localhost:8989`.
3. Daemon is reachable; CLI issues an HTTP request to `/api/v1/state/summary`.
4. Daemon responds with the active state summary payload.
5. CLI formats and prints the summary to stdout (e.g. System: Sol, Ship: Anaconda [Core Dynamics], Flight Mode: Supercruise, Fuel: Nominal).
6. Process terminates with exit code `0`.

## 6. Extensions (Alternative Flows)
* **3a. Local Daemon Is Not Running (Direct Fallback):**
  1. CLI fails to connect to `localhost:8989`.
  2. CLI automatically instantiates the embedded in-process `AmbientTelemetryFacade`.
  3. Facade performs UC-02 (Startup Back-Replay Hydration) against the local journal directory.
  4. Facade returns the active state snapshot.
  5. CLI prints formatted output and terminates cleanly with exit code `0`.
* **3b. Unseeded State (No Telemetry Found):**
  1. Facade/Daemon reports unseeded state (`None`).
  2. CLI outputs `"Commander Status: Unknown (No active journal telemetry detected)"`.
  3. Process exits with code `0`.
