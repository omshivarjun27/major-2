"""P4: FAISS Scaling Validation Tests (T-080).

Validates FAISS index scaling beyond 5,000 vectors while maintaining
<50ms query latency. Tests auto-selection of index types and migration.
"""

from __future__ import annotations

import gc
import os
import sys
import time
from typing import Any, Dict, List, Tuple

import pytest
import numpy as np

# Project imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def index_factory():
    """Create fresh index factory."""
    from core.memory.index_factory import FAISSIndexFactory, IndexConfig
    return FAISSIndexFactory(IndexConfig())


@pytest.fixture
def vectors_5k():
    """5,000 test vectors (SLA target)."""
    np.random.seed(42)
    return np.random.random((5000, 384)).astype('float32')


@pytest.fixture
def vectors_10k():
    """10,000 test vectors (scaling target)."""
    np.random.seed(42)
    return np.random.random((10000, 384)).astype('float32')


@pytest.fixture
def vectors_25k():
    """25,000 test vectors (stress test)."""
    np.random.seed(42)
    return np.random.random((25000, 384)).astype('float32')


# ---------------------------------------------------------------------------
# Import Tests
# ---------------------------------------------------------------------------

class TestIndexFactoryImports:
    """Test index factory imports."""
    
    def test_index_factory_import(self):
        """Should import index factory module."""
        from core.memory.index_factory import (
            FAISSIndexFactory,
            IndexConfig,
            IndexType,
            IndexMaintenance,
        )
        
        assert FAISSIndexFactory is not None
        assert IndexConfig is not None
        assert IndexType is not None


# ---------------------------------------------------------------------------
# IndexType Tests
# ---------------------------------------------------------------------------

class TestIndexType:
    """Test IndexType enum."""
    
    def test_index_type_values(self):
        """Should have expected index type values."""
        from core.memory.index_factory import IndexType
        
        assert IndexType.FLAT.value == "flat"
        assert IndexType.IVF.value == "ivf"
        assert IndexType.HNSW.value == "hnsw"
        assert IndexType.PQ.value == "pq"


# ---------------------------------------------------------------------------
# IndexConfig Tests
# ---------------------------------------------------------------------------

class TestIndexConfig:
    """Test IndexConfig dataclass."""
    
    def test_config_defaults(self):
        """Should have sensible defaults."""
        from core.memory.index_factory import IndexConfig
        
        config = IndexConfig()
        
        assert config.dimension == 384
        assert config.ivf_nlist == 100
        assert config.ivf_nprobe == 10
        assert config.flat_max_vectors == 10000
    
    def test_config_custom(self):
        """Should accept custom values."""
        from core.memory.index_factory import IndexConfig, IndexType
        
        config = IndexConfig(
            dimension=512,
            index_type=IndexType.IVF,
            ivf_nlist=200,
        )
        
        assert config.dimension == 512
        assert config.index_type == IndexType.IVF
        assert config.ivf_nlist == 200


# ---------------------------------------------------------------------------
# FAISSIndexFactory Tests
# ---------------------------------------------------------------------------

class TestFAISSIndexFactory:
    """Test FAISSIndexFactory class."""
    
    def test_factory_creation(self):
        """Should create factory instance."""
        from core.memory.index_factory import FAISSIndexFactory
        
        factory = FAISSIndexFactory()
        assert factory is not None
    
    @pytest.mark.skipif(
        not os.environ.get("FAISS_AVAILABLE", "true").lower() == "true",
        reason="FAISS not available"
    )
    def test_create_flat_index(self, index_factory):
        """Should create Flat index."""
        from core.memory.index_factory import IndexType
        
        try:
            index = index_factory.create_index(IndexType.FLAT)
            assert index is not None
            assert index_factory.index_type == IndexType.FLAT
        except ImportError:
            pytest.skip("FAISS not available")
    
    @pytest.mark.skipif(
        not os.environ.get("FAISS_AVAILABLE", "true").lower() == "true",
        reason="FAISS not available"
    )
    def test_create_ivf_index(self, index_factory):
        """Should create IVF index."""
        from core.memory.index_factory import IndexType
        
        try:
            index = index_factory.create_index(IndexType.IVF)
            assert index is not None
            assert index_factory.index_type == IndexType.IVF
        except ImportError:
            pytest.skip("FAISS not available")
    
    def test_auto_select_flat(self, index_factory):
        """Should select Flat for small indexes."""
        from core.memory.index_factory import IndexType
        
        recommended = index_factory.get_recommended_type(1000)
        assert recommended == IndexType.FLAT
    
    def test_auto_select_ivf(self, index_factory):
        """Should select IVF for medium indexes."""
        from core.memory.index_factory import IndexType
        
        recommended = index_factory.get_recommended_type(50000)
        assert recommended == IndexType.IVF
    
    def test_auto_select_hnsw(self, index_factory):
        """Should select HNSW for large indexes."""
        from core.memory.index_factory import IndexType
        
        recommended = index_factory.get_recommended_type(500000)
        assert recommended == IndexType.HNSW
    
    def test_should_migrate(self, index_factory):
        """Should detect when migration is needed."""
        # Small to medium should trigger migration
        should_migrate = index_factory.should_migrate(5000, 50000)
        assert should_migrate is True
        
        # Small to small should not
        should_migrate = index_factory.should_migrate(1000, 5000)
        assert should_migrate is False


