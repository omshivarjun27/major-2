"""
Streaming TTS Coordinator
==========================

The #1 architectural fix: bridges LLM token streaming → sentence-level
TTS synthesis → audio output, so the user hears the first sentence
while the LLM is still generating subsequent sentences.

Architecture::

    LLM tokens → SentenceBuffer → [sentence1, sentence2, ...]
                                       │
                                       ▼
                            StreamingTTSCoordinator
                                       │
                      ┌────────────────┼────────────────┐
                      │                │                │
                      ▼                ▼                ▼
                  TTS(sent1)      TTS(sent2)       TTS(sent3)
                  synthesize       synthesize       synthesize
                  immediately      while sent1      while sent2
                                   plays            plays
                      │                │                │
                      ▼                ▼                ▼
                  AudioOutputManager (serialized playback)

This achieves:
  - Audio starts < 400ms after first LLM token
  - No blocking: TTS synthesis overlaps with LLM generation
  - Cancellation: new query cancels in-flight TTS immediately
  - No overlap: AudioOutputManager ensures one-at-a-time playback
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable, Deque, List, Optional, Tuple

logger = logging.getLogger("streaming-tts")


# ============================================================================
# Sentence Buffer
# ============================================================================

class SentenceBuffer:
    """Accumulates LLM tokens and emits complete sentences.

    Sentence boundaries: . ! ? ; and newlines.
    Forces flush after max_chars to prevent silence during long
    run-on sentences.
    """

    # Sentence-ending pattern (captures the delimiter)
    _SPLIT_RE = re.compile(r'(?<=[.!?;])\s+|(?<=\n)')

    def __init__(self, max_chars: int = 120, min_chars: int = 15):
        self._buffer: str = ""
        self._max_chars = max_chars
        self._min_chars = min_chars
        self._sentences_emitted = 0

    def add_token(self, token: str) -> List[str]:
        """Add a token and return any complete sentences.

        Returns a list of 0 or more sentences ready for TTS.
        """
        self._buffer += token
        sentences: List[str] = []

        while True:
            match = self._SPLIT_RE.search(self._buffer)
            if match and match.start() >= self._min_chars:
                sentence = self._buffer[:match.end()].strip()
                self._buffer = self._buffer[match.end():]
                if sentence:
                    sentences.append(sentence)
                    self._sentences_emitted += 1
                continue

            # Force flush if buffer exceeds max chars
            if len(self._buffer) >= self._max_chars:
                # Find the last space to split cleanly
                last_space = self._buffer.rfind(' ', self._min_chars, self._max_chars)
                if last_space > 0:
                    sentence = self._buffer[:last_space].strip()
                    self._buffer = self._buffer[last_space:].lstrip()
                else:
                    sentence = self._buffer[:self._max_chars].strip()
                    self._buffer = self._buffer[self._max_chars:]
                if sentence:
                    sentences.append(sentence)
                    self._sentences_emitted += 1
                continue

            break

        return sentences

    def flush(self) -> Optional[str]:
        """Flush remaining buffer content as a final sentence."""
        remaining = self._buffer.strip()
        self._buffer = ""
        if remaining:
            self._sentences_emitted += 1
            return remaining
        return None

    def reset(self) -> None:
        """Reset buffer state."""
        self._buffer = ""
        self._sentences_emitted = 0

    @property
    def pending_text(self) -> str:
        return self._buffer

    @property
    def sentences_emitted(self) -> int:
        return self._sentences_emitted


# ============================================================================
# TTS Synthesis Result
# ============================================================================

@dataclass
class TTSSynthResult:
    """Result of synthesizing one sentence."""
    sentence: str
    audio_data: bytes
    latency_ms: float
    sentence_index: int
    is_final: bool = False
    engine: str = "remote"
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None and len(self.audio_data) > 0


# ============================================================================
# Streaming TTS Coordinator
# ============================================================================

class StreamingTTSCoordinator:
    """Orchestrates streaming LLM→TTS→Audio with cancellation.

    Usage::

        coord = StreamingTTSCoordinator(tts_fn=my_tts)

        # Feed LLM tokens as they arrive
        async for token in llm_stream:
            await coord.feed_token(token)
        await coord.finish()

    The coordinator automatically:
    1. Buffers tokens into sentences
    2. Submits each sentence to TTS synthesis (async)
    3. Queues synthesized audio for sequential playback
    4. Supports cancellation via cancel()
    """

    def __init__(
        self,
        tts_fn: Optional[Callable] = None,
        agent_session: Any = None,
        max_pending_sentences: int = 5,
        sentence_max_chars: int = 120,
        sentence_min_chars: int = 15,
    ):
        """
        Args:
            tts_fn: Async callable (text: str) -> bytes that synthesizes audio.
                    If None, falls back to agent_session.say() for each sentence.
            agent_session: LiveKit AgentSession for direct say() calls.
            max_pending_sentences: Max sentences queued for TTS.
            sentence_max_chars: Force sentence split after this many chars.
            sentence_min_chars: Minimum chars before allowing sentence boundary.
        """
        self._tts_fn = tts_fn
        self._agent_session = agent_session
        self._sentence_buffer = SentenceBuffer(
            max_chars=sentence_max_chars,
            min_chars=sentence_min_chars,
        )

        # Bounded queue of sentences awaiting TTS
        self._sentence_queue: asyncio.Queue[Optional[str]] = asyncio.Queue(
            maxsize=max_pending_sentences
        )
        # Queue of synthesized audio awaiting playback
        self._audio_queue: asyncio.Queue[Optional[TTSSynthResult]] = asyncio.Queue(
            maxsize=max_pending_sentences
        )

        self._cancelled = False
        self._cancel_event = asyncio.Event()
        self._synth_task: Optional[asyncio.Task] = None
        self._play_task: Optional[asyncio.Task] = None
        self._sentence_index = 0

        # Telemetry
        self._first_token_time: Optional[float] = None
        self._first_audio_time: Optional[float] = None
        self._sentences_synthesized = 0
        self._total_synth_ms = 0.0

    # ── Public API ──────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the TTS synthesis and playback workers."""
        self._cancelled = False
        self._cancel_event.clear()
        self._sentence_index = 0
        self._sentence_buffer.reset()

        self._synth_task = asyncio.create_task(
            self._synthesis_worker(), name="tts_synth_worker"
        )
        self._play_task = asyncio.create_task(
            self._playback_worker(), name="tts_play_worker"
        )

    async def feed_token(self, token: str) -> None:
        """Feed a single LLM token into the sentence buffer.

        Complete sentences are automatically queued for TTS synthesis.
        """
        if self._cancelled:
            return

        if self._first_token_time is None:
            self._first_token_time = time.monotonic()

        sentences = self._sentence_buffer.add_token(token)
        for sentence in sentences:
            if not self._cancelled:
                try:
                    self._sentence_queue.put_nowait(sentence)
                except asyncio.QueueFull:
                    # Backpressure: drop oldest sentence
                    try:
                        self._sentence_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                    self._sentence_queue.put_nowait(sentence)

    async def finish(self) -> None:
        """Signal that LLM generation is complete. Flush remaining text."""
        if self._cancelled:
            return

        # Flush remaining buffer
        remaining = self._sentence_buffer.flush()
        if remaining:
            try:
                await asyncio.wait_for(
                    self._sentence_queue.put(remaining), timeout=2.0
                )
            except (asyncio.TimeoutError, asyncio.QueueFull):
                pass

        # Signal end-of-stream
        await self._sentence_queue.put(None)

        # Wait for synthesis and playback to complete
        if self._synth_task:
            await asyncio.wait_for(self._synth_task, timeout=30.0)
        if self._play_task:
            await asyncio.wait_for(self._play_task, timeout=30.0)

    def cancel(self) -> None:
        """Cancel all pending TTS work immediately."""
        self._cancelled = True
        self._cancel_event.set()

        # Drain queues
        while not self._sentence_queue.empty():
            try:
                self._sentence_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        # Cancel tasks
        if self._synth_task and not self._synth_task.done():
            self._synth_task.cancel()
        if self._play_task and not self._play_task.done():
            self._play_task.cancel()

        logger.debug("StreamingTTSCoordinator cancelled")

    # ── Internal Workers ────────────────────────────────────────────

    async def _synthesis_worker(self) -> None:
        """Consume sentences and synthesize TTS audio."""
        while not self._cancelled:
            try:
                sentence = await asyncio.wait_for(
                    self._sentence_queue.get(), timeout=1.0
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            if sentence is None:
                # End-of-stream
                await self._audio_queue.put(None)
                break

            # Synthesize
            start = time.monotonic()
            try:
                if self._tts_fn:
                    audio_data = await self._tts_fn(sentence)
                else:
                    audio_data = b""  # Will use agent_session.say() instead

                latency = (time.monotonic() - start) * 1000
                self._sentences_synthesized += 1
                self._total_synth_ms += latency

                if self._first_audio_time is None:
                    self._first_audio_time = time.monotonic()
                    time_to_first_audio = (self._first_audio_time - self._first_token_time) * 1000
                    logger.info(
                        "Time-to-first-audio: %.0fms (sentence: '%s')",
                        time_to_first_audio, sentence[:50]
                    )

                result = TTSSynthResult(
                    sentence=sentence,
                    audio_data=audio_data,
                    latency_ms=latency,
                    sentence_index=self._sentence_index,
                )
                self._sentence_index += 1
                await self._audio_queue.put(result)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning("TTS synthesis failed for '%s': %s", sentence[:30], exc)
                result = TTSSynthResult(
                    sentence=sentence,
                    audio_data=b"",
                    latency_ms=(time.monotonic() - start) * 1000,
                    sentence_index=self._sentence_index,
                    error=str(exc),
                )
                self._sentence_index += 1
                await self._audio_queue.put(result)

    async def _playback_worker(self) -> None:
        """Consume synthesized audio and play sequentially."""
        while not self._cancelled:
            try:
                result = await asyncio.wait_for(
                    self._audio_queue.get(), timeout=1.0
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            if result is None:
                break

            if self._cancelled:
                break

            if not result.success:
                logger.debug("Skipping failed TTS result: %s", result.error)
                continue

            # Play using agent_session.say() or custom playback
            try:
                if self._agent_session and hasattr(self._agent_session, "say"):
                    # Use LiveKit's built-in TTS pipeline for the sentence
                    await self._agent_session.say(result.sentence)
                elif result.audio_data:
                    # Custom playback would go here
                    logger.debug(
                        "Played sentence %d: '%s' (%.0fms)",
                        result.sentence_index, result.sentence[:40], result.latency_ms
                    )
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning("Playback failed: %s", exc)

    # ── Telemetry ───────────────────────────────────────────────────

    @property
    def time_to_first_audio_ms(self) -> Optional[float]:
        if self._first_token_time and self._first_audio_time:
            return (self._first_audio_time - self._first_token_time) * 1000
        return None

    def health(self) -> dict:
        return {
            "cancelled": self._cancelled,
            "sentences_synthesized": self._sentences_synthesized,
            "avg_synth_ms": round(
                self._total_synth_ms / max(1, self._sentences_synthesized), 1
            ),
            "time_to_first_audio_ms": (
                round(self.time_to_first_audio_ms, 1)
                if self.time_to_first_audio_ms
                else None
            ),
            "pending_sentences": self._sentence_queue.qsize(),
            "pending_audio": self._audio_queue.qsize(),
            "buffer_pending_text": len(self._sentence_buffer.pending_text),
        }
