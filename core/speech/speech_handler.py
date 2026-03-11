"""
Speech Handler Module
=====================

Handles STT (Speech-to-Text) processing and audio capture
for the VQA pipeline integration.
"""

import base64
import io
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("speech-handler")


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class SpeechConfig:
    """Configuration for speech processing."""

    # STT settings
    stt_model: str = "nova-3"
    stt_language: str = "en"

    # Audio settings
    sample_rate: int = 16000
    channels: int = 1
    chunk_duration_ms: int = 100

    # Processing settings
    max_audio_duration_sec: float = 10.0
    silence_threshold_db: float = -40.0
    min_speech_duration_ms: int = 200

    # Latency targets
    target_stt_latency_ms: float = 100.0


# ============================================================================
# Speech Handler
# ============================================================================

class SpeechHandler:
    """
    Handles speech-to-text conversion for VQA pipeline.

    Integrates with existing Deepgram STT or can process
    raw audio bytes directly.
    """

    def __init__(self, config: Optional[SpeechConfig] = None):
        self.config = config or SpeechConfig()
        self._stt_client = None
        self._is_initialized = False

        # Metrics
        self._total_transcriptions = 0
        self._avg_latency_ms = 0.0

    async def initialize(self, stt_client=None):
        """
        Initialize speech handler with optional STT client.

        Args:
            stt_client: Existing STT client (e.g., Deepgram)
        """
        self._stt_client = stt_client
        self._is_initialized = True
        logger.info("Speech handler initialized")

    async def transcribe_audio(
        self,
        audio_data: bytes,
        sample_rate: Optional[int] = None,
    ) -> Tuple[str, float]:
        """
        Transcribe audio bytes to text.

        Args:
            audio_data: Raw audio bytes (PCM or WAV)
            sample_rate: Audio sample rate (default from config)

        Returns:
            Tuple of (transcribed_text, latency_ms)
        """
        start_time = time.time()

        if not self._is_initialized:
            await self.initialize()

        try:
            # Determine audio format
            sample_rate = sample_rate or self.config.sample_rate

            # If we have a Deepgram client, use it
            if self._stt_client and hasattr(self._stt_client, 'transcribe'):
                text = await self._transcribe_with_client(audio_data, sample_rate)
            else:
                # Fallback to REST API
                text = await self._transcribe_rest_api(audio_data, sample_rate)

            latency_ms = (time.time() - start_time) * 1000

            # Update metrics
            self._total_transcriptions += 1
            self._avg_latency_ms = (self._avg_latency_ms * 0.9) + (latency_ms * 0.1)

            logger.debug(f"Transcription completed in {latency_ms:.1f}ms: {text[:50]}...")

            return text, latency_ms

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"Transcription failed: {e}")
            return "", latency_ms

    async def _transcribe_with_client(
        self,
        audio_data: bytes,
        sample_rate: int,
    ) -> str:
        """Transcribe using existing STT client."""
        try:
            # This assumes the client has a transcribe method
            result = await self._stt_client.transcribe(
                audio_data,
                sample_rate=sample_rate,
                language=self.config.stt_language,
            )
            return result.text if hasattr(result, 'text') else str(result)
        except Exception as e:
            logger.warning(f"Client transcription failed, falling back to REST: {e}")
            return await self._transcribe_rest_api(audio_data, sample_rate)

    async def _transcribe_rest_api(
        self,
        audio_data: bytes,
        sample_rate: int,
    ) -> str:
        """Transcribe using Deepgram REST API."""
        try:
            import os

            import httpx

            api_key = os.getenv("DEEPGRAM_API_KEY")
            if not api_key:
                logger.error("DEEPGRAM_API_KEY not set")
                return ""

            url = "https://api.deepgram.com/v1/listen"
            params = {
                "model": self.config.stt_model,
                "language": self.config.stt_language,
                "encoding": "linear16",
                "sample_rate": sample_rate,
            }

            headers = {
                "Authorization": f"Token {api_key}",
                "Content-Type": "audio/raw",
            }

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    url,
                    params=params,
                    headers=headers,
                    content=audio_data,
                )
                response.raise_for_status()

                result = response.json()
                text = result["results"]["channels"][0]["alternatives"][0]["transcript"]
                return text

        except Exception as e:
            logger.error(f"REST API transcription failed: {e}")
            return ""

    async def transcribe_base64(
        self,
        audio_base64: str,
        sample_rate: Optional[int] = None,
    ) -> Tuple[str, float]:
        """
        Transcribe base64-encoded audio.

        Args:
            audio_base64: Base64-encoded audio data
            sample_rate: Audio sample rate

        Returns:
            Tuple of (transcribed_text, latency_ms)
        """
        try:
            # Remove data URL prefix if present
            if "," in audio_base64:
                audio_base64 = audio_base64.split(",", 1)[1]

            audio_data = base64.b64decode(audio_base64)
            return await self.transcribe_audio(audio_data, sample_rate)

        except Exception as e:
            logger.error(f"Base64 transcription failed: {e}")
            return "", 0.0

    def get_stats(self) -> Dict[str, Any]:
        """Get handler statistics."""
        return {
            "total_transcriptions": self._total_transcriptions,
            "avg_latency_ms": round(self._avg_latency_ms, 1),
            "is_initialized": self._is_initialized,
            "has_client": self._stt_client is not None,
        }


# ============================================================================
# Audio Utilities
# ============================================================================

def detect_audio_format(audio_data: bytes) -> str:
    """Detect audio format from header bytes."""
    if audio_data[:4] == b'RIFF':
        return "wav"
    elif audio_data[:4] == b'fLaC':
        return "flac"
    elif audio_data[:3] == b'ID3' or audio_data[:2] == b'\xff\xfb':
        return "mp3"
    elif audio_data[:4] == b'OggS':
        return "ogg"
    else:
        return "raw"  # Assume raw PCM


def convert_to_pcm(audio_data: bytes, target_sample_rate: int = 16000) -> bytes:
    """
    Convert audio to raw PCM format.

    Returns raw PCM bytes at target sample rate.
    """
    try:
        import wave

        audio_format = detect_audio_format(audio_data)

        if audio_format == "wav":
            # Parse WAV and extract PCM
            with io.BytesIO(audio_data) as f:
                with wave.open(f, 'rb') as wav:
                    pcm_data = wav.readframes(wav.getnframes())
                    return pcm_data

        # For other formats, return as-is (may need additional conversion)
        return audio_data

    except Exception as e:
        logger.warning(f"Audio conversion failed: {e}")
        return audio_data
