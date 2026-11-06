---
title: "Use-Case Specification: UC-05 Generate Archetype Registry from Matrix"
use_case_id: "UC-05"
status: "draft"
version: "1.0.0"
level: "sea_level"
primary_actor: "Developer / CI Release Automation"
created_at: "2026-11-06"
last_updated_at: "2026-11-06"
---

# Use-Case Specification: UC-05 Generate Archetype Registry from Matrix

## 1. Description & Goal
Allows an engineer or CI/CD workflow to parse the human-reviewed structured YAML taxonomy matrix (`architecture/designs/matrix/archetype_taxonomy_v<version>.yaml`), validate it against the installed `ed-models` package AST, and deterministically generate the static Python lookup dictionary (`src/ed_resolver/core/domain/classification/registry.py`).

## 2. Actors & Scope
* **Primary Actor:** Repository Developer or CI/CD Release Automation runner.
* **System Boundary:** `scripts/generate_archetype_registry.py` offline codegen tooling.

## 3. Preconditions
* A versioned YAML taxonomy matrix exists at `architecture/designs/matrix/archetype_taxonomy_v<version>.yaml` with all events classified.
* The matching version of `ed-models` is installed in the active virtual environment (`.venv`).

## 4. Postconditions
* On success: The static mapping dictionary file `src/ed_resolver/core/domain/classification/registry.py` is written or verified with zero discrepancy, and formatted according to project Ruff standards.
* On error: The generator terminates with exit code 1, emitting diagnostic logs detailing discrepancies, and does not alter the registry file.

## 5. Main Success Scenario (Basic Flow)
1. Actor invokes `uv run python scripts/generate_archetype_registry.py --matrix architecture/designs/matrix/archetype_taxonomy_v<version>.yaml`.
2. Generator parses the structured YAML matrix, validating entries with Pydantic schemas and extracting event names and declared archetypes.
3. Generator inspects the installed `ed-models` package hierarchy via Python AST / module introspection, discovering all concrete event model classes.
4. Generator reconciles the matrix entries against the AST discovered models:
   * Confirms every `ed-models` event class is explicitly declared in the matrix.
   * Confirms no phantom/deprecated event names exist in the matrix.
   * Validates all archetype strings match valid `TelemetryArchetype` enum members.
5. Generator generates Python source code declaring `DEFAULT_ARCHETYPE_REGISTRY: dict[type, TelemetryArchetype]`.
6. Generator writes the output to `src/ed_resolver/core/domain/classification/registry.py`.
7. Generator runs Ruff formatting and verification on the generated file.
8. Generator exits with status code 0 and reports total model count compiled.

## 6. Extensions (Alternative Flows)
* **4a. Discrepancy Gate Failure (Missing or Phantom Models):**
  1. Generator detects an `ed-models` class missing from the matrix or a matrix row referencing a non-existent class.
  2. Generator prints an error table detailing the discrepancies.
  3. Generator aborts code generation and exits immediately with exit code 1.
* **4b. Check-Only / Verification Mode (`--check`):**
  1. Actor invokes generator with `--check` flag during CI pipeline verification.
  2. Generator produces the code in-memory and compares it to the committed `registry.py`.
  3. If identical, exits 0. If differing, reports drift and exits 1.
