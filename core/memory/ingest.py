# pyright: reportAny=false, reportExplicitAny=false, reportDeprecated=false, reportUnannotatedClassAttribute=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportImplicitStringConcatenation=false, reportUnusedCallResult=false, reportUnusedParameter=false
"""
Memory Engine - Ingest Module
==============================

Multimodal memory ingestion pipeline.
Handles image, audio, text, and scene graph inputs.
"""

import base64
import hashlib
import io
import json
import logging
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from shared.utils.encryption import get_encryption_manager

from .api_schema import (
    EmbeddingStatus,
    MemoryStoreRequest,
    MemoryStoreResponse,
)
from .config import MemoryConfig, get_memory_config
from .embeddings import MultimodalFuser, TextEmbedder, create_embedders
from .indexer import FAISSIndexer

logger = logging.getLogger("memory-ingest")


class IngestValidationError(Exception):
    """Raised when an ingest request fails validation."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


@dataclass
class BatchIngestResult:
    """Result from a batch ingestion."""

    total: int = 0
    succeeded: int = 0
    failed: int = 0
    deduplicated: int = 0
    results: List[MemoryStoreResponse] = field(default_factory=list)
    errors: List[Dict[str, str]] = field(default_factory=list)
    total_time_ms: float = 0.0


class MemoryIngester:
    """Ingest multimodal memories with embedding and indexing.

    Pipeline:
    1. Validate and decode inputs
    2. Generate summary (template-based or LLM)
    3. Compute embeddings
    4. Store in FAISS index with metadata
    5. Optionally persist raw media

    Usage:
        ingester = MemoryIngester(indexer=indexer, fuser=multimodal_fuser)
        response = await ingester.ingest(request)
    """

    def __init__(
        self,
        indexer: FAISSIndexer,
        text_embedder: Optional[TextEmbedder] = None,
        fuser: Optional[MultimodalFuser] = None,
        config: Optional[MemoryConfig] = None,
        llm_client: Optional[Any] = None,
    ):
        self._indexer = indexer
        self._config = config or get_memory_config()
        self._llm_client = llm_client

        # Set up embedders
        if text_embedder is None or fuser is None:
            text, _, _, fuser_default = create_embedders(self._config)
            self._text_embedder = text_embedder or text
            self._fuser = fuser or fuser_default
        else:
            self._text_embedder = text_embedder
            self._fuser = fuser

        # Consent tracking (in production, use persistent storage)
        self._consent_log: dict[str, dict[str, Any]] = {}

        # Consent persistence directory
        self._consent_dir = Path(self._config.index_path).parent / "consent"
        self._consent_dir.mkdir(parents=True, exist_ok=True)
        self._load_persisted_consent()

        # Telemetry
        self._ingest_count = 0
        self._total_ingest_time_ms = 0.0

        # Dedup cache: content_hash -> memory_id (bounded LRU, max 10000)
        self._dedup_cache: OrderedDict[str, str] = OrderedDict()
        self._dedup_cache_max = 10_000

    async def ingest(
        self,
        request: MemoryStoreRequest,
        consent_given: bool = False,
    ) -> MemoryStoreResponse:
        """Ingest a multimodal memory.

        Args:
            request: Store request with multimodal inputs
            consent_given: Whether user has given storage consent

        Returns:
            MemoryStoreResponse with ID and metadata
        """
        start_time = time.time()

        # Generate unique ID
        memory_id = f"mem_{uuid.uuid4().hex[:12]}"
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Calculate expiry
        retention_days = self._config.retention_days
        expiry = (datetime.utcnow() + timedelta(days=retention_days)).isoformat() + "Z"

        # Step 1: Validate input
        try:
            self._validate_request(request)
        except IngestValidationError as e:
            logger.warning("Ingest rejected: %s", e.reason)
            return MemoryStoreResponse(
                id="",
                timestamp=timestamp,
                expiry=expiry,
                summary=f"Rejected: {e.reason}",
                embedding_status=EmbeddingStatus.REJECTED,
                ingest_time_ms=(time.time() - start_time) * 1000,
            )

        # Step 2: Dedup check
        content_hash = self._compute_content_hash(request)
        if content_hash in self._dedup_cache:
            existing_id = self._dedup_cache[content_hash]
            # Move to end (LRU refresh)
            self._dedup_cache.move_to_end(content_hash)
            logger.debug("Dedup hit: content_hash=%s existing_id=%s", content_hash[:16], existing_id)
            return MemoryStoreResponse(
                id=existing_id,
                timestamp=timestamp,
                expiry=expiry,
                summary="Duplicate content (previously ingested)",
                embedding_status=EmbeddingStatus.DEDUPLICATED,
                ingest_time_ms=(time.time() - start_time) * 1000,
            )

        # Step 3: Process
        try:
            # Decode inputs
            image = self._decode_image(request.image_base64) if request.image_base64 else None
            audio = self._decode_audio(request.audio_base64) if request.audio_base64 else None

            # Generate summary
            summary_start = time.time()
            summary = await self._generate_summary(
                transcript=request.transcript,
                scene_graph=request.scene_graph,
                user_label=request.user_label,
            )
            summary_time_ms = (time.time() - summary_start) * 1000

            # Compute embedding
            embed_start = time.time()
            embedding = await self._compute_embedding(
                text=request.transcript or summary,
                image=image,
                audio=audio,
            )
            embed_time_ms = (time.time() - embed_start) * 1000

            # Add to index
            idx_start = time.time()
            self._indexer.add(
                id=memory_id,
                embedding=embedding,
                timestamp=timestamp,
                expiry=expiry,
                summary=summary,
                session_id=request.session_id,
                user_label=request.user_label,
                scene_graph_ref=self._store_scene_graph(memory_id, request.scene_graph),
            )
            idx_time_ms = (time.time() - idx_start) * 1000

            # Store raw media if consented
            if request.save_raw and consent_given:
                await self._store_raw_media(memory_id, request.image_base64, request.audio_base64)

            # Calculate total time
            total_time_ms = (time.time() - start_time) * 1000

            # Update telemetry
            self._ingest_count += 1
            self._total_ingest_time_ms += total_time_ms

            if self._config.telemetry_enabled:
                logger.info(
                    f"Ingest telemetry: id={memory_id} "
                    f"total={total_time_ms:.1f}ms "
                    f"summary={summary_time_ms:.1f}ms "
                    f"embed={embed_time_ms:.1f}ms "
                    f"index={idx_time_ms:.1f}ms"
                )

            # Store hash in dedup cache on success
            self._dedup_cache[content_hash] = memory_id
            if len(self._dedup_cache) > self._dedup_cache_max:
                self._dedup_cache.popitem(last=False)  # Remove oldest entry

            return MemoryStoreResponse(
                id=memory_id,
                timestamp=timestamp,
                expiry=expiry,
                summary=summary,
                embedding_status=EmbeddingStatus.COMPLETED,
                ingest_time_ms=total_time_ms,
                embedding_time_ms=embed_time_ms,
            )

        except Exception as e:
            logger.error(f"Ingest failed for {memory_id}: {e}")

            # Do NOT store zero-vector entries in the index on failure
            total_time_ms = (time.time() - start_time) * 1000

            return MemoryStoreResponse(
                id=memory_id,
                timestamp=timestamp,
                expiry=expiry,
                summary="Error during ingestion",
                embedding_status=EmbeddingStatus.FAILED,
                ingest_time_ms=total_time_ms,
            )

    async def _generate_summary(
        self,
        transcript: Optional[str],
        scene_graph: Optional[dict[str, Any]],
        user_label: Optional[str],
    ) -> str:
        """Generate 1-2 line summary of the memory.

        Uses template-based approach by default.
        Falls back to LLM if configured.
        """
        parts = []

        # User label is highest priority
        if user_label:
            parts.append(user_label)

        # Extract from transcript
        if transcript:
            # Take first 100 chars for summary
            clean = transcript.strip()
            if len(clean) > 100:
                clean = clean[:97] + "..."
            parts.append(clean)

        # Extract from scene graph
        if scene_graph:
            objects = scene_graph.get("objects", [])
            if isinstance(objects, list) and objects:
                # Get unique object names
                if isinstance(objects[0], dict):
                    obj_names = [o.get("class", o.get("name", "")) for o in objects[:5]]
                else:
                    obj_names = objects[:5]
                obj_names = [n for n in obj_names if n]
                if obj_names:
                    parts.append(f"Scene with: {', '.join(obj_names)}")

            # Check for obstacles
            obstacles = scene_graph.get("obstacles", [])
            if obstacles:
                if isinstance(obstacles[0], dict):
                    obs_names = [o.get("class", "") for o in obstacles[:3]]
                else:
                    obs_names = obstacles[:3]
                obs_names = [n for n in obs_names if n]
                if obs_names:
                    parts.append(f"Obstacles: {', '.join(obs_names)}")

        if not parts:
            return "Memory recorded"

        # Combine parts into summary
        summary = ". ".join(parts)
        if len(summary) > 200:
            summary = summary[:197] + "..."

        return summary

    async def _compute_embedding(
        self,
        text: Optional[str],
        image: Optional[Any],
        audio: Optional[bytes],
    ) -> np.ndarray:
        """Compute fused embedding from available modalities."""

        # Use fuser for multimodal embedding
        if hasattr(self._fuser, "async_fuse"):
            embedding = await self._fuser.async_fuse(
                text=text,
                image=image if self._config.image_embedding_enabled else None,
                audio=audio if self._config.audio_embedding_enabled else None,
                audio_transcript=text,
            )
        else:
            embedding = self._fuser.fuse(
                text=text,
                image=image if self._config.image_embedding_enabled else None,
                audio=audio if self._config.audio_embedding_enabled else None,
                audio_transcript=text,
            )

        return embedding

    def _validate_request(self, request: MemoryStoreRequest) -> None:
        """Validate ingest request. Raises IngestValidationError on failure."""
        has_text = bool(request.transcript and request.transcript.strip())
        has_image = bool(request.image_base64)
        has_audio = bool(request.audio_base64)
        has_scene = bool(request.scene_graph)

        if not (has_text or has_image or has_audio or has_scene):
            raise IngestValidationError("Request has no content: provide transcript, image, audio, or scene_graph")

        # Text length limit
        if request.transcript and len(request.transcript) > 50_000:
            raise IngestValidationError(f"Transcript too long: {len(request.transcript)} chars (max 50000)")

        # Image size limit (base64 string, ~4MB decoded = ~5.3MB base64)
        if request.image_base64 and len(request.image_base64) > 6_000_000:
            raise IngestValidationError(f"Image too large: {len(request.image_base64)} chars (max ~4MB decoded)")

        # Audio size limit (~10MB decoded = ~13.3MB base64)
        if request.audio_base64 and len(request.audio_base64) > 14_000_000:
            raise IngestValidationError(f"Audio too large: {len(request.audio_base64)} chars (max ~10MB decoded)")

    def _compute_content_hash(self, request: MemoryStoreRequest) -> str:
        """SHA-256 hash of request content for dedup."""
        h = hashlib.sha256()
        if request.transcript:
            h.update(request.transcript.strip().lower().encode("utf-8"))
        if request.scene_graph:
            sg = json.dumps(request.scene_graph, sort_keys=True)
            h.update(sg.encode("utf-8"))
        if request.image_base64:
            # Hash first 1000 chars of base64 (enough to distinguish images)
            h.update(request.image_base64[:1000].encode("utf-8"))
        return h.hexdigest()

    async def ingest_batch(
        self,
        requests: List[MemoryStoreRequest],
        consent_given: bool = False,
        stop_on_error: bool = False,
    ) -> BatchIngestResult:
        """Ingest multiple memories with partial-success tracking.

        Args:
            requests: List of store requests
            consent_given: Whether user has given storage consent
            stop_on_error: If True, abort batch on first failure

        Returns:
            BatchIngestResult with per-item outcomes
        """
        start = time.time()
        results: List[MemoryStoreResponse] = []
        errors: List[Dict[str, str]] = []
        dedup_count = 0

        for idx, req in enumerate(requests):
            try:
                resp = await self.ingest(req, consent_given=consent_given)
                if resp.embedding_status == EmbeddingStatus.DEDUPLICATED:
                    dedup_count += 1
                if resp.embedding_status == EmbeddingStatus.REJECTED:
                    error_entry = {"index": str(idx), "error": resp.summary}
                    errors.append(error_entry)
                    if stop_on_error:
                        break
                else:
                    results.append(resp)
            except Exception as e:
                error_entry = {"index": str(idx), "error": str(e)}
                errors.append(error_entry)
                if stop_on_error:
                    break

        return BatchIngestResult(
            total=len(requests),
            succeeded=len(results),
            failed=len(errors),
            deduplicated=dedup_count,
            results=results,
            errors=errors,
            total_time_ms=(time.time() - start) * 1000,
        )

    def _decode_image(self, image_base64: str) -> Optional[Any]:
        """Decode base64 image to PIL Image."""
        try:
            from PIL import Image

            data = base64.b64decode(image_base64)
            return Image.open(io.BytesIO(data))
        except Exception as e:
            logger.warning(f"Failed to decode image: {e}")
            return None

    def _decode_audio(self, audio_base64: str) -> Optional[bytes]:
        """Decode base64 audio to bytes."""
        try:
            return base64.b64decode(audio_base64)
        except Exception as e:
            logger.warning(f"Failed to decode audio: {e}")
            return None

    def _store_scene_graph(self, memory_id: str, scene_graph: Optional[dict[str, Any]]) -> Optional[str]:
        """Store scene graph and return reference.

        For now, stores inline. In production, could use external storage.
        """
        if scene_graph is None:
            return None

        # Return hash as reference
        sg_json = json.dumps(scene_graph, sort_keys=True)
        ref = hashlib.sha256(sg_json.encode()).hexdigest()[:16]

        # In production, store to file/DB with ref as key
        # For now, scene graph is stored inline via metadata

        return f"sg_{ref}"

    async def _store_raw_media(
        self,
        memory_id: str,
        image_base64: Optional[str],
        audio_base64: Optional[str],
    ):
        """Store raw media to disk (if consent given).

        Raw media is stored separately from embeddings.
        """
        if not self._config.save_raw_media:
            return

        media_path = self._config.ensure_index_dir() / "raw_media"
        media_path.mkdir(exist_ok=True)

        if image_base64:
            img_path = media_path / f"{memory_id}.jpg"
            try:
                data = base64.b64decode(image_base64)
                with open(img_path, "wb") as f:
                    f.write(data)
            except Exception as e:
                logger.warning(f"Failed to save raw image: {e}")

        if audio_base64:
            audio_path = media_path / f"{memory_id}.wav"
            try:
                data = base64.b64decode(audio_base64)
                with open(audio_path, "wb") as f:
                    f.write(data)
            except Exception as e:
                logger.warning(f"Failed to save raw audio: {e}")

    def _load_persisted_consent(self) -> None:
        """Load consent records from encrypted files on disk."""
        enc = get_encryption_manager()
        for consent_file in self._consent_dir.glob("*.json"):
            try:
                entry = enc.load_json_decrypted(consent_file)
                device_id = consent_file.stem
                self._consent_log[device_id] = entry
                logger.debug("Loaded consent for device=%s", device_id)
            except Exception as e:
                logger.error("Failed to load consent file %s: %s", consent_file, e)
                # Tampered or corrupted — reject (fail-safe to no-consent)

    def record_consent(
        self,
        device_id: Optional[str],
        opt_in: bool,
        save_raw_media: bool,
        reason: Optional[str] = None,
    ) -> dict[str, Any]:
        """Record user consent for memory storage.

        Args:
            device_id: Device identifier
            opt_in: Whether user consents
            save_raw_media: Allow raw media storage
            reason: Reason for consent change

        Returns:
            Current consent settings
        """
        key = device_id or "default"

        consent_entry = {
            "opt_in": opt_in,
            "save_raw_media": save_raw_media,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        self._consent_log[key] = consent_entry

        # Persist encrypted to disk
        try:
            enc = get_encryption_manager()
            consent_path = self._consent_dir / f"{key}.json"
            enc.save_json_encrypted(consent_path, consent_entry)
        except Exception as e:
            logger.error("Failed to persist consent for %s: %s", key, e)

        logger.info(f"Consent recorded for {key}: opt_in={opt_in}, save_raw={save_raw_media}")

        return {
            "memory_enabled": opt_in,
            "save_raw_media": save_raw_media and opt_in,
        }

    def get_consent(self, device_id: Optional[str] = None) -> dict[str, bool]:
        """Get current consent settings."""
        key = device_id or "default"
        entry = self._consent_log.get(key)
        if entry is None:
            # Try loading from disk (might have been written by another process)
            consent_file = self._consent_dir / f"{key}.json"
            if consent_file.exists():
                try:
                    enc = get_encryption_manager()
                    entry = enc.load_json_decrypted(consent_file)
                    self._consent_log[key] = entry
                except Exception as e:
                    logger.error("Failed to load consent for %s: %s", key, e)
            if entry is None:
                entry = {}

        return {
            "memory_enabled": entry.get("opt_in", True),  # Default to enabled
            "save_raw_media": entry.get("save_raw_media", False),
        }

    def get_stats(self) -> dict[str, Any]:
        """Get ingestion statistics."""
        avg_time = self._total_ingest_time_ms / self._ingest_count if self._ingest_count > 0 else 0

        return {
            "total_ingested": self._ingest_count,
            "avg_ingest_time_ms": round(avg_time, 2),
            "index_size": self._indexer.size,
        }
