# pyright: reportMissingTypeArgument=false, reportExplicitAny=false
"""Tests for TextEmbedder native async methods (T-044).

Verifies:
- _async_embed_with_retry succeeds on first try
- _async_embed_with_retry retries on transient failure then succeeds
- _async_embed_with_retry raises after max retries exhausted
- async_embed() uses AsyncClient (not thread pool)
- async_embed_batch() uses AsyncClient (not thread pool)
- _ensure_async_client() creates AsyncClient lazily
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from core.memory.embeddings import TextEmbedder

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FAKE_DIM = 8
FAKE_VECTOR = [float(i) for i in range(FAKE_DIM)]
FAKE_BATCH_VECTORS = [FAKE_VECTOR, [float(i + 1) for i in range(FAKE_DIM)]]


def _make_embed_response(vectors: Any = None) -> dict:
    """Build a dict that mimics an Ollama embed response."""
    if vectors is None:
        vectors = [FAKE_VECTOR]
    return {"embeddings": vectors}


@pytest.fixture
def embedder() -> TextEmbedder:
    """Create a TextEmbedder without triggering real Ollama init."""
    e = TextEmbedder.__new__(TextEmbedder)
    e._model_name = "test-model"
    e._client = None
    e._async_client = None
    e._ready = False
    e._dimension = None
    e._MAX_RETRIES = 3
    e._BACKOFF_BASE = 0.0  # Zero backoff for fast tests
    return e


# ---------------------------------------------------------------------------
# _ensure_async_client
# ---------------------------------------------------------------------------


class TestEnsureAsyncClient:
    """Verify lazy creation of ollama.AsyncClient."""

    def test_creates_client_on_first_call(self, embedder: TextEmbedder) -> None:
        mock_async_cls = MagicMock()
        mock_instance = MagicMock()
        mock_async_cls.return_value = mock_instance

        with patch.dict("sys.modules", {"ollama": MagicMock(AsyncClient=mock_async_cls)}):
            result = embedder._ensure_async_client()

        assert result is not None
        assert embedder._async_client is not None

    def test_returns_existing_client_on_second_call(self, embedder: TextEmbedder) -> None:
        sentinel = MagicMock()
        embedder._async_client = sentinel
        result = embedder._ensure_async_client()
        assert result is sentinel

    def test_raises_import_error_when_ollama_missing(self, embedder: TextEmbedder) -> None:
        with patch.dict("sys.modules", {"ollama": None}):
            with pytest.raises((ImportError, ModuleNotFoundError)):
                embedder._ensure_async_client()


# ---------------------------------------------------------------------------
# _async_embed_with_retry
# ---------------------------------------------------------------------------


class TestAsyncEmbedWithRetry:
    """Verify retry logic with exponential backoff."""

    async def test_succeeds_first_try(self, embedder: TextEmbedder) -> None:
        mock_ac = AsyncMock()
        mock_ac.embed.return_value = _make_embed_response()

        result = await embedder._async_embed_with_retry(mock_ac, "hello")
        assert result == _make_embed_response()
        assert mock_ac.embed.await_count == 1

    async def test_retries_on_transient_failure(self, embedder: TextEmbedder) -> None:
        mock_ac = AsyncMock()
        mock_ac.embed.side_effect = [
            ConnectionError("server down"),
            _make_embed_response(),
        ]

        result = await embedder._async_embed_with_retry(mock_ac, "hello")
        assert result == _make_embed_response()
        assert mock_ac.embed.await_count == 2

    async def test_raises_after_max_retries(self, embedder: TextEmbedder) -> None:
        mock_ac = AsyncMock()
        mock_ac.embed.side_effect = ConnectionError("still down")

        with pytest.raises(ConnectionError, match="still down"):
            await embedder._async_embed_with_retry(mock_ac, "hello")

        assert mock_ac.embed.await_count == embedder._MAX_RETRIES

    async def test_passes_model_and_input(self, embedder: TextEmbedder) -> None:
        mock_ac = AsyncMock()
        mock_ac.embed.return_value = _make_embed_response()

        await embedder._async_embed_with_retry(mock_ac, ["text1", "text2"])
        mock_ac.embed.assert_awaited_once_with(model="test-model", input=["text1", "text2"])


# ---------------------------------------------------------------------------
# async_embed (single text)
# ---------------------------------------------------------------------------


class TestAsyncEmbed:
    """Verify async_embed() uses AsyncClient natively."""

    async def test_uses_async_client(self, embedder: TextEmbedder) -> None:
        mock_ac = AsyncMock()
        mock_ac.embed.return_value = _make_embed_response()
        embedder._async_client = mock_ac

        result = await embedder.async_embed("hello world")

        assert isinstance(result, np.ndarray)
        assert result.dtype == np.float32
        mock_ac.embed.assert_awaited_once()

    async def test_normalizes_output(self, embedder: TextEmbedder) -> None:
        mock_ac = AsyncMock()
        mock_ac.embed.return_value = _make_embed_response()
        embedder._async_client = mock_ac

        result = await embedder.async_embed("hello")
        norm = np.linalg.norm(result)
        assert abs(norm - 1.0) < 1e-5 or norm == 0.0

    async def test_updates_dimension(self, embedder: TextEmbedder) -> None:
        mock_ac = AsyncMock()
        mock_ac.embed.return_value = _make_embed_response()
        embedder._async_client = mock_ac

        assert embedder._dimension is None
        await embedder.async_embed("hello")
        assert embedder._dimension == FAKE_DIM

    async def test_sets_ready_flag(self, embedder: TextEmbedder) -> None:
        mock_ac = AsyncMock()
        mock_ac.embed.return_value = _make_embed_response()
        embedder._async_client = mock_ac

        assert not embedder._ready
        await embedder.async_embed("hello")
        assert embedder._ready

    async def test_truncates_long_text(self, embedder: TextEmbedder) -> None:
        mock_ac = AsyncMock()
        mock_ac.embed.return_value = _make_embed_response()
        embedder._async_client = mock_ac

        long_text = "x" * 1000
        await embedder.async_embed(long_text)

        # Verify the input was truncated to 512 chars
        call_args = mock_ac.embed.call_args
        input_text = call_args.kwargs.get("input", call_args[1].get("input", ""))
        assert len(input_text) == 512


# ---------------------------------------------------------------------------
# async_embed_batch
# ---------------------------------------------------------------------------


class TestAsyncEmbedBatch:
    """Verify async_embed_batch() uses AsyncClient natively."""

    async def test_uses_async_client(self, embedder: TextEmbedder) -> None:
        mock_ac = AsyncMock()
        mock_ac.embed.return_value = _make_embed_response(FAKE_BATCH_VECTORS)
        embedder._async_client = mock_ac

        result = await embedder.async_embed_batch(["hello", "world"])

        assert isinstance(result, np.ndarray)
        assert result.shape == (2, FAKE_DIM)
        mock_ac.embed.assert_awaited_once()

    async def test_does_not_use_thread_pool(self, embedder: TextEmbedder) -> None:
        mock_ac = AsyncMock()
        mock_ac.embed.return_value = _make_embed_response(FAKE_BATCH_VECTORS)
        embedder._async_client = mock_ac

        with patch("asyncio.get_running_loop") as mock_loop:
            await embedder.async_embed_batch(["a", "b"])
            # Should NOT call run_in_executor
            if mock_loop.return_value.run_in_executor.called:
                pytest.fail("async_embed_batch should NOT use run_in_executor")

    async def test_normalizes_all_vectors(self, embedder: TextEmbedder) -> None:
        mock_ac = AsyncMock()
        mock_ac.embed.return_value = _make_embed_response(FAKE_BATCH_VECTORS)
        embedder._async_client = mock_ac

        result = await embedder.async_embed_batch(["a", "b"])

        for row in result:
            norm = np.linalg.norm(row)
            assert abs(norm - 1.0) < 1e-5 or norm == 0.0

    async def test_updates_dimension_and_ready(self, embedder: TextEmbedder) -> None:
        mock_ac = AsyncMock()
        mock_ac.embed.return_value = _make_embed_response(FAKE_BATCH_VECTORS)
        embedder._async_client = mock_ac

        assert embedder._dimension is None
        assert not embedder._ready

        await embedder.async_embed_batch(["hello", "world"])

        assert embedder._dimension == FAKE_DIM
        assert embedder._ready

    async def test_cleans_and_truncates_input(self, embedder: TextEmbedder) -> None:
        mock_ac = AsyncMock()
        mock_ac.embed.return_value = _make_embed_response(FAKE_BATCH_VECTORS)
        embedder._async_client = mock_ac

        await embedder.async_embed_batch(["  padded  ", "x" * 1000])

        call_args = mock_ac.embed.call_args
        input_list = call_args.kwargs.get("input", call_args[1].get("input", []))
        assert input_list[0] == "padded"
        assert len(input_list[1]) == 512
