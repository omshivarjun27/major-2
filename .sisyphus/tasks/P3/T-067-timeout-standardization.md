# T-067: timeout-standardization

> Phase: P3 | Cluster: CL-INF | Risk: Medium | State: completed | created_at: 2026-02-27T16:00:00Z | completed_at: 2026-02-27T19:45:00Z

## Objective

Standardize all external call timeouts across the codebase to use `asyncio.wait_for()` with configured timeout values from `shared/config/settings.py`. Currently, some adapters use httpx timeouts, some use threading-based timeouts, and some have no timeouts at all. This task enforces the AGENTS.md rule: "Never ignore async timeouts; wrap I/O and external calls in asyncio.wait_for()."

## Implementation Plan

1. Audit all external calls in infrastructure/ for timeout usage:
   - `infrastructure/llm/ollama/handler.py` — httpx timeout (OK but verify config-driven).
   - `infrastructure/speech/elevenlabs/tts_manager.py` — ThreadPoolExecutor timeout.
   - `infrastructure/llm/internet_search.py` — `asyncio.to_thread` with no timeout.
   - `infrastructure/tavus/adapter.py` — aiohttp timeout (verify config-driven).
2. Add timeout config values to `shared/config/settings.py`:
   - `STT_TIMEOUT_S = 2.0`
   - `TTS_TIMEOUT_S = 2.0`
   - `LLM_TIMEOUT_S = 10.0`
   - `SEARCH_TIMEOUT_S = 5.0`
   - `AVATAR_TIMEOUT_S = 5.0`
3. Wrap all external async calls with `asyncio.wait_for()` using config values.
4. Convert ThreadPoolExecutor timeouts to async-native where possible.
5. Ensure timeout errors are classified correctly by error_classifier.
6. Write unit tests verifying timeout behavior for each adapter.

## Files to Modify

| File | Purpose |
|------|---------|
| `shared/config/settings.py` | Add timeout config values |
| `infrastructure/llm/internet_search.py` | Add asyncio.wait_for() |
| `infrastructure/speech/elevenlabs/tts_manager.py` | Standardize timeout |
| `infrastructure/tavus/adapter.py` | Verify config-driven timeout |
| `tests/unit/test_timeout_standardization.py` | Timeout behavior tests |

## Acceptance Criteria

- [x] All external calls wrapped with asyncio.wait_for() or equivalent
- [x] Timeout values configurable via shared/config/settings.py
- [x] No hardcoded timeout values in adapter code
- [x] Timeout errors correctly classified as TIMEOUT by error_classifier
- [x] asyncio.to_thread calls protected with timeout wrappers
- [x] Unit tests verify timeout triggers for each adapter
- [x] No regression in existing functionality

## Upstream Dependencies

T-054, T-055, T-056, T-057, T-058, T-059

## Downstream Unblocks

T-068 (resilience configuration)

## Estimated Scope

Medium. Cross-cutting changes across 4-5 files, ~100-150 lines of changes.
