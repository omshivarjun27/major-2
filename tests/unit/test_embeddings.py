"""
Unit Tests for Memory Engine - Embeddings Module
"""

import numpy as np
import pytest


class TestMockTextEmbedder:
    """Test MockTextEmbedder for deterministic embeddings."""

    def test_embed_returns_correct_dimension(self):
        """Embedding should have correct dimension."""
        from core.memory.embeddings import MockTextEmbedder

        embedder = MockTextEmbedder(dimension=384)
        emb = embedder.embed("Hello world")

        assert emb.shape == (384,)
        assert emb.dtype == np.float32

    def test_embed_is_normalized(self):
        """Embedding should be L2 normalized."""
        from core.memory.embeddings import MockTextEmbedder

        embedder = MockTextEmbedder(dimension=384)
        emb = embedder.embed("Test text")

        norm = np.linalg.norm(emb)
        assert abs(norm - 1.0) < 0.01  # Should be unit normalized

    def test_embed_is_deterministic(self):
        """Same text should produce same embedding."""
        from core.memory.embeddings import MockTextEmbedder

        embedder = MockTextEmbedder(dimension=384)
        emb1 = embedder.embed("Deterministic test")
        emb2 = embedder.embed("Deterministic test")

        assert np.allclose(emb1, emb2)

    def test_different_texts_produce_different_embeddings(self):
        """Different texts should produce different embeddings."""
        from core.memory.embeddings import MockTextEmbedder

        embedder = MockTextEmbedder(dimension=384)
        emb1 = embedder.embed("First text")
        emb2 = embedder.embed("Second text")

        assert not np.allclose(emb1, emb2)

    def test_embed_batch(self):
        """Batch embedding should return correct shape."""
        from core.memory.embeddings import MockTextEmbedder

        embedder = MockTextEmbedder(dimension=384)
        texts = ["Text one", "Text two", "Text three"]
        embeddings = embedder.embed_batch(texts)

        assert embeddings.shape == (3, 384)

    def test_is_ready(self):
        """Mock embedder should always be ready."""
        from core.memory.embeddings import MockTextEmbedder

        embedder = MockTextEmbedder()
        assert embedder.is_ready is True


class TestMultimodalFuser:
    """Test MultimodalFuser for combining embeddings."""

    def test_fuse_text_only(self):
        """Should handle text-only input."""
        from core.memory.embeddings import MockTextEmbedder, MultimodalFuser

        text_emb = MockTextEmbedder(dimension=384)
        fuser = MultimodalFuser(text_embedder=text_emb)

        result = fuser.fuse(text="Test text")

        assert result.shape == (384,)
        assert np.any(result)  # Should have non-zero values

    def test_fuse_returns_normalized(self):
        """Fused embedding should be normalized."""
        from core.memory.embeddings import MockTextEmbedder, MultimodalFuser

        text_emb = MockTextEmbedder(dimension=384)
        fuser = MultimodalFuser(text_embedder=text_emb)

        result = fuser.fuse(text="Normalize me")
        norm = np.linalg.norm(result)

        assert abs(norm - 1.0) < 0.01

    def test_fuse_no_input_returns_zeros(self):
        """Empty input should return zeros."""
        from core.memory.embeddings import MockTextEmbedder, MultimodalFuser

        text_emb = MockTextEmbedder(dimension=384)
        fuser = MultimodalFuser(text_embedder=text_emb)

        result = fuser.fuse()  # No inputs

        assert result.shape == (384,)
        assert np.allclose(result, 0)

    def test_dimension_property(self):
        """Should report correct output dimension."""
        from core.memory.embeddings import MockTextEmbedder, MultimodalFuser

        text_emb = MockTextEmbedder(dimension=384)
        fuser = MultimodalFuser(text_embedder=text_emb, fusion_method="average")

        assert fuser.dimension == 384


class TestTextEmbedderLazyLoad:
    """Test TextEmbedder lazy loading behavior."""

    def test_embedder_not_ready_before_use(self):
        """Embedder should not be ready until model is loaded."""
        from core.memory.embeddings import TextEmbedder

        embedder = TextEmbedder()
        # Before calling embed, _ready should be False
        assert embedder._ready is False

    def test_dimension_property_triggers_load(self):
        """Accessing dimension should trigger client load."""
        pytest.importorskip("ollama")
        from unittest.mock import MagicMock, patch

        from core.memory.embeddings import TextEmbedder

        mock_ollama = MagicMock()
        mock_ollama.embed.return_value = {"embeddings": [[0.1] * 128]}

        with patch("core.memory.embeddings._get_ollama_client", return_value=mock_ollama):
            embedder = TextEmbedder()
            dim = embedder.dimension

            assert dim > 0
            assert embedder.is_ready
