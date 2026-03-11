"""
Action Recognizer — Temporal action/intent detection from short video clips.

Uses a sliding-window clip buffer → optical flow + lightweight classifier
to detect actions (person approaching, waving, cycling, running, sitting, etc.)
and generate navigational cues for blind users.
"""

from __future__ import annotations

import collections
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Deque, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("action-recognizer")

_CV2_AVAILABLE = False
try:
    import cv2
    _CV2_AVAILABLE = True
except ImportError:
    pass


class ActionType(str, Enum):
    APPROACHING = "approaching"
    WALKING_AWAY = "walking_away"
    WAVING = "waving"
    RUNNING = "running"
    CYCLING = "cycling"
    STANDING = "standing"
    SITTING = "sitting"
    FALLING = "falling"
    REACHING = "reaching"
    UNKNOWN = "unknown"
    NO_ACTION = "no_action"


# Actions that should trigger immediate vocal alerts
ALERT_ACTIONS = {
    ActionType.APPROACHING,
    ActionType.RUNNING,
    ActionType.CYCLING,
    ActionType.FALLING,
}


@dataclass
class ActionConfig:
    """Configuration for the action recognizer."""
    clip_length: int = 16                  # frames in one analysis clip
    clip_stride: int = 4                   # frames between analysis triggers
    min_confidence: float = 0.3
    flow_scale: float = 0.5               # image resize for optical flow
    grid_size: int = 4                     # NxN grid for flow summarization
    model_path: Optional[str] = None      # path to trained action model


@dataclass
class ActionResult:
    """Detected action result."""
    action_type: ActionType
    confidence: float
    flow_magnitude: float
    flow_direction: str            # "left", "right", "towards", "away", etc.
    bounding_region: Optional[Tuple[float, float, float, float]] = None  # x1,y1,x2,y2 normalized
    timestamp_ms: float = 0.0
    all_scores: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "action_type": self.action_type.value,
            "confidence": round(self.confidence, 3),
            "flow_magnitude": round(self.flow_magnitude, 2),
            "flow_direction": self.flow_direction,
            "timestamp_ms": self.timestamp_ms,
            "is_alert": self.action_type in ALERT_ACTIONS,
        }

    @property
    def user_cue(self) -> str:
        cues = {
            ActionType.APPROACHING: "Person approaching you",
            ActionType.WALKING_AWAY: "Person walking away",
            ActionType.WAVING: "Someone is waving at you",
            ActionType.RUNNING: "Person running nearby — stay alert",
            ActionType.CYCLING: "Cyclist detected — exercise caution",
            ActionType.STANDING: "Person standing nearby",
            ActionType.SITTING: "Person sitting nearby",
            ActionType.FALLING: "Someone may have fallen nearby",
            ActionType.REACHING: "Someone reaching towards you",
        }
        return cues.get(self.action_type, "")


class ClipBuffer:
    """Sliding-window frame buffer for temporal analysis.

    Stores the last N frames and triggers analysis every `stride` frames.
    """

    def __init__(self, length: int = 16, stride: int = 4):
        self.length = length
        self.stride = stride
        self._buffer: Deque[np.ndarray] = collections.deque(maxlen=length)
        self._timestamps: Deque[float] = collections.deque(maxlen=length)
        self._frame_count = 0

    def add_frame(self, frame: np.ndarray, timestamp_ms: float = 0.0) -> bool:
        """Add a frame. Returns True if buffer is ready for analysis."""
        self._buffer.append(frame)
        self._timestamps.append(timestamp_ms or time.time() * 1000)
        self._frame_count += 1
        return len(self._buffer) >= self.length and (self._frame_count % self.stride == 0)

    def get_clip(self) -> List[np.ndarray]:
        """Return current clip frames."""
        return list(self._buffer)

    def get_timestamps(self) -> List[float]:
        return list(self._timestamps)

    @property
    def count(self) -> int:
        return len(self._buffer)

    def clear(self) -> None:
        self._buffer.clear()
        self._timestamps.clear()
        self._frame_count = 0


