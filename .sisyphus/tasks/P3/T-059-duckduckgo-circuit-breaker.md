# T-059: duckduckgo-circuit-breaker

> Phase: P3 | Cluster: CL-INF | Risk: Low | State: completed | created_at: 2026-02-27T16:00:00Z | completed_at: 2026-02-27T20:00:00Z

## Objective

Wire the CircuitBreaker pattern into the DuckDuckGo internet search adapter (`infrastructure/llm/internet_search.py`). The `InternetSearch` class uses langchain's DuckDuckGoSearchRun which makes HTTP calls that can fail or timeout. This task wraps the search calls with a circuit breaker so repeated failures skip the search and return a friendly error message instead of blocking. Register a "duckduckgo" circuit breaker with thresholds suitable for non-critical search (failure_threshold=3, reset_timeout_s=60).

## Implementation Plan

1. Read `infrastructure/llm/internet_search.py` to understand the search flow.
2. Import `register_circuit_breaker` and `CircuitBreakerOpenError`.
3. In `InternetSearch.__init__()`, register a "duckduckgo" circuit breaker.
4. In `InternetSearch.search()`, wrap each `asyncio.to_thread()` call with the circuit breaker:
   - If circuit is OPEN, return a structured error result immediately.
   - Record failures/successes for each search type (general, detailed, news).
5. Add a graceful degradation message: "Internet search is temporarily unavailable."
6. Write unit tests in `tests/unit/test_duckduckgo_circuit_breaker.py`.

## Files to Modify

| File | Purpose |
|------|---------|
| `infrastructure/llm/internet_search.py` | Wire circuit breaker into search calls |
| `tests/unit/test_duckduckgo_circuit_breaker.py` | Unit tests for CB integration |

## Acceptance Criteria

- [ ] "duckduckgo" circuit breaker registered on InternetSearch init
- [ ] Search calls routed through circuit breaker
- [ ] When circuit is OPEN, returns structured error instead of blocking
- [ ] Each search type (general, detailed, news) individually protected
- [ ] Graceful degradation message in results when circuit is open
- [ ] Unit tests pass with >90% coverage

## Upstream Dependencies

T-053

## Downstream Unblocks

T-065 (health registry), T-069 (per-service tests)

## Estimated Scope

Small. Integration into existing search class, ~80-120 lines of changes.
