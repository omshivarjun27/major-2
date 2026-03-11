"""
Tests for confidence_cascade.py
================================
Covers 3-tier filtering, confusion pair verifier, edge-density heuristic,
small-crop penalty, and misclassification tracker alerts.
"""

from __future__ import annotations

import numpy as np
import pytest

from application.frame_processing.confidence_cascade import (
    CascadeConfig,
    SecondaryVerifier,
    apply_robustness_heuristics,
    compute_edge_density,
    filter_by_confidence,
)

# ---------------------------------------------------------------------------
# 3-Tier Confidence Filtering
# ---------------------------------------------------------------------------

class TestConfidenceTiers:
    """Verify detections are correctly bucketed into 3 tiers."""

    def _make_det(self, label: str, conf: float) -> dict:
        return {"label": label, "conf": conf, "bbox": [10, 10, 100, 100]}

    def test_high_confidence_detected(self):
        dets = [self._make_det("person", 0.85)]
        reported, log_only = filter_by_confidence(dets)
        assert len(reported) == 1
        assert reported[0]["status"] == "detected"
        assert len(log_only) == 0

    def test_threshold_boundary_detected(self):
        dets = [self._make_det("chair", 0.60)]
        reported, _ = filter_by_confidence(dets)
        assert len(reported) == 1
        assert reported[0]["status"] == "detected"

    def test_low_confidence_possible(self):
        dets = [self._make_det("bottle", 0.45)]
        reported, log_only = filter_by_confidence(dets)
        assert len(reported) == 1
        assert reported[0]["status"] == "possible — low confidence"
        assert len(log_only) == 0

    def test_below_threshold_silent(self):
        dets = [self._make_det("cup", 0.15)]
        reported, log_only = filter_by_confidence(dets)
        assert len(reported) == 0
        assert len(log_only) == 1
        assert log_only[0]["status"] == "below_threshold"

    def test_mixed_detections(self):
        dets = [
            self._make_det("person", 0.90),
            self._make_det("bottle", 0.50),
            self._make_det("ghost", 0.10),
        ]
        reported, log_only = filter_by_confidence(dets)
        assert len(reported) == 2
        assert len(log_only) == 1

    def test_custom_thresholds(self):
        cfg = CascadeConfig(detected_threshold=0.80, low_confidence_threshold=0.50)
        dets = [self._make_det("chair", 0.65)]
        reported, _ = filter_by_confidence(dets, config=cfg)
        assert reported[0]["status"] == "possible — low confidence"


# ---------------------------------------------------------------------------
# Edge Density Computation
# ---------------------------------------------------------------------------

class TestEdgeDensity:

    def test_solid_color_low_density(self):
        """A solid colour crop should have near-zero edge density."""
        crop = np.full((50, 50, 3), 128, dtype=np.uint8)
        density = compute_edge_density(crop)
        assert density < 0.1

    def test_high_edge_content(self):
        """A striped pattern with thick bands should have measurable edge density."""
        crop = np.zeros((100, 100), dtype=np.uint8)
        # Create thick horizontal stripes (10px bands) → strong Sobel gradients
        for i in range(0, 100, 20):
            crop[i:i+10, :] = 255
        density = compute_edge_density(crop)
        assert density > 0.0  # should have edges

    def test_empty_crop(self):
        crop = np.array([], dtype=np.uint8)
        density = compute_edge_density(crop)
        assert density == 0.0

    def test_none_crop(self):
        density = compute_edge_density(None)
        assert density == 0.0


# ---------------------------------------------------------------------------
# Confusion Pair Verifier
# ---------------------------------------------------------------------------

