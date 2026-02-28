# T-054: deepgram-circuit-breaker

> Phase: P3 | Cluster: CL-INF | Risk: Medium | State: completed | created_at: 2026-02-27T16:00:00Z | completed_at: 2026-02-27T19:35:00Z

## Objective

Wire the CircuitBreaker pattern into the Deepgram STT adapter. Deepgram is accessed via LiveKit plugins (not a direct HTTP adapter in our codebase), so this task creates a thin resilience wrapper that monitors Deepgram health via LiveKit's STT plugin events. Register a "deepgram" circuit breaker in the global registry with service-appropriate thresholds (failure_threshold=3, reset_timeout_s=15 for real-time STT). Add state-change callbacks that log transitions and trigger fallback activation in T-063.

## Implementation Plan

1. Read `apps/realtime/agent.py` and `apps/realtime/voice_controller.py` to identify where Deepgram STT is invoked via LiveKit plugins.
2. Create `infrastructure/speech/deepgram/resilience.py` with a `DeepgramCircuitBreaker` wrapper that:
   - Registers a "deepgram" circuit breaker via `register_circuit_breaker()`.
   - Provides `wrap_stt_call()` method that routes STT through the circuit breaker.
   - Emits state-change callbacks for fallback activation.
3. Configure service-specific thresholds: failure_threshold=3, reset_timeout_s=15 (tight for real-time), half_open_max_calls=1.
4. Add a health-check method that returns the circuit breaker snapshot.
5. Write unit tests for the wrapper in `tests/unit/test_deepgram_circuit_breaker.py`.
6. Update `infrastructure/speech/deepgram/__init__.py` to export the new wrapper.

## Files to Create/Modify

| File | Purpose |
|------|---------|
| `infrastructure/speech/deepgram/resilience.py` | Deepgram-specific circuit breaker wrapper |
| `infrastructure/speech/deepgram/__init__.py` | Export new resilience symbols |
| `tests/unit/test_deepgram_circuit_breaker.py` | Unit tests |

## Acceptance Criteria

- [ ] "deepgram" circuit breaker registered in global registry on first use
- [ ] STT calls routed through circuit breaker with correct thresholds
- [ ] State-change callbacks fire and are testable
- [ ] Health snapshot returns current breaker state
- [ ] Unit tests pass with >90% coverage of new code
- [ ] No blocking calls introduced in the async path

## Upstream Dependencies

T-053

## Downstream Unblocks

T-063 (STT failover manager), T-065 (health registry), T-069 (per-service tests)

## Estimated Scope

Small-Medium. Wrapper around existing circuit breaker, ~150-200 lines of production code.
