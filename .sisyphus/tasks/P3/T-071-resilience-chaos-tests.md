# T-071: resilience-chaos-tests

> Phase: P3 | Cluster: CL-TQA | Risk: Medium | State: completed | created_at: 2026-02-27T16:00:00Z

## Objective

Write chaos/stress tests that simulate realistic failure patterns to validate the full resilience stack under pressure. Tests inject random failures, network delays, and service outages to verify that the system degrades gracefully, recovers correctly, and never leaves the user in silence. These are performance-category tests that validate NFRs.

## Implementation Plan

1. Create `tests/performance/test_resilience_stress.py` with stress scenarios:
   - Random service failure injection across all 6 services.
   - Rapid on/off failure patterns (flapping services).
   - Cascading failures (one service down triggers load on others).
   - Recovery under load (service returns while requests are queued).
   - Memory stability during extended degraded operation.
2. Create test helpers in `tests/conftest.py` or a dedicated fixture:
   - `chaos_injector`: Randomly fails service calls with configurable probability.
   - `latency_injector`: Adds random delays to service calls.
3. Verify system invariants during chaos:
   - No unhandled exceptions.
   - Circuit breakers in consistent states.
   - Health registry reports accurate status.
   - Degradation coordinator announces changes.
4. Mark tests with `@pytest.mark.slow`.

## Files to Create

| File | Purpose |
|------|---------|
| `tests/performance/test_resilience_stress.py` | Chaos/stress tests |

## Acceptance Criteria

- [x] Random failure injection tests pass without unhandled exceptions
- [x] Flapping service pattern handled correctly (circuit opens/closes)
- [x] Cascading failure scenario does not crash the system
- [x] Recovery under load verified
- [x] Health registry remains accurate during chaos
- [x] No memory leaks during extended degraded operation
- [x] Tests marked with @pytest.mark.slow
- [x] All tests pass within 60-second timeout (44.75s)

## Upstream Dependencies

T-066 (degradation coordinator), T-069 (per-service CB tests)

## Downstream Unblocks

T-072 (P3 exit criteria)

## Estimated Scope

Medium-Large. Chaos engineering tests, ~300-400 lines of test code.
