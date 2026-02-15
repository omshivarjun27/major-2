"""
Memory Engine - FAISS Indexer Module
=====================================

Local FAISS index management with persistence, sharding, and eviction.
"""

import json
import logging
import os
import shutil
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("memory-indexer")

# Optional at-rest encryption
try:
    from shared.utils.encryption import get_encryption_manager as _get_enc
except ImportError:
    _get_enc = None  # type: ignore[assignment]

# Lazy import FAISS
_faiss = None


def _get_faiss():
    """Lazy import faiss."""
    global _faiss
    if _faiss is None:
        try:
            import faiss
            _faiss = faiss
            logger.info(f"FAISS loaded (version: {faiss.__version__ if hasattr(faiss, '__version__') else 'unknown'})")
        except ImportError:
            logger.error("faiss-cpu not installed. Run: pip install faiss-cpu")
            raise
    return _faiss


@dataclass
class IndexMetadata:
    """Metadata for an indexed memory."""
    id: str
    timestamp: str
    expiry: str
    summary: str
    session_id: Optional[str] = None
    user_label: Optional[str] = None
    scene_graph_ref: Optional[str] = None
    vector_idx: int = -1  # Position in FAISS index


@dataclass
class SearchResult:
    """Result from a similarity search."""
    id: str
    score: float
    metadata: IndexMetadata


