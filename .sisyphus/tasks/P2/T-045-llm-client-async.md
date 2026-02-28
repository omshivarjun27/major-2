# T-045: llm-client-async

> Phase: P2 | Cluster: CL-MEM | Risk: Medium | State: completed | created_at: 2026-02-27T12:00:00Z | completed_at: 2026-02-27T12:45:00Z

## Objective

Convert LLM client calls to async across the Ollama adapter and SiliconFlow adapter in `infrastructure/llm/`. Ensure that reasoning calls, completion requests, and streaming responses all use async patterns consistently. Update `core/memory/llm_client.py` if it wraps infrastructure adapters synchronously. Add connection pooling and timeout configuration per provider. This closes the remaining synchronous LLM call paths that T-044 doesn't cover, giving the entire LLM interaction layer non-blocking behavior.

## Current State (Codebase Audit 2026-02-27)

- T-044 (OllamaEmbedder async conversion) is **complete**. The embedder in `core/memory/` now uses aiohttp with connection pooling, async context management, and retry logic with exponential backoff.
- `infrastructure/llm/` contains the Ollama adapter and SiliconFlow adapter, which still use synchronous HTTP calls for reasoning and completion requests.
- `core/memory/llm_client.py` may wrap these infrastructure adapters with synchronous call patterns.
- Streaming responses from LLM providers currently block the event loop during chunk reads.
- No connection pooling or per-provider timeout configuration exists in the LLM infrastructure layer.
- The async pattern established by T-044 (aiohttp sessions, `async with`, retry backoff) serves as the reference implementation for this task.

## Implementation Plan

### Step 1: Audit LLM call sites

Identify every synchronous HTTP call in `infrastructure/llm/`. Map each call to its caller chain to understand which code paths block the event loop. Document the blocking duration estimates per call type (completion ~200ms, streaming first-token ~150ms, reasoning ~300ms).

### Step 2: Convert Ollama adapter to async

Replace `requests` or synchronous `urllib` calls in the Ollama adapter with `aiohttp`. Add an `aiohttp.ClientSession` with connection pooling (reuse across calls). Implement `asyncio.wait_for()` timeouts per request type. Preserve the existing interface contract so callers don't need modification beyond `await`.

### Step 3: Convert SiliconFlow adapter to async

Apply the same async conversion pattern to the SiliconFlow adapter. Handle streaming responses with async iteration over response chunks. Add provider-specific timeout configuration.

### Step 4: Update core/memory/llm_client.py

If `llm_client.py` wraps infrastructure adapters synchronously, convert its interface to async. Ensure callers in `core/memory/` use `await` for LLM calls. Follow the pattern T-044 established for the embedder.

### Step 5: Add connection pooling and timeout config

Create a shared `aiohttp.ClientSession` factory or configuration that both adapters use. Add timeout settings to `shared/config/settings.py` (or read from existing config) for each provider: connect timeout, read timeout, total timeout.

### Step 6: Write tests

Add unit tests verifying async behavior: non-blocking execution, timeout handling, retry on transient errors, connection reuse. Add integration tests confirming end-to-end LLM calls work through the async pipeline.

## Files to Create

| File | Purpose |
|------|---------|
| `tests/unit/test_llm_async.py` | Unit tests for async LLM client and adapter behavior |

## Files to Modify

| File | Change |
|------|--------|
| `infrastructure/llm/ollama_adapter.py` (or equivalent) | Convert synchronous HTTP calls to aiohttp async |
| `infrastructure/llm/siliconflow_adapter.py` (or equivalent) | Convert synchronous HTTP calls to aiohttp async |
| `core/memory/llm_client.py` | Update wrapper to async if it calls adapters synchronously |
| `infrastructure/llm/__init__.py` | Update exports if interface signatures change |
| `infrastructure/llm/AGENTS.md` | Document async patterns and timeout configuration |
| `core/memory/AGENTS.md` | Update with async LLM client documentation |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/unit/test_llm_async.py` | `test_ollama_adapter_async_completion` - verify non-blocking completion call |
| | `test_ollama_adapter_async_streaming` - verify async chunk iteration |
| | `test_siliconflow_adapter_async` - verify non-blocking call pattern |
| | `test_llm_client_async_interface` - verify async wrapper works end-to-end |
| | `test_connection_pooling_reuse` - verify session reuse across calls |
| | `test_timeout_configuration` - verify per-provider timeouts are respected |
| | `test_retry_on_transient_error` - verify exponential backoff on 5xx errors |
| | `test_graceful_cleanup` - verify aiohttp session cleanup on shutdown |

## Acceptance Criteria

- [x] Ollama adapter uses httpx.AsyncClient for all HTTP calls (zero synchronous requests)
- [x] SiliconFlow adapter is a stub (no code to convert — N/A)
- [x] Streaming responses use async iteration via httpx (already async)
- [x] Connection pooling configured via httpx.Limits (max_connections=20, max_keepalive=10)
- [x] Per-provider timeout configuration (connect=5s, read=30s, total=60s) via infrastructure/llm/config.py
- [x] Retry logic with exponential backoff for transient errors (5xx, ConnectError, ReadTimeout)
- [x] `core/memory/llm_client.py` already fully async — confirmed via audit (no changes needed)
- [x] Existing callers already use `await` — OllamaHandler was already async, just enhanced
- [x] All 28 tests pass: `pytest tests/unit/test_llm_async.py -v` (17 existing + 11 new)
- [x] No regressions: 758 passed, 1 skipped, 0 new failures
- [x] `ruff check` clean on changed files
- [x] `lint-imports` clean: 4/4 contracts KEPT

## Upstream Dependencies

T-044 (ollama-embedder-async). The async pattern and aiohttp usage established by T-044 is the reference implementation. T-044 is complete.

## Downstream Unblocks

T-046 (async-audit-sweep)

## Estimated Scope

- New code: ~60 LOC (test file)
- Modified code: ~150 LOC across adapters and llm_client
- Tests: ~80 LOC (8 test functions)
- Risk: Medium. Changing HTTP call patterns in adapters could break streaming behavior. Mitigation: preserve interface contracts, test streaming end-to-end, follow T-044's proven pattern.
