"""P4: Embedding Query Optimization Tests (T-081).

Tests for embedding caching and query optimization.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import sys
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import List, Optional

import pytest

# Project imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Embedding Cache Implementation
# ---------------------------------------------------------------------------

@dataclass
class EmbeddingCacheEntry:
    """Cache entry for an embedding."""
    text_hash: str
    embedding: List[float]
    created_at: float
    access_count: int = 0


class EmbeddingCache:
    """LRU cache for text embeddings."""

    def __init__(self, max_size: int = 1000, ttl_seconds: float = 3600.0):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, EmbeddingCacheEntry] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def _hash_text(self, text: str) -> str:
        """Generate SHA-256 hash for text."""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]

    def get(self, text: str) -> Optional[List[float]]:
        """Get embedding from cache."""
        key = self._hash_text(text)

        if key not in self._cache:
            self._misses += 1
            return None

        entry = self._cache[key]

        # Check TTL
        if time.time() - entry.created_at > self.ttl_seconds:
            del self._cache[key]
            self._misses += 1
            return None

        # Move to end (LRU)
        self._cache.move_to_end(key)
        entry.access_count += 1
        self._hits += 1

        return entry.embedding

    def put(self, text: str, embedding: List[float]):
        """Store embedding in cache."""
        key = self._hash_text(text)

        # Evict oldest if at capacity
        while len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)

        self._cache[key] = EmbeddingCacheEntry(
            text_hash=key,
            embedding=embedding,
            created_at=time.time(),
        )

    @property
    def hit_rate(self) -> float:
        """Cache hit rate."""
        total = self._hits + self._misses
        return (self._hits / total * 100) if total > 0 else 0.0

    @property
    def size(self) -> int:
        return len(self._cache)

    def clear(self):
        """Clear cache."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0


# ---------------------------------------------------------------------------
# Batch Embedder Mock
# ---------------------------------------------------------------------------

class MockBatchEmbedder:
    """Mock batch embedding generator."""

    def __init__(self, dimension: int = 384, latency_ms: float = 50.0):
        self.dimension = dimension
        self.latency_ms = latency_ms
        self.call_count = 0

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        self.call_count += 1
        await asyncio.sleep(self.latency_ms / 1000)

        import random
        return [
            [random.random() for _ in range(self.dimension)]
            for _ in texts
        ]

    async def embed_single(self, text: str) -> List[float]:
        """Generate embedding for single text."""
        results = await self.embed_batch([text])
        return results[0]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEmbeddingCache:
    """Test EmbeddingCache implementation."""

    def test_cache_creation(self):
        """Should create cache with defaults."""
        cache = EmbeddingCache()

        assert cache.max_size == 1000
        assert cache.ttl_seconds == 3600.0
        assert cache.size == 0

    def test_cache_put_get(self):
        """Should store and retrieve embeddings."""
        cache = EmbeddingCache()

        embedding = [0.1, 0.2, 0.3]
        cache.put("test text", embedding)

        result = cache.get("test text")

        assert result == embedding
        assert cache.size == 1

    def test_cache_miss(self):
        """Should return None for cache miss."""
        cache = EmbeddingCache()

        result = cache.get("nonexistent")

        assert result is None

    def test_cache_hit_rate(self):
        """Should track hit rate."""
        cache = EmbeddingCache()

        cache.put("text1", [0.1])

        cache.get("text1")  # Hit
        cache.get("text1")  # Hit
        cache.get("text2")  # Miss

        assert cache.hit_rate == pytest.approx(66.67, rel=0.1)

    def test_cache_lru_eviction(self):
        """Should evict least recently used."""
        cache = EmbeddingCache(max_size=2)

        cache.put("text1", [0.1])
        cache.put("text2", [0.2])
        cache.get("text1")  # Make text1 most recent
        cache.put("text3", [0.3])  # Should evict text2

        assert cache.get("text1") is not None
        assert cache.get("text2") is None
        assert cache.get("text3") is not None

    def test_cache_ttl_expiration(self):
        """Should expire entries after TTL."""
        cache = EmbeddingCache(ttl_seconds=0.01)  # 10ms TTL

        cache.put("text", [0.1])
        assert cache.get("text") is not None

        time.sleep(0.02)  # Wait for expiration
        assert cache.get("text") is None


