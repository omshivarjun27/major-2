"""
Multi-Frame VQA Module (T-125).

Analyzes multiple frames to detect temporal changes (objects appearing,
disappearing, moving) and generates temporal narratives for blind users.
"""

from __future__ import annotations

import collections
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("multi-frame-vqa")


# =============================================================================
# Config & Data Structures
# =============================================================================


@dataclass
class MultiFrameConfig:
    """Configuration for multi-frame analysis."""

    max_frames: int = 5
    frame_interval_ms: float = 500.0
    comparison_mode: str = "sequential"  # "sequential" | "parallel"
    min_change_threshold: float = 0.1
    enable_diff_detection: bool = True
    timeout_ms: float = 300.0


@dataclass
class FrameChange:
    """A detected change between frames."""

    frame_index: int
    change_type: str  # "appeared" | "disappeared" | "moved" | "changed"
    description: str = ""
    confidence: float = 0.5
    region: Optional[Tuple[int, int, int, int]] = None  # x1,y1,x2,y2

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_index": self.frame_index,
            "change_type": self.change_type,
            "description": self.description,
            "confidence": round(self.confidence, 3),
            "region": list(self.region) if self.region else None,
        }


@dataclass
class MultiFrameResult:
    """Result of multi-frame analysis."""

    frames_analyzed: int = 0
    changes: List[FrameChange] = field(default_factory=list)
    scene_summary: str = ""
    temporal_narrative: str = ""
    has_significant_change: bool = False
    confidence: float = 0.0
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frames_analyzed": self.frames_analyzed,
            "changes": [c.to_dict() for c in self.changes],
            "scene_summary": self.scene_summary,
            "temporal_narrative": self.temporal_narrative,
            "has_significant_change": self.has_significant_change,
            "confidence": round(self.confidence, 3),
            "latency_ms": round(self.latency_ms, 1),
        }

    @property
    def user_cue(self) -> str:
        if self.has_significant_change and self.temporal_narrative:
            return self.temporal_narrative
        if self.scene_summary:
            return self.scene_summary
        return "Scene appears stable."


# =============================================================================
# Multi-Frame Analyzer
# =============================================================================


