# T-020: embedding-async-wrapper

> Phase: P1 | Cluster: CL-MEM | Risk: Low | State: not_started

## Schema

- **Phase**: P1
- **Cluster**: CL-MEM
- **Objective**: See below
- **Upstream Deps**: []
- **Downstream Impact**: [T-021]
- **Risk Tier**: Low
- **Test Layers**: [Unit]
- **Doc Mutation Map**: [core/memory/AGENTS.md]
- **Versioning Impact**: patch
- **Governance Level**: standard
- **Regression Sensitivity**: low
- **Parallelization Eligible**: yes
- **Execution Environment**: Local GPU
- **Current State**: not_started
- **Estimated LOC**: ~60 new, ~20 modified
- **Test Count Target**: 5

## Objective

Wrap `TextEmbedder.embed()` and `embed_batch()` in `core/memory/embeddings.py` with
`asyncio.run_in_executor()` so they stop blocking the event loop. Currently every
embedding call blocks for ~150ms while waiting on the Ollama API. This stalls the entire
async pipeline: TTS output freezes, WebSocket heartbeats miss deadlines, and frame
processing backs up.

Add `async_embed()` and `async_embed_batch()` methods to `TextEmbedder`. Then update
`MemoryIngester` and `MemoryRetriever` to call the new async methods instead of the
synchronous originals.

## Current State (Codebase Audit 2026-02-25)

- `core/memory/embeddings.py` is 487 lines. Contains 5 classes: `BaseEmbedder` (ABC), `TextEmbedder`, `MockTextEmbedder`, `ImageEmbedder`, `AudioEmbedder`, plus `MultimodalFuser` and `create_embedders()` factory.
- `TextEmbedder` (line 64):
  - `embed()` (line 102): synchronous. Calls `self._client.embed(model=..., input=text)` via the Ollama Python client. Blocks for the full round-trip.
  - `embed_batch()` (line 134): synchronous. Calls `self._client.embed(model=..., input=cleaned)` with a list of texts. Also blocks.
  - `_ensure_client()` (line 77): lazy-loads the Ollama client and probes dimension.
  - `_normalize()` (line 97): L2-normalizes a vector. Pure computation, fast.
- `MockTextEmbedder` (line 182): deterministic hash-based mock. No Ollama calls. No async needed.
- `BaseEmbedder` ABC (line 38): defines abstract `embed()`, `embed_batch()`, `dimension`, `is_ready`. Does not define async methods.
- `MultimodalFuser.fuse()` (line 353): calls `self._text_embedder.embed(text)` synchronously. Called from `MemoryIngester._compute_embedding()`.
- `MemoryIngester._compute_embedding()` (line 265 in ingest.py): calls `self._fuser.fuse()` which calls `embed()` synchronously inside an async method.
- `MemoryRetriever.search()` (line 61 in retriever.py): calls `self._text_embedder.embed(request.query)` synchronously inside an async method.
- No `asyncio` import exists in `embeddings.py`.
- `AudioEmbedder.embed()` (line 304): delegates to `self._text_embedder.embed(transcript)` when transcript is available.

## Implementation Plan

### Step 1: Add async methods to TextEmbedder

Add two new methods that wrap the synchronous calls using `asyncio.get_event_loop().run_in_executor()`:

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Module-level executor shared across embedders
_embedding_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="embed")


class TextEmbedder(BaseEmbedder):
    # ... existing code ...

    async def async_embed(self, text: str) -> np.ndarray:
        """Non-blocking embedding for a single text string.

        Offloads the synchronous Ollama API call to a thread pool executor
        so the event loop remains free.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(_embedding_executor, self.embed, text)

    async def async_embed_batch(self, texts: List[str], batch_size: int = 8) -> np.ndarray:
        """Non-blocking batch embedding.

        Offloads the synchronous Ollama batch API call to a thread pool executor.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            _embedding_executor,
            lambda: self.embed_batch(texts, batch_size),
        )
```

Using a dedicated `ThreadPoolExecutor` with 2 workers avoids starving the default executor
that other async tasks might share. The `thread_name_prefix` helps with debugging.

### Step 2: Add async methods to MockTextEmbedder

For test symmetry, add the same async interface to `MockTextEmbedder`:

```python
class MockTextEmbedder(BaseEmbedder):
    # ... existing code ...

    async def async_embed(self, text: str) -> np.ndarray:
        """Async wrapper for mock (runs instantly, no real I/O)."""
        return self.embed(text)

    async def async_embed_batch(self, texts: List[str], batch_size: int = 8) -> np.ndarray:
        """Async wrapper for mock batch."""
        return self.embed_batch(texts, batch_size)
