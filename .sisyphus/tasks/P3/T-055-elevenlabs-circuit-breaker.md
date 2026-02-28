# T-055: elevenlabs-circuit-breaker

> Phase: P3 | Cluster: CL-INF | Risk: Medium | State: completed | created_at: 2026-02-27T16:00:00Z | completed_at: 2026-02-27T19:40:00Z

## Objective

Wire the CircuitBreaker pattern into the ElevenLabs TTS adapter (`infrastructure/speech/elevenlabs/tts_manager.py`). The TTSManager already has a 3-tier chain (cache -> remote -> local fallback). This task wraps the remote TTS call with a circuit breaker so that repeated failures automatically trip the circuit and skip remote calls entirely, falling through to local fallback immediately. Register an "elevenlabs" circuit breaker with thresholds tuned for TTS (failure_threshold=3, reset_timeout_s=30).

## Implementation Plan

1. Read `infrastructure/speech/elevenlabs/tts_manager.py` to understand the existing remote/fallback flow.
2. Import `register_circuit_breaker` and `CircuitBreakerOpenError` in `tts_manager.py`.
3. In `TTSManager.__init__()`, register an "elevenlabs" circuit breaker.
4. In `TTSManager.synthesise()`, wrap the remote TTS call (step 2) with the circuit breaker:
   - If circuit is OPEN, skip remote entirely and go straight to local fallback.
   - If remote call fails, the circuit breaker records the failure.
5. Add state-change callback for logging and fallback activation.
6. Write unit tests in `tests/unit/test_elevenlabs_circuit_breaker.py`.

## Files to Modify

| File | Purpose |
|------|---------|
| `infrastructure/speech/elevenlabs/tts_manager.py` | Wire circuit breaker into remote TTS calls |
| `tests/unit/test_elevenlabs_circuit_breaker.py` | Unit tests for CB integration |

## Acceptance Criteria

- [ ] "elevenlabs" circuit breaker registered on TTSManager init
- [ ] Remote TTS calls routed through circuit breaker
- [ ] When circuit is OPEN, remote is skipped and local fallback used immediately
- [ ] TTSResult.fallback_used=True when circuit is open
- [ ] State-change callbacks fire on transitions
- [ ] Existing TTSManager tests still pass (no regression)
- [ ] New unit tests pass with >90% coverage

## Upstream Dependencies

T-053

## Downstream Unblocks

T-064 (TTS failover manager), T-065 (health registry), T-069 (per-service tests)

## Estimated Scope

Small. Integration into existing TTSManager, ~80-120 lines of changes.
