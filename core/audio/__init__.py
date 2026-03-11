"""
Audio Engine — Sound-source localization, event classification, and audio-vision fusion.

Supports both mic-array (multi-channel) and single-mic degraded modes.
"""

from .audio_event_detector import AudioEvent, AudioEventConfig, AudioEventDetector
from .audio_fusion import AudioFusionConfig, AudioVisionFuser, FusedAudioVisualEvent
from .enhanced_detector import (
    AudioEventCorrelation,
    EnhancedAudioConfig,
    EnhancedAudioDetector,
    EnhancedAudioResult,
    create_enhanced_detector,
)
from .ssl import SoundSourceLocalizer, SSLConfig, SSLResult

__all__ = [
    "SoundSourceLocalizer", "SSLResult", "SSLConfig",
    "AudioEventDetector", "AudioEvent", "AudioEventConfig",
    "AudioVisionFuser", "FusedAudioVisualEvent", "AudioFusionConfig",
    "EnhancedAudioConfig", "EnhancedAudioDetector", "EnhancedAudioResult",
    "AudioEventCorrelation", "create_enhanced_detector",
]
