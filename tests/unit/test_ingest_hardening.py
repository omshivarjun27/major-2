"""
Tests for Memory Ingest Hardening (T-021)
==========================================

Validates input validation, hash-based dedup, batch ingestion,
and error recovery in MemoryIngester.
"""

import numpy as np
import pytest

from core.memory.api_schema import EmbeddingStatus, MemoryStoreRequest
from core.memory.ingest import BatchIngestResult, MemoryIngester

# ============================================================================
# Shared Mocks
# ============================================================================


class StubTextEmbedder:
    """Minimal TextEmbedder returning fixed-dimension vectors."""

    dimension = 128

    def embed(self, text: str) -> np.ndarray:
        return np.random.randn(self.dimension).astype(np.float32)


class StubFuser:
    """Minimal MultimodalFuser returning fixed-dimension vectors."""

    async def async_fuse(self, *, text=None, image=None, audio=None, audio_transcript=None) -> np.ndarray:
        return np.random.randn(128).astype(np.float32)


class StubIndexer:
    """In-memory FAISS indexer replacement for testing."""

    def __init__(self):
        self.entries: dict = {}
        self.size = 0

    def add(self, *, id, embedding, timestamp, expiry, summary, session_id=None, user_label=None, scene_graph_ref=None):
        self.entries[id] = {
            "embedding": embedding,
            "timestamp": timestamp,
            "expiry": expiry,
            "summary": summary,
            "session_id": session_id,
            "user_label": user_label,
            "scene_graph_ref": scene_graph_ref,
        }
        self.size = len(self.entries)


class StubConfig:
    """Minimal MemoryConfig stub."""

    retention_days = 30
    telemetry_enabled = False
    image_embedding_enabled = False
    audio_embedding_enabled = False
    save_raw_media = False
    index_path = "data/test_memory_index"

    def ensure_index_dir(self):
        from pathlib import Path

        p = Path(self.index_path)
        p.mkdir(parents=True, exist_ok=True)
        return p


class BrokenFuser:
    """Fuser that always raises."""

    async def async_fuse(self, **kwargs) -> np.ndarray:
        raise RuntimeError("Fuser exploded")


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def ingester(tmp_path):
    """Create a MemoryIngester with stub components and a temp consent dir."""
    config = StubConfig()
    config.index_path = str(tmp_path / "memory_index")
    return MemoryIngester(
        indexer=StubIndexer(),
        text_embedder=StubTextEmbedder(),
        fuser=StubFuser(),
        config=config,
    )


@pytest.fixture
def broken_ingester(tmp_path):
    """Create a MemoryIngester whose fuser always fails."""
    config = StubConfig()
    config.index_path = str(tmp_path / "memory_index")
    return MemoryIngester(
        indexer=StubIndexer(),
        text_embedder=StubTextEmbedder(),
        fuser=BrokenFuser(),
        config=config,
    )


def _make_request(**overrides) -> MemoryStoreRequest:
    """Helper to build a MemoryStoreRequest with defaults."""
    defaults = {
        "transcript": "I left my keys on the table",
        "image_base64": None,
        "audio_base64": None,
        "scene_graph": None,
        "user_label": None,
        "session_id": "sess_test",
        "save_raw": False,
    }
    defaults.update(overrides)
    return MemoryStoreRequest(**defaults)


# ============================================================================
# Tests
# ============================================================================


class TestIngestValidation:
    """Tests for input validation (T-021 Steps 1 & 4)."""

    async def test_reject_empty_request(self, ingester):
        """Reject requests with no transcript, image, audio, or scene_graph."""
        req = _make_request(transcript=None, image_base64=None, audio_base64=None, scene_graph=None)
        resp = await ingester.ingest(req)

        assert resp.embedding_status == EmbeddingStatus.REJECTED, (
            f"Empty request should be REJECTED, got {resp.embedding_status}"
        )
        assert "no content" in resp.summary.lower()

    async def test_reject_oversized_transcript(self, ingester):
        """Reject transcripts exceeding 50000 chars."""
        # Use model_construct to bypass Pydantic's max_length=10000 on the field,
        # so we can test our own 50K validation gate in _validate_request.
        req = MemoryStoreRequest.model_construct(
            transcript="x" * 50_001,
            image_base64=None,
            audio_base64=None,
            scene_graph=None,
            user_label=None,
            session_id="sess_test",
            save_raw=False,
        )
        resp = await ingester.ingest(req)

        assert resp.embedding_status == EmbeddingStatus.REJECTED
        assert "too long" in resp.summary.lower()

    async def test_reject_oversized_image(self, ingester):
        """Reject base64 image strings exceeding 6MB."""
        req = _make_request(transcript=None, image_base64="A" * 6_000_001)
        resp = await ingester.ingest(req)

        assert resp.embedding_status == EmbeddingStatus.REJECTED
        assert "too large" in resp.summary.lower()


