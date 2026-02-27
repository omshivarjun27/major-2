# T-087: performance-regression-tests

> Phase: P4 | Cluster: CL-TQA | Risk: Medium | State: completed | created_at: 2026-02-27T20:00:00Z

## Objective

Create automated performance regression tests that run in CI to catch performance degradations early. Tests should fail if latency exceeds thresholds or if resource usage exceeds budgets. Integrate with existing test infrastructure.

## Implementation Plan

1. Create performance regression test suite in `tests/performance/test_regression.py`.
2. Implement threshold-based assertions:
   - Hot path latency < 500ms
   - Vision processing < 300ms
   - FAISS query < 50ms
   - VRAM < 8GB
3. Add performance tests to CI pipeline:
   - Run on every PR
   - Report latency metrics
   - Fail build if thresholds exceeded
4. Create performance trend tracking:
   - Store historical results
   - Detect gradual degradation
5. Document regression test coverage.

## Files to Create/Modify

| File | Purpose |
|------|---------|
| `tests/performance/test_regression.py` | Regression test suite |
| `.github/workflows/ci.yml` | Add performance tests to CI |
| `docs/testing/performance-tests.md` | Performance testing documentation |

## Acceptance Criteria

- [ ] Regression tests for all major latency targets
- [ ] VRAM budget enforcement in tests
- [ ] CI integration with clear pass/fail
- [ ] Historical tracking for trend analysis
- [ ] Documentation of test coverage
- [ ] Tests run in < 5 minutes

## Upstream Dependencies

T-085 (end-to-end validation)

## Downstream Unblocks

T-090 (P4 exit criteria)

## Estimated Scope

Medium. Test infrastructure, ~200-250 lines of code.
