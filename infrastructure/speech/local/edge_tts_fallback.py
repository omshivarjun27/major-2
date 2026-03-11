"""Local TTS fallback adapter using edge-tts or pyttsx3.

Provides offline text-to-speech when cloud TTS services (ElevenLabs) are unavailable.
The fallback chain is: edge-tts (natural voice) → pyttsx3 (fully offline) → error.

Architecture constraint: imports from ``shared/`` and ``infrastructure/resilience/`` only.

Latency:
- edge-tts: ~200-500ms per sentence (requires internet for first load, then cached)
- pyttsx3: ~100-300ms per sentence (fully offline, less natural)

Usage::

    from infrastructure.speech.local import LocalTTSFallback

    tts = LocalTTSFallback()  # Auto-selects best available backend
    audio_bytes = tts.synthesize("Hello, world!")  # Sync method (for TTSManager.local_fn)
    audio_bytes = await tts.async_synthesize("Hello, world!")  # Async method
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("speech.local-tts")

# Check available TTS backends
EDGE_TTS_AVAILABLE = False
PYTTSX3_AVAILABLE = False

_edge_tts = None
_pyttsx3 = None

try:
    import edge_tts
    _edge_tts = edge_tts
    EDGE_TTS_AVAILABLE = True
    logger.info("edge-tts is available for local TTS fallback")
except ImportError:
    logger.debug("edge-tts not installed — trying pyttsx3 fallback")

try:
    import pyttsx3
    _pyttsx3 = pyttsx3
    PYTTSX3_AVAILABLE = True
    logger.info("pyttsx3 is available for fully offline TTS fallback")
except ImportError:
    logger.debug("pyttsx3 not installed — local TTS fallback limited")


# Default voices for edge-tts
EDGE_TTS_VOICES: Dict[str, str] = {
    "en": "en-US-AriaNeural",
    "en-US": "en-US-AriaNeural",
    "en-GB": "en-GB-SoniaNeural",
    "es": "es-ES-ElviraNeural",
    "fr": "fr-FR-DeniseNeural",
    "de": "de-DE-KatjaNeural",
    "it": "it-IT-ElsaNeural",
    "pt": "pt-BR-FranciscaNeural",
    "zh": "zh-CN-XiaoxiaoNeural",
    "ja": "ja-JP-NanamiNeural",
    "ko": "ko-KR-SunHiNeural",
}


@dataclass
class LocalTTSConfig:
    """Configuration for local TTS fallback."""

    voice: str = "en-US-AriaNeural"
    """Voice ID for edge-tts (e.g., 'en-US-AriaNeural', 'en-GB-SoniaNeural')."""

    rate: str = "+0%"
    """Speech rate adjustment for edge-tts (e.g., '+10%', '-20%')."""

    volume: str = "+0%"
    """Volume adjustment for edge-tts (e.g., '+10%', '-10%')."""

    pyttsx3_rate: int = 150
    """Speech rate for pyttsx3 fallback (words per minute)."""

    pyttsx3_volume: float = 1.0
    """Volume for pyttsx3 fallback (0.0 to 1.0)."""

    prefer_edge_tts: bool = True
    """Prefer edge-tts over pyttsx3 when both are available."""

    @classmethod
    def from_env(cls) -> "LocalTTSConfig":
        """Create config from environment variables."""
        return cls(
            voice=os.environ.get("LOCAL_TTS_VOICE", "en-US-AriaNeural"),
            rate=os.environ.get("LOCAL_TTS_RATE", "+0%"),
            volume=os.environ.get("LOCAL_TTS_VOLUME", "+0%"),
            pyttsx3_rate=int(os.environ.get("LOCAL_TTS_PYTTSX3_RATE", "150")),
            pyttsx3_volume=float(os.environ.get("LOCAL_TTS_PYTTSX3_VOLUME", "1.0")),
            prefer_edge_tts=os.environ.get("LOCAL_TTS_PREFER_EDGE", "true").lower() == "true",
        )


@dataclass
class SynthesisResult:
    """Result of TTS synthesis."""

    audio_bytes: bytes
    """Synthesized audio in MP3/WAV format."""

    backend: str
    """Backend used: 'edge-tts', 'pyttsx3', or 'none'."""

    latency_ms: float
    """Synthesis latency in milliseconds."""

    voice: str
    """Voice used for synthesis."""

    error: Optional[str] = None
    """Error message if synthesis failed."""

    @property
    def success(self) -> bool:
        """True if synthesis succeeded."""
        return self.error is None and len(self.audio_bytes) > 0


class LocalTTSFallback:
    """Local TTS fallback adapter.

    Provides offline TTS using edge-tts (primary) or pyttsx3 (secondary).
    Compatible with TTSManager.local_fn signature (sync callable).

    Thread-safe: pyttsx3 is initialized per-call to avoid GIL issues.
    """

    def __init__(self, config: Optional[LocalTTSConfig] = None) -> None:
        """Initialize local TTS fallback.

        Args:
            config: Configuration options. Defaults to environment-based config.
        """
        self.config = config or LocalTTSConfig.from_env()
        self._backend = self._select_backend()

        logger.info(
            "LocalTTSFallback initialized (backend=%s, voice=%s)",
            self._backend,
            self.config.voice,
        )

    def _select_backend(self) -> str:
        """Select the best available TTS backend."""
        if self.config.prefer_edge_tts and EDGE_TTS_AVAILABLE:
            return "edge-tts"
        elif PYTTSX3_AVAILABLE:
            return "pyttsx3"
        elif EDGE_TTS_AVAILABLE:
            return "edge-tts"
        else:
            return "none"

    def synthesize(self, text: str) -> bytes:
        """Synthesize speech synchronously.

        This method is compatible with TTSManager.local_fn signature.

        Args:
            text: Text to synthesize.

        Returns:
            Audio bytes (MP3 for edge-tts, WAV for pyttsx3).
            Returns empty bytes on failure.
        """
        result = self.synthesize_with_result(text)
        return result.audio_bytes

    def synthesize_with_result(self, text: str) -> SynthesisResult:
        """Synthesize speech with full result metadata.

        Args:
            text: Text to synthesize.

        Returns:
            SynthesisResult with audio and metadata.
        """
        start_time = time.monotonic()

        if not text or not text.strip():
            return SynthesisResult(
                audio_bytes=b"",
                backend="none",
                latency_ms=0.0,
                voice=self.config.voice,
                error="Empty text provided",
            )

        # Try edge-tts first
        if self._backend == "edge-tts" or (self._backend == "none" and EDGE_TTS_AVAILABLE):
            result = self._synthesize_edge_tts_sync(text)
            if result.success:
                result.latency_ms = (time.monotonic() - start_time) * 1000
                return result
            # Fall through to pyttsx3 if edge-tts fails
            logger.warning("edge-tts failed, trying pyttsx3 fallback: %s", result.error)

        # Try pyttsx3
        if PYTTSX3_AVAILABLE:
            result = self._synthesize_pyttsx3(text)
            result.latency_ms = (time.monotonic() - start_time) * 1000
            return result

        # No backend available
        latency = (time.monotonic() - start_time) * 1000
        return SynthesisResult(
            audio_bytes=b"",
            backend="none",
            latency_ms=latency,
            voice=self.config.voice,
            error="No TTS backend available. Install edge-tts or pyttsx3.",
        )

    async def async_synthesize(self, text: str) -> bytes:
        """Synthesize speech asynchronously.

        Args:
            text: Text to synthesize.

        Returns:
            Audio bytes (MP3 for edge-tts, WAV for pyttsx3).
            Returns empty bytes on failure.
        """
        result = await self.async_synthesize_with_result(text)
        return result.audio_bytes

    async def async_synthesize_with_result(self, text: str) -> SynthesisResult:
        """Synthesize speech asynchronously with full result metadata.

        Args:
            text: Text to synthesize.

        Returns:
            SynthesisResult with audio and metadata.
        """
        start_time = time.monotonic()

        if not text or not text.strip():
            return SynthesisResult(
                audio_bytes=b"",
                backend="none",
                latency_ms=0.0,
                voice=self.config.voice,
                error="Empty text provided",
            )

        # Try edge-tts first (native async)
        if self._backend == "edge-tts" or (self._backend == "none" and EDGE_TTS_AVAILABLE):
            result = await self._synthesize_edge_tts_async(text)
            if result.success:
                result.latency_ms = (time.monotonic() - start_time) * 1000
                return result
            logger.warning("edge-tts failed, trying pyttsx3 fallback: %s", result.error)

        # Try pyttsx3 (run in executor since it's sync-only)
        if PYTTSX3_AVAILABLE:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._synthesize_pyttsx3, text)
            result.latency_ms = (time.monotonic() - start_time) * 1000
            return result

        latency = (time.monotonic() - start_time) * 1000
        return SynthesisResult(
            audio_bytes=b"",
            backend="none",
            latency_ms=latency,
            voice=self.config.voice,
            error="No TTS backend available. Install edge-tts or pyttsx3.",
        )

    def _synthesize_edge_tts_sync(self, text: str) -> SynthesisResult:
        """Synchronous wrapper for edge-tts synthesis."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self._synthesize_edge_tts_async(text))
            finally:
                loop.close()
        except Exception as exc:
            logger.error("edge-tts sync wrapper failed: %s", exc)
            return SynthesisResult(
                audio_bytes=b"",
                backend="edge-tts",
                latency_ms=0.0,
                voice=self.config.voice,
                error=str(exc),
            )

    async def _synthesize_edge_tts_async(self, text: str) -> SynthesisResult:
        """Synthesize using edge-tts (async native)."""
        if not EDGE_TTS_AVAILABLE:
            return SynthesisResult(
                audio_bytes=b"",
                backend="edge-tts",
                latency_ms=0.0,
                voice=self.config.voice,
                error="edge-tts not installed",
            )

        try:
            communicate = _edge_tts.Communicate(
                text,
                voice=self.config.voice,
                rate=self.config.rate,
                volume=self.config.volume,
            )

            # Collect audio chunks
            audio_chunks = []
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_chunks.append(chunk["data"])

            audio_bytes = b"".join(audio_chunks)

            return SynthesisResult(
                audio_bytes=audio_bytes,
                backend="edge-tts",
                latency_ms=0.0,  # Set by caller
                voice=self.config.voice,
            )

        except Exception as exc:
            logger.error("edge-tts synthesis failed: %s", exc)
            return SynthesisResult(
                audio_bytes=b"",
                backend="edge-tts",
                latency_ms=0.0,
                voice=self.config.voice,
                error=str(exc),
            )

    def _synthesize_pyttsx3(self, text: str) -> SynthesisResult:
        """Synthesize using pyttsx3 (fully offline)."""
        if not PYTTSX3_AVAILABLE:
            return SynthesisResult(
                audio_bytes=b"",
                backend="pyttsx3",
                latency_ms=0.0,
                voice="system",
                error="pyttsx3 not installed",
            )

        temp_file = None
        try:
            # pyttsx3 must be initialized per-call for thread safety
            engine = _pyttsx3.init()
            engine.setProperty("rate", self.config.pyttsx3_rate)
            engine.setProperty("volume", self.config.pyttsx3_volume)

            # Save to temp file (pyttsx3 doesn't support memory output)
            temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            temp_path = temp_file.name
            temp_file.close()

            engine.save_to_file(text, temp_path)
            engine.runAndWait()
            engine.stop()

            # Read the generated audio
            with open(temp_path, "rb") as f:
                audio_bytes = f.read()

            return SynthesisResult(
                audio_bytes=audio_bytes,
                backend="pyttsx3",
                latency_ms=0.0,  # Set by caller
                voice="system",
            )

        except Exception as exc:
            logger.error("pyttsx3 synthesis failed: %s", exc)
            return SynthesisResult(
                audio_bytes=b"",
                backend="pyttsx3",
                latency_ms=0.0,
                voice="system",
                error=str(exc),
            )

        finally:
            # Clean up temp file
            if temp_file is not None:
                try:
                    os.unlink(temp_file.name)
                except Exception:
                    pass

    def is_available(self) -> bool:
        """Check if any TTS backend is available."""
        return EDGE_TTS_AVAILABLE or PYTTSX3_AVAILABLE

    def get_backend(self) -> str:
        """Get the currently selected backend."""
        return self._backend

    def health(self) -> Dict[str, Any]:
        """Health snapshot for diagnostics."""
        return {
            "available": self.is_available(),
            "backend": self._backend,
            "edge_tts_available": EDGE_TTS_AVAILABLE,
            "pyttsx3_available": PYTTSX3_AVAILABLE,
            "voice": self.config.voice,
            "rate": self.config.rate,
        }


# Convenience function for TTSManager.local_fn
def create_local_tts_fn(config: Optional[LocalTTSConfig] = None) -> Callable[[str], bytes]:
    """Create a local TTS function compatible with TTSManager.local_fn.

    Args:
        config: Optional configuration. Uses environment defaults if not provided.

    Returns:
        A callable that takes text and returns audio bytes.
    """
    fallback = LocalTTSFallback(config=config)
    return fallback.synthesize