# ---------------------------------------------------------------------------
# Index Operations Tests
# ---------------------------------------------------------------------------

@pytest.fixture
def skip_if_no_faiss():
    """Skip test if FAISS is not available."""
    try:
        import faiss
    except ImportError:
        pytest.skip("FAISS not available")


class TestIndexOperations:
    """Test FAISS index operations."""
    
    def test_add_vectors(self, index_factory, vectors_5k, skip_if_no_faiss):
        """Should add vectors to index."""
        from core.memory.index_factory import IndexType
        
        index = index_factory.create_index(IndexType.FLAT)
        index_factory.add_vectors(vectors_5k[:1000])
        
        assert index_factory.vector_count == 1000
    
    def test_search_vectors(self, index_factory, vectors_5k, skip_if_no_faiss):
        """Should search vectors."""
        from core.memory.index_factory import IndexType
        
        index = index_factory.create_index(IndexType.FLAT)
        index_factory.add_vectors(vectors_5k[:1000])
        
        # Search
        query = vectors_5k[0]
        distances, indices = index_factory.search(query, k=10)
        
        assert len(indices[0]) == 10
        assert indices[0][0] == 0  # First result should be the query itself


# ---------------------------------------------------------------------------
# Scaling Tests
# ---------------------------------------------------------------------------

class TestFAISSScaling:
    """Test FAISS scaling characteristics."""
    
    def test_flat_5k_scaling(self, index_factory, vectors_5k, skip_if_no_faiss):
        """Flat index should handle 5K vectors within SLA."""
        from core.memory.index_factory import IndexType
        
        index = index_factory.create_index(IndexType.FLAT)
        index_factory.add_vectors(vectors_5k)
        
        # Benchmark queries
        latencies = []
        for i in range(100):
            query = vectors_5k[i % len(vectors_5k)]
            
            gc.collect()
            start = time.perf_counter()
            distances, indices = index_factory.search(query, k=10)
            latency_ms = (time.perf_counter() - start) * 1000
            latencies.append(latency_ms)
        
        avg_latency = sum(latencies) / len(latencies)
        p95_latency = sorted(latencies)[95]
        
        print(f"\n5K Flat Index: Avg={avg_latency:.2f}ms, P95={p95_latency:.2f}ms")
        
        assert p95_latency < 50.0, f"P95 latency {p95_latency:.1f}ms exceeds 50ms SLA"
    
    def test_flat_10k_scaling(self, index_factory, vectors_10k, skip_if_no_faiss):
        """Flat index should handle 10K vectors within extended SLA."""
        from core.memory.index_factory import IndexType
        
        index = index_factory.create_index(IndexType.FLAT)
        index_factory.add_vectors(vectors_10k)
        
        # Benchmark queries
        latencies = []
        for i in range(100):
            query = vectors_10k[i % len(vectors_10k)]
            
            gc.collect()
            start = time.perf_counter()
            distances, indices = index_factory.search(query, k=10)
            latency_ms = (time.perf_counter() - start) * 1000
            latencies.append(latency_ms)
        
        avg_latency = sum(latencies) / len(latencies)
        p95_latency = sorted(latencies)[95]
        
        print(f"\n10K Flat Index: Avg={avg_latency:.2f}ms, P95={p95_latency:.2f}ms")
        
        assert p95_latency < 100.0, f"P95 latency {p95_latency:.1f}ms exceeds 100ms target"
    
    def test_ivf_5k_scaling(self, index_factory, vectors_5k, skip_if_no_faiss):
        """IVF index should handle 5K vectors efficiently."""
        from core.memory.index_factory import IndexType, IndexConfig
        
        config = IndexConfig(ivf_nlist=50, ivf_nprobe=5)
        factory = type(index_factory)(config)
        
        index = factory.create_index(IndexType.IVF)
        factory.train_index(vectors_5k)
        factory.add_vectors(vectors_5k)
        
        # Benchmark queries
        latencies = []
        for i in range(100):
            query = vectors_5k[i % len(vectors_5k)]
            
            gc.collect()
            start = time.perf_counter()
            distances, indices = factory.search(query, k=10)
            latency_ms = (time.perf_counter() - start) * 1000
            latencies.append(latency_ms)
        
        avg_latency = sum(latencies) / len(latencies)
        p95_latency = sorted(latencies)[95]
        
        print(f"\n5K IVF Index: Avg={avg_latency:.2f}ms, P95={p95_latency:.2f}ms")
        
        assert p95_latency < 50.0, f"P95 latency {p95_latency:.1f}ms exceeds 50ms SLA"


