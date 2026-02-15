"""
Unit Tests for Memory Engine - Ingest Module
"""

import pytest
from datetime import datetime, timedelta

import numpy as np


class TestMemoryIngester:
    """Test MemoryIngester functionality."""
    
    @pytest.fixture
    def mock_indexer(self):
        """Create a mock FAISS indexer."""
        from core.memory.indexer import MockFAISSIndexer
        return MockFAISSIndexer(dimension=384)
    
    @pytest.fixture
    def mock_embedder(self):
        """Create a mock text embedder."""
        from core.memory.embeddings import MockTextEmbedder
        return MockTextEmbedder(dimension=384)
    
    @pytest.fixture
    def mock_fuser(self, mock_embedder):
        """Create a mock multimodal fuser."""
        from core.memory.embeddings import MultimodalFuser
        return MultimodalFuser(text_embedder=mock_embedder)
    
    @pytest.fixture
    def ingester(self, mock_indexer, mock_embedder, mock_fuser):
        """Create a MemoryIngester with mock dependencies."""
        from core.memory.ingest import MemoryIngester
        return MemoryIngester(
            indexer=mock_indexer,
            text_embedder=mock_embedder,
            fuser=mock_fuser,
        )
    
    @pytest.mark.asyncio
    async def test_ingest_with_transcript(self, ingester):
        """Ingesting with transcript should succeed."""
        from core.memory.api_schema import MemoryStoreRequest, EmbeddingStatus
        
        request = MemoryStoreRequest(
            transcript="I put my keys on the kitchen table",
            session_id="test_session",
        )
        
        response = await ingester.ingest(request)
        
        assert response.id.startswith("mem_")
        assert response.embedding_status == EmbeddingStatus.COMPLETED
        assert "keys" in response.summary.lower() or "table" in response.summary.lower()
    
    @pytest.mark.asyncio
    async def test_ingest_with_scene_graph(self, ingester):
        """Ingesting with scene graph should extract object info."""
        from core.memory.api_schema import MemoryStoreRequest
        
        request = MemoryStoreRequest(
            scene_graph={
                "objects": [
                    {"class": "keys"},
                    {"class": "table"},
                    {"class": "chair"},
                ]
            }
        )
        
        response = await ingester.ingest(request)
        
        assert response.id.startswith("mem_")
        assert "keys" in response.summary.lower() or "Scene" in response.summary
    
    @pytest.mark.asyncio
    async def test_ingest_with_user_label(self, ingester):
        """User label should be included in summary."""
        from core.memory.api_schema import MemoryStoreRequest
        
        request = MemoryStoreRequest(
            transcript="Some text",
            user_label="Important memory",
        )
        
        response = await ingester.ingest(request)
        
        assert "Important memory" in response.summary
    
    @pytest.mark.asyncio
    async def test_ingest_sets_expiry(self, ingester):
        """Expiry should be set based on retention days."""
        from core.memory.api_schema import MemoryStoreRequest
        
        request = MemoryStoreRequest(transcript="Test expiry")
        response = await ingester.ingest(request)
        
        # Parse expiry and check it's in the future
        expiry = datetime.fromisoformat(response.expiry.replace("Z", "+00:00"))
        now = datetime.utcnow().replace(tzinfo=expiry.tzinfo)
        
        assert expiry > now
        # Should be at least 1 day in future (default retention is 30 days)
        assert (expiry - now).days >= 1
    
    @pytest.mark.asyncio
    async def test_ingest_adds_to_indexer(self, ingester, mock_indexer):
        """Ingested memory should be searchable in indexer."""
        from core.memory.api_schema import MemoryStoreRequest
        
        request = MemoryStoreRequest(transcript="Searchable content")
        response = await ingester.ingest(request)
        
        assert mock_indexer.size == 1
        assert mock_indexer.get(response.id) is not None
    
    @pytest.mark.asyncio
    async def test_ingest_performance_under_threshold(self, ingester):
        """Ingestion should complete within reasonable time."""
        from core.memory.api_schema import MemoryStoreRequest
        import time
        
        request = MemoryStoreRequest(transcript="Performance test")
        
        start = time.time()
        response = await ingester.ingest(request)
        elapsed_ms = (time.time() - start) * 1000
        
        # Ingestion should complete within 500ms (mock embedder is fast)
        assert elapsed_ms < 500
        assert response.ingest_time_ms is not None


class TestConsentTracking:
    """Test consent recording and retrieval."""
    
    @pytest.fixture
    def ingester(self):
        """Create ingester for consent tests."""
        from core.memory.indexer import MockFAISSIndexer
        from core.memory.embeddings import MockTextEmbedder, MultimodalFuser
        from core.memory.ingest import MemoryIngester
        
        indexer = MockFAISSIndexer(dimension=384)
        embedder = MockTextEmbedder(dimension=384)
        fuser = MultimodalFuser(text_embedder=embedder)
        
        return MemoryIngester(indexer=indexer, text_embedder=embedder, fuser=fuser)
    
    def test_record_consent_opt_in(self, ingester):
        """Recording opt-in consent should be stored."""
        result = ingester.record_consent(
            device_id="device_123",
            opt_in=True,
            save_raw_media=True,
        )
        
        assert result["memory_enabled"] is True
        assert result["save_raw_media"] is True
    
    def test_record_consent_opt_out(self, ingester):
        """Recording opt-out consent should be stored."""
        result = ingester.record_consent(
            device_id="device_123",
            opt_in=False,
            save_raw_media=False,
        )
        
        assert result["memory_enabled"] is False
    
    def test_get_consent_returns_default(self, ingester):
        """Getting consent for unknown device returns defaults."""
        result = ingester.get_consent("unknown_device")
        
        assert result["memory_enabled"] is True  # Default enabled
        assert result["save_raw_media"] is False  # Default off


class TestSummaryGeneration:
    """Test automatic summary generation."""
    
    @pytest.fixture
    def ingester(self):
        from core.memory.indexer import MockFAISSIndexer
        from core.memory.embeddings import MockTextEmbedder, MultimodalFuser
        from core.memory.ingest import MemoryIngester
        
        indexer = MockFAISSIndexer(dimension=384)
        embedder = MockTextEmbedder(dimension=384)
        fuser = MultimodalFuser(text_embedder=embedder)
        return MemoryIngester(indexer=indexer, text_embedder=embedder, fuser=fuser)
    
    @pytest.mark.asyncio
    async def test_summary_from_transcript(self, ingester):
        """Summary should be generated from transcript."""
        from core.memory.api_schema import MemoryStoreRequest
        
        request = MemoryStoreRequest(transcript="This is a test transcript with some content")
        response = await ingester.ingest(request)
        
        assert len(response.summary) > 0
        assert "test" in response.summary.lower() or "transcript" in response.summary.lower()
    
    @pytest.mark.asyncio
    async def test_summary_truncation(self, ingester):
        """Long transcripts should be truncated in summary."""
        from core.memory.api_schema import MemoryStoreRequest
        
        long_text = "A" * 500
        request = MemoryStoreRequest(transcript=long_text)
        response = await ingester.ingest(request)
        
        assert len(response.summary) <= 250  # Should be truncated
    
    @pytest.mark.asyncio
    async def test_summary_from_obstacles(self, ingester):
        """Summary should include obstacle info."""
        from core.memory.api_schema import MemoryStoreRequest
        
        request = MemoryStoreRequest(
            scene_graph={
                "obstacles": [{"class": "car"}, {"class": "bicycle"}]
            }
        )
        response = await ingester.ingest(request)
        
        assert "Obstacles" in response.summary or "car" in response.summary.lower()
