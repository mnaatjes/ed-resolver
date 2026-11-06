---
title: "Master Risk Register"
tags: ["architecture", "risk", "governance", "boehm", "unified-process", "ed-resolver"]
created_at: "2026-11-06"
last_updated_at: "2026-11-06"
---

# Master Risk Register

This document tracks and quantifies the architectural, technical, and operational risks for `ed-resolver` using Barry Boehm's classical Risk Exposure ($RE$) metric:

$$RE = P \times I$$

* **Probability ($P$):** Integer scale `1` (Extremely Unlikely) to `5` (Near Certainty).
* **Impact ($I$):** Integer scale `1` (Negligible / Cosmetic) to `5` (Catastrophic / Outage / Data Corruption).
* **Risk Exposure ($RE$):** Product range `1` to `25`.
  * **Critical Exposure ($RE \ge 16$):** Architectural blocker requiring immediate mitigation spike or prototype prior to committing to construction.
  * **Moderate Exposure ($9 \le RE \le 15$):** Active monitoring with explicit mitigation plan in Elaboration.
  * **Low Exposure ($RE < 9$):** Documented; managed procedurally via standard tests.

---

## 1. Active Risk Matrix

| Risk ID | Title | Cat. | $P$ | $I$ | $RE$ | Exposure Level | Status |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- | :--- |
| **RISK-01** | Cold-Start Unseeded State & Null Dereference | Arch | 4 | 4 | **16** | 🔴 Critical | Active (ADR 0001) |
| **RISK-02** | High-Frequency Status Tick Concurrency Contention | Perf | 3 | 4 | **12** | 🟡 Moderate | Active |
| **RISK-03** | Staging Buffer Memory Leakage Without TTL Eviction | Res | 3 | 4 | **12** | 🟡 Moderate | Active |
| **RISK-04** | Hexagonal Core Boundary Leakage (I/O & Async Contagion) | Arch | 3 | 4 | **12** | 🟡 Moderate | Active |
| **RISK-05** | Journal Rotation & Lock Collisions Across File Watchers | OS | 2 | 3 | **6** | 🟢 Low | Active |
| **RISK-06** | Deserialization Drift & Schema Violation on Raw Ingress | Schema | 4 | 4 | **16** | 🔴 Critical | Active |
| **RISK-07** | Tight Ingress Transport Coupling to External Telemetry API | Arch | 4 | 3 | **12** | 🟡 Moderate | Active (ADR 0001) |
| **RISK-08** | Archetype Taxonomy Drift on Upstream ed-models Upgrades | Schema | 4 | 3 | **12** | 🟡 Moderate | Active (ADR 0002) |
| **RISK-09** | Ambiguous Multi-Archetype Event Overlap | Domain | 3 | 4 | **12** | 🟡 Moderate | Active (ADR 0002) |
| **RISK-10** | Semantic State Divergence Between Facade Snapshots and Predicates | Domain | 3 | 4 | **12** | 🟡 Moderate | Active (ADR 0003) |
| **RISK-11** | Unverified Scope Drift & Architectural Boundary Regression | Arch | 4 | 4 | **16** | 🔴 Critical | Active (ADR 0004) |

---

## 2. Risk Detail & Mitigation Plans

### RISK-01: Cold-Start Unseeded State & Null Dereference
* **Description:** When consumers invoke `get_location()` or `get_vessel()` immediately upon application launch mid-session before any Epoch Milestone (`Location` or `FSDJump`) has arrived in the live stream, uninitialized state could trigger `AttributeError` or unexpected exceptions downstream.
* **Scoring:** $P=4, I=4 \rightarrow RE=16$ (Critical).
* **Mitigation Plan:**
  1. Enforce ADR 0001 Hybrid Strategy D + Strategy B: perform a fast reverse journal scan during ingress initialization to recover the most recent milestone and loadout from the active log file before query methods open.
  2. Define strict return types as explicit nullable dataclasses (`LocationSnapshot | None`, `VesselSnapshot | None`), compelling callers to implement null-safe gating.
  3. Validate unseeded cold starts, partial log seeds, and fully hydrated states in automated unit tests.

