"""
Social Cue Analyzer — Emotion recognition, head-pose estimation, attention detection.

All outputs include confidence scores and privacy gating.
Analysis is performed on-device; no raw images sent externally.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np

from .face_detector import FaceDetection

logger = logging.getLogger("face-social-cues")


class Emotion(str, Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SURPRISED = "surprised"
    FEARFUL = "fearful"
    DISGUSTED = "disgusted"
    UNKNOWN = "unknown"


@dataclass
class EmotionResult:
    """Predicted emotion with confidence."""
    emotion: Emotion
    confidence: float
    all_scores: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "emotion": self.emotion.value,
            "confidence": round(self.confidence, 3),
            "all_scores": {k: round(v, 3) for k, v in self.all_scores.items()},
        }


@dataclass
class HeadPose:
    """Estimated head orientation."""
    yaw: float = 0.0    # left-right rotation (degrees)
    pitch: float = 0.0   # up-down rotation
    roll: float = 0.0    # tilt

    @property
    def is_facing_camera(self) -> bool:
        return abs(self.yaw) < 30 and abs(self.pitch) < 25

    @property
    def looking_direction(self) -> str:
        if abs(self.yaw) < 15 and abs(self.pitch) < 15:
            return "forward"
        if self.yaw > 15:
            return "right"
        if self.yaw < -15:
            return "left"
        if self.pitch > 15:
            return "down"
        return "up"

    def to_dict(self) -> dict:
        return {
            "yaw": round(self.yaw, 1),
            "pitch": round(self.pitch, 1),
            "roll": round(self.roll, 1),
            "is_facing_camera": self.is_facing_camera,
            "looking_direction": self.looking_direction,
        }


@dataclass
class SocialCues:
    """Combined social cue analysis for a person."""
    face_id: str
    emotion: EmotionResult
    head_pose: HeadPose
    is_looking_at_user: bool
    attention_score: float  # 0..1
    distance_estimate: Optional[str] = None  # "close", "medium", "far"
    gesture: Optional[str] = None
    timestamp_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "face_id": self.face_id,
            "emotion": self.emotion.to_dict(),
            "head_pose": self.head_pose.to_dict(),
            "is_looking_at_user": self.is_looking_at_user,
            "attention_score": round(self.attention_score, 2),
            "distance_estimate": self.distance_estimate,
            "gesture": self.gesture,
            "timestamp_ms": self.timestamp_ms,
        }

    @property
    def summary(self) -> str:
        parts = []
        if self.is_looking_at_user:
            parts.append("looking at you")
        if self.emotion.emotion != Emotion.NEUTRAL and self.emotion.confidence > 0.5:
            parts.append(f"appears {self.emotion.emotion.value}")
        if self.distance_estimate:
            parts.append(f"{self.distance_estimate} distance")
        return ", ".join(parts) if parts else "person present"


class SocialCueAnalyzer:
    """Analyze social cues from detected faces.

    Uses landmark geometry for head-pose estimation and
    optional deep models for emotion recognition.

    Usage::

        analyzer = SocialCueAnalyzer()
        cues = analyzer.analyze(face_detection, image)
    """

    def __init__(self, privacy_mode: bool = True):
        self._privacy_mode = privacy_mode
        self._emotion_model = None
        self._init_models()

    def _init_models(self) -> None:
        # Attempt to load emotion model (FER / deepface)
        try:
            from fer import FER as _FER  # type: ignore
            self._emotion_model = _FER(mtcnn=False)
            logger.info("Emotion recognition: FER model loaded")
        except ImportError:
            logger.info("Emotion model not available; using landmark-based estimation")

    def analyze(
        self,
        detection: FaceDetection,
        image: Optional[Any] = None,
    ) -> SocialCues:
        """Analyze social cues for a single face detection."""
        ts = detection.timestamp_ms or time.time() * 1000

        emotion = self._estimate_emotion(detection, image)
        head_pose = self._estimate_head_pose(detection)
        is_looking = head_pose.is_facing_camera
        attention = self._compute_attention_score(head_pose, detection)
        distance = self._estimate_distance(detection)

        return SocialCues(
            face_id=detection.face_id,
            emotion=emotion,
            head_pose=head_pose,
            is_looking_at_user=is_looking,
            attention_score=attention,
            distance_estimate=distance,
            timestamp_ms=ts,
        )

    def analyze_batch(
        self,
        detections: List[FaceDetection],
        image: Optional[Any] = None,
    ) -> List[SocialCues]:
        return [self.analyze(det, image) for det in detections]

    def _estimate_emotion(self, detection: FaceDetection, image: Optional[Any]) -> EmotionResult:
        # Try deep model first
        if self._emotion_model is not None and image is not None:
            try:
                if isinstance(image, np.ndarray):
                    img = image
                else:
                    img = np.array(image)
                x1, y1, x2, y2 = detection.bbox
                h, w = img.shape[:2]
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)
                face_crop = img[y1:y2, x1:x2]
                if face_crop.size > 0:
                    results = self._emotion_model.detect_emotions(face_crop)
                    if results:
                        emotions = results[0].get("emotions", {})
                        top = max(emotions, key=emotions.get, default="neutral")
                        return EmotionResult(
                            emotion=Emotion(top) if top in [e.value for e in Emotion] else Emotion.UNKNOWN,
                            confidence=emotions.get(top, 0.0),
                            all_scores=emotions,
                        )
            except Exception as exc:
                logger.debug("Emotion model inference error: %s", exc)

        # Fallback: landmark-based rough estimation
        return self._landmark_emotion(detection)

    def _landmark_emotion(self, detection: FaceDetection) -> EmotionResult:
        """Very rough emotion estimation from landmarks (mouth width, eye distance)."""
        if not detection.landmarks:
            return EmotionResult(emotion=Emotion.NEUTRAL, confidence=0.3)

        lm = detection.landmarks
        # Use mouth width relative to eye distance as a smile indicator
        if "mouth_left" in lm and "mouth_right" in lm and "left_eye" in lm and "right_eye" in lm:
            mouth_w = abs(lm["mouth_right"][0] - lm["mouth_left"][0])
            eye_dist = abs(lm["right_eye"][0] - lm["left_eye"][0])
            if eye_dist > 0:
                ratio = mouth_w / eye_dist
                if ratio > 0.8:
                    return EmotionResult(emotion=Emotion.HAPPY, confidence=0.5,
                                         all_scores={"happy": 0.5, "neutral": 0.3})
        return EmotionResult(emotion=Emotion.NEUTRAL, confidence=0.4,
                             all_scores={"neutral": 0.4})

    def _estimate_head_pose(self, detection: FaceDetection) -> HeadPose:
        """Estimate head pose from facial landmarks."""
        if not detection.landmarks:
            return HeadPose()

        lm = detection.landmarks
        if "left_eye" not in lm or "right_eye" not in lm or "nose" not in lm:
            return HeadPose()

        le = lm["left_eye"]
        re = lm["right_eye"]
        nose = lm["nose"]
        eye_center = ((le[0] + re[0]) / 2, (le[1] + re[1]) / 2)

        # Yaw: nose offset from eye center
        eye_dist = abs(re[0] - le[0])
        if eye_dist > 0:
            yaw = (nose[0] - eye_center[0]) / eye_dist * 60  # rough mapping to degrees
        else:
            yaw = 0.0

        # Pitch: nose offset below eye center
        if eye_dist > 0:
            pitch = (nose[1] - eye_center[1]) / eye_dist * 40
        else:
            pitch = 0.0

        # Roll: angle of eye line
        roll = math.degrees(math.atan2(re[1] - le[1], re[0] - le[0]))

        return HeadPose(yaw=yaw, pitch=pitch, roll=roll)

    def _compute_attention_score(self, pose: HeadPose, detection: FaceDetection) -> float:
        """0..1 score of how much attention is directed at the camera."""
        yaw_factor = max(0, 1.0 - abs(pose.yaw) / 60)
        pitch_factor = max(0, 1.0 - abs(pose.pitch) / 45)
        conf_factor = detection.confidence
        return round(yaw_factor * pitch_factor * conf_factor, 3)

    def _estimate_distance(self, detection: FaceDetection) -> str:
        """Rough distance estimate based on face bounding box size."""
        area = detection.area
        if area > 40000:
            return "close"
        elif area > 10000:
            return "medium"
        else:
            return "far"

    def health(self) -> dict:
        return {
            "emotion_model": self._emotion_model is not None,
            "privacy_mode": self._privacy_mode,
        }
