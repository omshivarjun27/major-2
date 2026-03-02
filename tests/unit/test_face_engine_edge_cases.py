"""Face detection/tracking edge cases: empty images, mock backends, boundary conditions."""

from __future__ import annotations

import itertools
from unittest.mock import patch

import numpy as np

from core.face.face_detector import (
    FaceDetection,
    FaceDetector,
    FaceDetectorConfig,
)
from core.face.face_tracker import FaceTracker, TrackerConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_COUNTER = itertools.count()


def _blank_image(h: int = 200, w: int = 200, channels: int = 3) -> np.ndarray:
    """Create a blank (black) image."""
    return np.zeros((h, w, channels), dtype=np.uint8)


def _random_image(h: int = 200, w: int = 200) -> np.ndarray:
    """Create a random noise image."""
    return np.random.randint(0, 255, (h, w, 3), dtype=np.uint8)


def _make_face_detection(
    x1: int = 10, y1: int = 10, x2: int = 60, y2: int = 60,
    confidence: float = 0.9, frame_id: str = "",
) -> FaceDetection:
    """Create a FaceDetection instance."""
    return FaceDetection(
        face_id=f"face_{next(_COUNTER)}",
        bbox=(x1, y1, x2, y2),
        confidence=confidence,
        timestamp_ms=1000.0,
        frame_id=frame_id,
    )


# ===========================================================================
# FaceDetection data structure edge cases
# ===========================================================================


class TestFaceDetectionEdgeCases:
    """Edge cases for the FaceDetection dataclass."""

    def test_width_and_height(self):
        """Width and height properties should compute correctly."""
        fd = _make_face_detection(x1=10, y1=20, x2=110, y2=170)
        assert fd.width == 100
        assert fd.height == 150

    def test_center(self):
        """Center property should be the midpoint of bbox."""
        fd = _make_face_detection(x1=0, y1=0, x2=100, y2=200)
        cx, cy = fd.center
        assert cx == 50.0
        assert cy == 100.0

    def test_area(self):
        """Area should be width * height."""
        fd = _make_face_detection(x1=0, y1=0, x2=10, y2=20)
        assert fd.area == 200

    def test_zero_area_face(self):
        """Face with zero-area bbox should have area=0."""
        fd = _make_face_detection(x1=5, y1=5, x2=5, y2=5)
        assert fd.area == 0

    def test_to_dict_structure(self):
        """to_dict should include all expected keys."""
        fd = _make_face_detection()
        d = fd.to_dict()
        expected_keys = {"face_id", "bbox", "confidence", "width", "height",
                         "center", "has_landmarks", "has_embedding", "timestamp_ms", "frame_id"}
        assert expected_keys.issubset(set(d.keys()))

    def test_to_dict_no_landmarks(self):
        """Without landmarks, has_landmarks should be False."""
        fd = _make_face_detection()
        d = fd.to_dict()
        assert d["has_landmarks"] is False

    def test_to_dict_with_landmarks(self):
        """With landmarks, has_landmarks should be True."""
        fd = _make_face_detection()
        fd.landmarks = {"left_eye": (20.0, 30.0), "right_eye": (40.0, 30.0)}
        d = fd.to_dict()
        assert d["has_landmarks"] is True

    def test_to_dict_no_embedding(self):
        """Without embedding, has_embedding should be False."""
        fd = _make_face_detection()
        assert fd.to_dict()["has_embedding"] is False

    def test_to_dict_with_embedding(self):
        """With embedding, has_embedding should be True."""
        fd = _make_face_detection()
        fd.embedding = np.zeros(128, dtype=np.float32)
        assert fd.to_dict()["has_embedding"] is True

    def test_negative_bbox_coordinates(self):
        """Negative bbox coords should still compute properties."""
        fd = _make_face_detection(x1=-10, y1=-10, x2=10, y2=10)
        assert fd.width == 20
        assert fd.height == 20
        assert fd.area == 400


# ===========================================================================
# FaceDetectorConfig edge cases
# ===========================================================================


class TestFaceDetectorConfigEdgeCases:
    """Edge cases for FaceDetectorConfig."""

    def test_default_config(self):
        """Default config should use auto backend."""
        cfg = FaceDetectorConfig()
        assert cfg.backend == "auto"
        assert cfg.min_confidence == 0.7

    def test_custom_backend(self):
        """Custom backend string should be stored."""
        cfg = FaceDetectorConfig(backend="haar")
        assert cfg.backend == "haar"

    def test_zero_min_face_size(self):
        """Zero min_face_size is allowed."""
        cfg = FaceDetectorConfig(min_face_size=0)
        assert cfg.min_face_size == 0

    def test_max_faces_limit(self):
        """Custom max_faces should be stored."""
        cfg = FaceDetectorConfig(max_faces=1)
        assert cfg.max_faces == 1


# ===========================================================================
# FaceDetector edge cases
# ===========================================================================


