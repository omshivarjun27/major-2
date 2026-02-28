"""Local speech adapters for fallback when cloud services are unavailable.

STT Fallback: WhisperSTT (local Whisper model via faster-whisper)
TTS Fallback: LocalTTSFallback (edge-tts or pyttsx3)
"""

from infrastructure.speech.local.whisper_stt import (
    WhisperSTT,
    WhisperConfig,
    TranscriptionResult,
    WHISPER_AVAILABLE,
)

from infrastructure.speech.local.edge_tts_fallback import (
    LocalTTSFallback,
    LocalTTSConfig,
    SynthesisResult,
    EDGE_TTS_AVAILABLE,
    PYTTSX3_AVAILABLE,
    create_local_tts_fn,
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
