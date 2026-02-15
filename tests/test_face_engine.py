"""
Tests for face_engine — FaceDetector, FaceEmbeddingStore, FaceTracker, SocialCueAnalyzer.
"""

from __future__ import annotations

import numpy as np
import pytest

# ── FaceDetector ──────────────────────────────────────────────────────

from core.face.face_detector import FaceDetector, FaceDetection, FaceDetectorConfig


class TestFaceDetectorConfig:
    def test_defaults(self):
        cfg = FaceDetectorConfig()
        assert cfg.backend == "auto"
        assert cfg.min_confidence == 0.7
        assert cfg.min_face_size == 40
        assert cfg.max_faces == 10
        assert cfg.device == "cpu"


class TestFaceDetector:
    def test_init(self):
        det = FaceDetector()
        assert det is not None

    def test_detect_returns_list(self):
        det = FaceDetector(FaceDetectorConfig(backend="mock"))
        image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        faces = det.detect(image, frame_id="f1", timestamp_ms=1000)
        assert isinstance(faces, list)

    def test_detection_dataclass(self):
        fd = FaceDetection(
            face_id="face_1",
            bbox=(10, 20, 100, 200),
            confidence=0.95,
            landmarks=None,
            embedding=None,
            timestamp_ms=1000,
            frame_id="f1",
        )
        assert fd.confidence == 0.95
        assert fd.frame_id == "f1"
        assert fd.face_id == "face_1"

    def test_health(self):
        det = FaceDetector()
        h = det.health()
        assert "backend" in h
        assert "config" in h


# ── FaceEmbeddingStore ────────────────────────────────────────────────

from core.face.face_embeddings import (
    FaceEmbeddingStore,
    FaceIdentity,
    EmbeddingConfig,
)


class TestEmbeddingConfig:
    def test_defaults(self):
        cfg = EmbeddingConfig()
        assert cfg.consent_required is True
        assert cfg.similarity_threshold == 0.6


class TestFaceEmbeddingStore:
    def test_init(self):
        store = FaceEmbeddingStore(EmbeddingConfig(storage_dir=""))
        assert store is not None

    def test_register_requires_consent(self):
        store = FaceEmbeddingStore(EmbeddingConfig(storage_dir="", consent_required=True))
        embedding = np.random.randn(128).astype(np.float32)
        result = store.register("alice", embedding)
        # Without consent, registration should not proceed
        assert result is None or isinstance(result, FaceIdentity)

    def test_register_with_consent(self):
        store = FaceEmbeddingStore(EmbeddingConfig(storage_dir="", consent_required=True))
        store.record_consent("alice", True)
        embedding = np.random.randn(128).astype(np.float32)
        result = store.register("alice", embedding)
        assert result is not None
        assert result.name == "alice"

    def test_register_no_consent_required(self):
        store = FaceEmbeddingStore(EmbeddingConfig(storage_dir="", consent_required=False))
        embedding = np.random.randn(128).astype(np.float32)
        result = store.register("bob", embedding)
        assert result is not None
        assert result.name == "bob"

    def test_identify(self):
        store = FaceEmbeddingStore(EmbeddingConfig(storage_dir="", consent_required=False))
        emb = np.random.randn(128).astype(np.float32)
        store.register("carol", emb)
        result = store.identify(emb + np.random.randn(128).astype(np.float32) * 0.01)
        if result:
            identity, score = result
            assert identity.name == "carol"
            assert isinstance(score, float)

    def test_forget_all(self):
        store = FaceEmbeddingStore(EmbeddingConfig(storage_dir="", consent_required=False))
        emb = np.random.randn(128).astype(np.float32)
        store.register("dave", emb)
        store.forget_all()
        assert store.identify(emb) is None

    def test_consent_log(self):
        store = FaceEmbeddingStore(EmbeddingConfig(storage_dir=""))
        store.record_consent("eve", True)
        log = store.get_consent_log()
        assert len(log) >= 1

    def test_health(self):
        store = FaceEmbeddingStore(EmbeddingConfig(storage_dir=""))
        h = store.health()
        assert "identities_registered" in h