class ActionRecognizer:
    """Temporal action recognizer using optical flow + heuristic classifier.

    Buffers frames in a ClipBuffer, computes dense optical flow between
    consecutive frames, summarizes flow in a spatial grid, and classifies
    the dominant action.

    Upgradable to a trained CNN+LSTM model.

    Usage::

        recognizer = ActionRecognizer()
        ready = recognizer.add_frame(frame)
        if ready:
            results = recognizer.analyze()
            for r in results:
                if r.user_cue:
                    speak(r.user_cue)
    """

    def __init__(self, config: Optional[ActionConfig] = None):
        self.config = config or ActionConfig()
        self._buffer = ClipBuffer(self.config.clip_length, self.config.clip_stride)
        self._model = None
        self._init_model()

    def _init_model(self) -> None:
        if self.config.model_path:
            try:
                import torch
                self._model = torch.jit.load(self.config.model_path)
                self._model.eval()
                logger.info("Action model loaded from %s", self.config.model_path)
            except Exception as exc:
                logger.warning("Failed to load action model: %s", exc)
        logger.info("ActionRecognizer initialized (cv2=%s, model=%s)",
                     _CV2_AVAILABLE, self._model is not None)

    def add_frame(self, frame: np.ndarray, timestamp_ms: float = 0.0) -> bool:
        """Add a frame to the clip buffer. Returns True when ready."""
        return self._buffer.add_frame(frame, timestamp_ms)

    def analyze(self) -> List[ActionResult]:
        """Analyze the current clip buffer for actions."""
        clip = self._buffer.get_clip()
        timestamps = self._buffer.get_timestamps()

        if len(clip) < 2:
            return []

        ts = timestamps[-1] if timestamps else time.time() * 1000

        if self._model is not None:
            return self._analyze_model(clip, ts)

        return self._analyze_flow(clip, ts)

    def _analyze_flow(self, clip: List[np.ndarray], ts: float) -> List[ActionResult]:
        """Optical-flow based action classification."""
        flows = self._compute_flows(clip)
        if not flows:
            return [ActionResult(
                action_type=ActionType.NO_ACTION,
                confidence=0.5,
                flow_magnitude=0.0,
                flow_direction="none",
                timestamp_ms=ts,
            )]

        # Aggregate flow statistics
        avg_mag, avg_angle, grid_stats = self._summarize_flows(flows)

        action, conf, scores = self._classify_from_flow(avg_mag, avg_angle, grid_stats)
        direction = self._angle_to_direction(avg_angle)

        return [ActionResult(
            action_type=action,
            confidence=conf,
            flow_magnitude=avg_mag,
            flow_direction=direction,
            timestamp_ms=ts,
            all_scores=scores,
        )]

    def _compute_flows(self, clip: List[np.ndarray]) -> List[np.ndarray]:
        """Compute dense optical flow between consecutive frames."""
        flows = []
        scale = self.config.flow_scale

        for i in range(len(clip) - 1):
            f1, f2 = clip[i], clip[i + 1]

            if _CV2_AVAILABLE:
                # Convert to grayscale if needed
                if len(f1.shape) == 3:
                    g1 = cv2.cvtColor(f1, cv2.COLOR_BGR2GRAY)
                    g2 = cv2.cvtColor(f2, cv2.COLOR_BGR2GRAY)
                else:
                    g1, g2 = f1, f2

                # Resize for speed
                if scale < 1.0:
                    h, w = g1.shape[:2]
                    new_size = (int(w * scale), int(h * scale))
                    g1 = cv2.resize(g1, new_size)
                    g2 = cv2.resize(g2, new_size)

                flow = cv2.calcOpticalFlowFarneback(
                    g1, g2, None,
                    pyr_scale=0.5, levels=3, winsize=15,
                    iterations=3, poly_n=5, poly_sigma=1.2, flags=0,
                )
                flows.append(flow)
            else:
                # Simple frame-difference fallback (no direction info)
                diff = f2.astype(np.float32) - f1.astype(np.float32)
                if len(diff.shape) == 3:
                    diff = diff.mean(axis=2)
                # Create fake 2-channel flow
                flow = np.stack([diff, np.zeros_like(diff)], axis=-1)
                flows.append(flow)

        return flows

    def _summarize_flows(self, flows: List[np.ndarray]) -> Tuple[float, float, np.ndarray]:
        """Summarize flows into magnitude, angle, and grid statistics."""
        all_mag = []
        all_angle = []
        grid_size = self.config.grid_size

        for flow in flows:
            fx, fy = flow[..., 0], flow[..., 1]
            mag = np.sqrt(fx ** 2 + fy ** 2)
            angle = np.arctan2(fy, fx) * 180 / np.pi
            all_mag.append(np.mean(mag))
            all_angle.append(np.mean(angle))

        avg_mag = float(np.mean(all_mag))
        avg_angle = float(np.mean(all_angle))

        # Grid statistics from last flow
        last_flow = flows[-1]
        h, w = last_flow.shape[:2]
        grid = np.zeros((grid_size, grid_size))
        cell_h, cell_w = h // grid_size, w // grid_size
        for gi in range(grid_size):
            for gj in range(grid_size):
                y1, y2 = gi * cell_h, (gi + 1) * cell_h
                x1, x2 = gj * cell_w, (gj + 1) * cell_w
                cell = last_flow[y1:y2, x1:x2]
                grid[gi, gj] = np.mean(np.sqrt(cell[..., 0] ** 2 + cell[..., 1] ** 2))

        return avg_mag, avg_angle, grid

    def _classify_from_flow(
        self, mag: float, angle: float, grid: np.ndarray
    ) -> Tuple[ActionType, float, Dict[str, float]]:
        """Rule-based classification from flow statistics."""
        scores: Dict[str, float] = {}

        # No significant motion
        if mag < 0.5:
            return ActionType.STANDING, 0.5, {"standing": 0.5}

        # Very high center flow = approaching/away
        center = grid.shape[0] // 2
        center_mag = grid[center - 1:center + 1, center - 1:center + 1].mean()

        # Expansion pattern: center flows outward = approaching
        edge_mag = np.mean([
            grid[0, :].mean(), grid[-1, :].mean(),
            grid[:, 0].mean(), grid[:, -1].mean(),
        ])

        if center_mag > mag * 0.8 and edge_mag > center_mag * 0.5:
            # Expansion = object approaching camera
            scores["approaching"] = min(0.7, mag / 10)

        # Contraction = walking away
        if center_mag < edge_mag * 0.5 and mag > 1.0:
            scores["walking_away"] = min(0.6, mag / 15)

        # High lateral flow = running/cycling
        if mag > 3.0:
            if abs(angle) < 45 or abs(angle) > 135:
                scores["cycling"] = min(0.5, mag / 20)
            scores["running"] = min(0.5, mag / 15)

        # Periodic upper-body motion = waving
        upper_mag = grid[:grid.shape[0] // 2, :].mean()
        lower_mag = grid[grid.shape[0] // 2:, :].mean()
        if upper_mag > lower_mag * 2 and 1.0 < mag < 5.0:
            scores["waving"] = 0.4

        # Sudden downward flow = falling
        if angle > 60 and angle < 120 and mag > 5.0:
            scores["falling"] = min(0.5, mag / 20)

        if not scores:
            scores["unknown"] = 0.3
            return ActionType.UNKNOWN, 0.3, scores

        best = max(scores, key=scores.get)
        try:
            action = ActionType(best)
        except ValueError:
            action = ActionType.UNKNOWN
        return action, scores[best], scores

    def _analyze_model(self, clip: List[np.ndarray], ts: float) -> List[ActionResult]:
        """Neural model action analysis (stub)."""
        try:
            import torch
            # Stack frames → (1, T, H, W, C) → permute for model
            tensor = torch.FloatTensor(np.stack(clip)).unsqueeze(0)
            with torch.no_grad():
                logits = self._model(tensor)
                probs = torch.softmax(logits, dim=-1).squeeze().numpy()

            types = list(ActionType)
            best_idx = int(np.argmax(probs))
            action = types[best_idx] if best_idx < len(types) else ActionType.UNKNOWN
            return [ActionResult(
                action_type=action,
                confidence=float(probs[best_idx]),
                flow_magnitude=0.0,
                flow_direction="model",
                timestamp_ms=ts,
            )]
        except Exception as exc:
            logger.debug("Model inference failed: %s", exc)
            return self._analyze_flow(clip, ts)

    @staticmethod
    def _angle_to_direction(angle: float) -> str:
        """Convert angle in degrees to human-readable direction."""
        a = angle % 360
        if a < 22.5 or a >= 337.5:
            return "right"
        elif a < 67.5:
            return "down-right"
        elif a < 112.5:
            return "down"
        elif a < 157.5:
            return "down-left"
        elif a < 202.5:
            return "left"
        elif a < 247.5:
            return "up-left"
        elif a < 292.5:
            return "up"
        else:
            return "up-right"

    def health(self) -> dict:
        return {
            "cv2_available": _CV2_AVAILABLE,
            "model_loaded": self._model is not None,
            "buffer_count": self._buffer.count,
            "clip_length": self.config.clip_length,
        }
