"""
Tests for action_engine — ActionRecognizer, ClipBuffer, ActionResult.
"""

from __future__ import annotations

import numpy as np
import pytest

from core.action.action_recognizer import (
    ActionRecognizer,
    ActionResult,
    ActionConfig,
    ActionType,
    ClipBuffer,
    ALERT_ACTIONS,
)


class TestActionConfig:
    def test_defaults(self):
        cfg = ActionConfig()
        assert cfg.clip_length == 16
        assert cfg.clip_stride == 4
        assert cfg.min_confidence == 0.3


class TestClipBuffer:
    def test_init(self):
        buf = ClipBuffer(length=8, stride=2)
        assert buf.count == 0

    def test_add_frame(self):
        buf = ClipBuffer(length=4, stride=2)
        frame = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        ready = buf.add_frame(frame, timestamp_ms=100)
        assert not ready
        assert buf.count == 1

    def test_buffer_ready(self):
        buf = ClipBuffer(length=4, stride=2)
        frame = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        results = []
        for i in range(8):
            results.append(buf.add_frame(frame, timestamp_ms=i * 100))
        # Should trigger at some point
        assert any(results)

    def test_get_clip(self):
        buf = ClipBuffer(length=4, stride=1)
        for i in range(4):
            frame = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)
            buf.add_frame(frame, timestamp_ms=i * 100)
        clip = buf.get_clip()
        assert len(clip) == 4

    def test_clear(self):
        buf = ClipBuffer(length=4, stride=1)
        frame = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)
        buf.add_frame(frame)
        buf.clear()
        assert buf.count == 0


class TestActionRecognizer:
    def test_init(self):
        rec = ActionRecognizer()
        assert rec is not None

    def test_add_frame(self):
        rec = ActionRecognizer(ActionConfig(clip_length=4, clip_stride=2))
        frame = np.random.randint(0, 255, (120, 160, 3), dtype=np.uint8)
        ready = rec.add_frame(frame, timestamp_ms=100)
        assert isinstance(ready, bool)

    def test_analyze_with_sufficient_frames(self):
        rec = ActionRecognizer(ActionConfig(clip_length=4, clip_stride=1))
        for i in range(5):
            frame = np.random.randint(0, 255, (120, 160, 3), dtype=np.uint8)
            rec.add_frame(frame, timestamp_ms=i * 100)
        results = rec.analyze()
        assert isinstance(results, list)
        if results:
            assert isinstance(results[0], ActionResult)

    def test_analyze_insufficient_frames(self):
        rec = ActionRecognizer(ActionConfig(clip_length=16, clip_stride=4))
        frame = np.random.randint(0, 255, (120, 160, 3), dtype=np.uint8)
        rec.add_frame(frame, timestamp_ms=100)
        results = rec.analyze()
        assert isinstance(results, list)

    def test_action_result_to_dict(self):
        r = ActionResult(
            action_type=ActionType.APPROACHING,
            confidence=0.6,
            flow_magnitude=3.5,
            flow_direction="towards",
            timestamp_ms=1000,
        )
        d = r.to_dict()
        assert d["action_type"] == "approaching"
        assert d["is_alert"] is True

    def test_action_result_user_cue(self):
        r = ActionResult(
            action_type=ActionType.WAVING,
            confidence=0.5,
            flow_magnitude=2.0,
            flow_direction="left",
            timestamp_ms=1000,
        )
        assert "waving" in r.user_cue.lower()

    def test_alert_actions(self):
        assert ActionType.APPROACHING in ALERT_ACTIONS
        assert ActionType.CYCLING in ALERT_ACTIONS
        assert ActionType.STANDING not in ALERT_ACTIONS

    def test_health(self):
        rec = ActionRecognizer()
        h = rec.health()
        assert "cv2_available" in h
        assert "buffer_count" in h


class TestActionType:
    def test_enum_values(self):
        assert ActionType.APPROACHING.value == "approaching"
        assert ActionType.NO_ACTION.value == "no_action"

    def test_enum_iteration(self):
        types = list(ActionType)
        assert len(types) >= 10


class TestPackageImports:
    def test_action_engine_imports(self):
        from core.action import (
            ActionRecognizer,
            ActionResult,
            ActionConfig,
            ActionType,
            ClipBuffer,
        )
        assert ActionRecognizer is not None
        assert ClipBuffer is not None