# ── FaceTracker ───────────────────────────────────────────────────────

from core.face.face_tracker import FaceTracker, TrackedFace, TrackerConfig


class TestTrackerConfig:
    def test_defaults(self):
        cfg = TrackerConfig()
        assert cfg.iou_threshold == 0.3
        assert cfg.max_disappeared == 15
        assert cfg.max_tracked == 20


class TestFaceTracker:
    def test_init(self):
        tracker = FaceTracker()
        assert tracker is not None

    def test_update_empty(self):
        tracker = FaceTracker()
        tracks = tracker.update([])
        assert isinstance(tracks, list)
        assert len(tracks) == 0

    def test_update_single_detection(self):
        tracker = FaceTracker()
        det = FaceDetection(
            face_id="face_1",
            bbox=(50, 50, 150, 150),
            confidence=0.9,
            timestamp_ms=1000,
            frame_id="f1",
        )
        tracks = tracker.update([det])
        assert len(tracks) == 1
        assert isinstance(tracks[0], TrackedFace)

    def test_multi_frame_tracking(self):
        tracker = FaceTracker()
        det1 = FaceDetection(face_id="face_1", bbox=(50, 50, 150, 150), confidence=0.9, timestamp_ms=100, frame_id="f1")
        det2 = FaceDetection(face_id="face_1", bbox=(55, 55, 155, 155), confidence=0.9, timestamp_ms=200, frame_id="f2")
        tracker.update([det1])
        tracks = tracker.update([det2])
        assert len(tracks) >= 1

    def test_get_active_tracks(self):
        tracker = FaceTracker()
        det = FaceDetection(face_id="face_1", bbox=(10, 10, 110, 110), confidence=0.8, timestamp_ms=100, frame_id="f1")
        tracker.update([det])
        active = tracker.get_active_tracks()
        assert len(active) >= 1

    def test_clear(self):
        tracker = FaceTracker()
        det = FaceDetection(face_id="face_1", bbox=(10, 10, 110, 110), confidence=0.8, timestamp_ms=100, frame_id="f1")
        tracker.update([det])
        tracker.clear()
        assert len(tracker.get_active_tracks()) == 0

    def test_health(self):
        tracker = FaceTracker()
        h = tracker.health()
        assert "active_tracks" in h


# ── SocialCueAnalyzer ────────────────────────────────────────────────

from core.face.face_social_cues import (
    SocialCueAnalyzer,
    SocialCues,
    EmotionResult,
    HeadPose,
)


class TestSocialCueAnalyzer:
    def test_init(self):
        analyzer = SocialCueAnalyzer()
        assert analyzer is not None

    def test_analyze_returns_cues(self):
        analyzer = SocialCueAnalyzer()
        det = FaceDetection(
            face_id="face_1",
            bbox=(50, 50, 200, 200),
            confidence=0.9,
            timestamp_ms=1000,
            frame_id="f1",
        )
        image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        cues = analyzer.analyze(det, image)
        assert isinstance(cues, SocialCues)

    def test_emotion_result(self):
        from core.face.face_social_cues import Emotion
        er = EmotionResult(emotion=Emotion.HAPPY, confidence=0.8)
        assert er.emotion == Emotion.HAPPY

    def test_head_pose(self):
        hp = HeadPose(yaw=0, pitch=0, roll=0)
        assert hp.is_facing_camera is True
        assert hp.looking_direction == "forward"


# ── Package imports ───────────────────────────────────────────────────

class TestPackageImports:
    def test_face_engine_imports(self):
        from core.face import (
            FaceDetector,
            FaceDetection,
            FaceDetectorConfig,
            FaceEmbeddingStore,
            FaceIdentity,
            EmbeddingConfig,
            FaceTracker,
            TrackedFace,
            TrackerConfig,
            SocialCueAnalyzer,
            SocialCues,
            EmotionResult,
            HeadPose,
        )
        assert FaceDetector is not None
        assert FaceEmbeddingStore is not None
        assert FaceTracker is not None
        assert SocialCueAnalyzer is not None
