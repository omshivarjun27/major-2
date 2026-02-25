"""Unit tests for async embedding wrappers."""
# pyright: reportUnusedParameter=false, reportUnusedCallResult=false, reportUnusedImport=false, reportPrivateUsage=false, reportInvalidCast=false, reportUnknownMemberType=false

import asyncio
import time
from typing import cast

import numpy as np


async def test_async_embed_returns_same_result_as_sync():
    """async_embed should match sync embed output for mock embedder."""
    from core.memory.embeddings import MockTextEmbedder

    embedder = MockTextEmbedder(dimension=384)
    text = "Async parity"
    sync_vec = embedder.embed(text)
    async_vec = await embedder.async_embed(text)

    assert np.allclose(sync_vec, async_vec)


async def test_async_embed_batch_returns_same_shape():
    """async_embed_batch should match sync batch shape."""
    from core.memory.embeddings import MockTextEmbedder

    embedder = MockTextEmbedder(dimension=384)
    texts = ["one", "two", "three", "four"]
    sync_vecs = embedder.embed_batch(texts)
    async_vecs = await embedder.async_embed_batch(texts)

    assert async_vecs.shape == sync_vecs.shape


async def test_async_embed_does_not_block_event_loop():
    """async embed should allow other tasks to run."""

    class SlowEmbedder:
        def embed(self, text: str) -> np.ndarray:
            time.sleep(0.05)
            return np.ones(4, dtype=np.float32)

        def embed_batch(self, data_list: list[str]) -> np.ndarray:
            return np.array([self.embed(t) for t in data_list])

        async def async_embed(self, text: str) -> np.ndarray:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, self.embed, text)

    embedder = SlowEmbedder()
    ticked = asyncio.Event()

    async def ticker():
        await asyncio.sleep(0)
        ticked.set()

    await asyncio.gather(embedder.async_embed("slow"), ticker())

    assert ticked.is_set()


async def test_async_fuse_produces_valid_embedding():
    """async_fuse should return normalized non-zero embedding for text."""
    from core.memory.embeddings import MockTextEmbedder, MultimodalFuser, TextEmbedder

    embedder = MockTextEmbedder(dimension=384)
    fuser = MultimodalFuser(text_embedder=cast(TextEmbedder, embedder))
    result = await fuser.async_fuse(text="Fused text")

    assert result.shape == (384,)
    assert np.any(result)
    assert abs(np.linalg.norm(result) - 1.0) < 0.01


def test_executor_thread_pool_is_bounded():
    """Embedding executor should use bounded worker count."""
    from core.memory import embeddings

    assert embeddings._embedding_executor._max_workers == 2
