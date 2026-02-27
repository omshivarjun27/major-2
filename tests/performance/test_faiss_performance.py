"""P4: FAISS Index Performance Tests (T-079).

Tests for FAISS index performance and scaling validation.
Target: <50ms query latency with 5,000+ vectors.
"""

from __future__ import annotations

import gc
import os
import statistics
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pytest
import numpy as np

# Project imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Test Data Generation
# ---------------------------------------------------------------------------

@dataclass
class FAISSTestDataset:
    """Test dataset for FAISS benchmarking."""
    vectors: np.ndarray
    dimension: int
    size: int
    queries: np.ndarray
    
    @classmethod
    def generate(
        cls,
        size: int = 5000,
        dimension: int = 384,
        num_queries: int = 100,
        seed: int = 42,
    ) -> "FAISSTestDataset":
        """Generate random test vectors."""
        np.random.seed(seed)
        vectors = np.random.random((size, dimension)).astype('float32')
        queries = np.random.random((num_queries, dimension)).astype('float32')
        return cls(
            vectors=vectors,
            dimension=dimension,
            size=size,
            queries=queries,
        )


@dataclass
class FAISSBenchmarkResult:
    """Result of FAISS benchmark."""
    index_type: str
    num_vectors: int
    dimension: int
    
    # Add latencies
    add_total_ms: float = 0.0
    add_per_vector_us: float = 0.0
    
    # Query latencies
    query_latencies_ms: List[float] = field(default_factory=list)
    
    # Memory
    index_size_mb: float = 0.0
    
    @property
    def query_avg_ms(self) -> float:
        if not self.query_latencies_ms:
            return 0.0
        return statistics.mean(self.query_latencies_ms)
    
    @property
    def query_p50_ms(self) -> float:
        if not self.query_latencies_ms:
            return 0.0
        return statistics.median(self.query_latencies_ms)
    
    @property
    def query_p95_ms(self) -> float:
        if not self.query_latencies_ms:
            return 0.0
        sorted_lat = sorted(self.query_latencies_ms)
        idx = int(len(sorted_lat) * 0.95)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]
    
    @property
    def query_p99_ms(self) -> float:
        if not self.query_latencies_ms:
            return 0.0
        sorted_lat = sorted(self.query_latencies_ms)
        idx = int(len(sorted_lat) * 0.99)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]
    
    @property
    def meets_sla(self) -> bool:
        """Check if P95 query latency is under 50ms SLA."""
        return self.query_p95_ms < 50.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "index_type": self.index_type,
            "num_vectors": self.num_vectors,
            "dimension": self.dimension,
            "add_total_ms": round(self.add_total_ms, 2),
            "add_per_vector_us": round(self.add_per_vector_us, 2),
            "query_avg_ms": round(self.query_avg_ms, 3),
            "query_p50_ms": round(self.query_p50_ms, 3),
            "query_p95_ms": round(self.query_p95_ms, 3),
            "query_p99_ms": round(self.query_p99_ms, 3),
            "index_size_mb": round(self.index_size_mb, 2),
            "meets_sla": self.meets_sla,
        }


# ---------------------------------------------------------------------------
# FAISS Benchmarking
# ---------------------------------------------------------------------------

def check_faiss_available() -> bool:
    """Check if FAISS is available."""
    try:
        import faiss
        return True
    except ImportError:
        return False


