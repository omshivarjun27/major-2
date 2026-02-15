"""
Speech-VQA Bridge Module
========================

Connects STT → VQA Pipeline → TTS for end-to-end voice interaction.

Target latencies:
- STT → processing: ≤100ms
- VQA inference: ≤300ms
- TTS generation: ≤100ms
- Total: ≤500ms
"""

from .speech_handler import SpeechHandler, SpeechConfig
from .voice_router import VoiceRouter, IntentType, RouteResult
from .tts_handler import TTSHandler, TTSConfig, ResponseFormatter
from .voice_ask_pipeline import VoiceAskPipeline, VoiceAskConfig, VoiceAskTelemetry

__all__ = [
    # Speech Handler
    "SpeechHandler",
    "SpeechConfig",
    # Voice Router
    "VoiceRouter",
    "IntentType",
    "RouteResult",
    # TTS Handler
    "TTSHandler",
    "TTSConfig",
    "ResponseFormatter",
    # Voice Ask Pipeline
    "VoiceAskPipeline",
    "VoiceAskConfig",
    "VoiceAskTelemetry",
]
