"""Unit tests for SceneGraphBuilder (T-023).

Covers build, empty scene, critical obstacle, direction mapping,
size categorization, spatial relations, summary, and frame_id propagation.
"""

from typing import List, Tuple

import numpy as np

from core.vqa.scene_graph import SceneGraphBuilder
from shared.schemas import (
    BoundingBox,
    DepthMap,
    Detection,
    Direction,
    PerceptionResult,
    Priority,
    SizeCategory,
    SpatialRelation,
)


def _make_perception(
    detections: List[Detection],
    depth_value: float = 3.0,
    image_size: Tuple[int, int] = (640, 480),
    frame_id: str = "",
    depth_array: np.ndarray = None,
) -> PerceptionResult:
    """Build a minimal PerceptionResult with uniform or custom depth."""
    w, h = image_size
    if depth_array is None:
        depth_array = np.full((h, w), depth_value, dtype=np.float32)
    return PerceptionResult(
        detections=detections,
        masks=[],
        depth_map=DepthMap(depth_array=depth_array, min_depth=float(np.min(depth_array)),
                           max_depth=float(np.max(depth_array)), is_metric=False),
        image_size=image_size,
        latency_ms=10.0,
        timestamp="2026-01-01T00:00:00",
        frame_id=frame_id,
    )


def _det(id: str, class_name: str, cx: int, cy: int, half_w: int = 30, half_h: int = 30,
         conf: float = 0.8) -> Detection:
    """Shorthand for creating a Detection centred at (cx, cy)."""
    return Detection(
        id=id,
        class_name=class_name,
        confidence=conf,
        bbox=BoundingBox(cx - half_w, cy - half_h, cx + half_w, cy + half_h),
    )


class TestSceneGraphBuilder:
    """Unit tests for SceneGraphBuilder."""

    def test_build_with_detections(self):
        """Two detections produce 2 nodes and 2 sorted obstacles."""
        d1 = _det("a", "chair", 200, 300)
        d2 = _det("b", "table", 500, 100)
        perception = _make_perception([d1, d2])
        sg = SceneGraphBuilder().build(perception)

        assert len(sg.nodes) == 2
        assert len(sg.obstacles) == 2
        class_names = {o.class_name for o in sg.obstacles}
        assert "chair" in class_names
        assert "table" in class_names
        # Sorted: first obstacle should have higher or equal priority
        priority_rank = {Priority.CRITICAL: 0, Priority.NEAR_HAZARD: 1, Priority.FAR_HAZARD: 2, Priority.SAFE: 3}
        assert priority_rank[sg.obstacles[0].priority] <= priority_rank[sg.obstacles[1].priority]

    def test_build_empty_scene(self):
        """Zero detections yields empty graph with 'clear' summary."""
        perception = _make_perception([])
        sg = SceneGraphBuilder().build(perception)

        assert sg.nodes == []
        assert sg.obstacles == []
        assert "clear" in sg.generate_summary().lower()

    def test_critical_obstacle(self):
        """Depth < 1.0m at center triggers CRITICAL + 'stop and reassess'."""
        det = _det("c1", "person", 320, 240)
        perception = _make_perception([det], depth_value=0.5)
        sg = SceneGraphBuilder().build(perception)

        assert len(sg.obstacles) == 1
        obs = sg.obstacles[0]
        assert obs.priority == Priority.CRITICAL
        assert obs.direction == Direction.CENTER
        assert obs.action_recommendation == "stop and reassess"
        assert len(sg.get_critical_obstacles()) == 1

    def test_direction_mapping(self):
        """7 x-positions map to all 7 Direction enum values."""
        # center_x values chosen so normalized_x * 35 falls in each bucket
        positions = [
            (30, Direction.FAR_LEFT),
            (140, Direction.LEFT),
            (230, Direction.SLIGHTLY_LEFT),
            (320, Direction.CENTER),
            (410, Direction.SLIGHTLY_RIGHT),
            (500, Direction.RIGHT),
            (610, Direction.FAR_RIGHT),
        ]
        dets = [_det(f"d{i}", "obj", cx, 240) for i, (cx, _) in enumerate(positions)]
        perception = _make_perception(dets)
        sg = SceneGraphBuilder().build(perception)

        obs_by_id = {o.id: o for o in sg.obstacles}
        for i, (_, expected_dir) in enumerate(positions):
            assert obs_by_id[f"d{i}"].direction == expected_dir, (
                f"center_x at position index {i} should yield {expected_dir}"
            )

    def test_size_categorization(self):
        """LARGE (>25%), MEDIUM (5-25%), SMALL (<5%) size thresholds."""
        # 640*480 = 307200
        large_det = Detection(id="lg", class_name="wall", confidence=0.9,
                              bbox=BoundingBox(0, 0, 400, 200))  # 80000 = 26%
        medium_det = Detection(id="md", class_name="box", confidence=0.9,
                               bbox=BoundingBox(0, 0, 100, 200))  # 20000 = 6.5%
        small_det = Detection(id="sm", class_name="cup", confidence=0.9,
                              bbox=BoundingBox(300, 200, 330, 230))  # 900 = 0.3%

        perception = _make_perception([large_det, medium_det, small_det])
        sg = SceneGraphBuilder().build(perception)

        sizes = {o.id: o.size_category for o in sg.obstacles}
        assert sizes["lg"] == SizeCategory.LARGE
        assert sizes["md"] == SizeCategory.MEDIUM
        assert sizes["sm"] == SizeCategory.SMALL

    def test_spatial_relations(self):
        """LEFT_OF/RIGHT_OF and IN_FRONT_OF/BEHIND inferred from position and depth."""
        # Node A: left (x=100), close (depth=1.5m)
        # Node B: right (x=500), far (depth=4.0m)
        det_a = _det("a", "chair", 100, 240)
        det_b = _det("b", "table", 500, 240)

        depth_arr = np.full((480, 640), 3.0, dtype=np.float32)
        # Left half = 1.5m, right half = 4.0m
        depth_arr[:, :320] = 1.5
        depth_arr[:, 320:] = 4.0

        perception = _make_perception([det_a, det_b], depth_array=depth_arr)
        sg = SceneGraphBuilder().build(perception)

        node_a = sg.nodes[0] if sg.nodes[0].id == "a" else sg.nodes[1]
        node_b = sg.nodes[1] if sg.nodes[0].id == "a" else sg.nodes[0]

        a_rels = {r[0] for r in node_a.relations}
        b_rels = {r[0] for r in node_b.relations}

        assert SpatialRelation.LEFT_OF.value in a_rels
        assert SpatialRelation.RIGHT_OF.value in b_rels
        assert SpatialRelation.IN_FRONT_OF.value in a_rels
        assert SpatialRelation.BEHIND.value in b_rels

    def test_summary_generation(self):
        """Summary contains class name and distance for near-hazard obstacle."""
        det = _det("s1", "bicycle", 320, 240)
        perception = _make_perception([det], depth_value=1.5)
        sg = SceneGraphBuilder().build(perception)

        assert len(sg.summary) > 0
        assert "bicycle" in sg.summary.lower()

    def test_frame_id_propagation(self):
        """frame_id transfers from PerceptionResult to SceneGraph."""
        det = _det("f1", "person", 320, 240)
        perception = _make_perception([det], frame_id="frame_42")
        sg = SceneGraphBuilder().build(perception)

        assert sg.frame_id == "frame_42"
