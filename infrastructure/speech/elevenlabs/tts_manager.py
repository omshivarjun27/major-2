"""
TTS Reliability Manager
========================

Provides:
  1. **TTSCache** — LRU cache keyed by text SHA-256 fingerprint.
  2. **TTSChunker** — Splits text into ≤ N-second chunks for non-blocking streaming.
  3. **TTSManager** — Orchestrates cache → remote (with timeout) → local fallback.

All latency and engine info is tracked for per-frame telemetry.
"""

from __future__ import annotations

import hashlib
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generator, List, Optional

logger = logging.getLogger("tts-manager")


# ---------------------------------------------------------------------------
# TTS Cache
# ---------------------------------------------------------------------------

class TTSCache:
    """LRU cache for synthesised audio keyed by text fingerprint (SHA-256).

    Each entry stores raw audio bytes + metadata.
    """

    def __init__(self, max_entries: int = 500):
        self._max = max_entries
        self._store: OrderedDict[str, bytes] = OrderedDict()
        self.hits: int = 0
        self.misses: int = 0

    @staticmethod
    def fingerprint(text: str) -> str:
        """SHA-256 fingerprint of normalised text."""
        normalised = text.strip().lower()
        return hashlib.sha256(normalised.encode("utf-8")).hexdigest()

    def get(self, text: str) -> Optional[bytes]:
        """Retrieve cached audio.  Returns None on miss."""
        fp = self.fingerprint(text)
        if fp in self._store:
            self.hits += 1
            self._store.move_to_end(fp)
            return self._store[fp]
        self.misses += 1
        return None

    def put(self, text: str, audio_bytes: bytes) -> None:
        """Store audio bytes for the given text."""
        fp = self.fingerprint(text)
        if fp in self._store:
            self._store.move_to_end(fp)
        self._store[fp] = audio_bytes
        while len(self._store) > self._max:
            self._store.popitem(last=False)

    def clear(self) -> None:
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)


# ---------------------------------------------------------------------------
# TTS Chunker
# ---------------------------------------------------------------------------

class TTSChunker:
    """Split text into chunks ≤ ``max_seconds`` of speech.

    Approximation: ~2.5 words per second → max_words = max_seconds * 2.5.
    Splits on sentence boundaries preferentially.
    """

    def __init__(self, max_seconds: float = 2.0, words_per_second: float = 2.5):
        self.max_words = max(1, int(max_seconds * words_per_second))

    def chunk(self, text: str) -> List[str]:
        """Return list of text chunks, each ≤ max_words words."""
        if not text or not text.strip():
            return []

        # Try sentence-level split first
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())

        chunks: List[str] = []
        current: List[str] = []
        current_words = 0

        for sentence in sentences:
            words = sentence.split()
            if current_words + len(words) <= self.max_words:
                current.append(sentence)
                current_words += len(words)
            else:
                if current:
                    chunks.append(" ".join(current))
                # If a single sentence is too long, split by words
                if len(words) > self.max_words:
                    for i in range(0, len(words), self.max_words):
                        chunk_words = words[i : i + self.max_words]
                        chunks.append(" ".join(chunk_words))
                    current = []
                    current_words = 0
                else:
                    current = [sentence]
                    current_words = len(words)

        if current:
            chunks.append(" ".join(current))

        return chunks


# ---------------------------------------------------------------------------
# TTS Result
# ---------------------------------------------------------------------------

@dataclass
class TTSResult:
    """Result of a TTS synthesis operation."""
    audio_bytes: bytes = b""
    engine: str = "local"           # "local" | "remote"
    latency_ms: float = 0.0
    fallback_used: bool = False     # True if remote failed → local
    cache_hit: bool = False
    text: str = ""
    chunk_index: int = 0
    total_chunks: int = 1


# ---------------------------------------------------------------------------
# TTS Manager
# ---------------------------------------------------------------------------

