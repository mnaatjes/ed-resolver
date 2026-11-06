---
title: "Use-Case Specification: UC-03 Stream Continuous State Transitions"
use_case_id: "UC-03"
status: "draft"
version: "1.0.0"
level: "sea_level"
primary_actor: "Real-Time Visualizer (In-Game Overlay / Web Dashboard / HUD)"
created_at: "2026-11-06"
last_updated_at: "2026-11-06"
---

# Use-Case Specification: UC-03 Stream Continuous State Transitions

## 1. Description & Goal
Streams discrete state edge transitions (rising/falling bitfield changes such as `LANDING_GEAR_DOWN`, `SHIELDS_UP`, `SUPERCRUISE`, `ON_FOOT`) and quantized metric crossings (fuel critical alerts) to subscribed clients in real time without drowning consumers in 1 Hz steady-state noise.

## 2. Actors & Scope
* **Primary Actor:** Real-time client application (in-game HUD overlay, web dashboard, audio alert annunciator).
* **System Boundary:** `ed-resolver` standalone daemon driving adapter (`WebSocket /ws/telemetry/stream` or Server-Sent Events `/api/v1/stream/transitions`).

## 3. Preconditions
* `ed-resolver-daemon` is running and connected to active Frontier telemetry streams.
* Client has established an active WebSocket or SSE connection to the daemon endpoint.

## 4. Postconditions
* Client receives pushed JSON transition payloads strictly when state boundaries are breached or bitfield values toggle.
* Steady-state 1 Hz status ticks are filtered out and suppressed by the core `EdgeTransitionDetector` and `MetricQuantizer`.

## 5. Main Success Scenario (Basic Flow)
1. Actor establishes WebSocket connection to `/ws/telemetry/stream`.
2. Daemon sends initial snapshot frame representing the current baseline state.
3. Ingress adapter receives a 1 Hz `Status.json` tick containing modified bitfields or fuel mass.
4. Core `IngressClassifier` routes the status tick to `EdgeTransitionDetector` and `MetricQuantizer`.
5. `EdgeTransitionDetector` detects a rising edge (e.g. `Flags` bit 22 toggled 0 $\to$ 1: `SHIELDS_UP` dropped to `SHIELDS_DOWN`).
6. The domain core produces a discrete `EdgeTransitionEvent(flag="SHIELDS_UP", previous=True, current=False)`.
7. Daemon broadcasts the transition event across the active client connection.
8. Client receives the event and renders an immediate alert on the in-game overlay.

## 6. Extensions (Alternative Flows)
* **5a. Status Tick Contains Identical State (Steady State):**
  1. `EdgeTransitionDetector` evaluates $\Delta \text{Flags} = 0$ and `MetricQuantizer` evaluates hysteresis threshold as unchanged.
  2. The domain core generates zero transition events.
  3. Daemon suppresses transmission; zero packets are sent over the network.
* **7a. Client Disconnects Prematurely:**
  1. Daemon detects broken socket pipe on client connection.
  2. Daemon safely unsubscribes client without affecting internal state reduction or other connected actors.
