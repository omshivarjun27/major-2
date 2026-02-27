# T-081: embedding-query-optimization

> Phase: P4 | Cluster: CL-MEM | Risk: Medium | State: completed | created_at: 2026-02-27T20:00:00Z

## Objective

Optimize the embedding generation and query pipeline to minimize latency in the RAG retrieval path. Target: embedding generation + FAISS query combined <100ms. Focus on batching, caching, and async optimizations.

## Implementation Plan

1. Profile current embedding generation latency (Ollama embeddings).
2. Implement embedding cache with LRU eviction:
   - Cache embeddings for repeated queries
   - SHA-256 hash key for cache lookup
3. Optimize batch embedding generation:
   - Batch multiple texts in single Ollama call
   - Async generation for non-blocking operation
4. Implement query result caching:
   - Cache top-k results for recent queries
   - TTL-based expiration
5. Benchmark optimizations against baseline.

## Files to Create/Modify

| File | Purpose |
|------|---------|
| `core/memory/embedding_cache.py` | Embedding caching layer |
| `infrastructure/llm/embeddings/batch_embedder.py` | Batch embedding optimization |
| `tests/performance/test_embedding_optimization.py` | Optimization benchmarks |

## Acceptance Criteria

- [ ] Embedding cache implemented with LRU eviction
- [ ] Batch embedding reduces per-item latency
- [ ] Cache hit rate >50% in typical usage
- [ ] Combined embedding + query <100ms
- [ ] Memory usage bounded (max cache size configurable)
- [ ] No regressions in retrieval quality

## Upstream Dependencies

T-080 (FAISS scaling)

## Downstream Unblocks

T-084 (end-to-end latency validation)

## Estimated Scope

Medium. Caching and optimization, ~200-250 lines of code.
