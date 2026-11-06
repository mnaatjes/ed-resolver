---
title: "Use-Case Specification: UC-02 Hydrate Startup State via Back-Replay"
use_case_id: "UC-02"
status: "draft"
version: "1.0.0"
level: "sea_level"
primary_actor: "Ingress Initialization Engine (Driven Ingress Adapter)"
created_at: "2026-11-06"
last_updated_at: "2026-11-06"
---

# Use-Case Specification: UC-02 Hydrate Startup State via Back-Replay

## 1. Description & Goal
Recovers the commander's active in-game spatial position, active vessel, and operational state upon process startup (mid-session launches or tool restarts) by performing a bounded reverse scan across the active Frontier journal file before serving public query traffic.

## 2. Actors & Scope
* **Primary Actor:** Ingress initialization lifecycle runner inside `ed-resolver` driving adapters.
* **System Boundary:** `ed-resolver` driven ingress adapter interfacing with local filesystem journal files.

## 3. Preconditions
* Frontier journal directory exists and contains at least one readable `Journal.*.log` file.
* Application has read permissions on the journal directory.

## 4. Postconditions
* In-memory `EpochMilestoneAggregator` and `ContextMutator` are seeded with the most recent historical milestones (`Location`, `FSDJump`, `Loadout`).
* Public facade and API query getters are unlocked and ready to return populated snapshots.

## 5. Main Success Scenario (Basic Flow)
1. Actor initiates `ed-resolver` startup lifecycle.
2. The ingress adapter discovers the most recent active journal file on disk.
3. The ingress adapter seeks to the end of the file and scans lines in reverse chronological order.
4. The scanner identifies the most recent spatial milestone event (`Location` or `FSDJump`).
5. The scanner identifies the most recent vessel configuration event (`Loadout`).
6. The ingress adapter dispatches these recovered events to the domain core's `EpochMilestoneAggregator` and `ContextMutator`.
7. The domain core initializes the atomic state snapshots in memory.
8. The ingress adapter positions its live streaming cursor at the file EOF and transitions to forward live watching mode.
9. Startup lifecycle completes; query interfaces begin serving populated snapshots.

## 6. Extensions (Alternative Flows)
* **3a. Active Journal File Empty or Corrupt:**
  1. The scanner fails to parse valid JSON lines in the active journal file.
  2. The ingress adapter falls back to the preceding journal file in the directory.
  3. Reverse scanning resumes from Step 4.
* **4a. No Milestone Events Found (New Commander / Brand New Log):**
  1. The scanner reaches the beginning of all available logs without finding a location milestone.
  2. The domain core leaves the state snapshots initialized as `None`.
  3. The ingress adapter proceeds to forward live streaming mode, awaiting the first live milestone event.