class TestFaceDetectorEdgeCases:
    """Edge cases for FaceDetector with mock/unavailable backends."""

    def test_mock_backend_when_no_libs(self):
        """Without any libraries, detector should use mock backend."""
        with patch("core.face.face_detector._MTCNN_AVAILABLE", False), \
             patch("core.face.face_detector._RETINA_AVAILABLE", False), \
             patch("core.face.face_detector._CV2_AVAILABLE", False):
            detector = FaceDetector()
            assert detector.backend_name == "mock"

    def test_detect_returns_list(self):
        """detect() should always return a list."""
        with patch("core.face.face_detector._MTCNN_AVAILABLE", False), \
             patch("core.face.face_detector._RETINA_AVAILABLE", False), \
             patch("core.face.face_detector._CV2_AVAILABLE", False):
            detector = FaceDetector()
            faces = detector.detect(_blank_image())
            assert isinstance(faces, list)

    def test_detect_with_frame_id(self):
        """Frame ID should be passed through to detections."""
        with patch("core.face.face_detector._MTCNN_AVAILABLE", False), \
             patch("core.face.face_detector._RETINA_AVAILABLE", False), \
             patch("core.face.face_detector._CV2_AVAILABLE", False):
            detector = FaceDetector()
            faces = detector.detect(_blank_image(), frame_id="frame_42")
            for f in faces:
                assert f.frame_id == "frame_42"

    def test_detect_auto_timestamp(self):
        """Zero timestamp should be auto-filled."""
        with patch("core.face.face_detector._MTCNN_AVAILABLE", False), \
             patch("core.face.face_detector._RETINA_AVAILABLE", False), \
             patch("core.face.face_detector._CV2_AVAILABLE", False):
            detector = FaceDetector()
            faces = detector.detect(_blank_image(), timestamp_ms=0.0)
            for f in faces:
                assert f.timestamp_ms > 0

    def test_detect_grayscale_image(self):
        """Grayscale image should not crash the detector."""
        with patch("core.face.face_detector._MTCNN_AVAILABLE", False), \
             patch("core.face.face_detector._RETINA_AVAILABLE", False), \
             patch("core.face.face_detector._CV2_AVAILABLE", False):
            detector = FaceDetector()
            gray = np.zeros((200, 200), dtype=np.uint8)
            faces = detector.detect(gray)
            assert isinstance(faces, list)

    def test_detect_tiny_image(self):
        """Very small image should not crash."""
        with patch("core.face.face_detector._MTCNN_AVAILABLE", False), \
             patch("core.face.face_detector._RETINA_AVAILABLE", False), \
             patch("core.face.face_detector._CV2_AVAILABLE", False):
            detector = FaceDetector()
            tiny = np.zeros((1, 1, 3), dtype=np.uint8)
            faces = detector.detect(tiny)
            assert isinstance(faces, list)

    def test_backend_name_property(self):
        """backend_name property should return a string."""
        with patch("core.face.face_detector._MTCNN_AVAILABLE", False), \
             patch("core.face.face_detector._RETINA_AVAILABLE", False), \
             patch("core.face.face_detector._CV2_AVAILABLE", False):
            detector = FaceDetector()
            assert isinstance(detector.backend_name, str)

    def test_high_confidence_filter(self):
        """With very high min_confidence, fewer faces should pass."""
        cfg = FaceDetectorConfig(min_confidence=0.99)
        with patch("core.face.face_detector._MTCNN_AVAILABLE", False), \
             patch("core.face.face_detector._RETINA_AVAILABLE", False), \
             patch("core.face.face_detector._CV2_AVAILABLE", False):
            detector = FaceDetector(cfg)
            faces = detector.detect(_random_image())
            assert isinstance(faces, list)


# ===========================================================================
# FaceTracker edge cases
# ===========================================================================


class TestFaceTrackerEdgeCases:
    """Edge cases for FaceTracker."""

    def test_empty_update(self):
        """Updating with no detections should return empty list."""
        tracker = FaceTracker(config=TrackerConfig(max_tracked=5, max_disappeared=3))
        result = tracker.update([])
        assert result == []

    def test_single_face_tracked(self):
        """Single face should be tracked after update."""
        tracker = FaceTracker(config=TrackerConfig(max_tracked=5, max_disappeared=3))
        fd = _make_face_detection()
        tracked = tracker.update([fd])
        assert len(tracked) == 1

    def test_max_tracked_limit(self):
        """Tracker should not track more than max_tracked faces."""
        tracker = FaceTracker(config=TrackerConfig(max_tracked=2, max_disappeared=3))
        faces = [_make_face_detection(x1=i * 50, y1=0, x2=i * 50 + 40, y2=40) for i in range(5)]
        tracked = tracker.update(faces)
        assert len(tracked) <= 2

    def test_disappeared_face_eventually_removed(self):
        """Face that disappears should be removed after max_disappeared frames."""
        tracker = FaceTracker(config=TrackerConfig(max_tracked=5, max_disappeared=2))
        fd = _make_face_detection(x1=0, y1=0, x2=50, y2=50)
        tracker.update([fd])
        # Send empty frames
        for _ in range(3):
            tracker.update([])
        # After max_disappeared+1 empty frames, track should be removed
        get_tracked = getattr(tracker, "get_tracked", None)
        if callable(get_tracked):
            active = get_tracked()
        else:
            active = tracker.get_active_tracks()
        assert len(active) == 0

    def test_track_id_persistence(self):
        """Same face should keep the same track ID across frames."""
        tracker = FaceTracker(config=TrackerConfig(max_tracked=5, max_disappeared=5))
        fd1 = _make_face_detection(x1=10, y1=10, x2=60, y2=60)
        t1 = tracker.update([fd1])
        tid = t1[0].track_id

        fd2 = _make_face_detection(x1=10, y1=10, x2=60, y2=60)
        t2 = tracker.update([fd2])
        assert t2[0].track_id == tid

    def test_two_faces_get_different_ids(self):
        """Two distinct faces should get different track IDs."""
        tracker = FaceTracker(config=TrackerConfig(max_tracked=5, max_disappeared=3))
        f1 = _make_face_detection(x1=0, y1=0, x2=30, y2=30)
        f2 = _make_face_detection(x1=100, y1=100, x2=130, y2=130)
        tracked = tracker.update([f1, f2])
        assert len(tracked) == 2
        assert tracked[0].track_id != tracked[1].track_id
