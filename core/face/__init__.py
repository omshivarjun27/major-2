"""
Face Engine — On-device face detection, consented embeddings, tracking & social cues.

All face features are OPT-IN and require explicit user consent.
Embeddings are stored locally and encrypted at rest when enabled.
"""

from .face_detector import FaceDetector, FaceDetection, FaceDetectorConfig
from .face_embeddings import FaceEmbeddingStore, FaceIdentity, EmbeddingConfig
from .face_tracker import FaceTracker, TrackedFace, TrackerConfig
from .face_social_cues import SocialCueAnalyzer, SocialCues, EmotionResult, HeadPose

__all__ = [
    "FaceDetector", "FaceDetection", "FaceDetectorConfig",
    "FaceEmbeddingStore", "FaceIdentity", "EmbeddingConfig",
    "FaceTracker", "TrackedFace", "TrackerConfig",
    "SocialCueAnalyzer", "SocialCues", "EmotionResult", "HeadPose",
]
