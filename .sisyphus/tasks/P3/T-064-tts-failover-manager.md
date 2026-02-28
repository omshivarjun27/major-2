# T-064: tts-failover-manager

> Phase: P3 | Cluster: CL-INF | Risk: High | State: completed | created_at: 2026-02-27T16:00:00Z

## Objective

Implement a TTS failover manager that automatically switches from ElevenLabs (cloud) to Edge TTS / pyttsx3 (local) when the ElevenLabs circuit breaker opens, and switches back when it recovers. The failover must complete within 2 seconds. The manager integrates with the existing TTSManager by updating its `local_fn` with the enhanced local fallback.

## Implementation Plan

1. Create `infrastructure/speech/tts_failover.py` with a `TTSFailoverManager` class that:
   - Wraps the existing TTSManager with failover awareness.
   - Subscribes to the "elevenlabs" circuit breaker state-change callbacks.
   - On CLOSED->OPEN: ensures local TTS fallback is active and warm.
   - On HALF_OPEN->CLOSED: restores ElevenLabs as primary.
   - Provides `synthesize()` that routes to the appropriate provider.
2. Integrate with TTSManager: replace the stub `_stub_tts` with the actual LocalTTSFallback from T-062.
3. Track failover statistics (times activated, total duration in fallback mode).
4. Ensure the TTS chunker still works correctly with local TTS.
5. Log all failover events with timestamps.
6. Write unit tests in `tests/unit/test_tts_failover.py`.

## Files to Create/Modify

| File | Purpose |
|------|---------|
| `infrastructure/speech/tts_failover.py` | TTS failover manager |
| `infrastructure/speech/elevenlabs/tts_manager.py` | Wire LocalTTSFallback as local_fn |
| `tests/unit/test_tts_failover.py` | Unit tests |

## Acceptance Criteria

- [x] Failover from ElevenLabs to local TTS completes within 2 seconds
- [x] Failback to ElevenLabs on circuit recovery
- [x] TTSManager.local_fn updated with actual LocalTTSFallback
- [x] Chunked synthesis works with local TTS provider
- [x] Failover statistics tracked and accessible
- [x] All failover events logged
- [x] Unit tests pass (36 tests passing)

## Upstream Dependencies

T-055 (ElevenLabs CB), T-062 (Edge TTS fallback)

## Downstream Unblocks

T-066 (degradation coordinator), T-070 (failover integration tests)

## Estimated Scope

Medium. Coordination logic building on existing TTSManager, ~200 lines of production code.
