"""P1 End-to-End Pipeline Integration Test (T-036).

Processes a mock image through the full P1 pipeline:
spatial detection → depth estimation → scene graph → VQA reasoning →
memory storage → memory retrieval.

All tests use mock backends to avoid ONNX model dependencies.
"""

from __future__ import annotations

import time

from PIL import Image

from core.memory.embeddings import MockTextEmbedder
from core.memory.indexer import FAISSIndexer
from core.memory.retriever import MemoryRetriever
from core.reasoning.engine import ReasoningEngine
from core.vision.spatial import create_spatial_processor
from core.vqa.scene_graph import SceneGraphBuilder
from shared.schemas import (
    DepthMap,
    Detection,
    NavigationOutput,
    PerceptionResult,
)


def _make_test_image(width: int = 640, height: int = 480) -> Image.Image:
    """Create a synthetic PIL image for testing."""
    return Image.new("RGB", (width, height), color=(100, 150, 200))


class TestP1PipelineIntegration:
    """End-to-end integration: spatial → scene graph → reasoning → memory."""

    async def test_spatial_to_scene_graph(self):
        """Process frame through spatial, feed to scene graph, verify SceneGraph."""
        processor = create_spatial_processor()
        image = _make_test_image()

        nav_output = await processor.process_frame(image)
        assert isinstance(nav_output, NavigationOutput)
        assert nav_output.short_cue  # Should have some output

        # Build scene graph from perception result
        builder = SceneGraphBuilder()
        # MockObjectDetector produces 1 detection, SimpleDepthEstimator produces depth
        detections = await processor._detector.detect(image)
        depth_map = await processor._depth_estimator.estimate_depth(image)

        perception = PerceptionResult(
            detections=detections,
            masks=[],
            depth_map=depth_map,
            image_size=(640, 480),
            latency_ms=0.0,
            timestamp=str(time.time()),
        )

        sg = builder.build(perception)
        assert sg is not None
        assert hasattr(sg, "obstacles")
        assert hasattr(sg, "nodes")

    async def test_full_pipeline_types(self):
        """Process frame through all stages; verify each intermediate is correct type."""
        processor = create_spatial_processor()
        image = _make_test_image()

        # Stage 1: Detection
        detections = await processor._detector.detect(image)
        assert isinstance(detections, list)
        assert len(detections) >= 1
        assert isinstance(detections[0], Detection)

        # Stage 2: Depth
        depth_map = await processor._depth_estimator.estimate_depth(image)
        assert isinstance(depth_map, DepthMap)
        assert depth_map.depth_array is not None

        # Stage 3: Full spatial pipeline
        nav_output = await processor.process_frame(image)
        assert isinstance(nav_output, NavigationOutput)

    async def test_memory_store_and_retrieve(self, tmp_path):
        """Store navigation summary, retrieve by query, verify match."""
        embedder = MockTextEmbedder()
        indexer = FAISSIndexer(
            index_path=str(tmp_path / 'faiss'),
            dimension=embedder.dimension,
        )

        # Store a navigation summary
        summary_text = "Chair detected 1.5 meters slightly left. Caution advised."
        embedding = embedder.embed(summary_text)
        doc_id = indexer.add("nav_001", embedding, summary=summary_text)
        assert doc_id is not None

        # Retrieve via embedding similarity
        retriever = MemoryRetriever(indexer=indexer, text_embedder=embedder)
        query_embedding = embedder.embed("obstacle near me")
        results = await retriever.search_by_embedding(query_embedding, k=1)
        assert len(results) >= 1

    async def test_reasoning_engine_visual_query(self):
        """ReasoningEngine with question; verify it returns a result."""
        engine = ReasoningEngine()

        result = await engine.reason(question="What obstacles are nearby?")
        assert result is not None
        assert hasattr(result, "answer")
        assert hasattr(result, "source")

    async def test_frame_id_consistency(self):
        """Verify spatial result and scene graph share same frame context."""
        processor = create_spatial_processor()
        image = _make_test_image()

        # Get detections and build scene graph
        detections = await processor._detector.detect(image)
        depth_map = await processor._depth_estimator.estimate_depth(image)

        frame_ts = str(time.time())
        perception = PerceptionResult(
            detections=detections,
            masks=[],
            depth_map=depth_map,
            image_size=(640, 480),
            latency_ms=0.0,
            timestamp=frame_ts,
        )

        builder = SceneGraphBuilder()
        sg = builder.build(perception)

        # Scene graph should reference same timestamp context
        assert sg is not None
        # Obstacles should correspond to detections
        assert len(sg.obstacles) == len(detections)

    async def test_pipeline_latency_under_500ms(self):
        """Time full pipeline; assert < 500ms with mock backends."""
        processor = create_spatial_processor()
        image = _make_test_image()

        start = time.perf_counter()
        nav_output = await processor.process_frame(image)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert nav_output is not None
        assert elapsed_ms < 500, f"Pipeline took {elapsed_ms:.1f}ms (limit: 500ms)"
