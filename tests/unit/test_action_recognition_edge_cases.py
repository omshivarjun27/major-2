"""Action recognition edge cases: empty clips, invalid frames, boundary conditions."""

from __future__ import annotations

from unittest.mock import patch

import numpy as np

from core.action.action_recognizer import (
    ALERT_ACTIONS,
    ActionConfig,
    ActionRecognizer,
    ActionResult,
    ActionType,
    ClipBuffer,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _frame(h: int = 64, w: int = 64, channels: int = 3) -> np.ndarray:
    """Create a random RGB frame."""
    return np.random.randint(0, 255, (h, w, channels), dtype=np.uint8)


def _grayscale_frame(h: int = 64, w: int = 64) -> np.ndarray:
    """Create a random grayscale frame."""
    return np.random.randint(0, 255, (h, w), dtype=np.uint8)


# ===========================================================================
# ClipBuffer edge cases
# ===========================================================================


class TestClipBufferEdgeCases:
    """Edge cases for the sliding-window clip buffer."""

    def test_empty_buffer_count(self):
        """New buffer should have count=0."""
        buf = ClipBuffer()
        assert buf.count == 0

    def test_add_single_frame_not_ready(self):
        """Single frame should not trigger analysis (default length=16)."""
        buf = ClipBuffer()
        ready = buf.add_frame(_frame())
        assert ready is False
        assert buf.count == 1

    def test_buffer_ready_at_length(self):
        """Buffer should signal ready when length is reached at stride boundary."""
        buf = ClipBuffer(length=4, stride=2)
        for i in range(4):
            ready = buf.add_frame(_frame())
        # Frame count=4, length=4, 4 % 2 == 0 → ready
        assert ready is True

    def test_buffer_maxlen_enforced(self):
        """Buffer should never exceed maxlen."""
        buf = ClipBuffer(length=4, stride=1)
        for _ in range(100):
            buf.add_frame(_frame())
        assert buf.count == 4

    def test_get_clip_returns_correct_frames(self):
        """get_clip should return the buffered frames."""
        buf = ClipBuffer(length=3, stride=1)
        frames = [_frame() for _ in range(3)]
        for f in frames:
            buf.add_frame(f)
        clip = buf.get_clip()
        assert len(clip) == 3

    def test_clear_resets_buffer(self):
        """clear() should reset buffer to empty."""
        buf = ClipBuffer(length=4, stride=1)
        for _ in range(4):
            buf.add_frame(_frame())
        buf.clear()
        assert buf.count == 0
        assert buf.get_clip() == []

    def test_timestamps_tracked(self):
        """Timestamps should be recorded for each frame."""
        buf = ClipBuffer(length=4, stride=1)
        ts_values = [100.0, 200.0, 300.0]
        for ts in ts_values:
            buf.add_frame(_frame(), timestamp_ms=ts)
        timestamps = buf.get_timestamps()
        assert timestamps == ts_values

    def test_zero_timestamp_auto_filled(self):
        """Zero timestamp should be auto-filled with current time."""
        buf = ClipBuffer(length=4, stride=1)
        buf.add_frame(_frame(), timestamp_ms=0.0)
        ts = buf.get_timestamps()
        assert ts[0] > 0  # auto-generated

    def test_stride_one_always_ready_after_length(self):
        """With stride=1, every frame after length should be ready."""
        buf = ClipBuffer(length=3, stride=1)
        results = []
        for i in range(6):
            results.append(buf.add_frame(_frame()))
        # Frames 0,1: not ready. Frame 2: count=3, frame_count=3, 3%1==0 → True
        assert results[2] is True


# ===========================================================================
# ActionConfig edge cases
# ===========================================================================


class TestActionConfigEdgeCases:
    """Edge cases for ActionConfig defaults and overrides."""

    def test_default_config_values(self):
        """Default config should have expected values."""
        cfg = ActionConfig()
        assert cfg.clip_length == 16
        assert cfg.clip_stride == 4
        assert cfg.min_confidence == 0.3

    def test_zero_clip_length(self):
        """Zero clip length is allowed at config level."""
        cfg = ActionConfig(clip_length=0)
        assert cfg.clip_length == 0

    def test_custom_flow_scale(self):
        """Custom flow_scale should be stored."""
        cfg = ActionConfig(flow_scale=0.25)
        assert cfg.flow_scale == 0.25


# ===========================================================================
# ActionResult edge cases
# ===========================================================================


class TestActionResultEdgeCases:
    """Edge cases for ActionResult data structure."""

    def test_to_dict_includes_is_alert(self):
        """to_dict should include is_alert field."""
        r = ActionResult(
            action_type=ActionType.APPROACHING,
            confidence=0.8,
            flow_magnitude=5.0,
            flow_direction="towards",
        )
        d = r.to_dict()
        assert d["is_alert"] is True

    def test_non_alert_action(self):
        """Non-alert actions should have is_alert=False."""
        r = ActionResult(
            action_type=ActionType.SITTING,
            confidence=0.7,
            flow_magnitude=0.1,
            flow_direction="none",
        )
        assert r.to_dict()["is_alert"] is False

    def test_user_cue_for_alert_actions(self):
        """Alert actions should have non-empty user_cue."""
        for action in ALERT_ACTIONS:
            r = ActionResult(
                action_type=action,
                confidence=0.8,
                flow_magnitude=3.0,
                flow_direction="towards",
            )
            assert r.user_cue != "", f"Missing cue for {action}"

    def test_user_cue_unknown_action(self):
        """UNKNOWN action should have empty user_cue."""
        r = ActionResult(
            action_type=ActionType.UNKNOWN,
            confidence=0.3,
            flow_magnitude=0.0,
            flow_direction="none",
        )
        assert r.user_cue == ""

    def test_no_action_user_cue(self):
        """NO_ACTION should have empty user_cue."""
        r = ActionResult(
            action_type=ActionType.NO_ACTION,
            confidence=0.5,
            flow_magnitude=0.0,
            flow_direction="none",
        )
        assert r.user_cue == ""

    def test_to_dict_rounds_values(self):
        """to_dict should round confidence and flow_magnitude."""
        r = ActionResult(
            action_type=ActionType.WAVING,
            confidence=0.77777,
            flow_magnitude=3.14159,
            flow_direction="left",
        )
        d = r.to_dict()
        assert d["confidence"] == 0.778
        assert d["flow_magnitude"] == 3.14


# ===========================================================================
# ActionRecognizer edge cases
# ===========================================================================


class TestActionRecognizerEdgeCases:
    """Edge cases for ActionRecognizer analysis."""

    def test_analyze_empty_buffer(self):
        """Analyzing with empty buffer should return empty list."""
        recognizer = ActionRecognizer(ActionConfig(clip_length=4, clip_stride=1))
        results = recognizer.analyze()
        assert results == []

    def test_analyze_single_frame(self):
        """Analyzing with one frame should return empty list."""
        recognizer = ActionRecognizer(ActionConfig(clip_length=4, clip_stride=1))
        recognizer.add_frame(_frame())
        results = recognizer.analyze()
        assert results == []

    def test_analyze_identical_frames_no_action(self):
        """Identical frames should produce NO_ACTION or low-magnitude result."""
        cfg = ActionConfig(clip_length=4, clip_stride=1)
        recognizer = ActionRecognizer(cfg)
        static_frame = _frame()
        for _ in range(4):
            recognizer.add_frame(static_frame.copy())
        results = recognizer.analyze()
        assert len(results) >= 1
        # With no motion, flow should be zero or near-zero
        assert results[0].flow_magnitude < 1.0 or results[0].action_type == ActionType.NO_ACTION

    def test_add_frame_returns_bool(self):
        """add_frame should always return a boolean."""
        recognizer = ActionRecognizer(ActionConfig(clip_length=4, clip_stride=1))
        result = recognizer.add_frame(_frame())
        assert isinstance(result, bool)

    def test_recognizer_without_cv2(self):
        """Recognizer should handle missing cv2 gracefully."""
        with patch("core.action.action_recognizer._CV2_AVAILABLE", False):
            recognizer = ActionRecognizer(ActionConfig(clip_length=2, clip_stride=1))
            recognizer.add_frame(_frame())
            recognizer.add_frame(_frame())
            results = recognizer.analyze()
            # Should return NO_ACTION when cv2 unavailable (flow computation fails)
            assert len(results) >= 1

    def test_recognizer_with_grayscale_frames(self):
        """Recognizer should handle grayscale frames."""
        recognizer = ActionRecognizer(ActionConfig(clip_length=2, clip_stride=1))
        recognizer.add_frame(_grayscale_frame())
        recognizer.add_frame(_grayscale_frame())
        results = recognizer.analyze()
        assert isinstance(results, list)

    def test_model_path_nonexistent(self):
        """Nonexistent model path should not crash initialization."""
        cfg = ActionConfig(model_path="/nonexistent/model.pt")
        recognizer = ActionRecognizer(cfg)
        assert recognizer._model is None


# ===========================================================================
# ActionType enum edge cases
# ===========================================================================


class TestActionTypeEdgeCases:
    """Edge cases for ActionType enum."""

    def test_all_action_types_have_string_values(self):
        """Every ActionType should have a string value."""
        for at in ActionType:
            assert isinstance(at.value, str)
            assert len(at.value) > 0

    def test_alert_actions_are_subset(self):
        """ALERT_ACTIONS should all be valid ActionType members."""
        for action in ALERT_ACTIONS:
            assert isinstance(action, ActionType)

    def test_action_type_from_string(self):
        """ActionType should be constructible from its value string."""
        at = ActionType("approaching")
        assert at == ActionType.APPROACHING