class TTSManager:
    """Orchestrate TTS with cache, remote-with-timeout, and local fallback.

    Usage::

        mgr = TTSManager(
            local_fn=my_local_tts,
            remote_fn=my_remote_tts,     # optional
            remote_timeout_ms=2000,
        )
        result = mgr.synthesise("Hello world")
    """

    def __init__(
        self,
        local_fn: Optional[Callable[[str], bytes]] = None,
        remote_fn: Optional[Callable[[str], bytes]] = None,
        remote_timeout_ms: float = 2000,
        cache_enabled: bool = True,
        cache_max_entries: int = 500,
        chunk_max_seconds: float = 2.0,
    ):
        self.local_fn = local_fn or self._stub_tts
        self.remote_fn = remote_fn
        self.remote_timeout_ms = remote_timeout_ms
        self.cache = TTSCache(max_entries=cache_max_entries) if cache_enabled else None
        self.chunker = TTSChunker(max_seconds=chunk_max_seconds)

        # Counters
        self.total_calls: int = 0
        self.remote_failures: int = 0
        self.cache_hits: int = 0

    def synthesise(self, text: str) -> TTSResult:
        """Synthesise speech for the given text.

        Order of operations:
          1. Check cache
          2. Try remote TTS with timeout
          3. Fallback to local TTS
          4. Cache result
        """
        self.total_calls += 1
        start = time.monotonic()

        # 1. Cache check
        if self.cache is not None:
            cached = self.cache.get(text)
            if cached is not None:
                self.cache_hits += 1
                elapsed = (time.monotonic() - start) * 1000
                return TTSResult(
                    audio_bytes=cached,
                    engine="cache",
                    latency_ms=elapsed,
                    cache_hit=True,
                    text=text,
                )

        # 2. Remote TTS (if configured)
        audio: Optional[bytes] = None
        engine = "local"
        fallback = False

        if self.remote_fn is not None:
            try:
                audio = self._call_with_timeout(self.remote_fn, text)
                engine = "remote"
            except Exception as exc:
                self.remote_failures += 1
                logger.warning("Remote TTS failed (%s), falling back to local", exc)
                fallback = True

        # 3. Local fallback
        if audio is None:
            try:
                audio = self.local_fn(text)
                engine = "local"
                if self.remote_fn is not None:
                    fallback = True
            except Exception as exc:
                logger.error("Local TTS also failed: %s", exc, exc_info=True)
                audio = b""

        # 4. Cache result
        if self.cache is not None and audio:
            self.cache.put(text, audio)

        elapsed = (time.monotonic() - start) * 1000
        return TTSResult(
            audio_bytes=audio or b"",
            engine=engine,
            latency_ms=elapsed,
            fallback_used=fallback,
            text=text,
        )

    def synthesise_chunked(self, text: str) -> Generator[TTSResult, None, None]:
        """Yield TTSResult for each chunk ≤ max_seconds.

        Enables non-blocking streaming playback.
        """
        chunks = self.chunker.chunk(text)
        if not chunks:
            return

        for i, chunk_text in enumerate(chunks):
            result = self.synthesise(chunk_text)
            result.chunk_index = i
            result.total_chunks = len(chunks)
            yield result

    def _call_with_timeout(self, fn: Callable[[str], bytes], text: str) -> bytes:
        """Call fn with a timeout in milliseconds.

        Uses threading-based timeout on platforms that don't support signals
        in non-main threads (i.e. Windows).
        """
        import concurrent.futures

        timeout_s = self.remote_timeout_ms / 1000.0
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(fn, text)
            try:
                return future.result(timeout=timeout_s)
            except concurrent.futures.TimeoutError:
                raise TimeoutError(
                    f"Remote TTS timed out after {self.remote_timeout_ms}ms"
                )

    @staticmethod
    def _stub_tts(text: str) -> bytes:
        """Stub local TTS that returns empty audio (for testing)."""
        logger.debug("Stub TTS called for: %s", text[:40])
        return b"\x00" * 100  # placeholder silence
