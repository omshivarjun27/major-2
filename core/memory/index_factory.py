"""FAISS index factory with automatic type selection.

Provides intelligent index selection based on vector count and
performance requirements. Supports multiple FAISS index types
with automatic migration as index size grows.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("faiss-index-factory")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class IndexType(Enum):
    """FAISS index types."""
    FLAT = "flat"          # IndexFlatL2 - exact search, O(n)
    IVF = "ivf"            # IndexIVFFlat - approximate, O(sqrt(n))
    HNSW = "hnsw"          # IndexHNSW - graph-based, O(log n)
    PQ = "pq"              # Product Quantization - compressed


@dataclass
class IndexConfig:
    """Configuration for FAISS index."""
    dimension: int = 384
    index_type: IndexType = IndexType.FLAT
    
    # IVF parameters
    ivf_nlist: int = 100        # Number of clusters
    ivf_nprobe: int = 10        # Clusters to search
    
    # HNSW parameters
    hnsw_m: int = 32            # Number of neighbors
    hnsw_ef_construction: int = 200
    hnsw_ef_search: int = 64
    
    # PQ parameters
    pq_m: int = 8               # Number of subquantizers
    pq_bits: int = 8            # Bits per subquantizer
    
    # Thresholds for auto-selection
    flat_max_vectors: int = 10000      # Use Flat up to this
    ivf_max_vectors: int = 100000      # Use IVF up to this
    
    @classmethod
    def from_env(cls) -> "IndexConfig":
        """Create config from environment variables."""
        return cls(
            dimension=int(os.environ.get("FAISS_DIMENSION", "384")),
            ivf_nlist=int(os.environ.get("FAISS_IVF_NLIST", "100")),
            ivf_nprobe=int(os.environ.get("FAISS_IVF_NPROBE", "10")),
        )


# ---------------------------------------------------------------------------
# Index Factory
# ---------------------------------------------------------------------------

def check_faiss_available() -> bool:
    """Check if FAISS is available."""
    try:
        import faiss
        return True
    except ImportError:
        return False


class FAISSIndexFactory:
    """Factory for creating and managing FAISS indexes."""
    
    def __init__(self, config: Optional[IndexConfig] = None):
        self.config = config or IndexConfig()
        self._index = None
        self._index_type = None
        self._vector_count = 0
    
    def create_index(
        self,
        index_type: Optional[IndexType] = None,
        num_vectors: int = 0,
    ) -> Any:
        """Create a FAISS index.
        
        Args:
            index_type: Explicit index type, or None for auto-selection
            num_vectors: Expected number of vectors (for auto-selection)
        
        Returns:
            FAISS index instance
        """
        if not check_faiss_available():
            raise ImportError("FAISS is not available")
        
        import faiss
        
        # Auto-select index type based on expected size
        if index_type is None:
            index_type = self._select_index_type(num_vectors)
        
        dim = self.config.dimension
        
        if index_type == IndexType.FLAT:
            index = faiss.IndexFlatL2(dim)
            
        elif index_type == IndexType.IVF:
            quantizer = faiss.IndexFlatL2(dim)
            index = faiss.IndexIVFFlat(
                quantizer, dim, self.config.ivf_nlist
            )
            
        elif index_type == IndexType.HNSW:
            index = faiss.IndexHNSWFlat(dim, self.config.hnsw_m)
            index.hnsw.efConstruction = self.config.hnsw_ef_construction
            index.hnsw.efSearch = self.config.hnsw_ef_search
            
        elif index_type == IndexType.PQ:
            index = faiss.IndexPQ(dim, self.config.pq_m, self.config.pq_bits)
            
        else:
            raise ValueError(f"Unknown index type: {index_type}")
        
        self._index = index
        self._index_type = index_type
        
        logger.info(f"Created FAISS index: {index_type.value} (dim={dim})")
        return index
    
    def _select_index_type(self, num_vectors: int) -> IndexType:
        """Auto-select index type based on expected vector count."""
        if num_vectors <= self.config.flat_max_vectors:
            return IndexType.FLAT
        elif num_vectors <= self.config.ivf_max_vectors:
            return IndexType.IVF
        else:
            return IndexType.HNSW
    
    def get_recommended_type(self, num_vectors: int) -> IndexType:
        """Get recommended index type for a given vector count."""
        return self._select_index_type(num_vectors)
    
    def should_migrate(self, current_count: int, new_count: int) -> bool:
        """Check if index should be migrated to a different type."""
        current_type = self._select_index_type(current_count)
        new_type = self._select_index_type(new_count)
        return current_type != new_type
    
    def train_index(self, vectors: np.ndarray):
        """Train the index (required for IVF, PQ)."""
        if self._index is None:
            raise ValueError("No index created")
        
        if self._index_type in [IndexType.IVF, IndexType.PQ]:
            if not self._index.is_trained:
                logger.info(f"Training {self._index_type.value} index with {len(vectors)} vectors")
                self._index.train(vectors.astype('float32'))
    
    def add_vectors(self, vectors: np.ndarray):
        """Add vectors to the index."""
        if self._index is None:
            raise ValueError("No index created")
        
        vectors = vectors.astype('float32')
        
        if self._index_type in [IndexType.IVF, IndexType.PQ]:
            if not self._index.is_trained:
                self.train_index(vectors)
        
        self._index.add(vectors)
        self._vector_count += len(vectors)
    
    def search(
        self,
        query: np.ndarray,
        k: int = 10,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Search the index.
        
        Returns:
            Tuple of (distances, indices) arrays
        """
        if self._index is None:
            raise ValueError("No index created")
        
        query = query.astype('float32')
        if query.ndim == 1:
            query = query.reshape(1, -1)
        
        # Set search parameters for IVF
        if self._index_type == IndexType.IVF:
            self._index.nprobe = self.config.ivf_nprobe
        
        distances, indices = self._index.search(query, k)
        return distances, indices
    
    @property
    def vector_count(self) -> int:
        """Get number of vectors in the index."""
        if self._index is None:
            return 0
        return self._index.ntotal
    
    @property
    def index_type(self) -> Optional[IndexType]:
        """Get current index type."""
        return self._index_type


