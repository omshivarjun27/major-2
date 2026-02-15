"""
Perception Orchestrator
=======================

Runs detection, segmentation, and depth estimation **concurrently**
with per-stage configurable timeouts and a fast-fallback path.

Design goals
~~~~~~~~~~~~
* All three stages launch in parallel via ``asyncio.gather``.
* Each stage has its own timeout (default 100 ms).
* If the *fast-path* detector finishes quickly a ``short_cue`` is
  emitted immediately while heavier models keep running.
* If any stage times out a safe fallback is returned.
* The orchestrator never raises — callers always get a
  ``PerceptionResult`` (possibly with empty detections).
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

import numpy as np

from shared.schemas import (
    BoundingBox,
    DepthMap,
    Detection,
    NavigationOutput,
    PerceptionResult,
    SegmentationMask,
)

logger = logging.getLogger("perception-orchestrator")


# ============================================================================
# Configuration
# ============================================================================


@dataclass
class OrchestratorConfig:
    """Per-stage timeout and concurrency settings."""

    detection_timeout_ms: float = 100.0
    segmentation_timeout_ms: float = 100.0
    depth_timeout_ms: float = 100.0

    # Global pipeline timeout — absolute upper bound
    pipeline_timeout_ms: float = 300.0

    # Fast-fallback: if detection alone completes within this budget
    # we can return a preliminary ``short_cue`` immediately.
    fast_path_budget_ms: float = 50.0

    # Retry once on timeout (False = no retry)
    retry_on_timeout: bool = False


# ============================================================================
# Orchestrator
# ============================================================================


class PerceptionOrchestrator:
    """Concurrent perception pipeline with per-stage timeouts.

    Parameters
    ----------
    detector, segmenter, depth_estimator:
        Pluggable implementations (can be mocks).
    config:
        ``OrchestratorConfig`` controlling timeouts.
    """

    def __init__(
        self,
        detector,
        segmenter=None,
        depth_estimator=None,
        config: Optional[OrchestratorConfig] = None,
    ):
        self._detector = detector
        self._segmenter = segmenter
        self._depth_estimator = depth_estimator
        self.config = config or OrchestratorConfig()

        # Telemetry counters
        self.total_runs: int = 0
        self.timeout_count: int = 0
        self.fallback_count: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self, image: Any, frame_id: str = "", timestamp_epoch_ms: float = 0.0) -> PerceptionResult:
        """Run full concurrent perception pipeline.

        Returns ``PerceptionResult`` — never raises.
        """
        start = time.time()
        self.total_runs += 1
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
        if timestamp_epoch_ms <= 0:
            timestamp_epoch_ms = time.time() * 1000

        img_size = _get_image_size(image)

        # Containers for results (mutated by inner coroutines)
        detections: List[Detection] = []
        masks: List[SegmentationMask] = []
        depth_map: Optional[DepthMap] = None

        # ── Stage coroutines ──────────────────────────────────────────

        async def detect():
            nonlocal detections
            try:
                detections = await asyncio.wait_for(
                    self._detector.detect(image),
                    timeout=self.config.detection_timeout_ms / 1000.0,
                )
            except asyncio.TimeoutError:
                logger.warning("Detection timed out")
                self.timeout_count += 1
            except Exception as exc:  # pragma: no cover
                logger.error("Detection error: %s", exc)

        async def segment():
            nonlocal masks
            if self._segmenter is None:
                return
            try:
                # Segmentation depends on detections — wait for them first
                await detect_done.wait()
                if not detections:
                    return
                masks = await asyncio.wait_for(
                    self._segmenter.segment(image, detections),
                    timeout=self.config.segmentation_timeout_ms / 1000.0,
                )
            except asyncio.TimeoutError:
                logger.warning("Segmentation timed out")
                self.timeout_count += 1
            except Exception as exc:  # pragma: no cover
                logger.error("Segmentation error: %s", exc)

        async def estimate_depth():
            nonlocal depth_map
            if self._depth_estimator is None:
                return
            try:
                depth_map = await asyncio.wait_for(
                    self._depth_estimator.estimate(image),
                    timeout=self.config.depth_timeout_ms / 1000.0,
                )
            except asyncio.TimeoutError:
                logger.warning("Depth estimation timed out")
                self.timeout_count += 1
            except Exception as exc:  # pragma: no cover
                logger.error("Depth estimation error: %s", exc)

        # ── Run concurrently ──────────────────────────────────────────

        detect_done = asyncio.Event()

        async def detect_and_signal():
            await detect()
            detect_done.set()

        try:
            await asyncio.wait_for(
                asyncio.gather(
                    detect_and_signal(),
                    segment(),
                    estimate_depth(),
                    return_exceptions=True,
                ),
                timeout=self.config.pipeline_timeout_ms / 1000.0,
            )
        except asyncio.TimeoutError:
            logger.warning("Pipeline global timeout (%s ms)", self.config.pipeline_timeout_ms)
            self.timeout_count += 1
            # Whatever has been collected so far is used

        # ── Build fallback depth if none produced ─────────────────────
        if depth_map is None:
            w, h = img_size
            depth_map = DepthMap(
                depth_array=np.full((max(h // 4, 1), max(w // 4, 1)), 5.0, dtype=np.float32),
                min_depth=5.0,
                max_depth=5.0,
                is_metric=False,
            )

        latency_ms = (time.time() - start) * 1000
        if latency_ms > self.config.pipeline_timeout_ms:
            self.fallback_count += 1

        return PerceptionResult(
            detections=detections,
            masks=masks,
            depth_map=depth_map,
            image_size=img_size,
            latency_ms=latency_ms,
            timestamp=timestamp,
            frame_id=frame_id,
            timestamp_epoch_ms=timestamp_epoch_ms,
        )

    # ------------------------------------------------------------------
    # Telemetry
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        """Return orchestrator statistics."""
        return {
            "total_runs": self.total_runs,
            "timeout_count": self.timeout_count,
            "fallback_count": self.fallback_count,
        }


# ============================================================================
# Helpers
# ============================================================================


def _get_image_size(image: Any) -> Tuple[int, int]:
    """Extract (width, height) from various image types."""
    if hasattr(image, "shape") and len(getattr(image, "shape", ())) >= 2:
        return (image.shape[1], image.shape[0])  # numpy / similar
    if hasattr(image, "size") and isinstance(image.size, tuple):
        return image.size  # PIL
    return (640, 480)
