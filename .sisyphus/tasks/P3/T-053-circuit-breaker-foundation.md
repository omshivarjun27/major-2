# T-053: circuit-breaker-foundation

> Phase: P3 | Cluster: CL-INF | Risk: Medium | State: completed | created_at: 2026-02-27T16:00:00Z | completed_at: 2026-02-27T19:30:00Z

## Objective

Implement the foundational circuit breaker pattern using Tenacity library. Create a reusable CircuitBreaker class in `infrastructure/resilience/circuit_breaker.py` with configurable failure thresholds, reset timeouts, half-open state probing, and event callbacks. The base implementation must support three states (closed, open, half-open) with configurable transition rules. Expose a decorator `@with_circuit_breaker(service_name)` for easy wrapping of external calls. Include metrics hooks for monitoring integration in Phase 5.

## Implementation Plan

1. Create the `infrastructure/resilience/` package with `__init__.py` exporting public symbols.
2. Implement the `CircuitBreaker` class with closed, open, and half-open states. Each state transition should be driven by configurable failure thresholds and reset timeouts.
3. Add the `@with_circuit_breaker(service_name)` decorator that wraps any async or sync callable with circuit breaker protection, looking up or creating a named breaker instance from a global registry.
4. Add event callback hooks (`on_open`, `on_close`, `on_half_open`) so downstream consumers can react to state transitions (e.g., triggering fallbacks).
5. Write unit tests covering all state transitions, threshold configurations, decorator behavior, and callback invocation.

## Files to Create

| File | Purpose |
|------|---------|
| `infrastructure/resilience/__init__.py` | Package init, exports CircuitBreaker and decorator |
| `infrastructure/resilience/circuit_breaker.py` | Core CircuitBreaker class and @with_circuit_breaker decorator |

## Acceptance Criteria

- [ ] CircuitBreaker supports closed, open, and half-open states
- [ ] Configurable failure threshold triggers open state
- [ ] Configurable reset timeout transitions from open to half-open
- [ ] Half-open state allows a single probe call before deciding next state
- [ ] `@with_circuit_breaker(service_name)` decorator works on both sync and async functions
- [ ] Event callbacks fire on every state transition
- [ ] Metrics hooks are stubbed for Phase 5 integration
- [ ] Unit tests pass with >90% coverage of the module

## Upstream Dependencies

None

## Downstream Unblocks

T-054, T-055, T-056, T-057, T-058, T-059

## Estimated Scope

Medium. Core pattern implementation with tests, roughly 300-400 lines of production code.
