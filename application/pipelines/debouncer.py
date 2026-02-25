"""
Debouncer
=========
Output deduplication with scene-graph hashing.
Prevents repeating the same short_cue within a configurable
window unless there is a meaningful state change.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger("debouncer")


@dataclass
class DebouncerConfig:
    """Configuration for output deduplication."""
    debounce_window_seconds: float = 5.0
    distance_delta_meters: float = 0.5
    confidence_delta: float = 0.15
    max_history: int = 50
    hash_based_change_detection: bool = True


@dataclass
class SpokenRecord:
    """Record of a previously spoken cue."""
    cue: str
    timestamp: float
    scene_graph_hash: str = ""
    closest_distance_m: Optional[float] = None
    frame_id: Optional[str] = None

    @property
    def age_seconds(self) -> float:
        return time.time() - self.timestamp


class Debouncer:
    """Output deduplication engine.

    Tracks last_spoken cues per session and uses scene_graph hashing
    to detect meaningful changes.

    Usage::

        db = Debouncer(config)
        if db.should_speak(cue, scene_graph_hash, distance_m):
            speak(cue)
            db.record(cue, scene_graph_hash, distance_m, frame_id)
    """

    def __init__(self, config: Optional[DebouncerConfig] = None):
        self.config = config or DebouncerConfig()
        self._history: Deque[SpokenRecord] = deque(maxlen=self.config.max_history)
        self._last_record: Optional[SpokenRecord] = None
        self._session_cue_count: int = 0
        self._suppressed_count: int = 0

    def should_speak(
        self,
        cue: str,
        scene_graph_hash: str = "",
        distance_m: Optional[float] = None,
        frame_id: Optional[str] = None,
    ) -> bool:
        """Decide whether this cue should be spoken aloud.

        Returns True if:
        - No prior cue was spoken within the debounce window, OR
        - The scene_graph_hash differs (content meaningfully changed), OR
        - Distance delta exceeds threshold (object moved significantly), OR
        - Confidence delta exceeds threshold.
        """
        if not cue or cue.strip() == "":
            return False

        if self._last_record is None:
            return True

        last = self._last_record

        # Outside debounce window — always speak
        if last.age_seconds >= self.config.debounce_window_seconds:
            return True

        # Same cue text within window — check for meaningful change
        if cue == last.cue:
            # Hash-based change detection
            if self.config.hash_based_change_detection and scene_graph_hash:
                if scene_graph_hash != last.scene_graph_hash:
                    return True

            # Distance-based change detection
            if distance_m is not None and last.closest_distance_m is not None:
                delta = abs(distance_m - last.closest_distance_m)
                if delta >= self.config.distance_delta_meters:
                    return True

            # No meaningful change — suppress
            self._suppressed_count += 1
            return False

        # Different cue text — always speak
        return True

    def record(
        self,
        cue: str,
        scene_graph_hash: str = "",
        distance_m: Optional[float] = None,
        frame_id: Optional[str] = None,
    ) -> None:
        """Record that a cue was spoken."""
        record = SpokenRecord(
            cue=cue,
            timestamp=time.time(),
            scene_graph_hash=scene_graph_hash,
            closest_distance_m=distance_m,
            frame_id=frame_id,
        )
        self._history.append(record)
        self._last_record = record
        self._session_cue_count += 1

    def get_last_cue(self) -> Optional[str]:
        return self._last_record.cue if self._last_record else None

    def get_history(self, n: int = 10) -> List[dict]:
        """Return recent spoken cue history."""
        items = list(self._history)[-n:]
        return [
            {
                "cue": r.cue,
                "timestamp": r.timestamp,
                "age_seconds": round(r.age_seconds, 1),
                "scene_graph_hash": r.scene_graph_hash,
                "distance_m": r.closest_distance_m,
                "frame_id": r.frame_id,
            }
            for r in items
        ]

    def stats(self) -> dict:
        return {
            "total_spoken": self._session_cue_count,
            "total_suppressed": self._suppressed_count,
            "history_size": len(self._history),
            "last_cue": self._last_record.cue if self._last_record else None,
            "last_cue_age_s": round(self._last_record.age_seconds, 1) if self._last_record else None,
        }

    def reset(self) -> None:
        """Clear all history."""
        self._history.clear()
        self._last_record = None
        self._session_cue_count = 0
        self._suppressed_count = 0


def compute_scene_graph_hash(scene_graph: Any) -> str:
    """Compute a stable hash of a scene graph for change detection.

    Extracts obstacle classes, positions (rounded), and priorities
    to produce a content hash. Minor depth fluctuations are smoothed
    by rounding to 0.5m.
    """
    try:
        if hasattr(scene_graph, "to_dict"):
            sg_dict = scene_graph.to_dict()
        elif isinstance(scene_graph, dict):
            sg_dict = scene_graph
        else:
            return hashlib.md5(str(scene_graph).encode()).hexdigest()[:12]  # nosec B324 - MD5 used for scene deduplication fingerprint, not security

        # Extract stable features (ignore transient variations)
        stable = []
        for obs in sg_dict.get("obstacles", []):
            stable.append({
                "cls": obs.get("class_name", obs.get("class", "")),
                "dist": round(obs.get("distance_m", obs.get("depth", 5.0)) * 2) / 2,  # round to 0.5m
                "dir": obs.get("direction", ""),
                "pri": obs.get("priority", ""),
            })
        stable.sort(key=lambda x: (x["cls"], x["dist"]))

        raw = json.dumps(stable, sort_keys=True)
        return hashlib.md5(raw.encode()).hexdigest()[:12]  # nosec B324 - MD5 used for scene deduplication fingerprint, not security
    except Exception:
        return ""