### RISK-02: High-Frequency Status Tick Concurrency Contention
* **Description:** In multi-threaded or async topologies where a background ingestion loop updates the in-memory state at 1 Hz (`Status.json`) while concurrent read requests arrive from WebSockets, HTTP controllers, or TUI render loops, race conditions could lead to torn reads or thread lock starvation.
* **Scoring:** $P=3, I=4 \rightarrow RE=12$ (Moderate).
* **Mitigation Plan:**
  1. Immutable Snapshot Replacement: State is stored as frozen dataclass instances (`@dataclass(frozen=True)`). Readers acquire an atomic reference to an immutable snapshot without holding long read locks.
  2. Implement fine-grained read-copy-update (RCU) or single-writer / multiple-reader (`RWLock` / atomic pointer swap) concurrency primitives in the state store.

### RISK-03: Staging Buffer Memory Leakage Without TTL Eviction
* **Description:** Out-of-band market or outfitting dumps (`Market.json`, `Outfitting.json`) held in accumulator buffers waiting for missing coordinates or system addresses could leak memory unbounded if the player logs out or disconnects before the required milestone event is emitted.
* **Scoring:** $P=3, I=4 \rightarrow RE=12$ (Moderate).
* **Mitigation Plan:**
  1. Implement deterministic TTL (Time-To-Live) sliding expiry windows (e.g., 300 seconds) on all staged contract packages.
  2. Cap maximum concurrent staged packages in the accumulator using an LRU cache or ring buffer with hard memory ceilings.
  3. Emit audit ledger events upon buffer expiration to alert operators of dropped packages.

### RISK-04: Hexagonal Core Boundary Leakage (I/O & Async Contagion)
* **Description:** Inadvertently introducing file path manipulation, HTTP server objects, or `asyncio` primitives into `src/ed_resolver/core/` violates hexagonal purity, making domain logic untestable without external runtimes and preventing synchronous library use.
* **Scoring:** $P=3, I=4 \rightarrow RE=12$ (Moderate).
* **Mitigation Plan:**
  1. Keep `src/ed_resolver/core/` 100% synchronous standard library Python with zero network, filesystem, or async framework imports.
  2. Confine all filesystem cursors, journal readers, and network protocols strictly to `src/ed_resolver/adapters/`.
  3. Enforce architectural boundaries automatically via `import-linter` contracts and `pytest-archon` in `scripts/verify.py`.

### RISK-05: Journal Rotation & Lock Collisions Across File Watchers
* **Description:** When the Frontier client rotates journal files (e.g. crossing midnight UTC or jumping game modes), file watchers attempting to hold exclusive read locks could encounter OS permission errors (`EBUSY` / `AccessDenied`) or miss lines appended during the rotation handoff.
* **Scoring:** $P=2, I=3 \rightarrow RE=6$ (Low).
* **Mitigation Plan:**
  1. Ingress file watchers must open files in non-exclusive, shared read mode (`os.O_RDONLY | os.O_NONBLOCK`).
  2. Detect file inode and size shrink transitions to handle file truncation and rotation smoothly.
  3. Rely on tested `ed-telemetry` ingress adapters rather than custom ad-hoc file polling loops.

### RISK-06: Deserialization Drift & Schema Violation on Raw Ingress
* **Description:** Frontier game updates frequently introduce unannounced fields, alter primitive types (e.g., int vs. float vs. string), or emit malformed/partial JSON slices during game crashes. Attempting rigid deserialization on raw ingress could throw unhandled `KeyError`, `ValueError`, or JSON decode exceptions, crashing the state reduction pipeline.
* **Scoring:** $P=4, I=4 \rightarrow RE=16$ (Critical).
* **Mitigation Plan:**
  1. Enforce permissive payload parsing: unknown or novel fields must be ignored or preserved in generic extra-attributes containers without halting execution.
  2. Implement an ingress Dead-Letter Queue (DLQ) / quarantine buffer: unparseable lines are logged to audit storage and bypassed rather than crashing the reducer loop.
  3. Delegate model deserialization to `ed-models` normalization interactors (`ed_models.parse_journal_event`) which incorporate canonical fallback entities.

