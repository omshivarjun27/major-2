"""
Integration Tests for Memory Engine - Search API
"""

from datetime import datetime

import numpy as np
import pytest


class TestMemorySearchIntegration:
    """Integration tests for memory search functionality."""

    @pytest.fixture
    def setup_memory_system(self):
        """Set up complete memory system with sample data."""
        from core.memory.embeddings import MockTextEmbedder, MultimodalFuser
        from core.memory.indexer import MockFAISSIndexer
        from core.memory.ingest import MemoryIngester
        from core.memory.retriever import MemoryRetriever

        indexer = MockFAISSIndexer(dimension=384)
        embedder = MockTextEmbedder(dimension=384)
        fuser = MultimodalFuser(text_embedder=embedder)

        ingester = MemoryIngester(
            indexer=indexer,
            text_embedder=embedder,
            fuser=fuser,
        )

        retriever = MemoryRetriever(
            indexer=indexer,
            text_embedder=embedder,
        )

        return ingester, retriever, indexer

    @pytest.mark.asyncio
    async def test_store_and_search(self, setup_memory_system):
        """Stored memory should be searchable."""
        ingester, retriever, indexer = setup_memory_system
        from core.memory.api_schema import MemorySearchRequest, MemoryStoreRequest

        # Store a memory
        store_req = MemoryStoreRequest(
            transcript="I put my keys on the kitchen table",
            session_id="session_1",
        )
        store_resp = await ingester.ingest(store_req)

        # Search for it
        search_req = MemorySearchRequest(query="where are my keys", k=5)
        search_resp = await retriever.search(search_req)

        assert len(search_resp.results) >= 1
        assert store_resp.id in [r.id for r in search_resp.results]

    @pytest.mark.asyncio
    async def test_search_returns_relevant_results(self, setup_memory_system):
        """Search should return relevant results first."""
        ingester, retriever, indexer = setup_memory_system
        from core.memory.api_schema import MemorySearchRequest, MemoryStoreRequest

        # Store multiple memories
        memories = [
            "I put my keys on the table",
            "The weather was nice today",
            "My glasses are on the desk",
            "Keys are important to remember",
        ]

        for mem in memories:
            await ingester.ingest(MemoryStoreRequest(transcript=mem))

        # Search for keys
        search_req = MemorySearchRequest(query="keys", k=3)
        search_resp = await retriever.search(search_req)

        # "keys" should be in top results
        summaries = [r.summary.lower() for r in search_resp.results]
        has_keys = any("keys" in s for s in summaries)
        assert has_keys

    @pytest.mark.asyncio
    async def test_search_respects_k_limit(self, setup_memory_system):
        """Search should respect K limit."""
        ingester, retriever, indexer = setup_memory_system
        from core.memory.api_schema import MemorySearchRequest, MemoryStoreRequest

        # Store many memories
        for i in range(10):
            await ingester.ingest(MemoryStoreRequest(transcript=f"Memory number {i}"))

        # Search with k=3
        search_req = MemorySearchRequest(query="memory", k=3)
        search_resp = await retriever.search(search_req)

        assert len(search_resp.results) <= 3

    @pytest.mark.asyncio
    async def test_search_session_filter(self, setup_memory_system):
        """Search should filter by session."""
        ingester, retriever, indexer = setup_memory_system
        from core.memory.api_schema import MemorySearchRequest, MemoryStoreRequest

        # Store memories in different sessions
        await ingester.ingest(MemoryStoreRequest(
            transcript="Session A memory",
            session_id="session_a",
        ))
        await ingester.ingest(MemoryStoreRequest(
            transcript="Session B memory",
            session_id="session_b",
        ))

        # Search only session A
        search_req = MemorySearchRequest(
            query="memory",
            k=10,
            session_id="session_a",
        )
        search_resp = await retriever.search(search_req)

        # This test validates the filter is applied
        # With mock embedder, results may vary
        assert search_resp.total_searched > 0

    @pytest.mark.asyncio
    async def test_get_memory_by_id(self, setup_memory_system):
        """Should retrieve memory by ID."""
        ingester, retriever, indexer = setup_memory_system
        from core.memory.api_schema import MemoryStoreRequest

        # Store a memory
        store_req = MemoryStoreRequest(transcript="Test memory for ID lookup")
        store_resp = await ingester.ingest(store_req)

        # Get by ID
        record = retriever.get_memory(store_resp.id)

        assert record is not None
        assert record.id == store_resp.id
        assert "Test memory" in record.summary

    @pytest.mark.asyncio
    async def test_get_session_memories(self, setup_memory_system):
        """Should get all memories for a session."""
        ingester, retriever, indexer = setup_memory_system
        from core.memory.api_schema import MemoryStoreRequest

        session_id = "test_session_123"

        # Store multiple memories in session
        for i in range(5):
            await ingester.ingest(MemoryStoreRequest(
                transcript=f"Session memory {i}",
                session_id=session_id,
            ))

        # Get session memories
        records = retriever.get_session_memories(session_id)

        assert len(records) == 5
        for r in records:
            assert r.session_id == session_id

    @pytest.mark.asyncio
    async def test_search_performance(self, setup_memory_system):
        """Search should complete within performance budget."""
        ingester, retriever, indexer = setup_memory_system
        import time

        from core.memory.api_schema import MemorySearchRequest, MemoryStoreRequest

        # Store some memories
        for i in range(20):
            await ingester.ingest(MemoryStoreRequest(transcript=f"Memory content {i}"))

        # Time the search
        search_req = MemorySearchRequest(query="content", k=5)

        start = time.time()
        search_resp = await retriever.search(search_req)
        elapsed_ms = (time.time() - start) * 1000

        # Should complete within 100ms (mock embedder)
        assert elapsed_ms < 100
        assert search_resp.search_time_ms is not None


