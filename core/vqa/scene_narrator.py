"""
Proactive Scene Narrator Module (T-126).

Narrates scene changes without user prompting — detects new objects,
departures, movements, and hazards, then generates spoken cues.
"""

from __future__ import annotations

import collections
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger("scene-narrator")


# =============================================================================
# Config & Data Structures
# =============================================================================


@dataclass
class NarrationConfig:
    """Configuration for proactive scene narration."""

    narration_interval_ms: float = 3000.0
    min_change_for_narration: float = 0.15
    max_narration_length: int = 100  # words
    priority_objects: List[str] = field(
        default_factory=lambda: ["person", "car", "door", "stairs", "obstacle"]
    )
    suppress_repeat_ms: float = 10000.0
    verbosity: str = "normal"  # "brief" | "normal" | "detailed"


@dataclass
class NarrationEvent:
    """A narration event to be spoken."""

    event_type: str  # "new_object" | "object_gone" | "scene_change" | "movement" | "hazard"
    description: str
    priority: str = "normal"  # "critical" | "high" | "normal" | "low"
    objects_involved: List[str] = field(default_factory=list)
    timestamp_ms: float = 0.0
    suppress_until_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "description": self.description,
            "priority": self.priority,
            "objects_involved": self.objects_involved,
            "timestamp_ms": self.timestamp_ms,
        }


# =============================================================================
# Scene Narrator
# =============================================================================


