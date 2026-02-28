# T-051: p2-god-file-split-validation

> Phase: P2 | Cluster: CL-APV | Risk: High | State: completed | created_at: 2026-02-27T12:00:00Z | completed_at: 2026-02-27T14:30:00Z

## Objective

Validate the agent.py decomposition meets all acceptance criteria. Confirm no single file in `apps/realtime/` exceeds 500 lines of code. Run the full test suite and verify all 28 REST endpoints return correct responses. Execute WebRTC session lifecycle tests confirming creation, reconnection, and teardown. Run `lint-imports` and confirm zero violations. Measure startup time regression (must not exceed 2x baseline). This is the first integration closeout task for Phase 2, covering the god file split chain.

## Current State (Codebase Audit 2026-02-27)

- The agent.py decomposition is **complete** (T-038 through T-042 all finished).
- `apps/realtime/agent.py` is 288 LOC, acting as a pure coordinator.
- Four extracted modules exist in `apps/realtime/`:
  - `session_manager.py` (session lifecycle)
  - `vision_controller.py` (perception dispatch)
  - `voice_controller.py` (audio pipeline)
  - `tool_router.py` (capability routing)
- T-043 (agent-split-test-suite) must be complete, providing the 60+ test functions that this validation task runs.
- T-048 (import-boundary-enforcement) must be complete, confirming `lint-imports` passes.
- No startup time baseline has been recorded yet for the decomposed agent. The pre-split baseline (if recorded) serves as the comparison point.
- The 28 REST endpoints are served through the coordinator's delegation layer.

## Implementation Plan

### Step 1: Verify file size constraints

Count lines of code for every `.py` file in `apps/realtime/`. Confirm no file exceeds 500 LOC. Record the exact LOC for each file.

### Step 2: Run full test suite

Execute `pytest tests/ --timeout=180` and confirm:
- All existing 429+ tests pass
- All 60+ new tests from T-043 pass
- Zero test failures or errors

### Step 3: Verify REST endpoint coverage

Run the integration tests from T-043 that cover all 28 REST endpoints. Confirm each endpoint returns the expected response code and payload structure through the coordinator delegation layer.

### Step 4: Verify WebRTC lifecycle

Run the WebRTC session lifecycle tests from T-043. Confirm session creation, reconnection, and teardown paths work correctly.

### Step 5: Run lint-imports

Execute `lint-imports` and confirm zero violations. This validates T-048's boundary enforcement work.

### Step 6: Measure startup time

Time the agent startup sequence (from import to ready state) and compare against the pre-split baseline. Confirm the regression is within 2x. If no baseline exists, establish one and document it.

### Step 7: Produce validation report

Create a summary confirming all checks passed, with specific metrics:
- LOC per file
- Test pass/fail counts
- Endpoint coverage percentage
- Startup time comparison
- lint-imports result

## Files to Create

| File | Purpose |
|------|---------|
| `docs/validations/p2_god_file_split.md` | Validation report with metrics and pass/fail results |
| `tests/performance/test_agent_startup.py` | Startup time benchmark test |

## Files to Modify

| File | Change |
|------|--------|
| `tests/integration/AGENTS.md` | Document validation test coverage |
| `AGENTS.md` | Update documentation coverage section |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/performance/test_agent_startup.py` | `test_startup_time_under_2x_baseline` - measure agent startup and assert within 2x of baseline |
| | `test_no_file_exceeds_500_loc` - programmatically count LOC for all apps/realtime/*.py files |
| | `test_all_endpoints_reachable` - verify all 28 REST endpoints respond through coordinator |

## Acceptance Criteria

- [ ] No file in `apps/realtime/` exceeds 500 lines of code
- [ ] `agent.py` is under 300 LOC (currently 288)
- [ ] Full test suite passes: `pytest tests/ --timeout=180` with zero failures
- [ ] All 28 REST endpoints return correct responses through coordinator delegation
- [ ] WebRTC session lifecycle tests pass (creation, reconnection, teardown)
- [ ] `lint-imports` returns zero violations
- [ ] Startup time regression within 2x of pre-split baseline
- [ ] Validation report produced at `docs/validations/p2_god_file_split.md`
- [ ] `ruff check .` clean

## Upstream Dependencies

T-043 (agent-split-test-suite), T-048 (import-boundary-enforcement). The test suite must exist and boundaries must be enforced before validation can run.

## Downstream Unblocks

T-052 (p2-async-conversion-verification)

## Estimated Scope

- New code: ~80 LOC (startup benchmark + validation report)
- Modified code: ~20 LOC (AGENTS.md updates)
- Tests: ~40 LOC (3 test functions)
- Risk: High. This is a validation gate. If any check fails, it blocks the P2 async verification closeout. Mitigation: all upstream tasks (T-038 through T-048) should have already resolved the issues this task validates.