# ---------------------------------------------------------------------------
# Index Maintenance
# ---------------------------------------------------------------------------

class IndexMaintenance:
    """Utilities for FAISS index maintenance."""
    
    def __init__(self, factory: FAISSIndexFactory):
        self.factory = factory
    
    def estimate_memory_mb(self, num_vectors: int, dimension: int = 384) -> float:
        """Estimate memory usage for an index."""
        # Base memory: vectors * dimension * sizeof(float32)
        base_mb = (num_vectors * dimension * 4) / (1024 * 1024)
        
        # Add overhead based on index type
        index_type = self.factory.get_recommended_type(num_vectors)
        
        if index_type == IndexType.FLAT:
            return base_mb * 1.1  # 10% overhead
        elif index_type == IndexType.IVF:
            return base_mb * 1.3  # 30% overhead for clustering
        elif index_type == IndexType.HNSW:
            return base_mb * 2.0  # 2x for graph structure
        else:
            return base_mb
    
    def recommend_index_type(
        self,
        num_vectors: int,
        latency_budget_ms: float = 50.0,
    ) -> Tuple[IndexType, str]:
        """Recommend index type based on requirements.
        
        Returns:
            Tuple of (index_type, reason)
        """
        if num_vectors <= 5000:
            return IndexType.FLAT, "Small index, exact search is fast enough"
        
        if num_vectors <= 50000:
            return IndexType.IVF, "Medium index, IVF provides good speed/accuracy tradeoff"
        
        return IndexType.HNSW, "Large index, HNSW provides best query performance"
    
    def should_compact(self, deleted_ratio: float = 0.2) -> bool:
        """Check if index should be compacted."""
        # Compact if >20% vectors are deleted
        return deleted_ratio > 0.2
    
    def should_rebuild(
        self,
        current_count: int,
        original_count: int,
        growth_factor: float = 2.0,
    ) -> bool:
        """Check if index should be rebuilt."""
        # Rebuild if index has grown 2x since creation
        return current_count > original_count * growth_factor


# ---------------------------------------------------------------------------
# Global Factory
# ---------------------------------------------------------------------------

_index_factory: Optional[FAISSIndexFactory] = None


def get_index_factory() -> FAISSIndexFactory:
    """Get global index factory instance."""
    global _index_factory
    if _index_factory is None:
        _index_factory = FAISSIndexFactory()
    return _index_factory


def create_index(
    index_type: Optional[IndexType] = None,
    num_vectors: int = 0,
    config: Optional[IndexConfig] = None,
) -> Any:
    """Convenience function to create a FAISS index."""
    factory = FAISSIndexFactory(config)
    return factory.create_index(index_type, num_vectors)
