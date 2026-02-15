"""
Audio Output Manager
====================

Single-writer audio output with interrupt, queue, and overlap prevention.

Fixes the #3 root cause: proactive announcements overlapping with
agent speech, and no mechanism to interrupt current speech cleanly.

Architecture::

    Source 1 (Agent TTS) ──┐
                           ├──→ AudioOutputManager ──→ WebRTC/Speaker
    Source 2 (Proactive) ──┘     (single writer)
                                 (priority queue)
                                 (interrupt support)

Rules:
  1. Only one audio source plays at a time (serialized)
  2. Higher-priority messages can interrupt lower-priority ones
  3. New user speech immediately cancels all pending audio
  4. Proactive warnings wait for agent speech to finish
  5. Critical warnings (< 1m obstacle) can interrupt everything
"""

from __future__ import annotations

import asyncio
import enum
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, List, Optional

logger = logging.getLogger("audio-manager")


class AudioPriority(enum.IntEnum):
    """Audio output priorities. Lower value = higher priority."""
    CRITICAL_HAZARD = 0   # "Stop! Wall ahead" — interrupts everything
    USER_RESPONSE = 1     # Agent's response to user query
    PROACTIVE_WARNING = 2 # Background hazard announcements
    SYSTEM_STATUS = 3     # "Degraded mode", "Camera stalled"
    AMBIENT = 4           # Low-priority ambient status


@dataclass
class AudioRequest:
    """A request to speak text via TTS."""
    text: str
    priority: AudioPriority
    request_id: str = ""
    created_at: float = field(default_factory=time.monotonic)
    max_age_ms: float = 5000.0  # Drop if older than this
    interruptible: bool = True   # Can be interrupted by higher priority

    @property
    def age_ms(self) -> float:
        return (time.monotonic() - self.created_at) * 1000

    @property
    def is_expired(self) -> bool:
        return self.age_ms > self.max_age_ms