class FAISSIndexer:
    """FAISS index manager for memory embeddings.
    
    Features:
    - Flat L2 index for exact search (good for small indices)
    - Persistence to disk (index + metadata)
    - Size limits with eviction policy (LRU or time-based)
    - Thread-safe operations
    
    Usage:
        indexer = FAISSIndexer(index_path="./data/memory_index/", max_vectors=5000)
        indexer.add(id="mem_001", embedding=vector, metadata=metadata)
        results = indexer.search(query_vector, k=5)
    """
    
    def __init__(
        self,
        index_path: str = "./data/memory_index/",
        dimension: int = 384,
        max_vectors: int = 5000,
        eviction_policy: str = "time",  # "time" or "lru"
    ):
        self._index_path = Path(index_path)
        self._dimension = dimension
        self._max_vectors = max_vectors
        self._eviction_policy = eviction_policy
        
        # FAISS index
        self._index = None
        
        # Metadata store: vector_idx -> IndexMetadata
        self._metadata: Dict[int, IndexMetadata] = {}
        
        # ID to vector index mapping
        self._id_to_idx: Dict[str, int] = {}
        
        # Next available vector index
        self._next_idx = 0
        
        # Deleted indices (for reuse)
        self._deleted_indices: List[int] = []
        
        # Thread lock
        self._lock = threading.RLock()
        
        # Load existing index if present
        self._load()
    
    def _ensure_index(self):
        """Create index if not exists."""
        if self._index is None:
            faiss = _get_faiss()
            # Use flat L2 index for small datasets (exact search)
            self._index = faiss.IndexFlatL2(self._dimension)
            logger.info(f"Created FAISS index (dim={self._dimension})")
    
    def add(
        self,
        id: str,
        embedding: np.ndarray,
        metadata: Optional[IndexMetadata] = None,
        timestamp: Optional[str] = None,
        expiry: Optional[str] = None,
        summary: str = "",
        session_id: Optional[str] = None,
        user_label: Optional[str] = None,
        scene_graph_ref: Optional[str] = None,
    ) -> int:
        """Add a vector to the index.
        
        Args:
            id: Unique memory ID
            embedding: Embedding vector (normalized)
            metadata: Optional pre-built IndexMetadata
            timestamp: ISO8601 timestamp (if not using metadata)
            expiry: ISO8601 expiry (if not using metadata)
            summary: Memory summary
            session_id: Session ID
            user_label: User label
            scene_graph_ref: Scene graph reference
            
        Returns:
            Vector index in FAISS
        """
        with self._lock:
            self._ensure_index()
            
            # Check if already exists
            if id in self._id_to_idx:
                logger.warning(f"Memory {id} already indexed, updating")
                self.delete(id)
            
            # Check capacity
            if len(self._id_to_idx) >= self._max_vectors:
                self._evict()
            
            # Prepare embedding
            embedding = np.array(embedding, dtype=np.float32).reshape(1, -1)
            if embedding.shape[1] != self._dimension:
                raise ValueError(f"Embedding dimension {embedding.shape[1]} != index dimension {self._dimension}")
            
            # Get vector index
            if self._deleted_indices:
                vec_idx = self._deleted_indices.pop(0)
            else:
                vec_idx = self._next_idx
                self._next_idx += 1
            
            # Add to FAISS
            # Note: IndexFlatL2 appends, so we track actual positions
            self._index.add(embedding)
            actual_idx = self._index.ntotal - 1
            
            # Create metadata
            if metadata is None:
                metadata = IndexMetadata(
                    id=id,
                    timestamp=timestamp or datetime.utcnow().isoformat() + "Z",
                    expiry=expiry or "",
                    summary=summary,
                    session_id=session_id,
                    user_label=user_label,
                    scene_graph_ref=scene_graph_ref,
                    vector_idx=actual_idx,
                )
            else:
                metadata.vector_idx = actual_idx
            
            # Store mappings
            self._metadata[actual_idx] = metadata
            self._id_to_idx[id] = actual_idx
            
            logger.debug(f"Added memory {id} at index {actual_idx}")
            return actual_idx
    
    def search(
        self,
        query: np.ndarray,
        k: int = 5,
        time_window_days: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> List[SearchResult]:
        """Search for similar vectors.
        
        Args:
            query: Query embedding vector
            k: Number of results
            time_window_days: Optional time filter
            session_id: Optional session filter
            
        Returns:
            List of SearchResult sorted by score (lower is better for L2)
        """
        with self._lock:
            if self._index is None or self._index.ntotal == 0:
                return []
            
            # Prepare query
            query = np.array(query, dtype=np.float32).reshape(1, -1)
            if query.shape[1] != self._dimension:
                raise ValueError(f"Query dimension {query.shape[1]} != index dimension {self._dimension}")
            
            # Search (get more results for filtering)
            search_k = min(k * 3, self._index.ntotal)
            distances, indices = self._index.search(query, search_k)
            
            # Convert to results with filtering
            results = []
            now = datetime.utcnow()
            
            for dist, idx in zip(distances[0], indices[0]):
                if idx == -1:
                    continue
                
                if idx not in self._metadata:
                    continue
                
                meta = self._metadata[idx]
                
                # Time filter
                if time_window_days is not None:
                    try:
                        ts = datetime.fromisoformat(meta.timestamp.replace("Z", "+00:00"))
                        age_days = (now - ts.replace(tzinfo=None)).days
                        if age_days > time_window_days:
                            continue
                    except (ValueError, AttributeError):
                        pass
                
                # Session filter
                if session_id is not None and meta.session_id != session_id:
                    continue
                
                # Convert L2 distance to similarity score (0-1)
                # L2 distance: lower is better, so we invert
                score = 1.0 / (1.0 + dist)
                
                results.append(SearchResult(
                    id=meta.id,
                    score=score,
                    metadata=meta,
                ))
                
                if len(results) >= k:
                    break
            
            return results
    
    def delete(self, id: str) -> bool:
        """Delete a memory from the index.
        
        Args:
            id: Memory ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        with self._lock:
            if id not in self._id_to_idx:
                return False
            
            idx = self._id_to_idx[id]
            
            # Remove from metadata
            if idx in self._metadata:
                del self._metadata[idx]
            
            # Remove from ID mapping
            del self._id_to_idx[id]
            
            # Mark index as deleted (for reuse)
            # Note: FAISS IndexFlatL2 doesn't support deletion,
            # so we mark as deleted and compact periodically
            self._deleted_indices.append(idx)
            
            logger.debug(f"Deleted memory {id} (index {idx})")
            return True
    
    def get(self, id: str) -> Optional[IndexMetadata]:
        """Get metadata for a memory ID.
        
        Args:
            id: Memory ID
            
        Returns:
            IndexMetadata or None
        """
        with self._lock:
            if id not in self._id_to_idx:
                return None
            idx = self._id_to_idx[id]
            return self._metadata.get(idx)
    
    def _evict(self):
        """Evict vectors to make room for new ones."""
        with self._lock:
            if self._eviction_policy == "time":
                # Remove oldest entries
                entries = list(self._metadata.values())
                entries.sort(key=lambda m: m.timestamp)
                
                # Remove 10% of oldest
                to_remove = max(1, len(entries) // 10)
                for meta in entries[:to_remove]:
                    self.delete(meta.id)
                    
                logger.info(f"Evicted {to_remove} memories (time-based)")
            else:
                # LRU - remove entries with oldest timestamps
                # (In a full impl, we'd track access times)
                entries = list(self._metadata.values())
                entries.sort(key=lambda m: m.timestamp)
                
                to_remove = max(1, len(entries) // 10)
                for meta in entries[:to_remove]:
                    self.delete(meta.id)
                    
                logger.info(f"Evicted {to_remove} memories (LRU)")
    
    def compact(self):
        """Rebuild index to reclaim space from deleted vectors.
        
        This is expensive, so call periodically (e.g., during maintenance).
        """
        with self._lock:
            if not self._metadata:
                return
            
            faiss = _get_faiss()
            
            logger.info(f"Compacting index ({self._index.ntotal} vectors, {len(self._deleted_indices)} deleted)")
            
            # Collect all valid vectors and metadata
            valid_entries = []
            for idx, meta in self._metadata.items():
                if idx < self._index.ntotal:
                    vector = self._index.reconstruct(idx)
                    valid_entries.append((meta, vector))
            
            # Create new index
            new_index = faiss.IndexFlatL2(self._dimension)
            new_metadata = {}
            new_id_to_idx = {}
            
            for i, (meta, vector) in enumerate(valid_entries):
                new_index.add(vector.reshape(1, -1))
                meta.vector_idx = i
                new_metadata[i] = meta
                new_id_to_idx[meta.id] = i
            
            # Replace old structures
            self._index = new_index
            self._metadata = new_metadata
            self._id_to_idx = new_id_to_idx
            self._next_idx = len(valid_entries)
            self._deleted_indices = []
            
            logger.info(f"Compaction complete ({new_index.ntotal} vectors)")
    
    def save(self):
        """Persist index and metadata to disk (encrypted when key is set)."""
        with self._lock:
            if self._index is None:
                return
            
            self._index_path.mkdir(parents=True, exist_ok=True)
            
            faiss = _get_faiss()
            enc = _get_enc() if _get_enc is not None else None
            
            # ── Save FAISS index ──────────────────────────────────
            index_file = self._index_path / "index.faiss"
            if enc and enc.active:
                # Serialize to bytes, then encrypt
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                    faiss.write_index(self._index, tmp.name)
                raw = Path(tmp.name).read_bytes()
                os.unlink(tmp.name)
                enc.save_encrypted(index_file, raw)
            else:
                faiss.write_index(self._index, str(index_file))
            
            # ── Save metadata as JSON ─────────────────────────────
            metadata_file = self._index_path / "metadata.json"
            meta_dict = {}
            for idx, meta in self._metadata.items():
                meta_dict[str(idx)] = {
                    "id": meta.id,
                    "timestamp": meta.timestamp,
                    "expiry": meta.expiry,
                    "summary": meta.summary,
                    "session_id": meta.session_id,
                    "user_label": meta.user_label,
                    "scene_graph_ref": meta.scene_graph_ref,
                    "vector_idx": meta.vector_idx,
                }
            
            payload = {
                "metadata": meta_dict,
                "id_to_idx": self._id_to_idx,
                "next_idx": self._next_idx,
                "deleted_indices": self._deleted_indices,
                "dimension": self._dimension,
                "saved_at": datetime.utcnow().isoformat() + "Z",
            }
            
            if enc and enc.active:
                enc.save_json_encrypted(metadata_file, payload)
            else:
                with open(metadata_file, "w") as f:
                    json.dump(payload, f, indent=2)
            
            logger.info(
                "Index saved to %s (%d vectors, encrypted=%s)",
                self._index_path, len(self._metadata),
                enc.active if enc else False,
            )
    
    def _load(self):
        """Load index and metadata from disk (decrypted when key is set)."""
        index_file = self._index_path / "index.faiss"
        metadata_file = self._index_path / "metadata.json"
        
        if not index_file.exists() or not metadata_file.exists():
            logger.info("No existing index found, starting fresh")
            return
        
        try:
            faiss = _get_faiss()
            enc = _get_enc() if _get_enc is not None else None
            
            # ── Load FAISS index ──────────────────────────────────
            if enc and enc.active:
                import tempfile
                raw = enc.load_decrypted(index_file)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".faiss") as tmp:
                    tmp.write(raw)
                    tmp.flush()
                self._index = faiss.read_index(tmp.name)
                os.unlink(tmp.name)
            else:
                self._index = faiss.read_index(str(index_file))
            
            # ── Load metadata ─────────────────────────────────────
            if enc and enc.active:
                data = enc.load_json_decrypted(metadata_file)
            else:
                with open(metadata_file, "r") as f:
                    data = json.load(f)
            
            # Restore metadata
            self._metadata = {}
            for idx_str, meta_dict in data.get("metadata", {}).items():
                idx = int(idx_str)
                self._metadata[idx] = IndexMetadata(
                    id=meta_dict["id"],
                    timestamp=meta_dict["timestamp"],
                    expiry=meta_dict["expiry"],
                    summary=meta_dict["summary"],
                    session_id=meta_dict.get("session_id"),
                    user_label=meta_dict.get("user_label"),
                    scene_graph_ref=meta_dict.get("scene_graph_ref"),
                    vector_idx=meta_dict.get("vector_idx", idx),
                )
            
            self._id_to_idx = data.get("id_to_idx", {})
            self._next_idx = data.get("next_idx", self._index.ntotal)
            self._deleted_indices = data.get("deleted_indices", [])
            self._dimension = data.get("dimension", self._dimension)
            
            logger.info(f"Loaded index from {self._index_path} ({len(self._metadata)} vectors)")
            
        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            self._index = None
            self._metadata = {}
            self._id_to_idx = {}
    
    def clear(self):
        """Clear all data from the index."""
        with self._lock:
            self._index = None
            self._metadata = {}
            self._id_to_idx = {}
            self._next_idx = 0
            self._deleted_indices = []
            
            # Remove files
            if self._index_path.exists():
                shutil.rmtree(self._index_path, ignore_errors=True)
            
            logger.info("Index cleared")
    
    @property
    def size(self) -> int:
        """Return number of indexed vectors."""
        return len(self._id_to_idx)
    
    @property
    def total_vectors(self) -> int:
        """Return total vectors in FAISS (including deleted)."""
        if self._index is None:
            return 0
        return self._index.ntotal
    
    @property
    def dimension(self) -> int:
        """Return index dimension."""
        return self._dimension


class MockFAISSIndexer(FAISSIndexer):
    """Mock indexer for testing without FAISS dependency."""
    
    def __init__(self, **kwargs):
        # Skip parent init to avoid FAISS loading
        self._index_path = Path(kwargs.get("index_path", "./data/test_index/"))
        self._dimension = kwargs.get("dimension", 384)
        self._max_vectors = kwargs.get("max_vectors", 100)
        self._eviction_policy = kwargs.get("eviction_policy", "time")
        
        self._vectors: Dict[int, np.ndarray] = {}
        self._metadata: Dict[int, IndexMetadata] = {}
        self._id_to_idx: Dict[str, int] = {}
        self._next_idx = 0
        self._deleted_indices: List[int] = []
        self._lock = threading.RLock()
    
    def _ensure_index(self):
        pass  # No-op for mock
    
    def add(self, id: str, embedding: np.ndarray, **kwargs) -> int:
        with self._lock:
            if id in self._id_to_idx:
                self.delete(id)
            
            if len(self._id_to_idx) >= self._max_vectors:
                self._evict()
            
            embedding = np.array(embedding, dtype=np.float32).flatten()
            
            vec_idx = self._next_idx
            self._next_idx += 1
            
            self._vectors[vec_idx] = embedding
            
            meta = IndexMetadata(
                id=id,
                timestamp=kwargs.get("timestamp", datetime.utcnow().isoformat() + "Z"),
                expiry=kwargs.get("expiry", ""),
                summary=kwargs.get("summary", ""),
                session_id=kwargs.get("session_id"),
                user_label=kwargs.get("user_label"),
                scene_graph_ref=kwargs.get("scene_graph_ref"),
                vector_idx=vec_idx,
            )
            
            self._metadata[vec_idx] = meta
            self._id_to_idx[id] = vec_idx
            
            return vec_idx
    
    def search(self, query: np.ndarray, k: int = 5, **kwargs) -> List[SearchResult]:
        with self._lock:
            if not self._vectors:
                return []
            
            query = np.array(query, dtype=np.float32).flatten()
            
            # Compute L2 distances
            results = []
            for idx, vec in self._vectors.items():
                if idx not in self._metadata:
                    continue
                dist = np.linalg.norm(query - vec)
                score = 1.0 / (1.0 + dist)
                results.append(SearchResult(
                    id=self._metadata[idx].id,
                    score=score,
                    metadata=self._metadata[idx],
                ))
            
            results.sort(key=lambda r: -r.score)
            return results[:k]
    
    def save(self):
        pass  # No-op for mock
    
    def compact(self):
        pass  # No-op for mock
    
    @property
    def total_vectors(self) -> int:
        return len(self._vectors)
