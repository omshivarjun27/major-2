"""Tests for Multi-Frame VQA (T-125) and Scene Narrator (T-126)."""

from __future__ import annotations

import numpy as np
import pytest

from core.vqa.multi_frame_vqa import (
    FrameChange,
    MultiFrameAnalyzer,
    MultiFrameConfig,
    MultiFrameResult,
    create_multi_frame_analyzer,
)
from core.vqa.scene_narrator import (
    NarrationConfig,
    NarrationEvent,
    SceneNarrator,
    create_scene_narrator,
)


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def mfa_config():
    return MultiFrameConfig(max_frames=5, min_change_threshold=0.1)


@pytest.fixture
def analyzer(mfa_config):
    return MultiFrameAnalyzer(mfa_config)


@pytest.fixture
def narrator():
    return SceneNarrator()


@pytest.fixture
def static_frames():
    """5 identical frames."""
    frame = np.zeros((64, 64, 3), dtype=np.uint8)
    return [frame.copy() for _ in range(5)]


@pytest.fixture
def changing_frames():
    """5 frames with increasing brightness."""
    return [np.full((64, 64, 3), i * 50, dtype=np.uint8) for i in range(5)]


# ===========================================================================
# T-125: Multi-Frame VQA — Config
# ===========================================================================

class TestMultiFrameConfig:
    def test_defaults(self):
        cfg = MultiFrameConfig()
        assert cfg.max_frames == 5
        assert cfg.frame_interval_ms == 500.0
        assert cfg.comparison_mode == "sequential"
        assert cfg.min_change_threshold == 0.1
        assert cfg.enable_diff_detection is True
        assert cfg.timeout_ms == 300.0


class TestFrameChange:
    def test_to_dict(self):
        fc = FrameChange(frame_index=1, change_type="appeared", description="test", confidence=0.7)
        d = fc.to_dict()
        assert d["frame_index"] == 1
        assert d["change_type"] == "appeared"
        assert d["confidence"] == 0.7

    def test_with_region(self):
        fc = FrameChange(frame_index=0, change_type="moved", region=(10, 20, 30, 40))
        d = fc.to_dict()
        assert d["region"] == [10, 20, 30, 40]


class TestMultiFrameResult:
    def test_to_dict(self):
        r = MultiFrameResult(frames_analyzed=3, scene_summary="stable", confidence=0.6)
        d = r.to_dict()
        assert d["frames_analyzed"] == 3
        assert d["scene_summary"] == "stable"

    def test_user_cue_stable(self):
        r = MultiFrameResult(scene_summary="stable")
        assert r.user_cue == "stable"

    def test_user_cue_with_change(self):
        r = MultiFrameResult(
            has_significant_change=True,
            temporal_narrative="Something moved",
        )
        assert r.user_cue == "Something moved"

    def test_user_cue_default(self):
        r = MultiFrameResult()
        assert r.user_cue == "Scene appears stable."


# ===========================================================================
# T-125: Multi-Frame Analyzer
# ===========================================================================

class TestMultiFrameAnalyzer:
    def test_add_frame_single(self, analyzer):
        frame = np.zeros((10, 10, 3), dtype=np.uint8)
        ready = analyzer.add_frame(frame)
        assert ready is False

    def test_add_frame_enough(self, analyzer):
        frame = np.zeros((10, 10, 3), dtype=np.uint8)
        analyzer.add_frame(frame)
        ready = analyzer.add_frame(frame)
        assert ready is True

    async def test_analyze_static(self, analyzer, static_frames):
        result = await analyzer.analyze(static_frames)
        assert result.frames_analyzed == 5
        assert result.has_significant_change is False

    async def test_analyze_changing(self, analyzer, changing_frames):
        result = await analyzer.analyze(changing_frames)
        assert result.frames_analyzed == 5
        assert len(result.changes) > 0
        assert result.has_significant_change is True

    async def test_analyze_single_frame(self, analyzer):
        result = await analyzer.analyze([np.zeros((10, 10, 3))])
        assert result.frames_analyzed == 1
        assert "Insufficient" in result.scene_summary

    async def test_analyze_empty(self, analyzer):
        result = await analyzer.analyze([])
        assert result.frames_analyzed == 0

    async def test_analyze_from_buffer(self, analyzer):
        f1 = np.zeros((10, 10, 3), dtype=np.uint8)
        f2 = np.full((10, 10, 3), 200, dtype=np.uint8)
        analyzer.add_frame(f1)
        analyzer.add_frame(f2)
        result = await analyzer.analyze()
        assert result.frames_analyzed == 2

    def test_compute_frame_diff_identical(self, analyzer):
        f = np.zeros((10, 10, 3), dtype=np.uint8)
        assert analyzer._compute_frame_diff(f, f) == 0.0

    def test_compute_frame_diff_different(self, analyzer):
        f1 = np.zeros((10, 10, 3), dtype=np.uint8)
        f2 = np.full((10, 10, 3), 255, dtype=np.uint8)
        diff = analyzer._compute_frame_diff(f1, f2)
        assert diff == pytest.approx(1.0)

    def test_compute_frame_diff_shape_mismatch(self, analyzer):
        f1 = np.zeros((10, 10, 3), dtype=np.uint8)
        f2 = np.zeros((20, 20, 3), dtype=np.uint8)
        diff = analyzer._compute_frame_diff(f1, f2)
        assert diff >= 0  # Should not crash

    def test_clear(self, analyzer):
        analyzer.add_frame(np.zeros((10, 10, 3)))
        analyzer.clear()
        assert analyzer.health()["buffer_size"] == 0

    def test_health(self, analyzer):
        h = analyzer.health()
        assert h["max_frames"] == 5
        assert h["total_analyses"] == 0

    def test_factory(self):
        a = create_multi_frame_analyzer()
        assert isinstance(a, MultiFrameAnalyzer)

    async def test_narrative_generation(self, analyzer, changing_frames):
        result = await analyzer.analyze(changing_frames)
        assert result.temporal_narrative != ""

    async def test_scene_summary(self, analyzer, static_frames):
        result = await analyzer.analyze(static_frames)
        assert "stable" in result.scene_summary.lower() or "0 change" in result.scene_summary.lower()