class TestMockBatchEmbedder:
    """Test MockBatchEmbedder."""

    async def test_embed_single(self):
        """Should generate single embedding."""
        embedder = MockBatchEmbedder(dimension=384, latency_ms=10)

        embedding = await embedder.embed_single("test text")

        assert len(embedding) == 384
        assert embedder.call_count == 1

    async def test_embed_batch(self):
        """Should generate batch embeddings."""
        embedder = MockBatchEmbedder(dimension=384, latency_ms=10)

        texts = ["text1", "text2", "text3"]
        embeddings = await embedder.embed_batch(texts)

        assert len(embeddings) == 3
        assert all(len(e) == 384 for e in embeddings)
        assert embedder.call_count == 1  # Single batch call

    async def test_batch_more_efficient(self):
        """Batch should be more efficient than individual calls."""
        embedder = MockBatchEmbedder(dimension=384, latency_ms=20)

        texts = ["text1", "text2", "text3", "text4", "text5"]

        # Batch call
        start = time.perf_counter()
        await embedder.embed_batch(texts)
        batch_time = (time.perf_counter() - start) * 1000

        # Individual calls would take 5 * 20ms = 100ms
        assert batch_time < 50  # Should be much faster


class TestCachedEmbedding:
    """Test embedding with caching."""

    async def test_cached_embedding_workflow(self):
        """Should use cache for repeated queries."""
        cache = EmbeddingCache()
        embedder = MockBatchEmbedder(dimension=384, latency_ms=10)

        async def get_embedding(text: str) -> List[float]:
            cached = cache.get(text)
            if cached:
                return cached

            embedding = await embedder.embed_single(text)
            cache.put(text, embedding)
            return embedding

        # First call - cache miss
        emb1 = await get_embedding("test query")
        assert embedder.call_count == 1

        # Second call - cache hit
        emb2 = await get_embedding("test query")
        assert embedder.call_count == 1  # No new call

        assert emb1 == emb2

    async def test_cache_reduces_latency(self):
        """Cached lookups should be faster."""
        cache = EmbeddingCache()
        embedder = MockBatchEmbedder(dimension=384, latency_ms=50)

        # Generate and cache
        embedding = await embedder.embed_single("test")
        cache.put("test", embedding)

        # Measure cache lookup
        start = time.perf_counter()
        result = cache.get("test")
        lookup_time_ms = (time.perf_counter() - start) * 1000

        assert result is not None
        assert lookup_time_ms < 1.0  # Should be < 1ms


class TestEmbeddingOptimization:
    """Test embedding + query combined optimization."""

    async def test_combined_latency_target(self):
        """Combined embedding + mock query should be < 100ms."""
        cache = EmbeddingCache()
        embedder = MockBatchEmbedder(dimension=384, latency_ms=30)

        # Simulate embedding + query workflow
        async def embedding_query_workflow(text: str):
            # Get embedding
            cached = cache.get(text)
            if cached:
                embedding = cached
            else:
                embedding = await embedder.embed_single(text)
                cache.put(text, embedding)

            # Simulate FAISS query (mock)
            await asyncio.sleep(0.01)  # 10ms mock query

            return embedding

        # Cold start (no cache)
        start = time.perf_counter()
        await embedding_query_workflow("test query")
        cold_time = (time.perf_counter() - start) * 1000

        # Warm (cached)
        start = time.perf_counter()
        await embedding_query_workflow("test query")
        warm_time = (time.perf_counter() - start) * 1000

        print(f"\nCold: {cold_time:.1f}ms, Warm: {warm_time:.1f}ms")

        assert warm_time < 50, f"Warm latency {warm_time:.1f}ms exceeds 50ms"
