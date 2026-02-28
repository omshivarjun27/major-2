# T-044: ollama-embedder-async

> Phase: P2 | Cluster: CL-MEM | Risk: High | State: completed | created_at: 2026-02-25T10:00:00Z | completed_at: 2026-02-25T12:00:00Z

## Objective

Convert OllamaEmbedder from synchronous to asynchronous execution. Replace blocking HTTP calls with aiohttp, add connection pooling for reuse across concurrent embedding requests, and implement proper async context management for cleanup. The current synchronous implementation blocks the event loop for approximately 150ms per call (PR-2), which is unacceptable in a real-time pipeline. After conversion, embedding calls must yield control to the event loop during network I/O. Add retry logic with exponential backoff for transient Ollama server errors. Preserve the existing embedding interface contract so callers don't need modification.

## Current State (Codebase Audit 2026-02-27)

- **COMPLETED** during the P2 architecture remediation work (prior to this session).
- `core/memory/embeddings.py` has been converted to native async using aiohttp.
- Connection pooling via aiohttp ClientSession implemented.
- Retry logic with exponential backoff added.
- Event loop no longer blocked during embedding calls.
- Existing interface contract preserved — callers unchanged.
- This was one of the first P2 tasks completed (T-038–T-042 + T-044 + T-047 were done before T-043).

## Implemented Files

| File | Purpose |
|------|---------|
| `core/memory/embeddings.py` | OllamaEmbedder with native async, aiohttp, connection pooling, retry |

## Evidence of Completion

- `core/memory/embeddings.py` uses `async def` for embedding calls.
- No `requests.get/post` or synchronous HTTP calls remain in the embedding path.
- PR-2 risk (150ms event loop blocking) is resolved.
- TD-003 (OllamaEmbedder sync blocking) marked as resolved in tech-debt.md.

## Acceptance Criteria

- [x] OllamaEmbedder uses async/await for all HTTP calls
- [x] aiohttp replaces synchronous requests library
- [x] Connection pooling via aiohttp ClientSession
- [x] Retry logic with exponential backoff for transient errors
- [x] Async context management for cleanup
- [x] Embedding interface contract preserved (callers unchanged)
- [x] Event loop no longer blocked during embedding calls
- [x] `ruff check .` clean
- [x] `lint-imports` clean

## Upstream Dependencies

T-020 (embedding async wrapper from P1).

## Downstream Unblocks

T-045, T-046, T-052

## Estimated Scope

- Modified code: ~150 LOC in embeddings.py
- Risk: High (async conversion in hot path; must not break callers)
