# T-048: import-boundary-enforcement

> Phase: P2 | Cluster: CL-APP | Risk: Medium | State: completed | created_at: 2026-02-27T12:00:00Z | completed_at: 2026-02-27T13:00:00Z

## Objective

Verify and enforce all 5-layer import boundaries after the agent split and shared cleanup are complete. Run `lint-imports` and fix any violations introduced by the new module structure in `apps/realtime/`. Update `pyproject.toml` import-linter contracts if the new modules (session_manager, vision_controller, voice_controller, tool_router) need explicit boundary definitions. Confirm that no circular dependencies exist between the extracted agent modules. Validate that shared/ still imports only from the standard library, core/ only from shared/, and so on up the hierarchy.

## Current State (Codebase Audit 2026-02-27)

- T-042 (agent-coordinator-slim) is **complete**. `apps/realtime/agent.py` is 288 LOC.
- Four extracted modules exist in `apps/realtime/`:
  - `session_manager.py` (session lifecycle)
  - `vision_controller.py` (perception dispatch)
  - `voice_controller.py` (audio pipeline)
  - `tool_router.py` (capability routing)
- T-047 (shared-init-cleanup) is **complete**. `shared/__init__.py` has been cleaned of unnecessary re-exports.
- The `pyproject.toml` import-linter contracts were written for the original monolithic agent.py structure. The new extracted modules may not be explicitly covered.
- `lint-imports` has not been run against the post-split codebase to verify boundary compliance.
- The 5-layer hierarchy: shared (no upward imports) -> core (shared only) -> application (core, shared) -> infrastructure (shared only) -> apps (all layers).
- Potential risk: extracted modules in `apps/realtime/` might import from each other in ways that create circular dependencies.

## Implementation Plan

### Step 1: Run lint-imports baseline

Execute `lint-imports` against the current codebase and capture all violations. Categorize violations by:
- New violations introduced by the agent split
- Pre-existing violations unrelated to P2 changes
- False positives from import-linter contract gaps

### Step 2: Analyze extracted module imports

For each of the 4 extracted modules and the coordinator, trace all import statements:
- Verify `session_manager.py` imports only from allowed layers
- Verify `vision_controller.py` imports only from allowed layers
- Verify `voice_controller.py` imports only from allowed layers
- Verify `tool_router.py` imports only from allowed layers
- Verify `agent.py` coordinator imports only from allowed layers and its own submodules

### Step 3: Check for circular dependencies

Map the import graph between extracted modules. Confirm no circular import chains exist (e.g., session_manager imports vision_controller which imports session_manager). If circular dependencies are found, refactor to break the cycle using dependency injection or interface extraction.

### Step 4: Update pyproject.toml contracts

Add or update import-linter contract definitions in `pyproject.toml` to explicitly cover the new modules. Ensure each extracted module is bound by the same layer rules as `apps/`.

### Step 5: Fix all violations

Resolve every violation found in Step 1. For each fix:
- Replace forbidden imports with allowed alternatives
- Move shared types to `shared/schemas/` if they're defined in the wrong layer
- Use lazy imports for heavy dependencies

### Step 6: Verify clean state

Run `lint-imports` again and confirm zero violations. Run `pytest tests/ --timeout=180` to confirm no regressions from import changes.

## Files to Create

| File | Purpose |
|------|---------|
| `tests/unit/test_import_boundaries.py` | Regression tests for import boundary compliance |

## Files to Modify

| File | Change |
|------|--------|
| `pyproject.toml` | Update import-linter contracts for new agent modules |
| Various files in `apps/realtime/` | Fix any import boundary violations |
| `AGENTS.md` | Update architectural risks section if violations were found |
| `docs/architecture.md` | Document import boundary rules for new modules |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/unit/test_import_boundaries.py` | `test_lint_imports_clean` - run lint-imports programmatically and assert zero violations |
| | `test_shared_no_upward_imports` - verify shared/ doesn't import from core/application/infrastructure/apps |
| | `test_core_only_imports_shared` - verify core/ only imports from shared/ and stdlib |
| | `test_no_circular_deps_in_realtime` - verify no circular imports between extracted modules |
| | `test_extracted_modules_respect_layer` - verify each new module follows apps/ layer rules |

## Acceptance Criteria

- [ ] `lint-imports` returns zero violations
- [ ] `pyproject.toml` contracts explicitly cover session_manager, vision_controller, voice_controller, tool_router
- [ ] No circular dependencies between extracted agent modules
- [ ] shared/ imports only from standard library
- [ ] core/ imports only from shared/ and standard library
- [ ] application/ imports only from core/, shared/, and standard library
- [ ] infrastructure/ imports only from shared/ and standard library
- [ ] All tests pass: `pytest tests/ --timeout=180`
- [ ] `ruff check .` clean
- [ ] Import boundary regression tests in place

## Upstream Dependencies

T-042 (agent-coordinator-slim, complete), T-047 (shared-init-cleanup, complete). Both the agent split and shared cleanup must be done before boundary enforcement can be validated.

## Downstream Unblocks

T-050 (p2-tech-debt-reassessment), T-051 (p2-god-file-split-validation)

## Estimated Scope

- New code: ~60 LOC (boundary regression tests)
- Modified code: ~30-80 LOC (pyproject.toml contracts + import fixes)
- Tests: ~50 LOC (5 test functions)
- Risk: Medium. Import changes can cause runtime failures if a needed symbol is no longer accessible. Mitigation: run full test suite after each import change, fix one violation at a time.
