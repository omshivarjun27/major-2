"""
Adaptive Frame Sampler
======================

Intelligent frame sampling that adapts to system load.
Instead of processing every frame at 10fps (100ms cadence),
dynamically adjusts sampling rate based on:

  1. Current processing latency
  2. Scene change detection (skip unchanged scenes)
  3. User interaction state (sample faster during active queries)
  4. CPU/memory load

This fixes frame queue backlog and reduces unnecessary processing.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("frame-sampler")


@dataclass
class SamplerConfig:
    """Configuration for adaptive frame sampling."""
    # Base cadence (ms between samples)
    base_cadence_ms: float = 200.0       # Default: 5fps
    min_cadence_ms: float = 100.0        # Max: 10fps (during user query)
    max_cadence_ms: float = 1000.0       # Min: 1fps (idle, nothing changing)

    # Scene change thresholds
    scene_change_threshold: float = 0.15  # 15% pixel change = new scene
    hash_block_size: int = 8             # Downsample to 8x8 for perceptual hash

    # Load-based adaptation
    target_processing_ms: float = 200.0   # Target time for frame processing
    max_processing_ms: float = 400.0      # Slow down if exceeding this

    # Latency history window
    latency_window: int = 20

    # Idle detection
    idle_threshold_ms: float = 5000.0     # No user interaction for this long → idle


class AdaptiveFrameSampler:
    """Samples frames at a dynamically-adjusted rate.

    Instead of a fixed 100ms cadence that overwhelms the pipeline,
    this sampler adjusts based on scene changes and system load.

    Usage::

        sampler = AdaptiveFrameSampler(config)

        # In capture loop:
        if sampler.should_sample(frame):
            result = await process(frame)
            sampler.record_processing(result.latency_ms)
    """

    def __init__(self, config: Optional[SamplerConfig] = None):
        self.config = config or SamplerConfig()
        self._current_cadence_ms = self.config.base_cadence_ms
        self._last_sample_time: float = 0.0
        self._last_hash: str = ""
        self._processing_latencies: Deque[float] = deque(
            maxlen=self.config.latency_window
        )
        self._last_user_interaction: float = time.monotonic()
        self._frames_sampled = 0
        self._frames_skipped = 0
        self._scene_changes = 0
        self._is_idle = False

    def should_sample(self, frame: Any = None) -> bool:
        """Decide whether to process this frame.

        Considers:
          1. Time since last sample (cadence)
          2. Scene change (perceptual hash comparison)
          3. System load (processing latency)

        Call record_processing() after processing to update load metrics.
        """
        now = time.monotonic()
        elapsed_ms = (now - self._last_sample_time) * 1000

        # Respect minimum cadence
        if elapsed_ms < self._current_cadence_ms:
            self._frames_skipped += 1
            return False

        # Check scene change if frame is available
        if frame is not None:
            frame_hash = self._compute_hash(frame)
            if frame_hash == self._last_hash and not self._is_user_active():
                # Scene hasn't changed and user isn't actively querying
                # Slow down sampling
                self._current_cadence_ms = min(
                    self._current_cadence_ms * 1.2,
                    self.config.max_cadence_ms,
                )
                self._frames_skipped += 1
                # Still sample periodically even if scene unchanged
                if elapsed_ms < self.config.max_cadence_ms:
                    return False
            elif frame_hash != self._last_hash:
                self._scene_changes += 1
                # Scene changed: speed up sampling
                self._current_cadence_ms = max(
                    self._current_cadence_ms * 0.8,
                    self.config.min_cadence_ms,
                )
            self._last_hash = frame_hash

        self._last_sample_time = now
        self._frames_sampled += 1
        return True

    def record_processing(self, latency_ms: float) -> None:
        """Record the processing latency for adaptive cadence adjustment."""
        self._processing_latencies.append(latency_ms)

        avg_latency = sum(self._processing_latencies) / len(self._processing_latencies)

        if avg_latency > self.config.max_processing_ms:
            # System is overloaded: slow down
            self._current_cadence_ms = min(
                self._current_cadence_ms * 1.5,
                self.config.max_cadence_ms,
            )
            logger.debug(
                "Frame sampler: slowdown (avg=%.0fms, cadence=%.0fms)",
                avg_latency, self._current_cadence_ms,
            )
        elif avg_latency < self.config.target_processing_ms * 0.5:
            # System has headroom: speed up (but respect min)
            self._current_cadence_ms = max(
                self._current_cadence_ms * 0.9,
                self.config.min_cadence_ms,
            )

    def record_user_interaction(self) -> None:
        """Record that the user is actively interacting.

        Temporarily speeds up frame sampling for responsive perception.
        """
        self._last_user_interaction = time.monotonic()
        self._is_idle = False
        # Speed up during active interaction
        self._current_cadence_ms = self.config.min_cadence_ms

    def _is_user_active(self) -> bool:
        """Check if user has interacted recently."""
        elapsed = (time.monotonic() - self._last_user_interaction) * 1000
        active = elapsed < self.config.idle_threshold_ms
        if not active and not self._is_idle:
            self._is_idle = True
            logger.debug("Frame sampler: entering idle mode")
        return active

    def _compute_hash(self, frame: Any) -> str:
        """Compute a fast perceptual hash of the frame.

        Downsamples to 8x8 grayscale and computes mean-based hash.
        Runtime: <0.1ms per frame.
        """
        try:
            # Convert to numpy if needed
            if hasattr(frame, "image"):
                img = frame.image
            else:
                img = frame

            if hasattr(img, "resize"):
                # PIL Image: fast downsample
                small = img.resize(
                    (self.config.hash_block_size, self.config.hash_block_size)
                ).convert("L")
                pixels = np.array(small, dtype=np.float32).flatten()
            elif isinstance(img, np.ndarray):
                # numpy array: fast resize via slicing
                h, w = img.shape[:2]
                step_h = max(1, h // self.config.hash_block_size)
                step_w = max(1, w // self.config.hash_block_size)
                gray = img[::step_h, ::step_w]
                if gray.ndim == 3:
                    gray = gray.mean(axis=2)
                pixels = gray.flatten().astype(np.float32)
            else:
                return ""

            # Mean-based hash: each pixel is above or below mean
            mean_val = pixels.mean()
            bits = (pixels > mean_val).astype(np.uint8)
            return hashlib.md5(bits.tobytes()).hexdigest()[:16]  # nosec B324 - MD5 used for perceptual frame fingerprint, not security

        except Exception:
            return ""

    @property
    def current_cadence_ms(self) -> float:
        return self._current_cadence_ms

    @property
    def effective_fps(self) -> float:
        if self._current_cadence_ms > 0:
            return 1000.0 / self._current_cadence_ms
        return 0.0

    def health(self) -> dict:
        avg_latency = (
            sum(self._processing_latencies) / len(self._processing_latencies)
            if self._processing_latencies else 0.0
        )
        return {
            "current_cadence_ms": round(self._current_cadence_ms, 0),
            "effective_fps": round(self.effective_fps, 1),
            "frames_sampled": self._frames_sampled,
            "frames_skipped": self._frames_skipped,
            "scene_changes": self._scene_changes,
            "avg_processing_ms": round(avg_latency, 1),
            "is_idle": self._is_idle,
            "sample_ratio": round(
                self._frames_sampled / max(1, self._frames_sampled + self._frames_skipped),
                2,
            ),
        }
