# T-069: per-service-circuit-breaker-tests

> Phase: P3 | Cluster: CL-TQA | Risk: Low | State: completed | created_at: 2026-02-27T16:00:00Z

## Objective

Write comprehensive unit tests for each service's circuit breaker integration. Each test suite verifies that the circuit breaker is correctly wired, thresholds are properly configured, state transitions work as expected, and callbacks fire correctly. Tests use mocked service backends to avoid external dependencies.

## Implementation Plan

1. Create/update test files for each service:
   - `tests/unit/test_deepgram_circuit_breaker.py` — Deepgram STT CB tests
   - `tests/unit/test_elevenlabs_circuit_breaker.py` — ElevenLabs TTS CB tests
   - `tests/unit/test_ollama_circuit_breaker.py` — Ollama LLM CB tests
   - `tests/unit/test_livekit_circuit_breaker.py` — LiveKit CB tests
   - `tests/unit/test_tavus_circuit_breaker.py` — Tavus CB tests
   - `tests/unit/test_duckduckgo_circuit_breaker.py` — DuckDuckGo CB tests
2. Each test suite must cover:
   - CB registration with correct service name and config.
   - CLOSED -> OPEN transition after failure_threshold failures.
   - OPEN -> HALF_OPEN after reset_timeout_s.
   - HALF_OPEN -> CLOSED on successful probe.
   - HALF_OPEN -> OPEN on failed probe.
   - Callback invocation on each transition.
   - Service-specific behavior (e.g., TTSManager skips remote when OPEN).
3. Ensure test isolation (clear_registry() in teardown).

## Files to Create/Update

| File | Purpose |
|------|---------|
| `tests/unit/test_deepgram_circuit_breaker.py` | Deepgram CB tests |
| `tests/unit/test_elevenlabs_circuit_breaker.py` | ElevenLabs CB tests |
| `tests/unit/test_ollama_circuit_breaker.py` | Ollama CB tests |
| `tests/unit/test_livekit_circuit_breaker.py` | LiveKit CB tests |
| `tests/unit/test_tavus_circuit_breaker.py` | Tavus CB tests |
| `tests/unit/test_duckduckgo_circuit_breaker.py` | DuckDuckGo CB tests |

## Acceptance Criteria

- [x] All 6 service CB test suites created and passing (124 tests total)
- [x] Each suite covers all state transitions (5 transitions minimum)
- [x] Callback invocation verified in each suite
- [x] Service-specific behavior tested (fallback activation, error degradation)
- [x] Test isolation maintained (no cross-test state leakage)
- [x] Total new tests: 124 across all 6 suites (exceeds 30+ requirement)
- [x] All tests pass in < 30 seconds (28.60s)

## Upstream Dependencies

T-054, T-055, T-056, T-057, T-058, T-059

## Downstream Unblocks

T-072 (P3 exit criteria)

## Estimated Scope

Medium. 6 test suites, ~400-500 lines of test code total.
