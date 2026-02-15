"""
Per-Frame JSON Telemetry & Misclassification Tracker
=====================================================

Emits one JSON log per processed frame in the mandatory schema and tracks
repeated misclassifications to generate ``meta.alerts``.

Schema (every field present on every log line)::

    {
      "ts": "<ISO8601>",
      "frame_id": "<string>",
      "device": "cpu|cuda",
      "venv": true|false,
      "num_dets": int,
      "detections": [
        {"label": str, "conf": float, "bbox":[x1,y1,x2,y2],
         "edge_density": float, "distance_m": float|null}
      ],
      "qr": {"found": bool, "decoded": str|null,
             "method": "<yolo|opencv|pyzbar|fullframe>"},
      "tts": {"last_output": str, "engine": "<local|remote>",
              "latency_ms": int},
      "errors": ["..."],
      "meta": {"conflicts": [...], "alerts": [...],
               "degraded_latency": bool, "tts_fallback": bool}
    }
"""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger("perception-telemetry")


# ---------------------------------------------------------------------------
# Frame Log dataclass
# ---------------------------------------------------------------------------

@dataclass
class DetectionEntry:
    label: str
    conf: float
    bbox: List[float]
    edge_density: float = 0.0
    distance_m: Optional[float] = None


@dataclass
class QREntry:
    found: bool = False
    decoded: Optional[str] = None
    method: Optional[str] = None
    confidence: Optional[float] = None


@dataclass
class TTSEntry:
    last_output: str = ""
    engine: str = "local"
    latency_ms: int = 0


@dataclass
class MetaEntry:
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    alerts: List[Dict[str, Any]] = field(default_factory=list)
    degraded_latency: bool = False
    tts_fallback: bool = False


@dataclass
class FrameLog:
    """One JSON telemetry record per processed frame."""

    ts: str = ""
    frame_id: str = ""
    device: str = "cpu"
    venv: bool = True
    num_dets: int = 0
    detections: List[DetectionEntry] = field(default_factory=list)
    qr: QREntry = field(default_factory=QREntry)
    tts: TTSEntry = field(default_factory=TTSEntry)
    errors: List[str] = field(default_factory=list)
    meta: MetaEntry = field(default_factory=MetaEntry)

    def __post_init__(self):
        if not self.ts:
            self.ts = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)


# ---------------------------------------------------------------------------
# Emitter
# ---------------------------------------------------------------------------

def emit_frame_log(frame_log: FrameLog) -> None:
    """Serialise and emit a per-frame JSON log line."""
    try:
        line = frame_log.to_json()
        logger.info(line, extra={"event": "frame_telemetry", "frame_id": frame_log.frame_id})
    except Exception as exc:
        logger.error("Failed to emit frame log: %s", exc, exc_info=True)


# ---------------------------------------------------------------------------
# Metrics accumulator (for /debug/metrics)
# ---------------------------------------------------------------------------

class MetricsAccumulator:
    """Thread-safe-ish accumulator for per-frame latency and error counters.

    Maintains rolling windows for latency and misclassification tracking.
    """

    def __init__(self, window: int = 100):
        self._window = window
        self._latencies: Deque[float] = deque(maxlen=window)
        self.total_frames: int = 0
        self.degraded_frames: int = 0
        self.tts_failures: int = 0
        self.misclassification_alerts: int = 0

    def record_frame(self, latency_ms: float, degraded: bool = False) -> None:
        self._latencies.append(latency_ms)
        self.total_frames += 1
        if degraded:
            self.degraded_frames += 1

    def record_tts_failure(self) -> None:
        self.tts_failures += 1

    def record_misclass_alert(self) -> None:
        self.misclassification_alerts += 1

    @property
    def avg_latency_ms(self) -> float:
        if not self._latencies:
            return 0.0
        return sum(self._latencies) / len(self._latencies)

    @property
    def misclassification_rate(self) -> float:
        if self.total_frames == 0:
            return 0.0
        return self.misclassification_alerts / self.total_frames

    def to_dict(self) -> Dict[str, Any]:
        return {
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "tts_failures": self.tts_failures,
            "misclassification_rate": round(self.misclassification_rate, 4),
            "total_frames_processed": self.total_frames,
            "degraded_latency_frames": self.degraded_frames,
        }


# Singleton
_metrics = MetricsAccumulator()


def get_metrics() -> MetricsAccumulator:
    return _metrics


# ---------------------------------------------------------------------------
# Misclassification Tracker
# ---------------------------------------------------------------------------

class MisclassificationTracker:
    """Track repeated mislabels per class within a sliding time window.

    When >``alert_count`` repeated detections of the same correction pattern
    within ``window_seconds``, an alert is generated with sample frame refs.
    """

    def __init__(
        self,
        alert_count: int = 3,
        window_seconds: float = 30.0,
    ):
        self.alert_count = alert_count
        self.window_seconds = window_seconds
        # class_label → deque of (timestamp, frame_id)
        self._history: Dict[str, Deque[Tuple[float, str]]] = defaultdict(
            lambda: deque(maxlen=50)
        )

    def record(self, label: str, frame_id: str) -> Optional[Dict[str, Any]]:
        """Record a detection that was flagged by the secondary verifier.

        Returns an alert dict if threshold exceeded, else None.
        """
        now = time.monotonic()
        hist = self._history[label]
        hist.append((now, frame_id))

        # Prune old entries
        cutoff = now - self.window_seconds
        while hist and hist[0][0] < cutoff:
            hist.popleft()

        if len(hist) >= self.alert_count:
            sample_frames = [fid for _, fid in list(hist)[-3:]]
            alert = {
                "type": "repeated_misclassification",
                "label": label,
                "count": len(hist),
                "window_seconds": self.window_seconds,
                "sample_frames": sample_frames,
                "ts": datetime.now(timezone.utc).isoformat(),
            }
            _metrics.record_misclass_alert()
            logger.warning(
                "meta.alerts: repeated misclassification for '%s' (%d in %.0fs)",
                label, len(hist), self.window_seconds,
            )
            # Reset to avoid flooding
            hist.clear()
            return alert

        return None


# Module-level singleton
_misclass_tracker = MisclassificationTracker()


def get_misclass_tracker() -> MisclassificationTracker:
    return _misclass_tracker
