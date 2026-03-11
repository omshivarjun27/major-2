"""Local Whisper-based STT fallback adapter.

Provides offline speech-to-text using OpenAI's Whisper model (via faster-whisper)
when cloud STT services (Deepgram) are unavailable.

Architecture constraint: imports from ``shared/`` and ``infrastructure/resilience/`` only.

VRAM Usage (GPU):
- tiny: ~100MB
- base: ~200MB
- small: ~500MB

Latency (typical utterance):
- tiny: ~100-200ms
- base: ~200-400ms
- small: ~400-800ms

Usage::

    from infrastructure.speech.local import WhisperSTT

    stt = WhisperSTT()  # Lazy loads model on first use
    result = await stt.transcribe(audio_bytes)
    print(result.text)
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Union

logger = logging.getLogger("speech.whisper")

# Check if faster-whisper is available
WHISPER_AVAILABLE = False
_faster_whisper = None

try:
    import faster_whisper
    _faster_whisper = faster_whisper
    WHISPER_AVAILABLE = True
    logger.info("faster-whisper is available for local STT fallback")
except ImportError:
    logger.debug("faster-whisper not installed — local STT fallback unavailable")


# Model sizes and their properties
MODEL_INFO: Dict[str, Dict[str, Any]] = {
    "tiny": {"vram_mb": 100, "latency_ms": 150, "quality": "low"},
    "base": {"vram_mb": 200, "latency_ms": 300, "quality": "medium"},
    "small": {"vram_mb": 500, "latency_ms": 600, "quality": "high"},
    "medium": {"vram_mb": 1500, "latency_ms": 1200, "quality": "very_high"},
    "large": {"vram_mb": 3000, "latency_ms": 2000, "quality": "best"},
}


@dataclass
class WhisperConfig:
    """Configuration for Whisper STT."""

    model_size: str = "base"
    """Model size: tiny, base, small, medium, large."""

    device: str = "auto"
    """Device: 'auto' (GPU if available), 'cuda', 'cpu'."""

    compute_type: str = "auto"
    """Compute type: 'auto', 'float16', 'int8', 'float32'."""

    language: str = "en"
    """Target language for transcription."""

    beam_size: int = 5
    """Beam size for decoding (higher = more accurate, slower)."""

    vad_filter: bool = True
    """Enable voice activity detection to skip silence."""

    @classmethod
    def from_env(cls) -> "WhisperConfig":
        """Create config from environment variables."""
        return cls(
            model_size=os.environ.get("WHISPER_MODEL_SIZE", "base"),
            device=os.environ.get("WHISPER_DEVICE", "auto"),
            compute_type=os.environ.get("WHISPER_COMPUTE_TYPE", "auto"),
            language=os.environ.get("WHISPER_LANGUAGE", "en"),
            beam_size=int(os.environ.get("WHISPER_BEAM_SIZE", "5")),
            vad_filter=os.environ.get("WHISPER_VAD_FILTER", "true").lower() == "true",
        )


@dataclass
class TranscriptionResult:
    """Result of a transcription."""

    text: str
    """Transcribed text."""

    language: str
    """Detected or specified language."""

    latency_ms: float
    """Transcription latency in milliseconds."""

    confidence: float
    """Average confidence score (0.0 to 1.0)."""

    model_size: str
    """Model size used for transcription."""

    segments: int
    """Number of audio segments processed."""

    error: Optional[str] = None
    """Error message if transcription failed."""

    @property
    def success(self) -> bool:
        """True if transcription succeeded."""
        return self.error is None and len(self.text) > 0


class WhisperSTT:
    """Local Whisper-based speech-to-text adapter.

    Provides offline STT using OpenAI's Whisper model via faster-whisper.
    The model is lazy-loaded on first use to avoid VRAM overhead when not needed.

    Thread-safe: transcription runs in a thread pool to avoid blocking the event loop.
    """

    def __init__(self, config: Optional[WhisperConfig] = None) -> None:
        """Initialize Whisper STT.

        Args:
            config: Configuration options. Defaults to environment-based config.
        """
        self.config = config or WhisperConfig.from_env()
        self._model = None
        self._model_loaded = False
        self._load_lock = asyncio.Lock()

        # Validate model size
        if self.config.model_size not in MODEL_INFO:
            logger.warning(
                "Unknown model size '%s', defaulting to 'base'",
                self.config.model_size,
            )
            self.config = WhisperConfig(
                model_size="base",
                device=self.config.device,
                compute_type=self.config.compute_type,
                language=self.config.language,
                beam_size=self.config.beam_size,
                vad_filter=self.config.vad_filter,
            )

        logger.info(
            "WhisperSTT initialized (model=%s, lazy_load=True)",
            self.config.model_size,
        )

    async def _ensure_model_loaded(self) -> bool:
        """Lazy-load the Whisper model.

        Returns True if model is loaded successfully, False otherwise.
        """
        if self._model_loaded:
            return True

        async with self._load_lock:
            # Double-check after acquiring lock
            if self._model_loaded:
                return True

            if not WHISPER_AVAILABLE:
                logger.error(
                    "Cannot load Whisper model: faster-whisper not installed. "
                    "Install with: pip install faster-whisper"
                )
                return False

            try:
                logger.info(
                    "Loading Whisper model '%s' (VRAM: ~%dMB)...",
                    self.config.model_size,
                    MODEL_INFO[self.config.model_size]["vram_mb"],
                )

                # Determine device
                device = self.config.device
                if device == "auto":
                    try:
                        import torch
                        device = "cuda" if torch.cuda.is_available() else "cpu"
                    except ImportError:
                        device = "cpu"

                # Determine compute type
                compute_type = self.config.compute_type
                if compute_type == "auto":
                    compute_type = "float16" if device == "cuda" else "int8"

                # Load model in thread pool to avoid blocking
                def load_model():
                    return _faster_whisper.WhisperModel(
                        self.config.model_size,
                        device=device,
                        compute_type=compute_type,
                    )

                self._model = await asyncio.get_event_loop().run_in_executor(
                    None, load_model
                )
                self._model_loaded = True

                logger.info(
                    "Whisper model '%s' loaded successfully (device=%s, compute=%s)",
                    self.config.model_size,
                    device,
                    compute_type,
                )
                return True

            except Exception as exc:
                logger.error("Failed to load Whisper model: %s", exc)
                return False

    async def transcribe(
        self,
        audio_data: Union[bytes, str],
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcribe audio to text.

        Args:
            audio_data: Audio bytes (PCM/WAV) or path to audio file.
            language: Override language (None = use config default).

        Returns:
            TranscriptionResult with text and metadata.
        """
        start_time = time.monotonic()
        target_language = language or self.config.language

        # Check if Whisper is available
        if not WHISPER_AVAILABLE:
            return TranscriptionResult(
                text="",
                language=target_language,
                latency_ms=(time.monotonic() - start_time) * 1000,
                confidence=0.0,
                model_size=self.config.model_size,
                segments=0,
                error="faster-whisper not installed. Install with: pip install faster-whisper",
            )

        # Ensure model is loaded
        if not await self._ensure_model_loaded():
            return TranscriptionResult(
                text="",
                language=target_language,
                latency_ms=(time.monotonic() - start_time) * 1000,
                confidence=0.0,
                model_size=self.config.model_size,
                segments=0,
                error="Failed to load Whisper model",
            )

        try:
            # Run transcription in thread pool
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                self._transcribe_sync,
                audio_data,
                target_language,
            )
            result.latency_ms = (time.monotonic() - start_time) * 1000
            return result

        except Exception as exc:
            logger.error("Transcription failed: %s", exc)
            return TranscriptionResult(
                text="",
                language=target_language,
                latency_ms=(time.monotonic() - start_time) * 1000,
                confidence=0.0,
                model_size=self.config.model_size,
                segments=0,
                error=str(exc),
            )

    def _transcribe_sync(
        self,
        audio_data: Union[bytes, str],
        language: str,
    ) -> TranscriptionResult:
        """Synchronous transcription (runs in thread pool)."""
        import tempfile

        # Handle bytes input — write to temp file
        temp_file = None
        audio_source = audio_data

        if isinstance(audio_data, bytes):
            temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            temp_file.write(audio_data)
            temp_file.close()
            audio_source = temp_file.name

        try:
            # Transcribe
            segments, info = self._model.transcribe(
                audio_source,
                language=language,
                beam_size=self.config.beam_size,
                vad_filter=self.config.vad_filter,
            )

            # Collect segments
            text_parts = []
            confidences = []
            segment_count = 0

            for segment in segments:
                text_parts.append(segment.text.strip())
                if hasattr(segment, "avg_logprob"):
                    # Convert log probability to confidence (approximate)
                    import math
                    conf = math.exp(segment.avg_logprob)
                    confidences.append(min(1.0, conf))
                segment_count += 1

            text = " ".join(text_parts).strip()
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            return TranscriptionResult(
                text=text,
                language=info.language if hasattr(info, "language") else language,
                latency_ms=0.0,  # Set by caller
                confidence=avg_confidence,
                model_size=self.config.model_size,
                segments=segment_count,
            )

        finally:
            # Clean up temp file
            if temp_file is not None:
                try:
                    os.unlink(temp_file.name)
                except Exception:
                    pass

    def is_available(self) -> bool:
        """Check if Whisper STT is available for use."""
        return WHISPER_AVAILABLE

    def is_loaded(self) -> bool:
        """Check if the model is currently loaded."""
        return self._model_loaded

    async def unload(self) -> None:
        """Unload the model to free VRAM."""
        async with self._load_lock:
            if self._model is not None:
                self._model = None
                self._model_loaded = False
                logger.info("Whisper model unloaded")

    def health(self) -> Dict[str, Any]:
        """Health snapshot for diagnostics."""
        model_info = MODEL_INFO.get(self.config.model_size, {})
        return {
            "available": WHISPER_AVAILABLE,
            "loaded": self._model_loaded,
            "model_size": self.config.model_size,
            "device": self.config.device,
            "language": self.config.language,
            "estimated_vram_mb": model_info.get("vram_mb", 0),
            "estimated_latency_ms": model_info.get("latency_ms", 0),
        }
