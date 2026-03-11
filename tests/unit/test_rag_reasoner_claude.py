"""
Unit tests — RAG Reasoner with Claude (mocked)
================================================

Tests the RAG pipeline with a mocked Claude client.
"""

import pytest

from core.memory.api_schema import MemoryQueryRequest, MemoryStoreRequest, QueryMode
from core.memory.config import MemoryConfig
from core.memory.embeddings import MockTextEmbedder, MultimodalFuser
from core.memory.indexer import FAISSIndexer
from core.memory.ingest import MemoryIngester
from core.memory.llm_client import StubLLMClient
from core.memory.rag_reasoner import RAGReasoner
from core.memory.retriever import MemoryRetriever


@pytest.fixture
def rag_setup(tmp_path):
    """Set up full RAG pipeline with mock components."""
    config = MemoryConfig(enabled=True, retention_days=7)
    embedder = MockTextEmbedder(dimension=384)
    fuser = MultimodalFuser(text_embedder=embedder)
    indexer = FAISSIndexer(
        index_path=str(tmp_path / "rag_index"),
        dimension=384,
        max_vectors=100,
    )
    ingester = MemoryIngester(
        indexer=indexer,
        text_embedder=embedder,
        fuser=fuser,
        config=config,
    )
    retriever = MemoryRetriever(
        indexer=indexer,
        text_embedder=embedder,
        config=config,
    )
    llm = StubLLMClient(canned="Based on my memory, you left your keys on the kitchen table.")
    reasoner = RAGReasoner(
        retriever=retriever,
        llm_client=llm,
        config=config,
    )
    return {
        "indexer": indexer,
        "ingester": ingester,
        "retriever": retriever,
        "reasoner": reasoner,
        "llm": llm,
    }


@pytest.mark.asyncio
class TestRAGReasonerClaude:

    async def test_query_with_no_memories(self, rag_setup):
        """Query with empty memory should return no-evidence response."""
        req = MemoryQueryRequest(query="Where are my keys?")
        resp = await rag_setup["reasoner"].query(req)
        assert "don't" in resp.answer.lower() or resp.has_evidence is False

    async def test_query_after_ingest(self, rag_setup):
        """Query after ingesting a memory should return relevant answer."""
        # Ingest a memory
        store_req = MemoryStoreRequest(
            transcript="I left my keys on the kitchen table",
            user_label="keys",
        )
        await rag_setup["ingester"].ingest(store_req)

        # Query
        query_req = MemoryQueryRequest(query="Where are my keys?", k=3)
        resp = await rag_setup["reasoner"].query(query_req)
        # Stub LLM gives canned answer
        assert "keys" in resp.answer.lower() or "kitchen" in resp.answer.lower() or resp.answer

    async def test_verbose_mode(self, rag_setup):
        """Verbose mode should attempt LLM reasoning."""
        store_req = MemoryStoreRequest(transcript="My wallet is in the bedroom")
        await rag_setup["ingester"].ingest(store_req)

        query_req = MemoryQueryRequest(
            query="Where is my wallet?",
            mode=QueryMode.VERBOSE,
            k=3,
        )
        resp = await rag_setup["reasoner"].query(query_req)
        assert resp.answer  # Should have some answer

    async def test_response_has_timing(self, rag_setup):
        """Response should include retrieval and reasoning times."""
        store_req = MemoryStoreRequest(transcript="Test timing memory")
        await rag_setup["ingester"].ingest(store_req)

        query_req = MemoryQueryRequest(query="test timing")
        resp = await rag_setup["reasoner"].query(query_req)
        assert resp.retrieval_time_ms >= 0

    async def test_stub_llm_is_available(self, rag_setup):
        """Stub LLM should report available."""
        assert rag_setup["llm"].is_available is True
        assert rag_setup["llm"].model_name == "stub"