class AudioOutputManager:
    """Thread-safe, priority-aware audio output coordinator.

    Ensures only one audio output is active at a time,
    with support for interruption and cancellation.

    Usage::

        mgr = AudioOutputManager(say_fn=agent_session.say)
        await mgr.start()

        # From agent response path:
        await mgr.enqueue("Hello, I see a door ahead.",
                          priority=AudioPriority.USER_RESPONSE)

        # From proactive announcer:
        await mgr.enqueue("Caution, chair 2 meters left.",
                          priority=AudioPriority.PROACTIVE_WARNING)

        # On new user speech (interrupt everything):
        mgr.interrupt_all()
    """

    def __init__(
        self,
        say_fn: Optional[Callable] = None,
        max_queue_size: int = 10,
        min_interval_ms: float = 500.0,
    ):
        """
        Args:
            say_fn: Async callable to speak text (e.g., agent_session.say).
            max_queue_size: Max pending audio requests.
            min_interval_ms: Minimum time between consecutive utterances.
        """
        self._say_fn = say_fn
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue(
            maxsize=max_queue_size
        )
        self._min_interval_s = min_interval_ms / 1000.0
        self._playing = False
        self._playing_priority: Optional[AudioPriority] = None
        self._current_text: str = ""
        self._cancel_current = asyncio.Event()
        self._worker_task: Optional[asyncio.Task] = None
        self._running = False
        self._lock = asyncio.Lock()
        self._last_play_time: float = 0.0
        self._request_counter = 0

        # Telemetry
        self._total_played = 0
        self._total_interrupted = 0
        self._total_dropped = 0
        self._total_expired = 0

    # ── Lifecycle ───────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the audio output worker."""
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(
            self._output_worker(), name="audio_output_worker"
        )
        logger.info("AudioOutputManager started")

    async def stop(self) -> None:
        """Stop the audio output worker."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("AudioOutputManager stopped")

    # ── Public API ──────────────────────────────────────────────────

    async def enqueue(
        self,
        text: str,
        priority: AudioPriority = AudioPriority.USER_RESPONSE,
        max_age_ms: float = 5000.0,
        interruptible: bool = True,
    ) -> bool:
        """Enqueue text for TTS playback.

        Returns True if enqueued, False if dropped.
        """
        if not text or not text.strip():
            return False

        self._request_counter += 1
        request = AudioRequest(
            text=text.strip(),
            priority=priority,
            request_id=f"audio_{self._request_counter}",
            max_age_ms=max_age_ms,
            interruptible=interruptible,
        )

        # Check if this should interrupt current playback
        if self._playing and self._playing_priority is not None:
            if priority.value < self._playing_priority.value:
                # Higher priority: interrupt current
                logger.info(
                    "Interrupting '%s' (priority %s) for '%s' (priority %s)",
                    self._current_text[:30], self._playing_priority.name,
                    text[:30], priority.name,
                )
                self._cancel_current.set()
                self._total_interrupted += 1

        try:
            # Priority queue: (priority_value, counter, request)
            self._queue.put_nowait((priority.value, self._request_counter, request))
            return True
        except asyncio.QueueFull:
            self._total_dropped += 1
            logger.debug("Audio queue full, dropping: '%s'", text[:30])
            return False

    def interrupt_all(self) -> None:
        """Interrupt current playback and clear the queue.

        Call this when a new user utterance is detected (VAD trigger).
        """
        # Cancel current playback
        self._cancel_current.set()

        # Drain the queue
        drained = 0
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                drained += 1
            except asyncio.QueueEmpty:
                break

        if drained > 0 or self._playing:
            self._total_interrupted += 1
            logger.info(
                "Interrupted all audio (drained %d pending, was_playing=%s)",
                drained, self._playing,
            )

    # ── Internal Worker ─────────────────────────────────────────────

    async def _output_worker(self) -> None:
        """Consume audio requests and play them sequentially."""
        while self._running:
            try:
                # Wait for next request
                try:
                    priority_val, counter, request = await asyncio.wait_for(
                        self._queue.get(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Drop expired requests
                if request.is_expired:
                    self._total_expired += 1
                    logger.debug("Dropped expired audio: '%s'", request.text[:30])
                    continue

                # Enforce minimum interval
                elapsed_since_last = time.monotonic() - self._last_play_time
                if elapsed_since_last < self._min_interval_s:
                    wait_time = self._min_interval_s - elapsed_since_last
                    await asyncio.sleep(wait_time)

                # Play
                self._playing = True
                self._playing_priority = request.priority
                self._current_text = request.text
                self._cancel_current.clear()

                try:
                    if self._say_fn:
                        # Race: either say() completes or cancel is triggered
                        say_task = asyncio.create_task(
                            self._say_fn(request.text)
                        )
                        cancel_task = asyncio.create_task(
                            self._cancel_current.wait()
                        )

                        done, pending = await asyncio.wait(
                            [say_task, cancel_task],
                            return_when=asyncio.FIRST_COMPLETED,
                        )

                        for t in pending:
                            t.cancel()
                            try:
                                await t
                            except asyncio.CancelledError:
                                pass

                        if cancel_task in done:
                            # Interrupted
                            logger.debug("Audio interrupted: '%s'", request.text[:30])
                        else:
                            self._total_played += 1
                            self._last_play_time = time.monotonic()

                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    logger.warning("Audio playback failed: %s", exc)
                finally:
                    self._playing = False
                    self._playing_priority = None
                    self._current_text = ""

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Audio output worker error: %s", exc)

    # ── Properties ──────────────────────────────────────────────────

    @property
    def is_playing(self) -> bool:
        return self._playing

    @property
    def queue_size(self) -> int:
        return self._queue.qsize()

    def health(self) -> dict:
        return {
            "running": self._running,
            "playing": self._playing,
            "playing_priority": self._playing_priority.name if self._playing_priority else None,
            "current_text": self._current_text[:50] if self._current_text else None,
            "queue_size": self._queue.qsize(),
            "total_played": self._total_played,
            "total_interrupted": self._total_interrupted,
            "total_dropped": self._total_dropped,
            "total_expired": self._total_expired,
        }