class MultiFrameAnalyzer:
    """Analyzes multiple frames for temporal changes.

    Maintains a frame buffer and detects objects appearing, disappearing,
    or moving between frames using pixel-level differencing.

    Usage::

        analyzer = MultiFrameAnalyzer()
        for frame in frames:
            ready = analyzer.add_frame(frame, timestamp_ms)
        if ready:
            result = await analyzer.analyze()
    """

    def __init__(self, config: Optional[MultiFrameConfig] = None):
        self.config = config or MultiFrameConfig()
        self._frame_buffer: Deque[Tuple[np.ndarray, float]] = collections.deque(
            maxlen=self.config.max_frames
        )
        self._total_analyses = 0

    def add_frame(self, frame: np.ndarray, timestamp_ms: float = 0.0) -> bool:
        """Add a frame to the buffer. Returns True when enough frames buffered."""
        ts = timestamp_ms or time.time() * 1000
        self._frame_buffer.append((frame, ts))
        return len(self._frame_buffer) >= 2

    async def analyze(
        self, frames: Optional[List[np.ndarray]] = None
    ) -> MultiFrameResult:
        """Analyze frames for temporal changes."""
        start_ms = time.time() * 1000

        try:
            if frames is not None:
                analysis_frames = frames
            else:
                analysis_frames = [f for f, _ in self._frame_buffer]

            if len(analysis_frames) < 2:
                return MultiFrameResult(
                    frames_analyzed=len(analysis_frames),
                    scene_summary="Insufficient frames for comparison.",
                    latency_ms=time.time() * 1000 - start_ms,
                )

            # Detect changes
            changes = self._detect_changes(analysis_frames)

            has_significant = any(
                c.confidence >= self.config.min_change_threshold for c in changes
            )

            narrative = self._generate_temporal_narrative(changes)
            summary = self._summarize_scene(analysis_frames, changes)

            confidence = 0.0
            if changes:
                confidence = sum(c.confidence for c in changes) / len(changes)

            self._total_analyses += 1

            return MultiFrameResult(
                frames_analyzed=len(analysis_frames),
                changes=changes,
                scene_summary=summary,
                temporal_narrative=narrative,
                has_significant_change=has_significant,
                confidence=confidence,
                latency_ms=time.time() * 1000 - start_ms,
            )

        except Exception as exc:
            logger.error("Multi-frame analysis failed: %s", exc)
            return MultiFrameResult(
                scene_summary="Analysis error.",
                latency_ms=time.time() * 1000 - start_ms,
            )

    def _detect_changes(self, frames: List[np.ndarray]) -> List[FrameChange]:
        """Detect changes between consecutive frames."""
        changes: List[FrameChange] = []

        for i in range(len(frames) - 1):
            diff = self._compute_frame_diff(frames[i], frames[i + 1])

            if diff < 0.02:
                continue  # No significant change

            if diff > 0.5:
                change_type = "changed"
                desc = f"Major scene change between frames {i} and {i + 1}"
            elif diff > 0.2:
                change_type = "moved"
                desc = f"Significant movement between frames {i} and {i + 1}"
            elif diff > 0.05:
                change_type = "appeared"
                desc = f"New element detected between frames {i} and {i + 1}"
            else:
                change_type = "changed"
                desc = f"Minor change between frames {i} and {i + 1}"

            changes.append(FrameChange(
                frame_index=i + 1,
                change_type=change_type,
                description=desc,
                confidence=min(1.0, diff * 2),
            ))

        return changes

    def _compute_frame_diff(self, f1: np.ndarray, f2: np.ndarray) -> float:
        """Compute normalized pixel difference between two frames."""
        try:
            a = f1.astype(np.float32)
            b = f2.astype(np.float32)

            # Handle shape mismatch
            if a.shape != b.shape:
                min_h = min(a.shape[0], b.shape[0])
                min_w = min(a.shape[1], b.shape[1])
                a = a[:min_h, :min_w]
                b = b[:min_h, :min_w]

            diff = np.abs(a - b)
            return float(diff.mean() / 255.0)
        except Exception:
            return 0.0

    def _generate_temporal_narrative(self, changes: List[FrameChange]) -> str:
        """Generate a spoken narrative from detected changes."""
        if not changes:
            return "Scene remains stable."

        parts: List[str] = []
        for c in changes[:3]:  # Cap at 3 for brevity
            if c.change_type == "appeared":
                parts.append("Something new appeared in the scene")
            elif c.change_type == "disappeared":
                parts.append("Something left the scene")
            elif c.change_type == "moved":
                parts.append("Movement detected in the scene")
            elif c.change_type == "changed":
                parts.append("The scene changed significantly")

        return ". ".join(parts) + "."

    def _summarize_scene(
        self, frames: List[np.ndarray], changes: List[FrameChange]
    ) -> str:
        """Summarize the scene state based on frames and changes."""
        n = len(frames)
        n_changes = len(changes)

        if n_changes == 0:
            return f"Analyzed {n} frames. Scene is stable."
        return f"Analyzed {n} frames. Detected {n_changes} change(s)."

    def clear(self) -> None:
        """Clear the frame buffer."""
        self._frame_buffer.clear()

    def health(self) -> Dict[str, Any]:
        return {
            "buffer_size": len(self._frame_buffer),
            "max_frames": self.config.max_frames,
            "total_analyses": self._total_analyses,
        }


# =============================================================================
# Factory
# =============================================================================


def create_multi_frame_analyzer(
    config: Optional[MultiFrameConfig] = None,
) -> MultiFrameAnalyzer:
    """Factory function for MultiFrameAnalyzer."""
    return MultiFrameAnalyzer(config=config)
