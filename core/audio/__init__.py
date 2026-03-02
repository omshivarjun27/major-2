"""
Audio Engine — Sound-source localization, event classification, and audio-vision fusion.

Supports both mic-array (multi-channel) and single-mic degraded modes.
"""

from .ssl import SoundSourceLocalizer, SSLResult, SSLConfig
from .audio_event_detector import AudioEventDetector, AudioEvent, AudioEventConfig
from .audio_fusion import AudioVisionFuser, FusedAudioVisualEvent, AudioFusionConfig
from .enhanced_detector import (
    EnhancedAudioConfig,
    EnhancedAudioDetector,
    EnhancedAudioResult,
    AudioEventCorrelation,
    create_enhanced_detector,
)

__all__ = [
    "SoundSourceLocalizer", "SSLResult", "SSLConfig",
    "AudioEventDetector", "AudioEvent", "AudioEventConfig",
    "AudioVisionFuser", "FusedAudioVisualEvent", "AudioFusionConfig",
    "EnhancedAudioConfig", "EnhancedAudioDetector", "EnhancedAudioResult",
    "AudioEventCorrelation", "create_enhanced_detector",
]
