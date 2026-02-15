"""
Event Detection & Auto-Summarization for Memory Engine.

Detects significant events from the scene-analysis stream and
auto-summarizes them into long-term memory entries.

Events: obstacle encounters, navigation landmarks, recognized faces,
        repeated locations, time-of-day patterns, etc.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("memory-events")


class EventCategory(str, Enum):
    OBSTACLE = "obstacle"
    LANDMARK = "landmark"
    FACE = "face"
    QR_CODE = "qr_code"
    NAVIGATION = "navigation"
    AUDIO = "audio"
    SAFETY = "safety"
    ROUTINE = "routine"
    USER_NOTE = "user_note"


@dataclass
class DetectedEvent:
    """A significant event detected from the analysis stream."""
    event_id: str
    category: EventCategory
    summary: str
    confidence: float = 0.5
    timestamp_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    should_memorize: bool = True
    user_cue: str = ""

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "category": self.category.value,
            "summary": self.summary,
            "confidence": round(self.confidence, 3),
            "timestamp_ms": self.timestamp_ms,
            "should_memorize": self.should_memorize,
        }


@dataclass
class EventDetectorConfig:
    """Configuration for event detection thresholds."""
    min_confidence: float = 0.3
    obstacle_repeat_window_s: float = 60.0  # suppress duplicate obstacles
    landmark_cooldown_s: float = 300.0       # 5 min between same landmark events
    max_events_per_minute: int = 10
    auto_summarize: bool = True
    summarize_window_s: float = 30.0         # summarize events every 30s


class EventDetector:
    """Detects significant events from scene analysis results and converts
    them into memory-ready summaries.

    Usage::

        detector = EventDetector()
        events = detector.process_scene(scene_data)
        for ev in events:
            if ev.should_memorize:
                await memory_engine.ingest(ev.summary, metadata=ev.metadata)
    """

    def __init__(self, config: Optional[EventDetectorConfig] = None):
        self.config = config or EventDetectorConfig()
        self._event_counter = 0
        self._recent_events: List[DetectedEvent] = []
        self._cooldowns: Dict[str, float] = {}  # key -> last_trigger_ms

    def process_scene(self, scene_data: Dict[str, Any]) -> List[DetectedEvent]:
        """Process a scene analysis result and extract significant events.

        Args:
            scene_data: Dictionary with keys like 'objects', 'faces',
                        'audio_events', 'qr_codes', 'text', 'narration', etc.

        Returns:
            List of detected events.
        """
        events: List[DetectedEvent] = []
        now_ms = time.time() * 1000

        # Check obstacles
        objects = scene_data.get("objects", [])
        for obj in objects:
            if self._is_obstacle(obj):
                ev = self._create_obstacle_event(obj, now_ms)
                if ev and not self._is_suppressed(ev):
                    events.append(ev)

        # Check faces
        faces = scene_data.get("faces", [])
        for face in faces:
            ev = self._create_face_event(face, now_ms)
            if ev and not self._is_suppressed(ev):
                events.append(ev)

        # Check audio events
        audio_events = scene_data.get("audio_events", [])
        for ae in audio_events:
            ev = self._create_audio_event(ae, now_ms)
            if ev and not self._is_suppressed(ev):
                events.append(ev)

        # Check QR codes
        qr_codes = scene_data.get("qr_codes", [])
        for qr in qr_codes:
            ev = self._create_qr_event(qr, now_ms)
            if ev and not self._is_suppressed(ev):
                events.append(ev)

        # Check narration for landmarks
        narration = scene_data.get("narration", "")
        if narration:
            landmark_ev = self._detect_landmark(narration, now_ms)
            if landmark_ev and not self._is_suppressed(landmark_ev):
                events.append(landmark_ev)

        # Rate limit
        events = events[: self.config.max_events_per_minute]

        # Track recent
        self._recent_events.extend(events)
        self._recent_events = [
            e for e in self._recent_events
            if now_ms - e.timestamp_ms < self.config.summarize_window_s * 1000
        ]

        return events

    def get_auto_summary(self) -> Optional[str]:
        """Generate an auto-summary of recent events for long-term memory."""
        if not self.config.auto_summarize or not self._recent_events:
            return None

        categories = {}
        for ev in self._recent_events:
            categories.setdefault(ev.category.value, []).append(ev.summary)

        parts = []
        for cat, summaries in categories.items():
            unique = list(dict.fromkeys(summaries))  # dedup preserving order
            parts.append(f"{cat}: {'; '.join(unique[:3])}")

        if not parts:
            return None

        return "Recent scene summary: " + " | ".join(parts)

    def _create_obstacle_event(self, obj: Dict[str, Any], ts: float) -> Optional[DetectedEvent]:
        label = obj.get("label", "object")
        distance = obj.get("distance_m") or obj.get("distance", None)
        conf = obj.get("confidence", 0.5)

        if conf < self.config.min_confidence:
            return None

        self._event_counter += 1
        summary = f"Obstacle: {label}"
        if distance is not None:
            summary += f" at {distance:.1f}m"

        return DetectedEvent(
            event_id=f"evt_{self._event_counter}",
            category=EventCategory.OBSTACLE,
            summary=summary,
            confidence=conf,
            timestamp_ms=ts,
            metadata={"label": label, "distance_m": distance},
            user_cue=f"Watch out — {label} ahead" + (f" about {distance:.1f} meters away" if distance else ""),
        )

    def _create_face_event(self, face: Dict[str, Any], ts: float) -> Optional[DetectedEvent]:
        name = face.get("name") or face.get("identity", "unknown")
        conf = face.get("confidence", 0.5)

        self._event_counter += 1
        if name and name != "unknown":
            summary = f"Recognized face: {name}"
            cue = f"{name} is nearby"
        else:
            summary = "Unknown person detected"
            cue = "Someone is nearby"

        return DetectedEvent(
            event_id=f"evt_{self._event_counter}",
            category=EventCategory.FACE,
            summary=summary,
            confidence=conf,
            timestamp_ms=ts,
            metadata={"name": name},
            user_cue=cue,
        )

    def _create_audio_event(self, ae: Dict[str, Any], ts: float) -> Optional[DetectedEvent]:
        event_type = ae.get("event_type", "unknown")
        conf = ae.get("confidence", 0.5)
        is_critical = ae.get("is_critical", False)

        if conf < self.config.min_confidence:
            return None

        self._event_counter += 1
        category = EventCategory.SAFETY if is_critical else EventCategory.AUDIO

        return DetectedEvent(
            event_id=f"evt_{self._event_counter}",
            category=category,
            summary=f"Audio event: {event_type}",
            confidence=conf,
            timestamp_ms=ts,
            metadata={"event_type": event_type, "is_critical": is_critical},
            user_cue=ae.get("user_cue", f"{event_type} detected nearby"),
        )

    def _create_qr_event(self, qr: Dict[str, Any], ts: float) -> Optional[DetectedEvent]:
        data = qr.get("data", "")
        qr_type = qr.get("type", "qr")

        self._event_counter += 1
        summary = f"QR code scanned: {data[:50]}" if data else "QR code detected"

        return DetectedEvent(
            event_id=f"evt_{self._event_counter}",
            category=EventCategory.QR_CODE,
            summary=summary,
            confidence=0.9,
            timestamp_ms=ts,
            metadata={"data": data, "type": qr_type},
            user_cue=f"Scanned {qr_type}: {data[:100]}" if data else "QR code found",
        )

    def _detect_landmark(self, narration: str, ts: float) -> Optional[DetectedEvent]:
        """Simple keyword-based landmark detection from narration."""
        landmark_keywords = [
            "intersection", "crosswalk", "traffic light", "bus stop", "train station",
            "entrance", "exit", "stairs", "elevator", "escalator", "door", "gate",
            "shop", "restaurant", "park", "hospital", "school", "church",
        ]
        narration_lower = narration.lower()
        for kw in landmark_keywords:
            if kw in narration_lower:
                self._event_counter += 1
                return DetectedEvent(
                    event_id=f"evt_{self._event_counter}",
                    category=EventCategory.LANDMARK,
                    summary=f"Landmark: {kw} mentioned in scene",
                    confidence=0.6,
                    timestamp_ms=ts,
                    metadata={"keyword": kw, "narration_snippet": narration[:200]},
                    user_cue=f"Approaching {kw}",
                )
        return None

    def _is_obstacle(self, obj: Dict[str, Any]) -> bool:
        """Determine if an object is an obstacle."""
        obstacle_labels = {
            "car", "truck", "bus", "motorcycle", "bicycle", "person",
            "dog", "pole", "fire hydrant", "bollard", "pothole",
            "construction", "barrier", "fence", "wall", "tree",
        }
        label = obj.get("label", "").lower()
        distance = obj.get("distance_m") or obj.get("distance")
        # Close objects or known obstacle types
        return label in obstacle_labels or (distance is not None and distance < 3.0)

    def _is_suppressed(self, event: DetectedEvent) -> bool:
        """Check if this event should be suppressed (cooldown)."""
        key = f"{event.category.value}:{event.summary}"
        now_ms = time.time() * 1000
        last = self._cooldowns.get(key, 0)

        cooldown_ms = (
            self.config.obstacle_repeat_window_s * 1000
            if event.category == EventCategory.OBSTACLE
            else self.config.landmark_cooldown_s * 1000
        )

        if now_ms - last < cooldown_ms:
            return True

        self._cooldowns[key] = now_ms
        return False

    def health(self) -> dict:
        return {
            "events_detected": self._event_counter,
            "recent_events": len(self._recent_events),
            "active_cooldowns": len(self._cooldowns),
        }
