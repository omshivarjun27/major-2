# T-058: tavus-circuit-breaker

> Phase: P3 | Cluster: CL-INF | Risk: Low | State: completed | created_at: 2026-02-27T16:00:00Z | completed_at: 2026-02-27T19:55:00Z

## Objective

Wire the CircuitBreaker pattern into the Tavus avatar adapter (`infrastructure/tavus/adapter.py`). Tavus is an optional service (disabled by default), but when enabled it makes REST and WebSocket calls that can fail. This task wraps the Tavus API calls with a circuit breaker so that repeated failures cause the adapter to silently degrade (no-op) rather than blocking or erroring. Register a "tavus" circuit breaker with conservative thresholds (failure_threshold=2, reset_timeout_s=60) since Tavus is non-critical.

## Implementation Plan

1. Read `infrastructure/tavus/adapter.py` to understand the connect/send/end flow.
2. Import `register_circuit_breaker` and `CircuitBreakerOpenError` in `adapter.py`.
3. In `TavusAdapter.__init__()`, register a "tavus" circuit breaker (only when enabled).
4. Wrap `connect()`, `send_narration()`, and `_send_rest()` with circuit breaker checks:
   - If circuit is OPEN, return False immediately (silent degradation).
   - Record failures/successes for state tracking.
5. Add state-change callback that logs transitions.
6. Write unit tests in `tests/unit/test_tavus_circuit_breaker.py`.

## Files to Modify

| File | Purpose |
|------|---------|
| `infrastructure/tavus/adapter.py` | Wire circuit breaker into API calls |
| `tests/unit/test_tavus_circuit_breaker.py` | Unit tests for CB integration |

## Acceptance Criteria

- [ ] "tavus" circuit breaker registered when adapter is enabled
- [ ] REST/WS calls routed through circuit breaker
- [ ] When circuit is OPEN, methods return False (silent degradation)
- [ ] Circuit breaker NOT registered when Tavus is disabled (no overhead)
- [ ] Existing TavusAdapter tests still pass
- [ ] Unit tests pass with >90% coverage

## Upstream Dependencies

T-053

## Downstream Unblocks

T-065 (health registry), T-069 (per-service tests)

## Estimated Scope

Small. Integration into existing adapter, ~60-100 lines of changes.
