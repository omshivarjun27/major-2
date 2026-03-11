"""
Live Frame Manager
==================
Continuous camera capture with ring buffer, publisher-subscriber pipeline,
frame_id tagging, and high-resolution timestamps.

Design:
- Capture loop runs continuously on a background task.
- Frames stored in a fixed-size ring buffer with per-frame metadata.
- Subscribers (perception workers) receive frames via async queues.
- Backpressure: if a subscriber queue is full, oldest frames are dropped.
- Each frame is tagged with a monotonic frame_id and epoch_ms timestamp.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, List, Optional

logger = logging.getLogger("live-frame-manager")


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class TimestampedFrame:
    """A camera frame tagged with identity and timing metadata."""
    frame_id: str
    sequence_num: int
    timestamp_epoch_ms: float
    image: Any  # PIL.Image or np.ndarray
    width: int = 0
    height: int = 0
    source: str = "livekit"

    @property
    def age_ms(self) -> float:
        """Milliseconds since this frame was captured."""
        return (time.time() * 1000) - self.timestamp_epoch_ms

    def is_fresh(self, max_age_ms: float = 500.0) -> bool:
        """Check if frame is within freshness budget."""
        return self.age_ms <= max_age_ms

    def to_dict(self) -> dict:
        return {
            "frame_id": self.frame_id,
            "sequence_num": self.sequence_num,
            "timestamp_epoch_ms": self.timestamp_epoch_ms,
            "age_ms": round(self.age_ms, 1),
            "width": self.width,
            "height": self.height,
            "source": self.source,
        }


@dataclass
class CaptureStats:
    """Telemetry for the capture subsystem."""
    frames_captured: int = 0
    frames_dropped: int = 0
    last_frame_epoch_ms: float = 0.0
    avg_capture_interval_ms: float = 0.0
    subscriber_count: int = 0
    _intervals: Deque[float] = field(default_factory=lambda: deque(maxlen=100))

    def record_capture(self, epoch_ms: float) -> None:
        if self.last_frame_epoch_ms > 0:
            self._intervals.append(epoch_ms - self.last_frame_epoch_ms)
        self.last_frame_epoch_ms = epoch_ms
        self.frames_captured += 1
        if self._intervals:
            self.avg_capture_interval_ms = sum(self._intervals) / len(self._intervals)

    def to_dict(self) -> dict:
        return {
            "frames_captured": self.frames_captured,
            "frames_dropped": self.frames_dropped,
            "last_frame_epoch_ms": self.last_frame_epoch_ms,
            "avg_capture_interval_ms": round(self.avg_capture_interval_ms, 1),
            "subscriber_count": self.subscriber_count,
        }


# ============================================================================
# Ring Buffer
# ============================================================================

class FrameRingBuffer:
    """Fixed-size ring buffer for TimestampedFrames.

    Thread-safe via asyncio (single-writer from capture loop).
    """

    def __init__(self, capacity: int = 30):
        self._capacity = max(1, capacity)
        self._buffer: Deque[TimestampedFrame] = deque(maxlen=self._capacity)

    @property
    def capacity(self) -> int:
        return self._capacity

    def __len__(self) -> int:
        return len(self._buffer)

    def push(self, frame: TimestampedFrame) -> Optional[TimestampedFrame]:
        """Add frame, return evicted frame if buffer was full."""
        evicted = None
        if len(self._buffer) >= self._capacity:
            evicted = self._buffer[0]
        self._buffer.append(frame)
        return evicted

    def latest(self) -> Optional[TimestampedFrame]:
        """Get the most recent frame without removing it."""
        return self._buffer[-1] if self._buffer else None

    def get_frames_since(self, epoch_ms: float) -> List[TimestampedFrame]:
        """Return all frames captured after the given timestamp."""
        return [f for f in self._buffer if f.timestamp_epoch_ms > epoch_ms]

    def clear(self) -> None:
        self._buffer.clear()


# ============================================================================
# Subscriber
# ============================================================================

@dataclass
class FrameSubscriber:
    """A named subscriber with its own async queue."""
    name: str
    queue: asyncio.Queue
    max_queue_size: int = 5
    frames_received: int = 0
    frames_dropped: int = 0
    active: bool = True

    async def get_frame(self, timeout: float = 1.0) -> Optional[TimestampedFrame]:
        """Wait for next frame with timeout."""
        try:
            frame = await asyncio.wait_for(self.queue.get(), timeout=timeout)
            return frame
        except asyncio.TimeoutError:
            return None


# ============================================================================
# Live Frame Manager
# ============================================================================

class LiveFrameManager:
    """Continuous capture → ring buffer → pub-sub distribution.

    Usage::

        manager = LiveFrameManager(capture_fn=my_capture, cadence_ms=100)
        sub = manager.subscribe("detector", max_queue_size=3)
        await manager.start()
        ...
        frame = await sub.get_frame()
    """

    def __init__(
        self,
        capture_fn: Optional[Callable] = None,
        cadence_ms: float = 100.0,
        buffer_capacity: int = 30,
        max_age_ms: float = 500.0,
    ):
        self._capture_fn = capture_fn  # async callable returning (image, width, height)
        self._cadence_s = cadence_ms / 1000.0
        self._max_age_ms = max_age_ms
        self._buffer = FrameRingBuffer(capacity=buffer_capacity)
        self._subscribers: Dict[str, FrameSubscriber] = {}
        self._sequence = 0
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self.stats = CaptureStats()
        self._on_frame_callbacks: List[Callable] = []

    # -- Configuration -------------------------------------------------------

    @property
    def cadence_ms(self) -> float:
        return self._cadence_s * 1000.0

    @cadence_ms.setter
    def cadence_ms(self, value: float) -> None:
        self._cadence_s = max(10, value) / 1000.0

    @property
    def max_age_ms(self) -> float:
        return self._max_age_ms

    @max_age_ms.setter
    def max_age_ms(self, value: float) -> None:
        self._max_age_ms = max(50, value)

    # -- Pub-sub -------------------------------------------------------------

    def subscribe(self, name: str, max_queue_size: int = 5) -> FrameSubscriber:
        """Register a subscriber and return its handle."""
        if name in self._subscribers:
            return self._subscribers[name]
        q = asyncio.Queue(maxsize=max_queue_size)
        sub = FrameSubscriber(name=name, queue=q, max_queue_size=max_queue_size)
        self._subscribers[name] = sub
        self.stats.subscriber_count = len(self._subscribers)
        logger.info("Subscriber registered: %s (queue=%d)", name, max_queue_size)
        return sub

    def unsubscribe(self, name: str) -> None:
        sub = self._subscribers.pop(name, None)
        if sub:
            sub.active = False
            self.stats.subscriber_count = len(self._subscribers)
            logger.info("Subscriber removed: %s", name)

    def on_frame(self, callback: Callable) -> None:
        """Register a synchronous callback invoked on every new frame."""
        self._on_frame_callbacks.append(callback)

    # -- Lifecycle -----------------------------------------------------------

    async def start(self) -> None:
        """Start the continuous capture loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._capture_loop())
        logger.info("LiveFrameManager started (cadence=%.0f ms, buffer=%d)",
                     self.cadence_ms, self._buffer.capacity)

    async def stop(self) -> None:
        """Gracefully stop the capture loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("LiveFrameManager stopped. Stats: %s", self.stats.to_dict())

    @property
    def running(self) -> bool:
        return self._running

    # -- Frame access --------------------------------------------------------

    def get_latest_frame(self) -> Optional[TimestampedFrame]:
        """Return the latest frame from the ring buffer (non-blocking)."""
        return self._buffer.latest()

    def get_fresh_frame(self, max_age_ms: Optional[float] = None) -> Optional[TimestampedFrame]:
        """Return latest frame only if within freshness budget."""
        frame = self._buffer.latest()
        if frame is None:
            return None
        budget = max_age_ms if max_age_ms is not None else self._max_age_ms
        return frame if frame.is_fresh(budget) else None

    async def capture_fresh_frame(self, max_age_ms: Optional[float] = None) -> Optional[TimestampedFrame]:
        """Try to get a fresh frame; if stale, attempt one quick capture."""
        frame = self.get_fresh_frame(max_age_ms)
        if frame is not None:
            return frame
        # Attempt a quick on-demand capture
        return await self._do_capture()

    # -- Injection (for non-continuous / LiveKit integration) -----------------

    async def inject_frame(self, image: Any, width: int = 0, height: int = 0, source: str = "livekit") -> TimestampedFrame:
        """Manually inject a frame (e.g., from LiveKit video track)."""
        self._sequence += 1
        now_ms = time.time() * 1000
        if width == 0 and hasattr(image, "size"):
            width, height = image.size
        elif width == 0 and hasattr(image, "shape"):
            height, width = image.shape[:2]

        frame = TimestampedFrame(
            frame_id=f"frm_{self._sequence:08d}",
            sequence_num=self._sequence,
            timestamp_epoch_ms=now_ms,
            image=image,
            width=width,
            height=height,
            source=source,
        )
        self._buffer.push(frame)
        self.stats.record_capture(now_ms)
        await self._publish(frame)
        return frame

    # -- Internal ------------------------------------------------------------

    async def _capture_loop(self) -> None:
        """Background capture loop."""
        logger.debug("Capture loop started")
        while self._running:
            try:
                await self._do_capture()
                await asyncio.sleep(self._cadence_s)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Capture error: %s", exc)
                await asyncio.sleep(self._cadence_s * 2)  # back off on error

    async def _do_capture(self) -> Optional[TimestampedFrame]:
        """Execute one capture cycle."""
        if self._capture_fn is None:
            return None
        try:
            result = await self._capture_fn()
            if result is None:
                return None
            if isinstance(result, tuple):
                image, width, height = result
            else:
                image = result
                width = getattr(image, "width", 0) or (image.shape[1] if hasattr(image, "shape") else 0)
                height = getattr(image, "height", 0) or (image.shape[0] if hasattr(image, "shape") else 0)
            return await self.inject_frame(image, width, height)
        except Exception as exc:
            logger.error("Capture function failed: %s", exc)
            return None

    async def _publish(self, frame: TimestampedFrame) -> None:
        """Distribute frame to all active subscribers."""
        for sub in list(self._subscribers.values()):
            if not sub.active:
                continue
            try:
                if sub.queue.full():
                    # Drop oldest from subscriber queue (backpressure)
                    try:
                        sub.queue.get_nowait()
                        sub.frames_dropped += 1
                        self.stats.frames_dropped += 1
                    except asyncio.QueueEmpty:
                        pass
                sub.queue.put_nowait(frame)
                sub.frames_received += 1
            except Exception:
                sub.frames_dropped += 1

        # Fire synchronous callbacks
        for cb in self._on_frame_callbacks:
            try:
                cb(frame)
            except Exception as exc:
                logger.warning("on_frame callback error: %s", exc)

    # -- Health --------------------------------------------------------------

    def health(self) -> dict:
        """Return health status for monitoring."""
        latest = self._buffer.latest()
        return {
            "running": self._running,
            "buffer_size": len(self._buffer),
            "buffer_capacity": self._buffer.capacity,
            "latest_frame_age_ms": round(latest.age_ms, 1) if latest else None,
            "latest_frame_id": latest.frame_id if latest else None,
            "stats": self.stats.to_dict(),
            "subscribers": {
                name: {
                    "active": sub.active,
                    "received": sub.frames_received,
                    "dropped": sub.frames_dropped,
                    "queue_size": sub.queue.qsize(),
                }
                for name, sub in self._subscribers.items()
            },
        }
