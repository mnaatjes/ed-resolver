---
title: "ADR 0010: Thin CLI Client Entrypoint, Daemon Process Supervision, and Zero-Dependency HTTP/SSE API"
tags: ["adr", "ed-resolver", "architecture", "cli", "daemon", "http", "sse", "api", "entrypoint", "hexagonal"]
created_at: "2026-11-08"
last_updated_at: "2026-11-08"
---

# ADR 0010: Thin CLI Client Entrypoint, Daemon Process Supervision, and Zero-Dependency HTTP/SSE API

* **Status:** Accepted
* **Date:** 2026-11-08
* **Deciders:** Michael Naatjes, Antigravity Agent
* **Consulted:** [ADR 0001](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0001_core_domain_state_architecture_and_unified_ingress_lifecycle.md), [ADR 0004](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0004_hexagonal_scope_boundary_contracts_and_quality_gates.md), [ADR 0009](file:///home/michael/src/github.com/mnaatjes/ed-resolver/architecture/adr/0009_ambient_telemetry_facade_and_composition_root.md)

---

## 1. Context and Problem Statement

`ed-resolver` provides domain state reduction and an in-process `AmbientTelemetryFacade`. However, non-Python client applications (e.g. Go/Rust companion apps, web overlays, Discord bots, and homelab microservices) cannot embed a Python library directly. Furthermore, multiple running tools must not open competing file handles to local journal logs on disk.

ADR 0001 articulated the requirement for a dual operational topology:
1. An embedded library (`create_resolver()`).
2. A standalone daemon CLI entrypoint (`ed-resolver`) serving state out-of-process.

How should the thin CLI client and standalone daemon server be structured in `ed-resolver` to provide robust process supervision, signal handling, zero mandatory heavy dependencies, and a complete REST/SSE API surface while strictly respecting hexagonal boundary rules?

---

## 2. Decision Drivers

* **Hexagonal Layer Decoupling (HEXA-TRUTH-01, HEXA-TRUTH-19):** CLI entrypoints and HTTP servers are outermost driving adapters (Layer 4). They must never pollute `core.domain`, `core.ports`, or `core.use_cases`.
* **Zero Mandatory Heavy Dependencies:** Following the architectural precedent in `ed-telemetry`, the daemon's HTTP/SSE server must run out-of-the-box using Python's standard library (`http.server.ThreadingHTTPServer` with `asyncio` bridging) without forcing third-party dependencies (`fastapi`, `uvicorn`, `starlette`) onto minimal consumers.
* **Complete State Surface Exposure:** The HTTP API must expose all 9 domain states (`location`, `vessel`, `flight`, `cargo`, `commander`, `station`, `carrier`, `exploration`, `powerplay`), health/liveness probes, macro predicates, and a real-time Server-Sent Events (SSE) transition stream.
* **Clean OS Process Supervision:** Support graceful shutdown via POSIX signal interception (`SIGINT`, `SIGTERM`), port binding options (`--host`, `--port`), and automated ingress adapter selection.

---

## 3. Decision Outcome

**Chosen Option:** Author a modular CLI driving package under `src/ed_resolver/daemon/` containing:
1. `cli.py`: Click/argparse CLI entrypoint registered in `pyproject.toml` console scripts as `ed-resolver`.
2. `server.py`: Driving HTTP adapter built on standard library `http.server.ThreadingHTTPServer` with CORS headers, JSON serialization, and an active SSE subscriber broadcast hub.
3. Complete OpenAPI 3.1 contract documented under `architecture/api/openapi.yaml`.

---

## 4. Architectural Details

### 4.1 CLI Entrypoint (`src/ed_resolver/daemon/cli.py`)

The CLI exposes two primary commands:
* `ed-resolver serve`: Launches the standalone background daemon, connects telemetry ingress, initializes `AmbientTelemetryFacade`, and hosts the HTTP/SSE server until `SIGINT`/`SIGTERM`.
* `ed-resolver status`: Lightweight client probe verifying whether a local daemon is healthy and printing current star system / vessel state.

CLI Flags for `serve`:
* `--host`: Interface to bind (default: `127.0.0.1`).
* `--port`: Port to listen on (default: `8989`).
* `--telemetry-url`: HTTP/SSE base URL of an upstream `ed-telemetry` provider (default: `http://127.0.0.1:8080`).
* `--log-level`: Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`).

### 4.2 API Endpoint Inventory

The daemon provides REST and SSE endpoints matching all sub-facade query capabilities:

1. **System & Health:**
   * `GET /api/v1/health`: Liveness and status check.
   * `GET /api/v1/predicates`: Consolidated map of all atomic convenience predicates (`is_docked`, `is_on_foot`, etc.).

2. **Domain State Endpoints (REST GET):**
   * `GET /api/v1/state/location`: Returns serialized `LocationState`.
   * `GET /api/v1/state/vessel`: Returns serialized `VesselState`.
   * `GET /api/v1/state/flight`: Returns serialized `FlightState`.
   * `GET /api/v1/state/cargo`: Returns serialized `CargoState`.
   * `GET /api/v1/state/commander`: Returns serialized `CommanderState`.
   * `GET /api/v1/state/station`: Returns serialized `StationState`.
   * `GET /api/v1/state/carrier`: Returns serialized `CarrierState`.
   * `GET /api/v1/state/exploration`: Returns serialized `ExplorationState`.
   * `GET /api/v1/state/powerplay`: Returns serialized `PowerplayState`.
   * `GET /api/v1/state`: Consolidated snapshot of all 9 domain states.

3. **Real-time Event Streaming:**
   * `GET /api/v1/stream`: Server-Sent Events (SSE) streaming live domain updates whenever incoming telemetry mutates state.

---

## 5. Consequences

### Positive
* External non-Python homelab applications and companion tools gain full, unified access to resolved *Elite Dangerous* domain state.
* The daemon requires zero third-party web frameworks for basic operation, preserving a minimal dependency tree.
* Signal supervision guarantees clean cleanup of threads and network sockets.

### Negative / Trade-Offs
* Standard library `http.server` provides synchronous thread-per-request handling. For high-volume fleet traffic, future iterations can introduce optional ASGI extra dependencies (`ed-resolver[uvicorn]`).
