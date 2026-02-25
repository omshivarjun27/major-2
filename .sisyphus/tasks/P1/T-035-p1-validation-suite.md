# T-035: p1-validation-suite

> Phase: P1 | Cluster: CL-APV | Risk: Low | State: not_started

## Objective

Create a P1 validation test suite that verifies all P1 phase exit criteria in a single
pytest file. The suite checks: (1) stub count is below 10 (baseline was 11), (2) total
test count is at least 880 (baseline was 840), (3) all five placeholder modules have
MVP implementations, (4) no import-linter violations, and (5) documentation coverage
for all new modules.

This is the gateway test that confirms P1 is complete. It runs automatically as part
of the CI pipeline and blocks the phase transition to P2 if any criterion fails.

## Current State (Codebase Audit 2026-02-25)

- P0 baseline metrics (from `docs/baselines/p0_metrics.json`):
  - 31,032 LOC across 5 modules
  - 1,835 tests collected (3 errors)
  - 11 stubs total (shared:0, core:7, application:0, infrastructure:1, apps:3)
  - 41 total dependencies
- P1 exit criteria (from `.sisyphus/phases/P1-tasks.md`):
  1. All 25 tasks completed
  2. Zero failing tests
  3. Doc mutation maps verified
  4. Stub count reduced below 10 (from 11)
  5. All 5 placeholder modules have MVPs: core/reasoning, infrastructure/storage,
     infrastructure/monitoring, application/event_bus, application/session_management
  6. Test count >= 880 (baseline 840 + 40 new minimum)
  7. 100% documentation coverage for new modules
- `scripts/capture_baseline.py` (from P0 T-012) can capture current metrics.
- `tests/performance/test_p0_baseline.py` (from P0 T-012) validates P0 baseline.
- No P1 validation suite exists.

## Implementation Plan

### Step 1: Create test file structure

```python
import subprocess
import json
import importlib
from pathlib import Path
import pytest

class TestP1ExitCriteria:
    """P1 phase exit validation suite."""
```

### Step 2: Implement stub count check

Scan all layer directories for stub modules (directories with only `__init__.py` and
optionally `AGENTS.md`, no other `.py` files with real code). Assert count < 10.

```python
def test_stub_count_below_threshold(self):
    stub_dirs = []
    for layer in ["shared", "core", "application", "infrastructure", "apps"]:
        # walk subdirectories, check for real .py files
        ...
    assert len(stub_dirs) < 10, f"Too many stubs: {stub_dirs}"
```

### Step 3: Implement test count check

Run `pytest --collect-only -q` and count the output lines to determine total test count.
Assert >= 880.

### Step 4: Implement MVP existence checks

For each of the 5 placeholder modules, verify that importable classes/functions exist:
- `core.reasoning`: ReasoningEngine
- `infrastructure.storage`: StorageAdapter, LocalFileStorage
- `infrastructure.monitoring`: MetricsCollector, InMemoryMetrics
- `application.event_bus`: EventBus
- `application.session_management`: SessionManager

### Step 5: Implement import-linter check

Run `lint-imports` subprocess and verify exit code 0.

### Step 6: Implement documentation coverage check

For each new module created in P1, verify an `AGENTS.md` file exists in its directory.

## Files to Create

| File | Purpose |
|------|---------|
| `tests/performance/test_p1_validation.py` | P1 exit criteria validation suite |

## Files to Modify

| File | Change |
|------|--------|
| `tests/AGENTS.md` | Document P1 validation suite location and purpose |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/performance/test_p1_validation.py` | `test_stub_count_below_10` - scan all layers, verify < 10 stub directories |
| | `test_total_test_count_above_880` - collect tests, verify count >= 880 |
| | `test_reasoning_engine_mvp_exists` - import core.reasoning.ReasoningEngine |
| | `test_storage_adapter_mvp_exists` - import infrastructure.storage.StorageAdapter |
| | `test_monitoring_mvp_exists` - import infrastructure.monitoring.MetricsCollector |
| | `test_event_bus_mvp_exists` - import application.event_bus.EventBus |
| | `test_session_management_mvp_exists` - import application.session_management.SessionManager |
| | `test_import_linter_passes` - run lint-imports, verify exit code 0 |
| | `test_new_modules_have_docs` - verify AGENTS.md exists in all new module directories |

## Acceptance Criteria

- [ ] Stub count < 10 across all 5 layers
- [ ] Total test count >= 880
- [ ] All 5 placeholder modules have importable MVP classes
- [ ] `lint-imports` passes with exit code 0
- [ ] All new module directories have AGENTS.md documentation
- [ ] All 9 validation tests pass: `pytest tests/performance/test_p1_validation.py -v`
- [ ] `ruff check .` clean

## Upstream Dependencies

T-021 (ingest-pipeline-hardening), T-025 (visual-qa-reasoner-tests),
T-029 (face-consent-integration), T-031 (frame-processing-integration),
T-034 (monitoring-adapter-mvp) — all must be complete for exit criteria to pass.

## Downstream Unblocks

T-036 (p1-integration-test) — can only run after validation confirms all components exist.

## Estimated Scope

- New code: ~0 LOC (test-only task)
- Modified code: ~0 lines
- Tests: ~150 LOC
- Risk: Low. Pure validation, no production code changes. Failures indicate incomplete
  P1 tasks rather than bugs in this test file.
