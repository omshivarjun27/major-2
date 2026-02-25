# T-019: rag-retriever-mvp

> Phase: P1 | Cluster: CL-MEM | Risk: Low | State: not_started

## Schema

- **Phase**: P1
- **Cluster**: CL-MEM
- **Objective**: See below
- **Upstream Deps**: [T-018]
- **Downstream Impact**: []
- **Risk Tier**: Low
- **Test Layers**: [Unit]
- **Doc Mutation Map**: [core/memory/AGENTS.md]
- **Versioning Impact**: patch
- **Governance Level**: standard
- **Regression Sensitivity**: low
- **Parallelization Eligible**: yes
- **Execution Environment**: Local GPU
- **Current State**: not_started
- **Estimated LOC**: ~80 new, ~30 modified
- **Test Count Target**: 5

## Objective

Complete the `MemoryRetriever` in `core/memory/retriever.py` by adding three missing
capabilities: L2-to-cosine score normalization, result deduplication, and proper async
wrapping of the synchronous FAISS search call. The retriever already works for basic
queries, but its score values are unintuitive (an inverse-distance transform that doesn't
map cleanly to 0..1 similarity), duplicate memories can appear when the same content was
indexed with slight variations, and the `async search()` method blocks the event loop
because it calls `TextEmbedder.embed()` synchronously.

This task fixes all three issues while keeping the public API signature unchanged.

## Current State (Codebase Audit 2026-02-25)

- `core/memory/retriever.py` is 270 lines. `MemoryRetriever` is the only public class.
- Constructor (line 42): accepts `indexer`, `text_embedder`, `config`. Creates embedders from factory if not provided.
- `search()` (line 61): async method that calls `self._text_embedder.embed(request.query)` synchronously (line 77), then `self._indexer.search()` (line 80). Both are blocking calls inside an async function.
- Score conversion happens in `FAISSIndexer.search()` at line 263 of `indexer.py`: `score = 1.0 / (1.0 + dist)`. This is a monotonic transform of L2 distance but doesn't produce true cosine similarity.
- `search_by_embedding()` (line 137): thin wrapper over `self._indexer.search()`, also synchronous.
- `get_memory()` (line 164): synchronous, returns `MemoryRecord` from indexer metadata. No issues.
- `get_session_memories()` (line 187): iterates `self._indexer._metadata` directly (accesses private dict). Works but fragile.
- `get_recent_memories()` (line 222): similar pattern, iterates private metadata dict.
- Score threshold filtering at line 91: `if result.score < self._config.similarity_threshold`.
- No deduplication logic exists anywhere in the retriever.
- `MemorySearchResponse` (from `api_schema.py`) is the return type for `search()`.
- `SearchResult` (from `indexer.py`, line 61): has `id`, `score`, `metadata` fields.

## Implementation Plan

### Step 1: Add L2-to-cosine score normalization

The FAISS index uses `IndexFlatL2`, which returns raw L2 distances. The current
`1.0 / (1.0 + dist)` transform produces values in (0, 1] but they aren't true cosine
similarities. Since all embeddings are L2-normalized before indexing (the `TextEmbedder._normalize()` call at line 99 of embeddings.py), we can convert L2 distance to cosine similarity exactly:

```python
# For L2-normalized vectors: ||a - b||^2 = 2 - 2*cos(a,b)
# Therefore: cos(a,b) = 1 - (dist^2 / 2)
# But FAISS returns squared L2 distance for IndexFlatL2
cosine_sim = 1.0 - (l2_dist / 2.0)
cosine_sim = max(0.0, min(1.0, cosine_sim))  # Clamp to [0, 1]
```

Add a `_normalize_score()` method to `MemoryRetriever` that applies this transform.
Apply it in `search()` after receiving raw results, before filtering and ranking.

### Step 2: Add result deduplication

Implement deduplication based on summary text similarity. When two results have
identical `metadata.summary` strings (or summaries that differ only in whitespace/casing),
keep only the one with the higher score.

