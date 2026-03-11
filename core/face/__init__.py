"""
Face Engine — On-device face detection, consented embeddings, tracking & social cues.

All face features are OPT-IN and require explicit user consent.
Embeddings are stored locally and encrypted at rest when enabled.
"""

from .face_detector import FaceDetection, FaceDetector, FaceDetectorConfig
from .face_embeddings import EmbeddingConfig, FaceEmbeddingStore, FaceIdentity
from .face_social_cues import EmotionResult, HeadPose, SocialCueAnalyzer, SocialCues
from .face_tracker import FaceTracker, TrackedFace, TrackerConfig

__all__ = [
    "FaceDetector", "FaceDetection", "FaceDetectorConfig",
    "FaceEmbeddingStore", "FaceIdentity", "EmbeddingConfig",
    "FaceTracker", "TrackedFace", "TrackerConfig",
    "SocialCueAnalyzer", "SocialCues", "EmotionResult", "HeadPose",
]
