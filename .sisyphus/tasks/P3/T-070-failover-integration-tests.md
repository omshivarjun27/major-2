# T-070: failover-integration-tests

> Phase: P3 | Cluster: CL-TQA | Risk: Medium | State: completed | created_at: 2026-02-27T16:00:00Z

## Objective

Write integration tests that verify end-to-end failover scenarios: Deepgram failure triggers Whisper activation, ElevenLabs failure triggers Edge TTS activation, and recovery returns to primary providers. Tests simulate realistic failure patterns (gradual degradation, sudden outage, intermittent failures) and verify the 2-second failover SLA.

## Implementation Plan

1. Create `tests/integration/test_failover_scenarios.py` with scenario-based tests:
   - Scenario 1: Deepgram -> Whisper failover (gradual failure).
   - Scenario 2: ElevenLabs -> Edge TTS failover (sudden outage).
   - Scenario 3: Simultaneous STT + TTS failure (both fallbacks active).
   - Scenario 4: Recovery after failover (primary restored).
   - Scenario 5: Intermittent failures (circuit stays closed with retries).
2. Use `unittest.mock` to simulate service failures without real API calls.
3. Measure and assert failover timing (< 2 seconds).
4. Verify circuit breaker states at each stage of the scenario.
5. Verify user-facing behavior (speech output continues during failover).
6. Mark tests with `@pytest.mark.integration`.

## Files to Create

| File | Purpose |
|------|---------|
| `tests/integration/test_failover_scenarios.py` | End-to-end failover tests |

## Acceptance Criteria

- [x] 5 failover scenarios tested end-to-end (24 tests total)
- [x] Failover timing verified (< 2 seconds for each scenario)
- [x] Circuit breaker states verified at each stage
- [x] Recovery tested (failback to primary)
- [x] Simultaneous multi-service failure handled correctly
- [x] All tests pass with mocked backends (2.60s runtime)
- [x] Tests marked with @pytest.mark.integration

## Upstream Dependencies

T-063 (STT failover), T-064 (TTS failover)

## Downstream Unblocks

T-072 (P3 exit criteria)

## Estimated Scope

Medium. 5 integration test scenarios, ~300-400 lines of test code.