# ===========================================================================
# T-126: Scene Narrator — Config & Data
# ===========================================================================

class TestNarrationConfig:
    def test_defaults(self):
        cfg = NarrationConfig()
        assert cfg.narration_interval_ms == 3000.0
        assert cfg.min_change_for_narration == 0.15
        assert cfg.max_narration_length == 100
        assert "person" in cfg.priority_objects
        assert cfg.suppress_repeat_ms == 10000.0
        assert cfg.verbosity == "normal"


class TestNarrationEvent:
    def test_to_dict(self):
        e = NarrationEvent(
            event_type="new_object",
            description="Chair appeared",
            priority="normal",
            objects_involved=["chair"],
            timestamp_ms=1000,
        )
        d = e.to_dict()
        assert d["event_type"] == "new_object"
        assert d["priority"] == "normal"


# ===========================================================================
# T-126: Scene Narrator
# ===========================================================================

class TestSceneNarrator:
    async def test_empty_scene(self, narrator):
        events = await narrator.narrate([], timestamp_ms=1000)
        assert events == []

    async def test_new_object(self, narrator):
        events = await narrator.narrate(
            [{"label": "person", "confidence": 0.9}],
            timestamp_ms=1000,
        )
        assert len(events) >= 1
        assert any(e.event_type == "new_object" for e in events)

    async def test_object_departed(self, narrator):
        # First: add person
        await narrator.narrate(
            [{"label": "person", "confidence": 0.9}],
            timestamp_ms=1000,
        )
        # Second: person gone
        events = await narrator.narrate([], timestamp_ms=12000)
        assert any(e.event_type == "object_gone" for e in events)

    async def test_movement_detection(self, narrator):
        await narrator.narrate(
            [{"label": "car", "bbox": [0, 0, 100, 100]}],
            timestamp_ms=1000,
        )
        events = await narrator.narrate(
            [{"label": "car", "bbox": [200, 0, 300, 100]}],
            timestamp_ms=12000,
        )
        assert any(e.event_type == "movement" for e in events)

    async def test_hazard_detection(self, narrator):
        events = await narrator.narrate(
            [{"label": "car", "distance_m": 1.5}],
            timestamp_ms=1000,
        )
        hazards = [e for e in events if e.event_type == "hazard"]
        assert len(hazards) >= 1
        assert hazards[0].priority == "critical"

    async def test_priority_sorting(self, narrator):
        events = await narrator.narrate(
            [
                {"label": "chair"},
                {"label": "car", "distance_m": 2.0},
            ],
            timestamp_ms=1000,
        )
        # Hazard (critical/high) should come before new_object (normal)
        if len(events) >= 2:
            priorities = [e.priority for e in events]
            assert priorities.index("critical") < priorities.index("normal") or \
                   priorities.index("high") < priorities.index("normal")

    async def test_suppression(self, narrator):
        # First narrate: person appears
        events1 = await narrator.narrate(
            [{"label": "person"}], timestamp_ms=1000
        )
        assert len(events1) >= 1

        # Second narrate same: should be suppressed (within suppress window)
        narrator._last_scene_state["objects"] = {}  # Reset to trigger "new" again
        events2 = await narrator.narrate(
            [{"label": "person"}], timestamp_ms=2000
        )
        # new_object event type should be suppressed
        new_obj_events = [e for e in events2 if e.event_type == "new_object"]
        assert len(new_obj_events) == 0

    async def test_suppression_expires(self, narrator):
        narrator.config.suppress_repeat_ms = 1000
        await narrator.narrate([{"label": "person"}], timestamp_ms=1000)
        narrator._last_scene_state["objects"] = {}
        events = await narrator.narrate(
            [{"label": "person"}], timestamp_ms=3000
        )
        assert len(events) >= 1

    async def test_priority_objects_flagged_high(self, narrator):
        events = await narrator.narrate(
            [{"label": "person"}], timestamp_ms=1000
        )
        person_events = [e for e in events if "person" in e.objects_involved]
        assert all(e.priority in ("high", "critical") for e in person_events)

    async def test_non_priority_object(self, narrator):
        events = await narrator.narrate(
            [{"label": "plant"}], timestamp_ms=1000
        )
        plant_events = [e for e in events if "plant" in e.objects_involved]
        assert all(e.priority == "normal" for e in plant_events)

    def test_health(self, narrator):
        h = narrator.health()
        assert h["total_narrations"] == 0
        assert h["tracked_objects"] == 0

    def test_factory(self):
        n = create_scene_narrator()
        assert isinstance(n, SceneNarrator)

    async def test_multiple_narrations_update_history(self, narrator):
        await narrator.narrate([{"label": "chair"}], timestamp_ms=1000)
        await narrator.narrate([{"label": "table"}], timestamp_ms=12000)
        assert narrator.health()["history_size"] >= 1

    def test_format_narration(self, narrator):
        events = [
            NarrationEvent("new_object", "Chair appeared"),
            NarrationEvent("hazard", "Car nearby"),
        ]
        result = narrator._format_narration(events)
        assert "Chair appeared" in result
        assert "Car nearby" in result

    def test_format_narration_empty(self, narrator):
        assert narrator._format_narration([]) == ""
