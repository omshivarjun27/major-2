"""Local speech adapters for fallback when cloud services are unavailable.

STT Fallback: WhisperSTT (local Whisper model via faster-whisper)
TTS Fallback: LocalTTSFallback (edge-tts or pyttsx3)
"""

from infrastructure.speech.local.edge_tts_fallback import (
    EDGE_TTS_AVAILABLE,
    PYTTSX3_AVAILABLE,
    LocalTTSConfig,
    LocalTTSFallback,
    SynthesisResult,
    create_local_tts_fn,
)
from infrastructure.speech.local.whisper_stt import (
    WHISPER_AVAILABLE,
    TranscriptionResult,
    WhisperConfig,
    WhisperSTT,
)

__all__ = [
    # STT (Whisper)
    "WhisperSTT",
    "WhisperConfig",
    "TranscriptionResult",
    "WHISPER_AVAILABLE",
    # TTS (Edge TTS / pyttsx3)
    "LocalTTSFallback",
    "LocalTTSConfig",
    "SynthesisResult",
    "EDGE_TTS_AVAILABLE",
    "PYTTSX3_AVAILABLE",
    "create_local_tts_fn",
]