class SceneNarrator:
    """Proactively narrates scene changes for blind users.

    Tracks scene state and generates spoken narrations when objects
    appear, disappear, move, or present hazards.

    Usage::

        narrator = SceneNarrator()
        events = await narrator.narrate(
            current_detections=[{"label": "person", "confidence": 0.9}],
            scene_context={"scene_type": "indoor"},
            timestamp_ms=1000,
        )
        for event in events:
            speak(event.description)
    """

    def __init__(self, config: Optional[NarrationConfig] = None):
        self.config = config or NarrationConfig()
        self._last_scene_state: Dict[str, Any] = {"objects": {}, "timestamp_ms": 0}
        self._narration_history: Deque[NarrationEvent] = collections.deque(maxlen=50)
        self._suppressed_events: Dict[str, float] = {}
        self._total_narrations = 0

    async def narrate(
        self,
        current_detections: List[Dict[str, Any]],
        scene_context: Optional[Dict[str, Any]] = None,
        timestamp_ms: float = 0.0,
    ) -> List[NarrationEvent]:
        """Generate narration events from current detections."""
        ts = timestamp_ms or time.time() * 1000

        try:
            events: List[NarrationEvent] = []

            previous_objects = self._last_scene_state.get("objects", {})
            current_objects = {
                d.get("label", d.get("class_name", f"object_{i}")): d
                for i, d in enumerate(current_detections)
            }

            # Detect changes
            events.extend(self._detect_new_objects(current_objects, previous_objects, ts))
            events.extend(self._detect_departed_objects(current_objects, previous_objects, ts))
            events.extend(self._detect_movements(current_objects, previous_objects, ts))
            events.extend(self._detect_hazards(current_objects, ts))

            # Filter suppressed
            events = [e for e in events if not self._is_suppressed(e.event_type, ts)]

            # Suppress reported events
            for e in events:
                self._suppressed_events[e.event_type] = ts + self.config.suppress_repeat_ms

            # Prioritize
            events = self._prioritize_events(events)

            # Update state
            self._last_scene_state = {
                "objects": current_objects,
                "timestamp_ms": ts,
                "scene_context": scene_context,
            }

            for e in events:
                self._narration_history.append(e)

            self._total_narrations += len(events)
            return events

        except Exception as exc:
            logger.error("Narration failed: %s", exc)
            return []

    def _detect_new_objects(
        self,
        current: Dict[str, Dict],
        previous: Dict[str, Dict],
        ts: float,
    ) -> List[NarrationEvent]:
        """Detect objects that are new to the scene."""
        events: List[NarrationEvent] = []
        for label in current:
            if label not in previous:
                is_priority = label.lower() in self.config.priority_objects
                events.append(NarrationEvent(
                    event_type="new_object",
                    description=f"{label} appeared in the scene",
                    priority="high" if is_priority else "normal",
                    objects_involved=[label],
                    timestamp_ms=ts,
                ))
        return events

    def _detect_departed_objects(
        self,
        current: Dict[str, Dict],
        previous: Dict[str, Dict],
        ts: float,
    ) -> List[NarrationEvent]:
        """Detect objects that left the scene."""
        events: List[NarrationEvent] = []
        for label in previous:
            if label not in current:
                events.append(NarrationEvent(
                    event_type="object_gone",
                    description=f"{label} is no longer visible",
                    priority="normal",
                    objects_involved=[label],
                    timestamp_ms=ts,
                ))
        return events

    def _detect_movements(
        self,
        current: Dict[str, Dict],
        previous: Dict[str, Dict],
        ts: float,
    ) -> List[NarrationEvent]:
        """Detect significant movements of existing objects."""
        events: List[NarrationEvent] = []
        for label in current:
            if label not in previous:
                continue
            # Compare bboxes if available
            cur_bbox = current[label].get("bbox")
            prev_bbox = previous[label].get("bbox")
            if cur_bbox and prev_bbox:
                try:
                    if isinstance(cur_bbox, (list, tuple)) and isinstance(prev_bbox, (list, tuple)):
                        dx = abs(cur_bbox[0] - prev_bbox[0])
                        dy = abs(cur_bbox[1] - prev_bbox[1])
                        if dx > 50 or dy > 50:
                            events.append(NarrationEvent(
                                event_type="movement",
                                description=f"{label} has moved",
                                priority="normal",
                                objects_involved=[label],
                                timestamp_ms=ts,
                            ))
                except (IndexError, TypeError):
                    pass
        return events

    def _detect_hazards(
        self,
        current: Dict[str, Dict],
        ts: float,
    ) -> List[NarrationEvent]:
        """Detect potential hazards in current detections."""
        events: List[NarrationEvent] = []
        hazard_objects = {"car", "bicycle", "motorcycle", "truck", "bus"}

        for label, det in current.items():
            if label.lower() in hazard_objects:
                distance = det.get("distance_m", None)
                if distance is not None and distance < 3.0:
                    events.append(NarrationEvent(
                        event_type="hazard",
                        description=f"Caution: {label} detected nearby at {distance:.1f} meters",
                        priority="critical",
                        objects_involved=[label],
                        timestamp_ms=ts,
                    ))
                elif distance is None:
                    events.append(NarrationEvent(
                        event_type="hazard",
                        description=f"Caution: {label} detected in the scene",
                        priority="high",
                        objects_involved=[label],
                        timestamp_ms=ts,
                    ))
        return events

    def _is_suppressed(self, event_type: str, timestamp_ms: float) -> bool:
        """Check if this event type is currently suppressed."""
        suppress_until = self._suppressed_events.get(event_type, 0)
        return timestamp_ms < suppress_until

    def _format_narration(self, events: List[NarrationEvent]) -> str:
        """Format events into a spoken narration string."""
        if not events:
            return ""
        parts = [e.description for e in events[:3]]
        return ". ".join(parts)

    def _prioritize_events(self, events: List[NarrationEvent]) -> List[NarrationEvent]:
        """Sort events by priority."""
        priority_order = {"critical": 0, "high": 1, "normal": 2, "low": 3}
        return sorted(events, key=lambda e: priority_order.get(e.priority, 2))

    def health(self) -> Dict[str, Any]:
        return {
            "total_narrations": self._total_narrations,
            "history_size": len(self._narration_history),
            "suppressed_events": len(self._suppressed_events),
            "tracked_objects": len(self._last_scene_state.get("objects", {})),
        }


# =============================================================================
# Factory
# =============================================================================


def create_scene_narrator(
    config: Optional[NarrationConfig] = None,
) -> SceneNarrator:
    """Factory function for SceneNarrator."""
    return SceneNarrator(config=config)
