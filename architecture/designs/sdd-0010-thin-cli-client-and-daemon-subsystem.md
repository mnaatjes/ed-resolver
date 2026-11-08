---
title: "SDD 0010: Thin CLI Client and Daemon HTTP/SSE Subsystem"
tags: ["sdd", "architecture", "cli", "daemon", "http", "sse", "ed-resolver"]
created_at: "2026-11-08"
last_updated_at: "2026-11-08"
---

# SDD 0010: Thin CLI Client and Daemon HTTP/SSE Subsystem

* **Status:** Proposed
* **Governing ADRs:** [ADR 0001](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0001_core_domain_state_architecture_and_unified_ingress_lifecycle.md), [ADR 0004](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0004_hexagonal_scope_boundary_contracts_and_quality_gates.md), [ADR 0009](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0009_ambient_telemetry_facade_and_composition_root.md), [ADR 0010](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0010_thin_cli_client_and_daemon_api.md)
* **Author:** Antigravity Pair Programmer
* **Version:** 1.0.0
* **Target Package:** `ed-resolver`

---

## 1. Introduction & Context

### 1.1 Purpose
This Software Design Document specifies the architecture, routing structure, concurrency model, and execution lifecycle for the `ed-resolver` CLI command-line client and standalone daemon HTTP/SSE server.

### 1.2 System Boundary & Scope
The subsystem resides entirely in `src/ed_resolver/daemon/`:
* `cli.py`: Command-line interface driver (`serve`, `status`, `version`).
* `server.py`: Standard library HTTP/SSE daemon server.
* `broadcaster.py`: SSE subscriber fan-out event hub.
* `__init__.py`: Module entry point.
* Integration tests: `tests/daemon/test_cli_and_server.py`.

---

## 2. Component Structure & Concurrency Blueprint

```
src/ed_resolver/daemon/
├── __init__.py
├── broadcaster.py      # Thread-safe queue manager for SSE subscribers
├── cli.py              # CLI argument parser and signal supervisor
└── server.py           # ThreadingHTTPServer with REST routes & SSE handler
```

### 2.1 Concurrency & Execution Model
1. The CLI initializes an `asyncio` event loop on the main thread running `facade.start()`.
2. The `ThreadingHTTPServer` runs on a dedicated daemon background thread, accepting incoming HTTP requests and dispatching them to worker threads.
3. When domain states are updated or queried:
   - REST endpoints read thread-safely from `facade.<domain>.state()` (guaranteed lockless and atomic via `InMemoryDomainStateStore` pointer swapping).
   - The SSE broadcast hub receives state push notifications and enqueues SSE frames to active HTTP streaming connections.
4. On `SIGINT` or `SIGTERM`, the main loop cancels tasks, calls `server.shutdown()`, awaits `facade.stop()`, and exits cleanly with return code 0.

---

## 3. Concrete Endpoint Specifications

### 3.1 Health & Diagnostics
* `GET /api/v1/health`
  - Response: `{"status": "ok", "version": "0.1.0", "timestamp": "...", "uptime_seconds": 12.3}`
* `GET /api/v1/predicates`
  - Response:
    ```json
    {
      "is_docked": false,
      "in_supercruise": true,
      "on_surface": false,
      "is_on_foot": false,
      "is_in_srv": false,
      "is_wanted": false
    }
    ```

### 3.2 Domain State Endpoints
* `GET /api/v1/state/location` -> JSON representation of `LocationState`.
* `GET /api/v1/state/vessel` -> JSON representation of `VesselState`.
* `GET /api/v1/state/flight` -> JSON representation of `FlightState`.
* `GET /api/v1/state/cargo` -> JSON representation of `CargoState`.
* `GET /api/v1/state/commander` -> JSON representation of `CommanderState`.
* `GET /api/v1/state/station` -> JSON representation of `StationState`.
* `GET /api/v1/state/carrier` -> JSON representation of `CarrierState`.
* `GET /api/v1/state/exploration` -> JSON representation of `ExplorationState`.
* `GET /api/v1/state/powerplay` -> JSON representation of `PowerplayState`.
* `GET /api/v1/state` -> Combined object mapping domain names to their respective current states.

### 3.3 Real-time Stream
* `GET /api/v1/stream`
  - Content-Type: `text/event-stream`
  - Keeps connection open and streams JSON events:
    ```text
    event: state_update
    data: {"domain": "location", "state": {"star_system": "Sol", ...}}
    ```

---

## 4. Error Handling and Resilience

* Invalid URL paths return `404 Not Found` with JSON: `{"error": "Endpoint not found", "path": "..."}`.
* Methods other than `GET` return `405 Method Not Allowed`.
* Unhandled server exceptions return `500 Internal Server Error` with JSON error details without leaking stack traces.
* CORS headers (`Access-Control-Allow-Origin: *`, `Access-Control-Allow-Methods: GET, OPTIONS`) are applied across all responses to permit browser-based overlay consumption.