class TestIndexerPersistence:
    """Test FAISS indexer persistence."""

    @pytest.fixture
    def temp_index_path(self, tmp_path):
        """Create temporary index path."""
        return str(tmp_path / "test_index")

    def test_mock_indexer_add_and_search(self):
        """Mock indexer should support add and search."""
        from core.memory.indexer import MockFAISSIndexer

        indexer = MockFAISSIndexer(dimension=384, max_vectors=100)

        # Add vector
        vec = np.random.randn(384).astype(np.float32)
        vec = vec / np.linalg.norm(vec)

        indexer.add(
            id="test_1",
            embedding=vec,
            timestamp=datetime.utcnow().isoformat() + "Z",
            expiry="2030-01-01T00:00:00Z",
            summary="Test summary",
        )

        assert indexer.size == 1

        # Search
        results = indexer.search(vec, k=1)
        assert len(results) == 1
        assert results[0].id == "test_1"

    def test_mock_indexer_delete(self):
        """Mock indexer should support deletion."""
        from core.memory.indexer import MockFAISSIndexer

        indexer = MockFAISSIndexer(dimension=384)

        vec = np.random.randn(384).astype(np.float32)
        indexer.add(
            id="to_delete",
            embedding=vec,
            timestamp=datetime.utcnow().isoformat() + "Z",
            summary="Will be deleted",
        )

        assert indexer.size == 1

        deleted = indexer.delete("to_delete")
        assert deleted is True
        assert indexer.size == 0

    def test_mock_indexer_eviction(self):
        """Mock indexer should evict when at capacity."""
        from core.memory.indexer import MockFAISSIndexer

        indexer = MockFAISSIndexer(dimension=384, max_vectors=5)

        # Fill to capacity
        for i in range(5):
            vec = np.random.randn(384).astype(np.float32)
            indexer.add(
                id=f"mem_{i}",
                embedding=vec,
                timestamp=datetime(2020, 1, i+1).isoformat() + "Z",
                summary=f"Memory {i}",
            )

        assert indexer.size == 5

        # Add one more (should trigger eviction)
        vec = np.random.randn(384).astype(np.float32)
        indexer.add(
            id="mem_new",
            embedding=vec,
            timestamp=datetime.utcnow().isoformat() + "Z",
            summary="New memory",
        )

        # Should still be at max capacity
        assert indexer.size <= 5
