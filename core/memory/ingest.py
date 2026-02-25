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
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from shared.utils.encryption import get_encryption_manager

from .config import get_memory_config, MemoryConfig
from .api_schema import (
    MemoryStoreRequest,
    MemoryStoreResponse,
    MemoryRecord,
    EmbeddingStatus,
    PrivacyFlag,
)
from .embeddings import TextEmbedder, MultimodalFuser, create_embedders
from .indexer import FAISSIndexer, IndexMetadata

logger = logging.getLogger("memory-ingest")


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
        self._consent_log: Dict[str, Dict] = {}

        # Consent persistence directory
        self._consent_dir = Path(self._config.index_path).parent / "consent"
        self._consent_dir.mkdir(parents=True, exist_ok=True)
        self._load_persisted_consent()
        
        # Telemetry
        self._ingest_count = 0
        self._total_ingest_time_ms = 0.0
    
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
            
            # Store with failed embedding status
            try:
                summary = request.user_label or "Memory ingestion failed"
                self._indexer.add(
                    id=memory_id,
                    embedding=np.zeros(self._text_embedder.dimension, dtype=np.float32),
                    timestamp=timestamp,
                    expiry=expiry,
                    summary=summary,
                    session_id=request.session_id,
                    user_label=request.user_label,
                )
            except Exception:
                pass
            
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
        scene_graph: Optional[Dict],
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
        embedding = self._fuser.fuse(
            text=text,
            image=image if self._config.image_embedding_enabled else None,
            audio=audio if self._config.audio_embedding_enabled else None,
            audio_transcript=text,
        )
        
        return embedding
    
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
    
    def _store_scene_graph(self, memory_id: str, scene_graph: Optional[Dict]) -> Optional[str]:
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
    ) -> Dict[str, Any]:
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
    
    def get_consent(self, device_id: Optional[str] = None) -> Dict[str, bool]:
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
    
    def get_stats(self) -> Dict[str, Any]:
        """Get ingestion statistics."""
        avg_time = (
            self._total_ingest_time_ms / self._ingest_count
            if self._ingest_count > 0 else 0
        )
        
        return {
            "total_ingested": self._ingest_count,
            "avg_ingest_time_ms": round(avg_time, 2),
            "index_size": self._indexer.size,
        }
