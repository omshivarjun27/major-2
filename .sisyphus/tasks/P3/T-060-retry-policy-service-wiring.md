# T-060: retry-policy-service-wiring

> Phase: P3 | Cluster: CL-INF | Risk: Medium | State: completed | created_at: 2026-02-27T16:00:00Z | completed_at: 2026-02-27T20:10:00Z

## Objective

Wire the shared RetryPolicy from `infrastructure/resilience/retry_policy.py` into all 6 service adapters, replacing any ad-hoc retry logic. The retry policy already has per-service default configs (deepgram, livekit, ollama_reasoning, ollama_embedding, duckduckgo, elevenlabs, tavus). This task ensures every external call uses the shared retry infrastructure with circuit-breaker awareness (retries stop when circuit is open). Also adds `@with_retry` decorator usage where appropriate.

## Implementation Plan

1. Audit all 6 service adapters for existing ad-hoc retry logic.
2. For each adapter, replace manual retry loops with shared `RetryPolicy.execute()` or `@with_retry` decorator:
   - `infrastructure/llm/ollama/handler.py` — replace `_request_with_retry` (done in T-056, verify here).
   - `infrastructure/speech/elevenlabs/tts_manager.py` — add retry around remote TTS call.
   - `infrastructure/llm/internet_search.py` — add retry around search calls.
   - `infrastructure/tavus/adapter.py` — add retry around REST calls.
3. Verify retry configs are appropriate for each service's latency SLA:
   - Real-time (deepgram, livekit): max_retries=2, base_delay=0.5s
   - Batch (ollama, duckduckgo): max_retries=3, base_delay=1.0s
   - Optional (tavus): max_retries=1, base_delay=1.0s
4. Ensure retries stop when circuit breaker is OPEN (already handled by RetryPolicy).
5. Write integration test verifying retry + circuit breaker interaction.

## Files to Modify

| File | Purpose |
|------|---------|
| `infrastructure/speech/elevenlabs/tts_manager.py` | Add shared retry policy |
| `infrastructure/llm/internet_search.py` | Add shared retry policy |
| `infrastructure/tavus/adapter.py` | Add shared retry policy |
| `tests/unit/test_retry_service_wiring.py` | Integration tests |

## Acceptance Criteria

- [ ] All 6 service adapters use shared RetryPolicy (no ad-hoc retry loops remaining)
- [ ] Retry configs match service latency requirements
- [ ] Retries stop immediately when circuit breaker is OPEN
- [ ] No duplicate retry logic (shared policy only)
- [ ] Unit tests verify retry + CB interaction for at least 3 services
- [ ] No regression in existing adapter behavior

## Upstream Dependencies

T-054, T-055, T-056, T-057, T-058, T-059

## Downstream Unblocks

T-067 (timeout standardization), T-069 (per-service tests)

## Estimated Scope

Medium. Wiring across 6 adapters, ~150-200 lines of changes total.