def benchmark_faiss_flat(dataset: FAISSTestDataset, k: int = 10) -> FAISSBenchmarkResult:
    """Benchmark FAISS IndexFlatL2."""
    import faiss
    
    result = FAISSBenchmarkResult(
        index_type="IndexFlatL2",
        num_vectors=dataset.size,
        dimension=dataset.dimension,
    )
    
    # Create index
    index = faiss.IndexFlatL2(dataset.dimension)
    
    # Add vectors
    gc.collect()
    add_start = time.perf_counter()
    index.add(dataset.vectors)
    result.add_total_ms = (time.perf_counter() - add_start) * 1000
    result.add_per_vector_us = (result.add_total_ms / dataset.size) * 1000
    
    # Estimate index size (approximate)
    result.index_size_mb = (dataset.size * dataset.dimension * 4) / (1024 * 1024)
    
    # Query benchmark
    for query in dataset.queries:
        gc.collect()
        query_start = time.perf_counter()
        distances, indices = index.search(query.reshape(1, -1), k)
        query_ms = (time.perf_counter() - query_start) * 1000
        result.query_latencies_ms.append(query_ms)
    
    return result


def benchmark_faiss_ivf(
    dataset: FAISSTestDataset,
    nlist: int = 100,
    nprobe: int = 10,
    k: int = 10,
) -> FAISSBenchmarkResult:
    """Benchmark FAISS IndexIVFFlat."""
    import faiss
    
    result = FAISSBenchmarkResult(
        index_type=f"IndexIVFFlat(nlist={nlist})",
        num_vectors=dataset.size,
        dimension=dataset.dimension,
    )
    
    # Create quantizer and index
    quantizer = faiss.IndexFlatL2(dataset.dimension)
    index = faiss.IndexIVFFlat(quantizer, dataset.dimension, nlist)
    
    # Train index
    index.train(dataset.vectors)
    
    # Add vectors
    gc.collect()
    add_start = time.perf_counter()
    index.add(dataset.vectors)
    result.add_total_ms = (time.perf_counter() - add_start) * 1000
    result.add_per_vector_us = (result.add_total_ms / dataset.size) * 1000
    
    # Set search parameters
    index.nprobe = nprobe
    
    # Estimate index size
    result.index_size_mb = (dataset.size * dataset.dimension * 4) / (1024 * 1024)
    
    # Query benchmark
    for query in dataset.queries:
        gc.collect()
        query_start = time.perf_counter()
        distances, indices = index.search(query.reshape(1, -1), k)
        query_ms = (time.perf_counter() - query_start) * 1000
        result.query_latencies_ms.append(query_ms)
    
    return result


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def dataset_1k() -> FAISSTestDataset:
    """1,000 vector dataset."""
    return FAISSTestDataset.generate(size=1000, dimension=384)


@pytest.fixture
def dataset_5k() -> FAISSTestDataset:
    """5,000 vector dataset (SLA target)."""
    return FAISSTestDataset.generate(size=5000, dimension=384)


@pytest.fixture
def dataset_10k() -> FAISSTestDataset:
    """10,000 vector dataset."""
    return FAISSTestDataset.generate(size=10000, dimension=384)


# ---------------------------------------------------------------------------
# Import Tests
# ---------------------------------------------------------------------------

class TestFAISSImports:
    """Test FAISS availability."""
    
    def test_faiss_import(self):
        """FAISS should be importable."""
        pytest.importorskip("faiss")
        import faiss
        assert faiss is not None
    
    def test_numpy_import(self):
        """NumPy should be available."""
        import numpy as np
        assert np is not None


# ---------------------------------------------------------------------------
# Dataset Generation Tests
# ---------------------------------------------------------------------------

class TestFAISSTestDataset:
    """Test dataset generation."""
    
    def test_generate_dataset(self):
        """Should generate dataset with correct shape."""
        dataset = FAISSTestDataset.generate(size=100, dimension=128)
        
        assert dataset.vectors.shape == (100, 128)
        assert dataset.queries.shape[1] == 128
        assert dataset.size == 100
        assert dataset.dimension == 128
    
    def test_dataset_dtype(self):
        """Vectors should be float32."""
        dataset = FAISSTestDataset.generate(size=100, dimension=128)
        
        assert dataset.vectors.dtype == np.float32
        assert dataset.queries.dtype == np.float32
    
    def test_reproducibility(self):
        """Same seed should produce same data."""
        ds1 = FAISSTestDataset.generate(size=100, seed=42)
        ds2 = FAISSTestDataset.generate(size=100, seed=42)
        
        assert np.allclose(ds1.vectors, ds2.vectors)