class TestConfusionPairVerifier:

    def test_no_penalty_for_non_confusion_label(self):
        """Labels not in confusion pairs should pass through unchanged."""
        verifier = SecondaryVerifier()
        dets = [{"label": "person", "conf": 0.80, "bbox": [10, 10, 100, 200]}]
        updated, conflicts = verifier.verify(dets)
        assert len(conflicts) == 0
        assert updated[0]["conf"] == 0.80

    def test_penalty_applied_for_bad_aspect_ratio(self):
        """A bottle with a very wide aspect ratio should get penalised."""
        config = CascadeConfig(confusion_pair_penalty=0.20)
        verifier = SecondaryVerifier(config=config)
        # Bottle expected AR = 0.2–0.6, giving it a very wide box (AR ~3.0)
        dets = [{"label": "bottle", "conf": 0.75, "bbox": [0, 0, 300, 100]}]
        updated, conflicts = verifier.verify(dets)
        assert len(conflicts) == 1
        assert updated[0]["conf"] == pytest.approx(0.55, abs=0.01)
        assert "aspect_ratio_mismatch" in conflicts[0]["reason"]

    def test_no_penalty_for_correct_aspect_ratio(self):
        """A bottle with a tall narrow box should not be penalised."""
        verifier = SecondaryVerifier()
        # AR = 30/100 = 0.3, which is within bottle's expected range (0.2–0.6)
        dets = [{"label": "bottle", "conf": 0.75, "bbox": [0, 0, 30, 100]}]
        updated, conflicts = verifier.verify(dets)
        assert len(conflicts) == 0
        assert updated[0]["conf"] == 0.75


# ---------------------------------------------------------------------------
# Small Crop Penalty
# ---------------------------------------------------------------------------

class TestSmallCropPenalty:

    def test_small_bbox_gets_penalty(self):
        config = CascadeConfig(small_crop_min_area=1024, small_crop_penalty=0.15)
        dets = [{"label": "cup", "conf": 0.70, "bbox": [0, 0, 10, 10]}]  # area=100
        result = apply_robustness_heuristics(dets, config=config)
        assert result[0]["conf"] == pytest.approx(0.55, abs=0.01)

    def test_large_bbox_no_penalty(self):
        config = CascadeConfig(small_crop_min_area=1024, small_crop_penalty=0.15)
        dets = [{"label": "cup", "conf": 0.70, "bbox": [0, 0, 100, 100]}]  # area=10000
        result = apply_robustness_heuristics(dets, config=config)
        assert result[0]["conf"] == pytest.approx(0.70, abs=0.01)


# ---------------------------------------------------------------------------
# Misclassification Tracker
# ---------------------------------------------------------------------------

class TestMisclassificationTracker:

    def test_no_alert_below_threshold(self):
        from application.pipelines.perception_telemetry import MisclassificationTracker
        tracker = MisclassificationTracker(alert_count=3, window_seconds=30)
        # Record only 2 events — should not trigger
        alert1 = tracker.record("bottle", "frame_001")
        alert2 = tracker.record("bottle", "frame_002")
        assert alert1 is None
        assert alert2 is None

    def test_alert_on_threshold(self):
        from application.pipelines.perception_telemetry import MisclassificationTracker
        tracker = MisclassificationTracker(alert_count=3, window_seconds=30)
        tracker.record("bottle", "frame_001")
        tracker.record("bottle", "frame_002")
        alert = tracker.record("bottle", "frame_003")
        assert alert is not None
        assert alert["type"] == "repeated_misclassification"
        assert alert["label"] == "bottle"
        assert alert["count"] >= 3
        assert "sample_frames" in alert

    def test_separate_labels_tracked_independently(self):
        from application.pipelines.perception_telemetry import MisclassificationTracker
        tracker = MisclassificationTracker(alert_count=3, window_seconds=60)
        tracker.record("bottle", "f1")
        tracker.record("bottle", "f2")
        tracker.record("cup", "f3")
        tracker.record("cup", "f4")
        # Neither should trigger yet
        assert tracker.record("cup", "f5") is not None  # cup hits 3
        # bottle is at 2, should not trigger
        assert tracker.record("bottle", "f6") is not None  # now bottle hits 3 too

    def test_alert_resets_after_trigger(self):
        from application.pipelines.perception_telemetry import MisclassificationTracker
        tracker = MisclassificationTracker(alert_count=3, window_seconds=60)
        tracker.record("remote", "f1")
        tracker.record("remote", "f2")
        alert = tracker.record("remote", "f3")
        assert alert is not None  # triggered

        # After trigger, history should be cleared
        assert tracker.record("remote", "f4") is None
        assert tracker.record("remote", "f5") is None
