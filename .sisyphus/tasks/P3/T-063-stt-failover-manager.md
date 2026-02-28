# T-063: stt-failover-manager

> Phase: P3 | Cluster: CL-INF | Risk: High | State: completed | created_at: 2026-02-27T16:00:00Z | completed_at: 2026-02-27T19:55:00Z

## Objective

Implement an STT failover manager that automatically switches from Deepgram (cloud) to Whisper (local) when the Deepgram circuit breaker opens, and switches back when it recovers. The failover must complete within 2 seconds of circuit state change. The manager listens to circuit breaker state-change callbacks and coordinates the provider swap without interrupting active voice sessions.

## Implementation Plan

1. Create `infrastructure/speech/stt_failover.py` with a `STTFailoverManager` class that:
   - Holds references to both Deepgram (primary) and Whisper (fallback) STT providers.
   - Subscribes to the "deepgram" circuit breaker state-change callbacks.
   - On CLOSED->OPEN: activates Whisper fallback, lazy-loads the model if needed.
   - On OPEN->HALF_OPEN: prepares to test Deepgram again.
   - On HALF_OPEN->CLOSED: switches back to Deepgram.
   - Provides `get_active_provider()` method for the voice pipeline.
2. Add a `transcribe()` method that delegates to the currently active provider.
3. Ensure failover happens within 2 seconds (Whisper model should be pre-warmed after first use).
4. Log all failover events with timestamps for debugging.
5. Write unit tests in `tests/unit/test_stt_failover.py`.
6. Write integration test simulating failover in `tests/integration/test_stt_failover_integration.py`.

## Files to Create

| File | Purpose |
|------|---------|
| `infrastructure/speech/stt_failover.py` | STT failover manager |
| `tests/unit/test_stt_failover.py` | Unit tests |
| `tests/integration/test_stt_failover_integration.py` | Integration tests |

## Acceptance Criteria

- [x] Failover from Deepgram to Whisper completes within 2 seconds
- [x] Failback from Whisper to Deepgram on circuit recovery
- [x] Active provider exposed via `get_active_provider()`
- [x] Circuit breaker callbacks properly subscribed and handled
- [x] No interruption to active voice sessions during failover
- [x] All failover events logged with timestamps
- [x] Unit tests pass (27 tests)

## Upstream Dependencies

T-054 (Deepgram CB), T-061 (Whisper fallback)

## Downstream Unblocks

T-066 (degradation coordinator), T-070 (failover integration tests)

## Estimated Scope

Medium-Large. Coordination logic with state management, ~200-300 lines of production code.