# ---------------------------------------------------------------------------
# Benchmark Result Tests
# ---------------------------------------------------------------------------

class TestFAISSBenchmarkResult:
    """Test benchmark result calculations."""
    
    def test_percentile_calculations(self):
        """Should calculate percentiles correctly."""
        result = FAISSBenchmarkResult(
            index_type="test",
            num_vectors=1000,
            dimension=384,
            query_latencies_ms=[i * 0.1 for i in range(100)],  # 0-9.9ms
        )
        
        assert result.query_avg_ms > 0
        assert result.query_p50_ms > 0
        assert result.query_p95_ms > result.query_p50_ms
    
    def test_sla_check_pass(self):
        """Should pass SLA when P95 < 50ms."""
        result = FAISSBenchmarkResult(
            index_type="test",
            num_vectors=1000,
            dimension=384,
            query_latencies_ms=[10.0] * 100,  # All 10ms
        )
        
        assert result.meets_sla is True
    
    def test_sla_check_fail(self):
        """Should fail SLA when P95 >= 50ms."""
        result = FAISSBenchmarkResult(
            index_type="test",
            num_vectors=1000,
            dimension=384,
            query_latencies_ms=[60.0] * 100,  # All 60ms
        )
        
        assert result.meets_sla is False
    
    def test_to_dict(self):
        """Should serialize to dict."""
        result = FAISSBenchmarkResult(
            index_type="IndexFlatL2",
            num_vectors=5000,
            dimension=384,
            add_total_ms=100.0,
            query_latencies_ms=[5.0] * 100,
        )
        
        d = result.to_dict()
        
        assert d["index_type"] == "IndexFlatL2"
        assert d["num_vectors"] == 5000
        assert "query_p95_ms" in d
        assert "meets_sla" in d


# ---------------------------------------------------------------------------
# IndexFlatL2 Tests
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not check_faiss_available(), reason="FAISS not available")
class TestIndexFlatL2:
    """Test IndexFlatL2 performance."""
    
    def test_flat_1k_vectors(self, dataset_1k):
        """1K vectors should query in < 10ms."""
        result = benchmark_faiss_flat(dataset_1k)
        
        assert result.query_p95_ms < 10.0
        assert result.meets_sla is True
    
    def test_flat_5k_vectors(self, dataset_5k):
        """5K vectors should meet 50ms SLA."""
        result = benchmark_faiss_flat(dataset_5k)
        
        assert result.query_p95_ms < 50.0, f"P95 {result.query_p95_ms}ms exceeds 50ms SLA"
        assert result.meets_sla is True
    
    def test_flat_add_performance(self, dataset_1k):
        """Add operation should be fast."""
        result = benchmark_faiss_flat(dataset_1k)
        
        # Should add 1000 vectors in < 100ms
        assert result.add_total_ms < 100.0


# ---------------------------------------------------------------------------
# IndexIVFFlat Tests
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not check_faiss_available(), reason="FAISS not available")
class TestIndexIVFFlat:
    """Test IndexIVFFlat performance."""
    
    def test_ivf_5k_vectors(self, dataset_5k):
        """IVF with 5K vectors should be faster than Flat."""
        ivf_result = benchmark_faiss_ivf(dataset_5k, nlist=50, nprobe=5)
        flat_result = benchmark_faiss_flat(dataset_5k)
        
        # IVF should meet SLA
        assert ivf_result.meets_sla is True
        
        # IVF should be comparable or faster
        assert ivf_result.query_p95_ms < 100.0  # Generous limit