# ---------------------------------------------------------------------------
# IndexMaintenance Tests
# ---------------------------------------------------------------------------

class TestIndexMaintenance:
    """Test index maintenance utilities."""
    
    def test_estimate_memory(self, index_factory):
        """Should estimate memory usage."""
        from core.memory.index_factory import IndexMaintenance
        
        maintenance = IndexMaintenance(index_factory)
        
        # 5000 vectors * 384 dims * 4 bytes = ~7.5 MB base
        memory_mb = maintenance.estimate_memory_mb(5000)
        
        assert 7.0 < memory_mb < 15.0  # With overhead
    
    def test_recommend_index_type(self, index_factory):
        """Should recommend appropriate index type."""
        from core.memory.index_factory import IndexMaintenance, IndexType
        
        maintenance = IndexMaintenance(index_factory)
        
        # Small index
        idx_type, reason = maintenance.recommend_index_type(1000)
        assert idx_type == IndexType.FLAT
        
        # Medium index
        idx_type, reason = maintenance.recommend_index_type(20000)
        assert idx_type == IndexType.IVF
        
        # Large index
        idx_type, reason = maintenance.recommend_index_type(100000)
        assert idx_type == IndexType.HNSW
    
    def test_should_compact(self, index_factory):
        """Should detect when compaction is needed."""
        from core.memory.index_factory import IndexMaintenance
        
        maintenance = IndexMaintenance(index_factory)
        
        assert maintenance.should_compact(0.1) is False
        assert maintenance.should_compact(0.3) is True
    
    def test_should_rebuild(self, index_factory):
        """Should detect when rebuild is needed."""
        from core.memory.index_factory import IndexMaintenance
        
        maintenance = IndexMaintenance(index_factory)
        
        assert maintenance.should_rebuild(5000, 5000) is False
        assert maintenance.should_rebuild(15000, 5000) is True


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------

class TestScalingIntegration:
    """Integration tests for FAISS scaling."""
    
    def test_complete_workflow(self, index_factory, vectors_5k, skip_if_no_faiss):
        """Test complete index workflow."""
        from core.memory.index_factory import IndexType, IndexMaintenance
        
        # Get recommendation
        maintenance = IndexMaintenance(index_factory)
        idx_type, reason = maintenance.recommend_index_type(5000)
        
        # Create index
        index = index_factory.create_index(idx_type)
        
        # Add vectors
        if idx_type in [IndexType.IVF, IndexType.PQ]:
            index_factory.train_index(vectors_5k)
        index_factory.add_vectors(vectors_5k)
        
        # Verify
        assert index_factory.vector_count == 5000
        
        # Search
        distances, indices = index_factory.search(vectors_5k[0], k=10)
        assert len(indices[0]) == 10
    
    def test_memory_scaling_linear(self, index_factory):
        """Memory should scale linearly with vector count."""
        from core.memory.index_factory import IndexMaintenance
        
        maintenance = IndexMaintenance(index_factory)
        
        mem_1k = maintenance.estimate_memory_mb(1000)
        mem_5k = maintenance.estimate_memory_mb(5000)
        mem_10k = maintenance.estimate_memory_mb(10000)
        
        # Should scale roughly linearly (within 2x factor)
        ratio_5k = mem_5k / mem_1k
        ratio_10k = mem_10k / mem_1k
        
        assert 4.0 < ratio_5k < 6.0  # ~5x
        assert 9.0 < ratio_10k < 12.0  # ~10x
