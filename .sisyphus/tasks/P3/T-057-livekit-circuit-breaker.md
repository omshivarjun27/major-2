# T-057: livekit-circuit-breaker

> Phase: P3 | Cluster: CL-INF | Risk: Medium | State: completed | created_at: 2026-02-27T16:00:00Z | completed_at: 2026-02-27T19:50:00Z

## Objective

Wire the CircuitBreaker pattern for LiveKit WebRTC connection management. LiveKit is managed through the `livekit-agents` SDK and does not have a direct adapter in `infrastructure/`. This task creates a resilience wrapper that monitors LiveKit connection health, registers a "livekit" circuit breaker, and provides hooks for the realtime agent to detect when LiveKit is experiencing issues. The wrapper tracks connection failures, reconnection attempts, and room join errors.

## Implementation Plan

1. Read `apps/realtime/agent.py` and `apps/realtime/session_manager.py` to understand LiveKit integration points.
2. Create `infrastructure/resilience/livekit_monitor.py` with a `LiveKitCircuitBreaker` class that:
   - Registers a "livekit" circuit breaker (failure_threshold=3, reset_timeout_s=30).
   - Provides `record_connection_failure()` and `record_connection_success()` methods.
   - Exposes `is_healthy()` for pre-flight checks before room operations.
3. Add state-change callbacks for logging and alerting.
4. The monitor is passive (does not intercept LiveKit SDK calls) — it tracks health based on events reported by the agent.
5. Write unit tests in `tests/unit/test_livekit_circuit_breaker.py`.

## Files to Create

| File | Purpose |
|------|---------|
| `infrastructure/resilience/livekit_monitor.py` | LiveKit health monitor with circuit breaker |
| `tests/unit/test_livekit_circuit_breaker.py` | Unit tests |

## Acceptance Criteria

- [ ] "livekit" circuit breaker registered in global registry
- [ ] Connection failures tracked and circuit trips after threshold
- [ ] `is_healthy()` returns False when circuit is OPEN
- [ ] State-change callbacks fire on transitions
- [ ] Monitor is passive (does not intercept SDK calls)
- [ ] Unit tests pass with >90% coverage

## Upstream Dependencies

T-053

## Downstream Unblocks

T-065 (health registry), T-069 (per-service tests)

## Estimated Scope

Small. Passive monitor wrapper, ~100-150 lines of production code.
