# pyright: reportDeprecated=false, reportUnannotatedClassAttribute=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownLambdaType=false, reportExplicitAny=false, reportPrivateUsage=false, reportUnusedVariable=false
"""
Memory Engine - Retriever Module
==================================

Vector search API for memory retrieval.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

from .api_schema import (
    EmbeddingStatus,
    MemoryHit,
    MemoryRecord,
    MemorySearchRequest,
    MemorySearchResponse,
    PrivacyFlag,
)
from .config import MemoryConfig, get_memory_config
from .embeddings import TextEmbedder, create_embedders
from .indexer import FAISSIndexer, SearchResult

logger = logging.getLogger("memory-retriever")


class MemoryRetriever:
    """Search and retrieve memories from the FAISS index.

    Supports:
    - Text query embedding and similarity search
    - Time window filtering
    - Session filtering
    - Score thresholding

    Usage:
        retriever = MemoryRetriever(indexer=indexer, text_embedder=embedder)
        results = await retriever.search(MemorySearchRequest(query="my keys", k=5))
    """

    def __init__(
        self,
        indexer: FAISSIndexer,
        text_embedder: Optional[TextEmbedder] = None,
        config: Optional[MemoryConfig] = None,
    ):
        self._indexer = indexer
        self._config = config or get_memory_config()

        if text_embedder is None:
            text, _, _, _ = create_embedders(self._config)
            self._text_embedder = text
        else:
            self._text_embedder = text_embedder

        # Telemetry
        self._search_count = 0
        self._total_search_time_ms = 0.0

    def _normalize_score(self, raw_score: float) -> float:
        """Clamp raw score to a 0-1 cosine similarity range."""
        return max(0.0, min(1.0, raw_score))

    def _deduplicate(self, results: List[SearchResult]) -> List[SearchResult]:
        """Deduplicate results by normalized summary while keeping top scores."""
        deduped: Dict[str, SearchResult] = {}
        for result in results:
            summary_key = (result.metadata.summary or "").strip().lower()
            existing = deduped.get(summary_key)
            if existing is None or result.score > existing.score:
                deduped[summary_key] = result
        return sorted(deduped.values(), key=lambda r: r.score, reverse=True)

    async def search(
        self,
        request: MemorySearchRequest,
    ) -> MemorySearchResponse:
        """Search memories by text query.

        Args:
            request: Search request with query and filters

        Returns:
            MemorySearchResponse with matching memories
        """
        start_time = time.time()

        try:
            # Embed query
            query_embedding = await asyncio.to_thread(self._text_embedder.embed, request.query)

            # Search index
            raw_results = await asyncio.to_thread(
                self._indexer.search,
                query=query_embedding,
                k=request.k * 2,
                time_window_days=request.time_window_days,
                session_id=request.session_id,
            )

            normalized_results = [
                SearchResult(
                    id=result.id,
                    score=self._normalize_score(result.score),
                    metadata=result.metadata,
                )
                for result in raw_results
            ]
            deduped_results = self._deduplicate(normalized_results)

            # Convert to response format
            hits = []
            for result in deduped_results:
                # Apply score threshold
                if result.score < self._config.similarity_threshold:
                    continue

                hit = MemoryHit(
                    id=result.id,
                    timestamp=result.metadata.timestamp,
                    summary=result.metadata.summary,
                    score=round(result.score, 4),
                    scene_graph_ref=result.metadata.scene_graph_ref,
                    user_label=result.metadata.user_label,
                    scene_graph=None,
                )

                # Include scene graph if requested
                if request.include_scene_graph:
                    # In production, load from storage
                    hit.scene_graph = None  # Placeholder

                hits.append(hit)
                if len(hits) >= request.k:
                    break

            total_time_ms = (time.time() - start_time) * 1000

            # Update telemetry
            self._search_count += 1
            self._total_search_time_ms += total_time_ms

            logger.debug(
                f"Search completed: query='{request.query[:50]}...' results={len(hits)} time={total_time_ms:.1f}ms"
            )

            return MemorySearchResponse(
                query=request.query,
                results=hits,
                total_searched=self._indexer.size,
                search_time_ms=total_time_ms,
            )

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return MemorySearchResponse(
                query=request.query,
                results=[],
                total_searched=0,
                search_time_ms=(time.time() - start_time) * 1000,
            )

    async def search_by_embedding(
        self,
        embedding: np.ndarray,
        k: int = 5,
        time_window_days: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> List[SearchResult]:
        """Search by pre-computed embedding vector.

        Lower-level API for direct vector search.

        Args:
            embedding: Query embedding
            k: Number of results
            time_window_days: Optional time filter
            session_id: Optional session filter

        Returns:
            List of SearchResult
        """
        raw_results = await asyncio.to_thread(
            self._indexer.search,
            query=embedding,
            k=k,
            time_window_days=time_window_days,
            session_id=session_id,
        )
        normalized_results = [
            SearchResult(
                id=result.id,
                score=self._normalize_score(result.score),
                metadata=result.metadata,
            )
            for result in raw_results
        ]
        return self._deduplicate(normalized_results)

    def get_memory(self, memory_id: str) -> Optional[MemoryRecord]:
        """Get a specific memory by ID.

        Args:
            memory_id: Memory ID

        Returns:
            MemoryRecord or None
        """
        metadata = self._indexer.get(memory_id)
        if metadata is None:
            return None

        return MemoryRecord(
            id=metadata.id,
            timestamp=metadata.timestamp,
            expiry=metadata.expiry,
            summary=metadata.summary,
            transcript=None,
            scene_graph=None,
            scene_graph_ref=metadata.scene_graph_ref,
            user_label=metadata.user_label,
            device_id=None,
            session_id=metadata.session_id,
            embedding_status=EmbeddingStatus.PENDING,
            privacy_flag=PrivacyFlag.NORMAL,
            has_raw_image=False,
            has_raw_audio=False,
            vector_dim=None,
        )

    def get_session_memories(
        self,
        session_id: str,
        limit: int = 50,
    ) -> List[MemoryRecord]:
        """Get all memories for a session.

        Args:
            session_id: Session ID
            limit: Maximum results

        Returns:
            List of MemoryRecord sorted by timestamp (newest first)
        """
        # Search with a dummy query to get session memories
        # In production, we'd have a separate session index

        records = []
        for idx, meta in self._indexer._metadata.items():
            if meta.session_id == session_id:
                records.append(
                    MemoryRecord(
                        id=meta.id,
                        timestamp=meta.timestamp,
                        expiry=meta.expiry,
                        summary=meta.summary,
                        transcript=None,
                        scene_graph=None,
                        scene_graph_ref=meta.scene_graph_ref,
                        user_label=meta.user_label,
                        device_id=None,
                        session_id=meta.session_id,
                        embedding_status=EmbeddingStatus.PENDING,
                        privacy_flag=PrivacyFlag.NORMAL,
                        has_raw_image=False,
                        has_raw_audio=False,
                        vector_dim=None,
                    )
                )

        # Sort by timestamp (newest first)
        records.sort(key=lambda r: r.timestamp, reverse=True)

        return records[:limit]

    def get_recent_memories(
        self,
        hours: float = 24.0,
        limit: int = 20,
    ) -> List[MemoryRecord]:
        """Get memories from the last N hours.

        Args:
            hours: Time window in hours
            limit: Maximum results

        Returns:
            List of MemoryRecord sorted by timestamp (newest first)
        """
        now = datetime.utcnow()
        cutoff = now.timestamp() - (hours * 3600)

        records = []
        for idx, meta in self._indexer._metadata.items():
            try:
                ts = datetime.fromisoformat(meta.timestamp.replace("Z", "+00:00"))
                if ts.timestamp() >= cutoff:
                    records.append(
                        MemoryRecord(
                            id=meta.id,
                            timestamp=meta.timestamp,
                            expiry=meta.expiry,
                            summary=meta.summary,
                            transcript=None,
                            scene_graph=None,
                            scene_graph_ref=meta.scene_graph_ref,
                            user_label=meta.user_label,
                            device_id=None,
                            session_id=meta.session_id,
                        embedding_status=EmbeddingStatus.PENDING,
                        privacy_flag=PrivacyFlag.NORMAL,
                            has_raw_image=False,
                            has_raw_audio=False,
                            vector_dim=None,
                        )
                    )
            except (ValueError, AttributeError):
                continue

        records.sort(key=lambda r: r.timestamp, reverse=True)
        return records[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """Get retrieval statistics."""
        avg_time = self._total_search_time_ms / self._search_count if self._search_count > 0 else 0

        return {
            "total_searches": self._search_count,
            "avg_search_time_ms": round(avg_time, 2),
            "index_size": self._indexer.size,
        }