```python
def _deduplicate(self, results: List[SearchResult]) -> List[SearchResult]:
    """Remove duplicate results based on summary text."""
    seen: Dict[str, SearchResult] = {}
    for result in results:
        key = result.metadata.summary.strip().lower()
        if key not in seen or result.score > seen[key].score:
            seen[key] = result
    # Preserve original ordering by score
    deduped = list(seen.values())
    deduped.sort(key=lambda r: -r.score)
    return deduped
```

### Step 3: Wrap synchronous calls with asyncio.to_thread

The `search()` method is declared `async` but calls `self._text_embedder.embed()` and
`self._indexer.search()` synchronously. Wrap both with `asyncio.to_thread()`:

```python
async def search(self, request: MemorySearchRequest) -> MemorySearchResponse:
    start_time = time.time()
    try:
        # Non-blocking embedding
        query_embedding = await asyncio.to_thread(
            self._text_embedder.embed, request.query
        )
        # Non-blocking FAISS search
        raw_results = await asyncio.to_thread(
            self._indexer.search,
            query_embedding,
            request.k * 2,  # Over-fetch for dedup headroom
            request.time_window_days,
            request.session_id,
        )
        # Normalize scores
        for r in raw_results:
            r.score = self._normalize_score(r.score)
        # Deduplicate
        raw_results = self._deduplicate(raw_results)
        # ... rest of processing
```

Add `import asyncio` to the module imports.

### Step 4: Update search_by_embedding similarly

Apply score normalization and deduplication to `search_by_embedding()` as well. This
method is also async, so wrap the `self._indexer.search()` call with `asyncio.to_thread()`.

### Step 5: Write tests

Create 5 focused tests that verify each new behavior independently.

## Files to Create

| File | Purpose |
|------|---------|
| (none) | All changes are modifications to existing files |

## Files to Modify

| File | Change |
|------|--------|
| `core/memory/retriever.py` | Add `import asyncio`. Add `_normalize_score()` and `_deduplicate()` methods. Wrap sync calls in `search()` and `search_by_embedding()` with `asyncio.to_thread()`. Over-fetch results for dedup headroom. |
| `core/memory/AGENTS.md` | Note that retriever now returns cosine similarity scores and deduplicates results. |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/unit/test_retriever_mvp.py` | `test_score_normalization_l2_to_cosine` - verify normalized scores are in [0, 1] and closer vectors score higher |
| | `test_deduplication_removes_summary_duplicates` - verify identical summaries collapse to single result |
| | `test_deduplication_keeps_highest_score` - verify the higher-scored duplicate wins |
| | `test_search_does_not_block_event_loop` - verify `search()` yields control (using `asyncio.to_thread` mock) |
| | `test_search_with_empty_index_returns_empty` - verify graceful handling of empty index after normalization changes |

## Acceptance Criteria

- [ ] `search()` returns cosine similarity scores in [0, 1] range for L2-normalized embeddings
- [ ] Duplicate results with identical summaries are collapsed, keeping the highest score
- [ ] `search()` wraps `TextEmbedder.embed()` and `FAISSIndexer.search()` in `asyncio.to_thread()`
- [ ] `search_by_embedding()` also wraps the synchronous indexer call
- [ ] Score threshold filtering still works correctly with the new score scale
- [ ] `get_memory()`, `get_session_memories()`, `get_recent_memories()` remain unchanged
- [ ] Over-fetch factor (k * 2) compensates for results lost to deduplication
- [ ] All existing retriever tests continue to pass
- [ ] 5 new test functions covering normalization, dedup, and async wrapping
- [ ] `ruff check .` clean
- [ ] `lint-imports` clean

## Upstream Dependencies

T-018 (faiss-indexer-persistence): the retriever depends on reliable index persistence.
The indexer must save/load correctly for retriever integration tests to work.

## Downstream Unblocks

No tasks directly depend on T-019. However, the RAGReasoner in `rag_reasoner.py` consumes
retriever output, so correct score normalization improves downstream reasoning quality.

## Estimated Scope

- New code: ~80 LOC (normalization, dedup, async wrapping)
- Modified code: ~30 lines in existing `search()` and `search_by_embedding()`
- Tests: ~90 LOC
- Risk: Low (additive changes, public API signature unchanged)
