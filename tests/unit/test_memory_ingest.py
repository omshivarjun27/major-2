"""
Unit Tests for Memory Engine - Ingest Module
"""

from datetime import datetime

import pytest


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
        from core.memory.api_schema import EmbeddingStatus, MemoryStoreRequest

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
        import time

        from core.memory.api_schema import MemoryStoreRequest

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
        from core.memory.embeddings import MockTextEmbedder, MultimodalFuser
        from core.memory.indexer import MockFAISSIndexer
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
        from core.memory.embeddings import MockTextEmbedder, MultimodalFuser
        from core.memory.indexer import MockFAISSIndexer
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


class TestConsentPersistence:
    """Tests for consent at-rest persistence."""

    @pytest.fixture
    def consent_ingester(self, tmp_path, monkeypatch):
        """Create a MemoryIngester with a temporary consent directory."""
        monkeypatch.setenv("MEMORY_ENCRYPTION_KEY", "test-consent-key")
        from shared.utils.encryption import reset_encryption_manager
        reset_encryption_manager()

        from unittest.mock import MagicMock
        mock_indexer = MagicMock()
        mock_indexer.dimension = 768
        mock_indexer.add = MagicMock()
        mock_config = MagicMock()
        mock_config.index_path = str(tmp_path / "memory_index")
        mock_config.save_raw_media = False
        mock_config.max_vectors = 1000
        mock_config.retention_days = 30
        mock_config.enabled = True

        (tmp_path / "memory_index").mkdir(parents=True, exist_ok=True)

        from core.memory.ingest import MemoryIngester
        ingester = MemoryIngester(
            indexer=mock_indexer,
            config=mock_config,
        )
        # Override consent_dir to use tmp_path
        ingester._consent_dir = tmp_path / "consent"
        ingester._consent_dir.mkdir(parents=True, exist_ok=True)
        yield ingester
        reset_encryption_manager()

    def test_consent_persists_to_file(self, consent_ingester):
        """record_consent writes an encrypted file."""
        consent_ingester.record_consent("device-1", opt_in=True, save_raw_media=False)
        consent_file = consent_ingester._consent_dir / "device-1.json"
        assert consent_file.exists(), "Consent file should be persisted"
        raw = consent_file.read_bytes()
        assert b"opt_in" not in raw, "Consent file should be encrypted"

    def test_consent_loaded_on_restart(self, consent_ingester):
        """Consent survives MemoryIngester restart."""
        consent_ingester.record_consent("device-2", opt_in=False, save_raw_media=True, reason="testing")
        consent_ingester._consent_log.clear()
        consent_ingester._load_persisted_consent()
        result = consent_ingester.get_consent("device-2")
        assert result["memory_enabled"] is False
        assert result["save_raw_media"] is True  # raw stored value (gating is in record_consent return)

    def test_tampered_consent_rejected(self, consent_ingester):
        """Tampered consent files are rejected."""
        consent_ingester.record_consent("device-3", opt_in=True, save_raw_media=False)
        consent_file = consent_ingester._consent_dir / "device-3.json"
        data = consent_file.read_bytes()
        consent_file.write_bytes(data[:-5] + b"XXXXX")
        consent_ingester._consent_log.clear()
        consent_ingester._load_persisted_consent()
        assert "device-3" not in consent_ingester._consent_log

    def test_missing_consent_returns_default(self, consent_ingester):
        """Missing consent returns default (opt_in=True, save_raw=False)."""
        result = consent_ingester.get_consent("nonexistent-device")
        assert result["memory_enabled"] is True
        assert result["save_raw_media"] is False

    def test_multiple_devices_separate_files(self, consent_ingester):
        """Multiple device IDs get separate files."""
        consent_ingester.record_consent("device-a", opt_in=True, save_raw_media=True)
        consent_ingester.record_consent("device-b", opt_in=False, save_raw_media=False)
        files = list(consent_ingester._consent_dir.glob("*.json"))
        assert len(files) == 2
        assert consent_ingester.get_consent("device-a")["memory_enabled"] is True
        assert consent_ingester.get_consent("device-b")["memory_enabled"] is False

    def test_get_consent_loads_from_disk_if_not_in_memory(self, consent_ingester):
        """get_consent tries disk when key not in memory."""
        consent_ingester.record_consent("device-disk", opt_in=True, save_raw_media=False)
        del consent_ingester._consent_log["device-disk"]
        result = consent_ingester.get_consent("device-disk")
        assert result["memory_enabled"] is True
