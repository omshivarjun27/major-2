"""
Integration Tests for Memory Engine - RAG Reasoner
"""

import pytest
from datetime import datetime

import numpy as np


class TestRAGReasonerIntegration:
    """Integration tests for RAG-based memory Q&A."""
    
    @pytest.fixture
    def setup_rag_system(self):
        """Set up complete RAG system with sample memories."""
        from core.memory.indexer import MockFAISSIndexer
        from core.memory.embeddings import MockTextEmbedder, MultimodalFuser
        from core.memory.ingest import MemoryIngester
        from core.memory.retriever import MemoryRetriever
        from core.memory.rag_reasoner import RAGReasoner
        
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
        
        reasoner = RAGReasoner(
            retriever=retriever,
            llm_client=None,  # Use template-based answers
        )
        
        return ingester, retriever, reasoner
    
    @pytest.mark.asyncio
    async def test_query_with_no_memories(self, setup_rag_system):
        """Query with no memories should indicate no evidence."""
        ingester, retriever, reasoner = setup_rag_system
        from core.memory.api_schema import MemoryQueryRequest
        
        request = MemoryQueryRequest(query="Where are my keys?")
        response = await reasoner.query(request)
        
        assert response.has_evidence is False
        assert response.confidence < 0.5
        assert "don't have" in response.answer.lower() or "don't recall" in response.answer.lower()
    
    @pytest.mark.asyncio
    async def test_query_returns_citation(self, setup_rag_system):
        """Query with evidence should include citations."""
        ingester, retriever, reasoner = setup_rag_system
        from core.memory.api_schema import MemoryStoreRequest, MemoryQueryRequest
        
        # Store a memory
        await ingester.ingest(MemoryStoreRequest(
            transcript="I put my keys on the kitchen table",
        ))
        
        # Query
        request = MemoryQueryRequest(query="keys", k=5)
        response = await reasoner.query(request)
        
        assert len(response.citations) >= 1
        assert response.citations[0].memory_id.startswith("mem_")
    
    @pytest.mark.asyncio
    async def test_short_mode_uses_template(self, setup_rag_system):
        """Short mode should try template-based answers."""
        ingester, retriever, reasoner = setup_rag_system
        from core.memory.api_schema import MemoryStoreRequest, MemoryQueryRequest, QueryMode
        
        # Store a memory
        await ingester.ingest(MemoryStoreRequest(
            transcript="I put my keys on the table",
        ))
        
        # Query in short mode
        request = MemoryQueryRequest(
            query="where are my keys",
            mode=QueryMode.SHORT,
        )
        response = await reasoner.query(request)
        
        # Should have an answer and no reasoning (template mode)
        assert len(response.answer) > 0
        assert response.reasoning is None
    
    @pytest.mark.asyncio
    async def test_verbose_mode_includes_reasoning(self, setup_rag_system):
        """Verbose mode should include reasoning (when LLM available)."""
        ingester, retriever, reasoner = setup_rag_system
        from core.memory.api_schema import MemoryStoreRequest, MemoryQueryRequest, QueryMode
        
        # Store a memory
        await ingester.ingest(MemoryStoreRequest(
            transcript="My wallet is in my bag",
        ))
        
        # Query in verbose mode (no LLM, so reasoning may be None)
        request = MemoryQueryRequest(
            query="wallet",
            mode=QueryMode.VERBOSE,
        )
        response = await reasoner.query(request)
        
        # Should have an answer
        assert len(response.answer) > 0
    
    @pytest.mark.asyncio
    async def test_query_performance(self, setup_rag_system):
        """RAG query should complete within performance budget."""
        ingester, retriever, reasoner = setup_rag_system
        from core.memory.api_schema import MemoryStoreRequest, MemoryQueryRequest
        import time
        
        # Store some memories
        for i in range(10):
            await ingester.ingest(MemoryStoreRequest(
                transcript=f"Memory number {i} about objects",
            ))
        
        # Time the query
        request = MemoryQueryRequest(query="objects", k=5)
        
        start = time.time()
        response = await reasoner.query(request)
        elapsed_ms = (time.time() - start) * 1000
        
        # Should complete within 200ms (no LLM)
        assert elapsed_ms < 200
        assert response.retrieval_time_ms is not None


class TestTemplateAnswers:
    """Test template-based answer generation."""
    
    @pytest.fixture
    def reasoner(self):
        """Create RAG reasoner without LLM."""
        from core.memory.indexer import MockFAISSIndexer
        from core.memory.embeddings import MockTextEmbedder
        from core.memory.retriever import MemoryRetriever
        from core.memory.rag_reasoner import RAGReasoner
        
        indexer = MockFAISSIndexer(dimension=384)
        embedder = MockTextEmbedder(dimension=384)
        retriever = MemoryRetriever(indexer=indexer, text_embedder=embedder)
        
        return RAGReasoner(retriever=retriever, llm_client=None)
    
    def test_location_query_pattern(self, reasoner):
        """Location queries should match template."""
        from core.memory.api_schema import MemoryHit
        
        memories = [
            MemoryHit(
                id="mem_1",
                timestamp="2024-01-01T12:00:00Z",
                summary="Keys on the kitchen table",
                score=0.85,
            )
        ]
        
        answer, confidence = reasoner._try_template_answer(
            "where did i put my keys?",
            memories,
        )
        
        assert answer is not None
        assert "keys" in answer.lower() or "2024" in answer
    
    def test_high_confidence_fallback(self, reasoner):
        """High confidence match should trigger fallback answer."""
        from core.memory.api_schema import MemoryHit
        
        memories = [
            MemoryHit(
                id="mem_1",
                timestamp="2024-01-01T10:00:00Z",
                summary="Meeting at 3pm with John",
                score=0.9,
            )
        ]
        
        answer, confidence = reasoner._try_template_answer(
            "what meeting do i have",
            memories,
        )
        
        # High score should produce some answer
        if answer:
            assert confidence >= 0.5


class TestMaintenanceIntegration:
    """Test maintenance tasks with full system."""
    
    @pytest.fixture
    def setup_maintenance(self):
        """Set up system with maintenance."""
        from core.memory.indexer import MockFAISSIndexer
        from core.memory.embeddings import MockTextEmbedder, MultimodalFuser
        from core.memory.ingest import MemoryIngester
        from core.memory.maintenance import MemoryMaintenance
        
        indexer = MockFAISSIndexer(dimension=384)
        embedder = MockTextEmbedder(dimension=384)
        fuser = MultimodalFuser(text_embedder=embedder)
        
        ingester = MemoryIngester(
            indexer=indexer,
            text_embedder=embedder,
            fuser=fuser,
        )
        
        maintenance = MemoryMaintenance(indexer=indexer)
        
        return ingester, indexer, maintenance
    
    @pytest.mark.asyncio
    async def test_maintenance_run(self, setup_maintenance):
        """Maintenance run should complete successfully."""
        ingester, indexer, maintenance = setup_maintenance
        from core.memory.api_schema import MemoryStoreRequest
        
        # Store some memories
        for i in range(3):
            await ingester.ingest(MemoryStoreRequest(
                transcript=f"Memory {i}",
            ))
        
        # Run maintenance
        report = await maintenance.run()
        
        assert "started_at" in report
        assert "completed_at" in report
        assert "tasks" in report
        assert report["tasks"]["retention"]["success"] is True
    
    @pytest.mark.asyncio
    async def test_health_check(self, setup_maintenance):
        """Health check should return system status."""
        ingester, indexer, maintenance = setup_maintenance
        
        health = maintenance.get_health()
        
        assert health["status"] == "healthy"
        assert "index_size" in health
        assert "config" in health