```

The mock doesn't need `run_in_executor` since it's purely computational and instant.

### Step 3: Add async fuse to MultimodalFuser

Add `async_fuse()` that calls `async_embed()` instead of `embed()`:

```python
async def async_fuse(
    self,
    text: Optional[str] = None,
    image: Optional[Any] = None,
    audio: Optional[Any] = None,
    audio_transcript: Optional[str] = None,
    weights: Optional[dict] = None,
) -> np.ndarray:
    """Async version of fuse(). Uses async_embed for text embeddings."""
    embeddings = []
    modality_weights = []
    default_weights = weights or {"text": 1.0, "image": 0.8, "audio": 0.6}

    if text and self._text_embedder and hasattr(self._text_embedder, 'async_embed'):
        emb = await self._text_embedder.async_embed(text)
        if np.any(emb):
            embeddings.append(emb)
            modality_weights.append(default_weights.get("text", 1.0))
    elif text and self._text_embedder:
        emb = self._text_embedder.embed(text)
        if np.any(emb):
            embeddings.append(emb)
            modality_weights.append(default_weights.get("text", 1.0))

    # Image and audio paths remain synchronous (CLIP is optional,
    # audio falls back to text which is now async above)
    # ... rest follows same fusion logic as sync fuse() ...
```

### Step 4: Update MemoryIngester to use async embedding

In `core/memory/ingest.py`, update `_compute_embedding()`:

```python
async def _compute_embedding(self, text, image, audio) -> np.ndarray:
    if hasattr(self._fuser, 'async_fuse'):
        return await self._fuser.async_fuse(
            text=text,
            image=image if self._config.image_embedding_enabled else None,
            audio=audio if self._config.audio_embedding_enabled else None,
            audio_transcript=text,
        )
    return self._fuser.fuse(text=text, image=image, audio=audio, audio_transcript=text)
```

### Step 5: Update MemoryRetriever to use async embedding

In `core/memory/retriever.py`, update `search()`:

```python
# Replace:
query_embedding = self._text_embedder.embed(request.query)
# With:
if hasattr(self._text_embedder, 'async_embed'):
    query_embedding = await self._text_embedder.async_embed(request.query)
else:
    query_embedding = self._text_embedder.embed(request.query)
```

The `hasattr` check preserves backward compatibility with any custom embedder
implementations that lack the async methods.

## Files to Create

| File | Purpose |
|------|---------|
| (none) | All changes are modifications to existing files |

## Files to Modify

| File | Change |
|------|--------|
| `core/memory/embeddings.py` | Add `import asyncio` and `ThreadPoolExecutor`. Add `async_embed()` and `async_embed_batch()` to `TextEmbedder`. Add same methods to `MockTextEmbedder`. Add `async_fuse()` to `MultimodalFuser`. |
| `core/memory/ingest.py` | Update `_compute_embedding()` to call `async_fuse()` when available. |
| `core/memory/retriever.py` | Update `search()` to call `async_embed()` when available. |
| `core/memory/AGENTS.md` | Note the new async embedding interface and thread pool executor. |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/unit/test_embedding_async.py` | `test_async_embed_returns_same_result_as_sync` - verify output parity between `embed()` and `async_embed()` using MockTextEmbedder |
| | `test_async_embed_batch_returns_same_shape` - verify batch output shape matches sync version |
| | `test_async_embed_does_not_block_event_loop` - create a concurrent task, verify it runs during embedding |
| | `test_async_fuse_produces_valid_embedding` - verify `async_fuse()` output is normalized and non-zero |
| | `test_executor_thread_pool_is_bounded` - verify the executor has max_workers=2 |

## Acceptance Criteria

- [ ] `TextEmbedder.async_embed()` returns the same vector as `embed()` for the same input
- [ ] `TextEmbedder.async_embed_batch()` returns the same array as `embed_batch()`
- [ ] Both async methods use `asyncio.run_in_executor()` with a dedicated thread pool
- [ ] `MockTextEmbedder` has matching `async_embed()` and `async_embed_batch()` methods
- [ ] `MultimodalFuser.async_fuse()` calls `async_embed()` for the text modality
- [ ] `MemoryIngester._compute_embedding()` calls `async_fuse()` when available
- [ ] `MemoryRetriever.search()` calls `async_embed()` when available
- [ ] Backward compatibility: callers that pass custom embedders without async methods still work
- [ ] Thread pool executor has max_workers=2 and a descriptive thread name prefix
- [ ] All existing embedding and ingester tests continue to pass
- [ ] 5 new test functions covering async parity, non-blocking behavior, and integration
- [ ] `ruff check .` clean
- [ ] `lint-imports` clean

## Upstream Dependencies

None. This task has no upstream dependencies within the CL-MEM cluster.
The `TextEmbedder` and `MockTextEmbedder` classes exist and function correctly today.

## Downstream Unblocks

T-021 (ingest-pipeline-hardening): depends on async embedding being available so that
the hardened ingest pipeline can process batches without blocking the event loop.

## Estimated Scope

- New code: ~60 LOC (async methods on TextEmbedder, MockTextEmbedder, MultimodalFuser)
- Modified code: ~20 lines in ingest.py and retriever.py
- Tests: ~80 LOC
- Risk: Low (additive methods, sync originals unchanged, backward compatible)
