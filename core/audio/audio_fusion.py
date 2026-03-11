"""
Audio-Vision Fusion — Cross-modal fusion of sound source localization with visual scene data.

Combines SSL results with vision-based object detection to produce
spatially-grounded multimodal events for the blind user.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import List, Optional

from .audio_event_detector import AudioEvent, AudioEventType
from .ssl import SSLResult

logger = logging.getLogger("audio-fusion")


@dataclass
class AudioFusionConfig:
    """Configuration for audio-vision fusion."""
    angular_tolerance_deg: float = 30.0         # max angle diff for matching
    temporal_tolerance_ms: float = 2000.0        # max time diff for matching
    min_fusion_confidence: float = 0.25
    distance_weight: float = 0.5                 # weight for distance agreement
    max_fused_events: int = 10


@dataclass
class VisualObject:
    """Lightweight visual object representation for fusion."""
    label: str
    bbox: tuple  # (x1, y1, x2, y2) normalized 0-1
    confidence: float = 0.5
    azimuth_deg: Optional[float] = None  # camera-estimated angle
    distance_m: Optional[float] = None
    timestamp_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "bbox": self.bbox,
            "confidence": round(self.confidence, 3),
            "azimuth_deg": round(self.azimuth_deg, 1) if self.azimuth_deg else None,
            "distance_m": round(self.distance_m, 2) if self.distance_m else None,
        }


@dataclass
class FusedAudioVisualEvent:
    """A cross-modal event combining audio + visual signals."""
    event_id: str
    audio_event: Optional[AudioEvent] = None
    ssl_result: Optional[SSLResult] = None
    visual_match: Optional[VisualObject] = None
    fusion_confidence: float = 0.0
    spatial_description: str = ""
    is_critical: bool = False
    timestamp_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "audio_event": self.audio_event.to_dict() if self.audio_event else None,
            "ssl_azimuth": round(self.ssl_result.azimuth_deg, 1) if self.ssl_result else None,
            "visual_match": self.visual_match.to_dict() if self.visual_match else None,
            "fusion_confidence": round(self.fusion_confidence, 3),
            "spatial_description": self.spatial_description,
            "is_critical": self.is_critical,
            "timestamp_ms": self.timestamp_ms,
        }

    @property
    def user_cue(self) -> str:
        parts = []
        if self.audio_event and self.audio_event.user_cue:
            parts.append(self.audio_event.user_cue)
        if self.spatial_description:
            parts.append(self.spatial_description)
        return " — ".join(parts) if parts else "Multimodal event detected"


class AudioVisionFuser:
    """Fuses audio SSL + event detection with visual scene objects.

    Matches sound source angles to visual object positions, producing
    spatially-grounded event descriptions for the blind user.

    Usage::

        fuser = AudioVisionFuser()
        fused = fuser.fuse(
            audio_events=[AudioEvent(...)],
            ssl_results=[SSLResult(...)],
            visual_objects=[VisualObject(...)],
        )
        for event in fused:
            speak(event.user_cue)
    """

    def __init__(self, config: Optional[AudioFusionConfig] = None):
        self.config = config or AudioFusionConfig()
        self._event_counter = 0

    def fuse(
        self,
        audio_events: Optional[List[AudioEvent]] = None,
        ssl_results: Optional[List[SSLResult]] = None,
        visual_objects: Optional[List[VisualObject]] = None,
    ) -> List[FusedAudioVisualEvent]:
        """Perform cross-modal fusion.

        Args:
            audio_events: Classified audio events
            ssl_results: Sound source localization results
            visual_objects: Detected visual objects from vision pipeline

        Returns:
            List of fused events sorted by criticality then confidence.
        """
        audio_events = audio_events or []
        ssl_results = ssl_results or []
        visual_objects = visual_objects or []

        fused: List[FusedAudioVisualEvent] = []

        # Match SSL to audio events by timestamp
        ssl_audio_pairs = self._match_ssl_audio(ssl_results, audio_events)

        for ssl, audio_ev in ssl_audio_pairs:
            best_visual = self._match_visual(ssl, visual_objects)
            spatial = self._describe_spatial(ssl, audio_ev, best_visual)

            self._event_counter += 1
            fc = self._compute_fusion_confidence(ssl, audio_ev, best_visual)

            if fc < self.config.min_fusion_confidence:
                continue

            fused.append(FusedAudioVisualEvent(
                event_id=f"fav_{self._event_counter}",
                audio_event=audio_ev,
                ssl_result=ssl,
                visual_match=best_visual,
                fusion_confidence=fc,
                spatial_description=spatial,
                is_critical=audio_ev.is_critical if audio_ev else False,
                timestamp_ms=ssl.timestamp_ms if ssl else (audio_ev.timestamp_ms if audio_ev else time.time() * 1000),
            ))

        # Handle unmatched audio events (no SSL)
        matched_audio = {id(ae) for _, ae in ssl_audio_pairs if ae}
        for ae in audio_events:
            if id(ae) in matched_audio:
                continue
            if ae.confidence < self.config.min_fusion_confidence:
                continue
            self._event_counter += 1
            fused.append(FusedAudioVisualEvent(
                event_id=f"fav_{self._event_counter}",
                audio_event=ae,
                fusion_confidence=ae.confidence * 0.7,
                spatial_description=ae.user_cue,
                is_critical=ae.is_critical,
                timestamp_ms=ae.timestamp_ms,
            ))

        # Sort: critical first, then by confidence
        fused.sort(key=lambda e: (not e.is_critical, -e.fusion_confidence))
        return fused[: self.config.max_fused_events]

    def _match_ssl_audio(
        self,
        ssl_results: List[SSLResult],
        audio_events: List[AudioEvent],
    ) -> List[tuple]:
        """Match SSL results to audio events by temporal proximity."""
        pairs: List[tuple] = []
        used_audio: set = set()

        for ssl in ssl_results:
            best_ae: Optional[AudioEvent] = None
            best_dt = float("inf")
            for i, ae in enumerate(audio_events):
                if i in used_audio:
                    continue
                dt = abs(ssl.timestamp_ms - ae.timestamp_ms)
                if dt < best_dt and dt <= self.config.temporal_tolerance_ms:
                    best_dt = dt
                    best_ae = ae
                    best_idx = i
            if best_ae is not None:
                used_audio.add(best_idx)
            pairs.append((ssl, best_ae))

        return pairs

    def _match_visual(
        self,
        ssl: SSLResult,
        visual_objects: List[VisualObject],
    ) -> Optional[VisualObject]:
        """Find the visual object best matching this sound direction."""
        if not visual_objects or not ssl:
            return None

        best: Optional[VisualObject] = None
        best_score = 0.0

        for vo in visual_objects:
            az = vo.azimuth_deg
            if az is None:
                # Estimate azimuth from bbox center x (0=left, 1=right → -90 to +90)
                cx = (vo.bbox[0] + vo.bbox[2]) / 2
                az = (cx - 0.5) * 180  # rough mapping

            angle_diff = abs(ssl.azimuth_deg - az)
            if angle_diff > 180:
                angle_diff = 360 - angle_diff

            if angle_diff > self.config.angular_tolerance_deg:
                continue

            # Score = angular closeness * visual confidence
            angle_score = 1.0 - angle_diff / self.config.angular_tolerance_deg
            score = angle_score * 0.6 + vo.confidence * 0.4

            if score > best_score:
                best_score = score
                best = vo

        return best

    def _describe_spatial(
        self,
        ssl: Optional[SSLResult],
        audio_ev: Optional[AudioEvent],
        visual: Optional[VisualObject],
    ) -> str:
        """Generate a natural-language spatial description."""
        parts = []

        if ssl:
            parts.append(f"Sound from {ssl.direction_label}")
            if ssl.distance_estimate and ssl.distance_estimate < 10:
                parts.append(f"approximately {ssl.distance_estimate:.1f} meters away")

        if audio_ev and audio_ev.event_type != AudioEventType.UNKNOWN:
            parts.append(f"identified as {audio_ev.event_type.value.replace('_', ' ')}")

        if visual:
            parts.append(f"possibly matching visual object: {visual.label}")

        return ", ".join(parts) if parts else ""

    def _compute_fusion_confidence(
        self,
        ssl: Optional[SSLResult],
        audio_ev: Optional[AudioEvent],
        visual: Optional[VisualObject],
    ) -> float:
        """Compute a combined confidence score."""
        scores = []

        if ssl:
            scores.append(ssl.confidence * 0.3)
        if audio_ev:
            scores.append(audio_ev.confidence * 0.4)
        if visual:
            scores.append(visual.confidence * 0.3)

        if not scores:
            return 0.0

        # Normalize so that having more modalities increases confidence
        base = sum(scores)
        modality_bonus = len(scores) * 0.05
        return min(base + modality_bonus, 1.0)

    def health(self) -> dict:
        return {
            "events_produced": self._event_counter,
            "config": {
                "angular_tolerance_deg": self.config.angular_tolerance_deg,
                "temporal_tolerance_ms": self.config.temporal_tolerance_ms,
            },
        }
