"""
Face Tracker — Continuous multi-face tracking with per-face IDs.

Tracks faces across frames using IoU-based association and optional
embedding-based re-identification. Supports delete/forget per face.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

from .face_detector import FaceDetection

logger = logging.getLogger("face-tracker")


@dataclass
class TrackerConfig:
    """Configuration for face tracking."""
    iou_threshold: float = 0.3
    max_disappeared: int = 15  # frames before losing track
    max_tracked: int = 20
    use_embeddings: bool = False
    embedding_weight: float = 0.4  # blend with IoU


@dataclass
class TrackedFace:
    """A face being tracked across frames."""
    track_id: str
    face_detection: FaceDetection
    first_seen_ms: float
    last_seen_ms: float
    frames_tracked: int = 1
    frames_disappeared: int = 0
    identity_id: Optional[str] = None  # linked to FaceEmbeddingStore
    identity_name: Optional[str] = None

    @property
    def duration_ms(self) -> float:
        return self.last_seen_ms - self.first_seen_ms

    @property
    def is_active(self) -> bool:
        return self.frames_disappeared == 0

    def to_dict(self) -> dict:
        return {
            "track_id": self.track_id,
            "bbox": list(self.face_detection.bbox),
            "confidence": self.face_detection.confidence,
            "first_seen_ms": self.first_seen_ms,
            "last_seen_ms": self.last_seen_ms,
            "duration_ms": round(self.duration_ms, 1),
            "frames_tracked": self.frames_tracked,
            "is_active": self.is_active,
            "identity_id": self.identity_id,
            "identity_name": self.identity_name,
        }


class FaceTracker:
    """Multi-face tracker using IoU association.

    Usage::

        tracker = FaceTracker()
        tracked = tracker.update(detections)
    """

    def __init__(self, config: Optional[TrackerConfig] = None):
        self.config = config or TrackerConfig()
        self._tracks: Dict[str, TrackedFace] = {}
        self._next_id = 0

    def _generate_track_id(self) -> str:
        self._next_id += 1
        return f"trk_{self._next_id:06d}"

    def update(self, detections: List[FaceDetection]) -> List[TrackedFace]:
        """Update tracker with new detections. Returns currently tracked faces."""
        now_ms = time.time() * 1000 if not detections else (
            detections[0].timestamp_ms if detections[0].timestamp_ms > 0 else time.time() * 1000
        )

        if not self._tracks:
            # First frame: create new tracks for all detections
            for det in detections[:self.config.max_tracked]:
                tid = self._generate_track_id()
                self._tracks[tid] = TrackedFace(
                    track_id=tid,
                    face_detection=det,
                    first_seen_ms=now_ms,
                    last_seen_ms=now_ms,
                )
            return list(self._tracks.values())

        if not detections:
            # No detections: increment disappeared count
            to_remove = []
            for tid, track in self._tracks.items():
                track.frames_disappeared += 1
                if track.frames_disappeared > self.config.max_disappeared:
                    to_remove.append(tid)
            for tid in to_remove:
                del self._tracks[tid]
            return list(self._tracks.values())

        # Match detections to existing tracks via IoU
        active_tracks = list(self._tracks.values())
        iou_matrix = self._compute_iou_matrix(active_tracks, detections)

        matched_tracks = set()
        matched_dets = set()

        # Greedy matching by highest IoU
        while True:
            if iou_matrix.size == 0:
                break
            max_idx = np.unravel_index(np.argmax(iou_matrix), iou_matrix.shape)
            max_iou = iou_matrix[max_idx]
            if max_iou < self.config.iou_threshold:
                break

            t_idx, d_idx = max_idx
            track = active_tracks[t_idx]
            det = detections[d_idx]

            track.face_detection = det
            track.last_seen_ms = now_ms
            track.frames_tracked += 1
            track.frames_disappeared = 0

            matched_tracks.add(t_idx)
            matched_dets.add(d_idx)
            iou_matrix[t_idx, :] = -1
            iou_matrix[:, d_idx] = -1

        # Increment disappeared for unmatched tracks
        to_remove = []
        for i, track in enumerate(active_tracks):
            if i not in matched_tracks:
                track.frames_disappeared += 1
                if track.frames_disappeared > self.config.max_disappeared:
                    to_remove.append(track.track_id)
        for tid in to_remove:
            self._tracks.pop(tid, None)

        # Create new tracks for unmatched detections
        for i, det in enumerate(detections):
            if i not in matched_dets and len(self._tracks) < self.config.max_tracked:
                tid = self._generate_track_id()
                self._tracks[tid] = TrackedFace(
                    track_id=tid,
                    face_detection=det,
                    first_seen_ms=now_ms,
                    last_seen_ms=now_ms,
                )

        return list(self._tracks.values())

    @staticmethod
    def _compute_iou_matrix(tracks: List[TrackedFace], detections: List[FaceDetection]) -> np.ndarray:
        matrix = np.zeros((len(tracks), len(detections)), dtype=np.float32)
        for i, track in enumerate(tracks):
            for j, det in enumerate(detections):
                matrix[i, j] = FaceTracker._iou(track.face_detection.bbox, det.bbox)
        return matrix

    @staticmethod
    def _iou(box_a: Tuple[int, int, int, int], box_b: Tuple[int, int, int, int]) -> float:
        x1 = max(box_a[0], box_b[0])
        y1 = max(box_a[1], box_b[1])
        x2 = min(box_a[2], box_b[2])
        y2 = min(box_a[3], box_b[3])
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
        area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
        union = area_a + area_b - inter
        return inter / union if union > 0 else 0.0

    def get_active_tracks(self) -> List[TrackedFace]:
        return [t for t in self._tracks.values() if t.is_active]

    def get_track(self, track_id: str) -> Optional[TrackedFace]:
        return self._tracks.get(track_id)

    def remove_track(self, track_id: str) -> bool:
        return self._tracks.pop(track_id, None) is not None

    def clear(self) -> None:
        self._tracks.clear()

    def count(self) -> int:
        return len(self._tracks)

    def health(self) -> dict:
        active = self.get_active_tracks()
        return {
            "total_tracks": self.count(),
            "active_tracks": len(active),
            "config": {
                "iou_threshold": self.config.iou_threshold,
                "max_disappeared": self.config.max_disappeared,
            },
        }
