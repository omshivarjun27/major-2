# T-037: p1-architecture-check

> Phase: P1 | Cluster: CL-APV | Risk: Low | State: not_started

## Objective

Run `lint-imports` to verify no architectural boundary violations were introduced
during P1 execution. Check all new files conform to the 5-layer import rules. Generate
a P1 metrics snapshot comparable to the P0 baseline (`docs/baselines/p0_metrics.json`)
and store it at `docs/baselines/p1_metrics.json`. Compare key metrics between P0 and
P1 to quantify the phase's impact.

This task is the final gate before P1 is marked complete. It produces an auditable
record of what changed during the phase and confirms the codebase's architectural
integrity was maintained.

## Current State (Codebase Audit 2026-02-25)

- P0 baseline at `docs/baselines/p0_metrics.json`:
  - 31,032 LOC
  - 1,835 tests collected
  - 11 stubs
  - 41 dependencies
  - 81 config vars
- `scripts/capture_baseline.py` (from P0 T-012): captures LOC, test count, stub count,
  dependency count, config vars. Outputs JSON.
- `pyproject.toml` has `[tool.importlinter]` config with layer contracts:
  - shared: no imports from core, application, infrastructure, apps
  - core: no imports from application, infrastructure, apps
  - application: no imports from infrastructure, apps
  - infrastructure: no imports from apps
- `lint-imports` is installed and configured.
- `ruff check .` is the linter.
- P1 will add new files in: core/reasoning/, infrastructure/storage/,
  infrastructure/monitoring/, application/event_bus/, application/session_management/.
- No P1 metrics snapshot exists yet.

## Implementation Plan

### Step 1: Run lint-imports and capture results

Execute `lint-imports` and capture both exit code and output. If violations are found,
log them clearly for remediation.

### Step 2: Run ruff check and capture results

Execute `ruff check .` and capture any remaining violations.

### Step 3: Generate P1 metrics snapshot

Run `scripts/capture_baseline.py` (or equivalent logic) to produce the P1 metrics
JSON. Save to `docs/baselines/p1_metrics.json`.

### Step 4: Compare P0 vs P1 metrics

Load both baseline files and compute deltas:
- LOC delta (how much code was added)
- Test count delta (how many tests were added)
- Stub count delta (how many stubs were replaced)
- Dependency count delta (any new dependencies?)

### Step 5: Write comparison test

A pytest test that loads both baselines and verifies:
- Test count increased by at least 40
- Stub count decreased (or stayed same)
- No new dependencies added beyond what P1 tasks specified

### Step 6: Generate human-readable summary

Write a brief P1 completion summary with before/after metrics to stdout.

## Files to Create

| File | Purpose |
|------|---------|
| `docs/baselines/p1_metrics.json` | P1 phase metrics snapshot |
| `tests/performance/test_p1_architecture.py` | Architecture validation and metric comparison tests |

## Files to Modify

| File | Change |
|------|--------|
| `tests/AGENTS.md` | Document P1 architecture check test |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/performance/test_p1_architecture.py` | `test_lint_imports_passes` - run lint-imports, verify exit code 0 |
| | `test_ruff_check_passes` - run ruff check, verify exit code 0 |
| | `test_p1_metrics_snapshot_exists` - verify docs/baselines/p1_metrics.json exists |
| | `test_test_count_increased` - compare P1 vs P0 test counts, verify increase >= 40 |
| | `test_stub_count_decreased` - compare P1 vs P0 stub counts, verify P1 <= P0 |
| | `test_no_unexpected_dependencies` - compare P1 vs P0 dependency count, verify delta explained |
| | `test_all_new_modules_have_agents_md` - check core/reasoning, infra/storage, infra/monitoring, app/event_bus, app/session_mgmt |

## Acceptance Criteria

- [ ] `lint-imports` exits with code 0 (no architectural violations)
- [ ] `ruff check .` exits with code 0 (no lint violations)
- [ ] `docs/baselines/p1_metrics.json` generated with same schema as P0 baseline
- [ ] P1 test count >= P0 test count + 40
- [ ] P1 stub count <= P0 stub count
- [ ] All new module directories have AGENTS.md files
- [ ] Comparison summary printed to test output
- [ ] All 7 tests pass: `pytest tests/performance/test_p1_architecture.py -v`
- [ ] This is the final P1 task — passing means P1 is complete

## Upstream Dependencies

T-036 (p1-integration-test) — integration must pass before architecture sign-off.

## Downstream Unblocks

None (terminal task for P1 phase).

## Estimated Scope

- New code: ~20 LOC (metric capture script adjustments if needed)
- Modified code: ~0 lines
- Tests: ~120 LOC
- Risk: Low. Read-only checks plus metric snapshot. No production code changes.
  Failures indicate P1 tasks left the codebase in a non-compliant state.