### RISK-07: Tight Ingress Transport Coupling to External Telemetry API
* **Description:** Hardcoding `ed-resolver` to require a live network connection to an external `ed-telemetry` HTTP or WebSocket server prevents in-process execution, breaks offline/mock testing, and introduces circular startup race conditions.
* **Scoring:** $P=4, I=3 \rightarrow RE=12$ (Moderate).
* **Mitigation Plan:**
  1. Adopt the Pluggable Ingress Port pattern (ADR 0001 Section 4.4): the domain core defines a pure `TelemetryIngressPort` accepting raw envelopes (`TelemetryPayloadDTO`).
  2. Decouple transport mechanisms into pluggable driven adapters: `DirectQueueIngressAdapter` (in-memory queues for tests/copilots), `LocalJournalFileIngressAdapter` (embedded disk tailing via `ed-telemetry` library), and `RemoteTelemetryApiIngressAdapter` (network WebSocket/SSE client).
  3. Allow consumers to select or inject the appropriate ingress adapter at bootstrap without altering domain reducer logic.

### RISK-08: Archetype Taxonomy Drift on Upstream ed-models Upgrades
* **Description:** Upgrading `ed-models` to a newer version containing newly cataloged event classes without re-running the registry generator causes new game events to resolve to `None` in `classifier.classify()`, silently dropping state transitions.
* **Scoring:** $P=4, I=3 \rightarrow RE=12$ (Moderate).
* **Mitigation Plan:**
  1. Enforce ADR 0002 Two-Phase Codification Lifecycle: version-pin the architectural Markdown taxonomy matrix (`architecture/designs/archetype_taxonomy_matrix_v<version>.md`) matching the installed `ed-models` version.
  2. Integrate `tests/architecture/test_archetype_parity.py` in CI asserting that 100% of event classes exported by `ed-models` are accounted for in `DEFAULT_ARCHETYPE_REGISTRY`.
  3. The generator tool aborts with exit code 1 if any unmapped or obsolete event classes are detected.

### RISK-09: Ambiguous Multi-Archetype Event Overlap
* **Description:** Certain compound game events exhibit multiple operational behaviors simultaneously (e.g. `ShipyardSwapEvent` updates the active vessel milestone while mutating shipyard inventory context). Forcing an oversimplified 1:1 single-archetype mapping could discard secondary state mutations.
* **Scoring:** $P=3, I=4 \rightarrow RE=12$ (Moderate).
* **Mitigation Plan:**
  1. Exhaustively document compound event handling in the version-pinned Markdown taxonomy matrix.
  2. Allow the `IngressClassifier` or dispatch pipeline to register secondary handler hooks or route composite events across multiple reducer stages where necessary.
  3. Validate compound state transitions in integration scenario tests.

### RISK-10: Semantic State Divergence Between Facade Snapshots and Predicates
* **Description:** If atomic predicate helpers on `AmbientTelemetryFacade` (e.g., `is_on_foot()`, `is_docked()`) evaluate independent state or inspect raw journal lines separately from compound snapshots (`get_vessel()`, `get_location()`), race conditions or divergent answers could occur across concurrent readers.
* **Scoring:** $P=3, I=4 \rightarrow RE=12$ (Moderate).
* **Mitigation Plan:**
  1. Enforce ADR 0003 Non-Divergent Projection Guarantee: every atomic predicate method must strictly read from the underlying frozen snapshot instance.
  2. Verify non-divergence via automated parameter-sweep property tests in `tests/unit/test_facade_projections.py`.
  3. Maintain consensus matrices under `architecture/designs/matrix/` governing predicate qualification.

### RISK-11: Unverified Scope Drift & Architectural Boundary Regression
* **Description:** In complex multi-adapter state synthesis libraries, ongoing feature additions risk breaking layer isolation (e.g., adapters leaking into domain core, async contagion in synchronous facades, or unchecked event omissions). Without strict automated enforcement gates across CI and pre-commit, architectural regressions accumulate silently.
* **Scoring:** $P=4, I=4 \rightarrow RE=16$ (Critical).
* **Mitigation Plan:**
  1. Codify complete layer boundaries and verification tooling into ADR 0004.
  2. Multi-tier automated enforcement: `import-linter` boundary contracts, `pytest-archon` AST rules, `mypy` strict static typing, and pre-commit hooks (`check-yaml`, `ruff`).
  3. Wire all enforcement gates into `scripts/verify.py` and GitHub Actions CI workflow (`.github/workflows/ci.yml`), blocking any PR that introduces layer leaks or unverified scope drift.