class TestIngestDedup:
    """Tests for hash-based deduplication (T-021 Step 2)."""

    async def test_dedup_returns_existing_id(self, ingester):
        """Second identical request returns DEDUPLICATED with original ID."""
        req = _make_request(transcript="Duplicate content here")

        first = await ingester.ingest(req)
        assert first.embedding_status == EmbeddingStatus.COMPLETED
        first_id = first.id

        second = await ingester.ingest(req)
        assert second.embedding_status == EmbeddingStatus.DEDUPLICATED, (
            f"Duplicate should be DEDUPLICATED, got {second.embedding_status}"
        )
        assert second.id == first_id, "Duplicate should return the original memory ID"

    async def test_dedup_different_content_creates_new(self, ingester):
        """Similar but different content creates a new entry."""
        req1 = _make_request(transcript="Keys on the kitchen table")
        req2 = _make_request(transcript="Keys on the bedroom table")

        first = await ingester.ingest(req1)
        second = await ingester.ingest(req2)

        assert first.embedding_status == EmbeddingStatus.COMPLETED
        assert second.embedding_status == EmbeddingStatus.COMPLETED
        assert first.id != second.id, "Different content should create separate entries"


class TestIngestBatch:
    """Tests for batch ingestion (T-021 Step 3)."""

    async def test_batch_ingest_partial_success(self, ingester):
        """Batch with mix of valid and invalid items reports partial success."""
        requests = [
            _make_request(transcript="Valid memory 1"),
            _make_request(transcript=None, image_base64=None, audio_base64=None, scene_graph=None),  # empty
            _make_request(transcript="Valid memory 2"),
        ]

        result = await ingester.ingest_batch(requests, consent_given=False)

        assert isinstance(result, BatchIngestResult)
        assert result.total == 3
        assert result.succeeded == 2, f"Expected 2 successes, got {result.succeeded}"
        assert result.failed == 1, f"Expected 1 failure, got {result.failed}"
        assert result.total_time_ms >= 0

    async def test_batch_stop_on_error(self, ingester):
        """Batch with stop_on_error=True aborts after first failure."""
        requests = [
            _make_request(transcript="Valid memory"),
            _make_request(transcript=None, image_base64=None, audio_base64=None, scene_graph=None),  # empty
            _make_request(transcript="Should not be reached"),
        ]

        result = await ingester.ingest_batch(requests, consent_given=False, stop_on_error=True)

        assert result.total == 3
        assert result.succeeded == 1, f"Expected 1 success before stop, got {result.succeeded}"
        assert result.failed == 1, f"Expected 1 failure that triggered stop, got {result.failed}"
        # Third request should not have been processed
        processed_count = result.succeeded + result.failed
        assert processed_count == 2, f"Only 2 items should be processed, got {processed_count}"


class TestIngestErrorRecovery:
    """Tests for error recovery (T-021 Step 4)."""

    async def test_failed_ingestion_does_not_store_zero_vector(self, broken_ingester):
        """Failed ingestions should NOT pollute the index with zero-vector entries."""
        indexer = broken_ingester._indexer
        initial_size = indexer.size

        req = _make_request(transcript="This will fail at embedding")
        resp = await broken_ingester.ingest(req)

        assert resp.embedding_status == EmbeddingStatus.FAILED
        assert indexer.size == initial_size, f"Index should not grow on failure. Was {initial_size}, now {indexer.size}"
