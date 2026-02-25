"""Unit tests for MemoryRetriever MVP behaviors."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import cast

import numpy as np
from _pytest.monkeypatch import MonkeyPatch

from core.memory.api_schema import MemorySearchRequest
from core.memory.config import MemoryConfig
from core.memory.embeddings import TextEmbedder
from core.memory.indexer import FAISSIndexer, IndexMetadata, SearchResult
from core.memory.retriever import MemoryRetriever


class StubEmbedder:
    """Simple text embedder mock returning a fixed vector."""

    def __init__(self, embedding: np.ndarray) -> None:
        self._embedding: np.ndarray = embedding

    def embed(self, data: object) -> np.ndarray:
        _ = data
        return self._embedding


class StaticIndexer:
    """Mock indexer returning predefined results."""

    def __init__(self, results: list[SearchResult]) -> None:
        self._results: list[SearchResult] = results
        self.size: int = len(results)

    def search(
        self,
        query: np.ndarray,
        k: int = 5,
        time_window_days: int | None = None,
        session_id: str | None = None,
    ) -> list[SearchResult]:
        _ = (query, time_window_days, session_id)
        return self._results[:k]

class DistanceIndexer:
    """Mock indexer scoring by L2 distance."""

    def __init__(self, vectors: dict[str, np.ndarray], summaries: dict[str, str]) -> None:
        self._vectors: dict[str, np.ndarray] = vectors
        self._summaries: dict[str, str] = summaries
        self.size: int = len(vectors)

    def search(
        self,
        query: np.ndarray,
        k: int = 5,
        time_window_days: int | None = None,
        session_id: str | None = None,
    ) -> list[SearchResult]:
        _ = (time_window_days, session_id)
        results: list[SearchResult] = []
        for idx, (memory_id, vec) in enumerate(self._vectors.items()):
            dist = float(np.linalg.norm(query - vec))
            score = 1.0 / (1.0 + dist)
            metadata = _make_metadata(memory_id, self._summaries[memory_id], idx)
            results.append(SearchResult(id=memory_id, score=score, metadata=metadata))
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:k]

def _make_metadata(memory_id: str, summary: str, vector_idx: int) -> IndexMetadata:
    return IndexMetadata(
        id=memory_id,
        timestamp="2024-01-01T00:00:00Z",
        expiry="",
        summary=summary,
        session_id=None,
        user_label=None,
        scene_graph_ref=None,
        vector_idx=vector_idx,
    )


def _make_result(memory_id: str, score: float, summary: str, vector_idx: int) -> SearchResult:
    return SearchResult(id=memory_id, score=score, metadata=_make_metadata(memory_id, summary, vector_idx))


def _as_indexer(value: object) -> FAISSIndexer:
    return cast(FAISSIndexer, value)


def _as_embedder(value: object) -> TextEmbedder:
    return cast(TextEmbedder, value)


async def test_score_normalization_l2_to_cosine() -> None:
    query = np.array([1.0, 0.0], dtype=np.float32)
    vectors = {
        "mem_close": np.array([1.0, 0.0], dtype=np.float32),
        "mem_far": np.array([0.0, 1.0], dtype=np.float32),
    }
    summaries = {"mem_close": "Close match", "mem_far": "Far match"}

    indexer: object = DistanceIndexer(vectors=vectors, summaries=summaries)
    retriever = MemoryRetriever(
        indexer=_as_indexer(indexer),
        text_embedder=_as_embedder(StubEmbedder(query)),
        config=MemoryConfig(similarity_threshold=0.0),
    )

    results = await retriever.search_by_embedding(query, k=2)

    assert len(results) == 2
    assert all(0.0 <= result.score <= 1.0 for result in results)
    assert results[0].score > results[1].score


async def test_deduplication_removes_summary_duplicates() -> None:
    results = [
        _make_result("mem_1", 0.9, "Keys on table", 0),
        _make_result("mem_2", 0.8, "  keys on table  ", 1),
        _make_result("mem_3", 0.7, "Door open", 2),
    ]
    indexer: object = StaticIndexer(results)
    retriever = MemoryRetriever(
        indexer=_as_indexer(indexer),
        text_embedder=_as_embedder(StubEmbedder(np.zeros(2, dtype=np.float32))),
        config=MemoryConfig(similarity_threshold=0.0),
    )

    deduped = await retriever.search_by_embedding(np.zeros(2, dtype=np.float32), k=5)

    summaries = [result.metadata.summary.strip().lower() for result in deduped]
    assert len(deduped) == 2
    assert summaries.count("keys on table") == 1


async def test_deduplication_keeps_highest_score() -> None:
    results = [
        _make_result("mem_low", 0.25, "Same summary", 0),
        _make_result("mem_high", 0.95, " same summary ", 1),
    ]
    indexer: object = StaticIndexer(results)
    retriever = MemoryRetriever(
        indexer=_as_indexer(indexer),
        text_embedder=_as_embedder(StubEmbedder(np.zeros(2, dtype=np.float32))),
        config=MemoryConfig(similarity_threshold=0.0),
    )

    deduped = await retriever.search_by_embedding(np.zeros(2, dtype=np.float32), k=5)

    assert len(deduped) == 1
    assert deduped[0].id == "mem_high"


async def test_search_does_not_block_event_loop(monkeypatch: MonkeyPatch) -> None:
    calls: list[tuple[object, str]] = []

    async def fake_to_thread(
        func: Callable[..., object],
        *args: object,
        **kwargs: object,
    ) -> object:
        bound_self = cast(object, getattr(func, "__self__", None))
        call_name = str(getattr(func, "__name__", ""))
        calls.append((bound_self, call_name))
        return func(*args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)

    embedding = np.array([1.0, 0.0], dtype=np.float32)
    embedder: object = StubEmbedder(embedding)
    indexer: object = StaticIndexer([_make_result("mem_1", 0.9, "One", 0)])
    retriever = MemoryRetriever(
        indexer=_as_indexer(indexer),
        text_embedder=_as_embedder(embedder),
        config=MemoryConfig(similarity_threshold=0.0),
    )

    response = await retriever.search(
        MemorySearchRequest(
            query="hello",
            k=1,
            time_window_days=None,
            session_id=None,
            include_scene_graph=False,
        )
    )

    assert response.results
    assert len(calls) == 2
    assert calls[0] == (embedder, "embed")
    assert calls[1] == (indexer, "search")


async def test_search_with_empty_index_returns_empty() -> None:
    indexer: object = StaticIndexer([])
    retriever = MemoryRetriever(
        indexer=_as_indexer(indexer),
        text_embedder=_as_embedder(StubEmbedder(np.zeros(2, dtype=np.float32))),
        config=MemoryConfig(similarity_threshold=0.0),
    )

    response = await retriever.search(
        MemorySearchRequest(
            query="empty",
            k=3,
            time_window_days=None,
            session_id=None,
            include_scene_graph=False,
        )
    )

    assert response.results == []
    assert response.total_searched == 0
