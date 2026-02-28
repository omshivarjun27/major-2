# T-056: ollama-circuit-breaker

> Phase: P3 | Cluster: CL-INF | Risk: Medium | State: completed | created_at: 2026-02-27T16:00:00Z | completed_at: 2026-02-27T19:45:00Z

## Objective

Wire the CircuitBreaker and shared RetryPolicy into the Ollama LLM handler (`infrastructure/llm/ollama/handler.py`). The handler currently has its own ad-hoc retry logic (`_request_with_retry`). This task replaces that with the shared resilience infrastructure: circuit breaker for failure tracking and state management, retry policy for backoff. Register an "ollama" circuit breaker with thresholds appropriate for LLM calls (failure_threshold=3, reset_timeout_s=30).

## Implementation Plan

1. Read `infrastructure/llm/ollama/handler.py` to understand the existing `_request_with_retry` method.
2. Import `register_circuit_breaker`, `CircuitBreakerOpenError` and `get_retry_policy` from `infrastructure.resilience`.
3. In `OllamaHandler.__init__()`, register an "ollama" circuit breaker.
4. Replace `_request_with_retry` with a method that:
   - Routes through the circuit breaker first.
   - Uses the shared RetryPolicy for backoff (already configured as "ollama_reasoning" in SERVICE_RETRY_CONFIGS).
   - On CircuitBreakerOpenError, raise immediately (no retry).
5. Add state-change callback for logging.
6. Preserve the existing 4xx no-retry behavior (already handled by error_classifier).
7. Write unit tests in `tests/unit/test_ollama_circuit_breaker.py`.

## Files to Modify

| File | Purpose |
|------|---------|
| `infrastructure/llm/ollama/handler.py` | Replace ad-hoc retry with shared CB + retry policy |
| `tests/unit/test_ollama_circuit_breaker.py` | Unit tests for CB integration |

## Acceptance Criteria

- [ ] "ollama" circuit breaker registered on handler init
- [ ] Ad-hoc `_request_with_retry` replaced with shared resilience
- [ ] Retry behavior uses shared RetryPolicy with exponential backoff
- [ ] Circuit breaker trips after 3 consecutive failures
- [ ] 4xx errors do NOT trip the circuit breaker (handled by error_classifier)
- [ ] Existing OllamaHandler functionality preserved (no regression)
- [ ] Unit tests pass with >90% coverage

## Upstream Dependencies

T-053

## Downstream Unblocks

T-065 (health registry), T-069 (per-service tests)

## Estimated Scope

Medium. Replacing existing retry logic with shared infrastructure, ~100-150 lines of changes.