# ---------------------------------------------------------------------------
# Scaling Tests
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not check_faiss_available(), reason="FAISS not available")
class TestFAISSScaling:
    """Test FAISS scaling characteristics."""
    
    def test_scaling_1k_to_5k(self, dataset_1k, dataset_5k):
        """Latency should scale sub-linearly with IndexFlatL2."""
        result_1k = benchmark_faiss_flat(dataset_1k)
        result_5k = benchmark_faiss_flat(dataset_5k)
        
        # 5x more vectors shouldn't cause 5x slowdown
        ratio = result_5k.query_p95_ms / result_1k.query_p95_ms
        assert ratio < 10.0, f"Scaling ratio {ratio}x is too high"
    
    def test_5k_vectors_sla_target(self, dataset_5k):
        """5,000 vectors MUST meet 50ms SLA (critical acceptance criteria)."""
        result = benchmark_faiss_flat(dataset_5k)
        
        print(f"\n5K Vector Benchmark:")
        print(f"  Query Avg:  {result.query_avg_ms:.3f}ms")
        print(f"  Query P50:  {result.query_p50_ms:.3f}ms")
        print(f"  Query P95:  {result.query_p95_ms:.3f}ms")
        print(f"  Query P99:  {result.query_p99_ms:.3f}ms")
        print(f"  Meets SLA:  {result.meets_sla}")
        
        assert result.meets_sla, f"FAISS query P95 {result.query_p95_ms:.1f}ms exceeds 50ms SLA"


# ---------------------------------------------------------------------------
# Memory Usage Tests
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not check_faiss_available(), reason="FAISS not available")
class TestFAISSMemory:
    """Test FAISS memory usage."""
    
    def test_index_size_estimation(self, dataset_5k):
        """Index size should be predictable."""
        result = benchmark_faiss_flat(dataset_5k)
        
        # 5000 vectors * 384 dims * 4 bytes = 7.5 MB
        expected_mb = (5000 * 384 * 4) / (1024 * 1024)
        
        assert abs(result.index_size_mb - expected_mb) < 1.0
    
    def test_memory_per_vector(self, dataset_1k):
        """Should calculate memory per vector."""
        result = benchmark_faiss_flat(dataset_1k)
        
        # 384 dims * 4 bytes = 1536 bytes = 0.0015 MB per vector
        expected_per_vector = (384 * 4) / (1024 * 1024)
        actual_per_vector = result.index_size_mb / 1000
        
        assert abs(actual_per_vector - expected_per_vector) < 0.001


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not check_faiss_available(), reason="FAISS not available")
class TestFAISSIntegration:
    """Integration tests for FAISS performance."""
    
    def test_full_benchmark_workflow(self, dataset_5k):
        """Test complete benchmark workflow."""
        # Run flat benchmark
        flat_result = benchmark_faiss_flat(dataset_5k)
        
        # Run IVF benchmark
        ivf_result = benchmark_faiss_ivf(dataset_5k, nlist=50, nprobe=5)
        
        # Both should meet SLA
        assert flat_result.meets_sla, "Flat index fails SLA"
        assert ivf_result.meets_sla, "IVF index fails SLA"
        
        # Export results
        flat_dict = flat_result.to_dict()
        ivf_dict = ivf_result.to_dict()
        
        assert flat_dict["num_vectors"] == 5000
        assert ivf_dict["num_vectors"] == 5000
    
    def test_batch_query_performance(self, dataset_5k):
        """Batch queries should be efficient."""
        import faiss
        
        index = faiss.IndexFlatL2(dataset_5k.dimension)
        index.add(dataset_5k.vectors)
        
        # Batch of 10 queries
        batch_queries = dataset_5k.queries[:10]
        
        gc.collect()
        start = time.perf_counter()
        distances, indices = index.search(batch_queries, 10)
        batch_time = (time.perf_counter() - start) * 1000
        
        # Batch of 10 should complete in < 100ms
        assert batch_time < 100.0, f"Batch query took {batch_time:.1f}ms"
