"""
Enhanced Audio Event Detector — Multi-channel support and event correlation.

Extends the base AudioEventDetector with temporal event correlation,
adaptive thresholding, ambient noise estimation, and multi-channel support.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from core.audio.audio_event_detector import (
    AudioEvent,
    AudioEventConfig,
    AudioEventDetector,
    AudioEventType,
)

logger = logging.getLogger("enhanced-audio-detector")


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class EnhancedAudioConfig:
    """Configuration for enhanced audio event detection."""

    # Base config fields
    sample_rate: int = 16000
    frame_length_ms: float = 1000.0
    hop_length_ms: float = 500.0
    min_confidence: float = 0.3
    n_mfcc: int = 13
    n_mel: int = 40
    model_path: Optional[str] = None

    # Enhanced features
    multi_channel: bool = False
    correlation_window_ms: float = 2000
    event_history_size: int = 50
    adaptive_threshold: bool = True
    noise_floor_db: float = -60

    def to_base_config(self) -> AudioEventConfig:
        """Convert to base AudioEventConfig."""
        return AudioEventConfig(
            sample_rate=self.sample_rate,
            frame_length_ms=self.frame_length_ms,
            hop_length_ms=self.hop_length_ms,
            min_confidence=self.min_confidence,
            n_mfcc=self.n_mfcc,
            n_mel=self.n_mel,
            model_path=self.model_path,
        )


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class AudioEventCorrelation:
    """Correlation between two audio events."""

    event_a: AudioEvent
    event_b: AudioEvent
    correlation_score: float
    temporal_gap_ms: float
    likely_same_source: bool

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "event_a": self.event_a.event_type.value,
            "event_b": self.event_b.event_type.value,
            "correlation_score": round(self.correlation_score, 3),
            "temporal_gap_ms": round(self.temporal_gap_ms, 1),
            "likely_same_source": self.likely_same_source,
        }


@dataclass
class EnhancedAudioResult:
    """Result from enhanced audio detection."""

    events: List[AudioEvent] = field(default_factory=list)
    correlations: List[AudioEventCorrelation] = field(default_factory=list)
    ambient_noise_db: float = -60.0
    dominant_event: Optional[AudioEvent] = None
    event_density: float = 0.0
    timestamp_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "events": [e.to_dict() for e in self.events],
            "correlations": [c.to_dict() for c in self.correlations],
            "ambient_noise_db": round(self.ambient_noise_db, 1),
            "dominant_event": self.dominant_event.to_dict() if self.dominant_event else None,
            "event_density": round(self.event_density, 3),
            "timestamp_ms": self.timestamp_ms,
        }


# =============================================================================
# Enhanced Detector
# =============================================================================

# Events that commonly co-occur
_CO_OCCURRING_EVENTS = {
    (AudioEventType.CAR_HORN, AudioEventType.TRAFFIC): 0.8,
    (AudioEventType.TRAFFIC, AudioEventType.CAR_HORN): 0.8,
    (AudioEventType.SIREN, AudioEventType.TRAFFIC): 0.7,
    (AudioEventType.TRAFFIC, AudioEventType.SIREN): 0.7,
    (AudioEventType.VOICE, AudioEventType.FOOTSTEPS): 0.6,
    (AudioEventType.FOOTSTEPS, AudioEventType.VOICE): 0.6,
    (AudioEventType.ALARM, AudioEventType.VOICE): 0.5,
    (AudioEventType.VOICE, AudioEventType.ALARM): 0.5,
    (AudioEventType.DOG_BARK, AudioEventType.VOICE): 0.4,
    (AudioEventType.VOICE, AudioEventType.DOG_BARK): 0.4,
}


class EnhancedAudioDetector:
    """Enhanced audio event detector with correlation and adaptive thresholding.

    Extends the base AudioEventDetector with:
    - Temporal event correlation across detection windows
    - Adaptive thresholding based on ambient noise levels
    - Multi-channel audio support
    - Event density tracking
    - Event history for pattern analysis

    Args:
        config: Enhanced audio configuration.
    """

    def __init__(self, config: Optional[EnhancedAudioConfig] = None):
        self.config = config or EnhancedAudioConfig()
        self._base_detector = AudioEventDetector(self.config.to_base_config())
        self._event_history: deque[AudioEvent] = deque(maxlen=self.config.event_history_size)
        self._ambient_history: deque[float] = deque(maxlen=20)
        self._total_detections = 0
        self._total_latency_ms = 0.0

    def detect(
        self,
        audio: np.ndarray,
        timestamp_ms: Optional[float] = None,
    ) -> EnhancedAudioResult:
        """Detect and correlate audio events.

        Args:
            audio: Audio samples (1D mono or 2D multi-channel).
            timestamp_ms: Optional timestamp in milliseconds.

        Returns:
            EnhancedAudioResult with events, correlations, and metadata.
        """
        start_ms = time.time() * 1000
        ts = timestamp_ms or start_ms

        try:
            # Handle multi-channel: average to mono
            processed_audio = self._preprocess_audio(audio)

            # Compute ambient noise level
            ambient_db = self._compute_ambient_noise(processed_audio)
            self._ambient_history.append(ambient_db)

            # Run base detection
            events = self._base_detector.detect(processed_audio, timestamp_ms=ts)

            # Apply adaptive threshold if enabled
            if self.config.adaptive_threshold and events:
                events = self._adaptive_threshold_filter(events, ambient_db)

            # Correlate with history
            correlations = self._correlate_events(events, list(self._event_history))

            # Update history
            for event in events:
                self._event_history.append(event)

            # Determine dominant event
            dominant = None
            if events:
                # Prefer critical events, then highest confidence
                critical = [e for e in events if e.is_critical]
                if critical:
                    dominant = max(critical, key=lambda e: e.confidence)
                else:
                    dominant = max(events, key=lambda e: e.confidence)

            # Compute event density (events per second over recent history)
            event_density = self._compute_event_density(ts)

            latency = time.time() * 1000 - start_ms
            self._total_detections += 1
            self._total_latency_ms += latency

            return EnhancedAudioResult(
                events=events,
                correlations=correlations,
                ambient_noise_db=ambient_db,
                dominant_event=dominant,
                event_density=event_density,
                timestamp_ms=ts,
            )

        except Exception as exc:
            logger.error("Enhanced audio detection failed: %s", exc)
            return EnhancedAudioResult(
                events=[],
                correlations=[],
                ambient_noise_db=-80.0,
                dominant_event=None,
                event_density=0.0,
                timestamp_ms=ts,
            )

    def _preprocess_audio(self, audio: np.ndarray) -> np.ndarray:
        """Preprocess audio: handle multi-channel, normalize."""
        if audio.ndim == 0:
            return np.array([], dtype=np.float32)

        # Multi-channel: average to mono
        if audio.ndim == 2:
            if self.config.multi_channel:
                audio = np.mean(audio, axis=0)
            else:
                audio = audio[0] if audio.shape[0] < audio.shape[1] else audio[:, 0]

        audio = audio.flatten()

        # Normalize to float32
        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32768.0
        elif audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        return audio

    def _correlate_events(
        self,
        current_events: List[AudioEvent],
        history: List[AudioEvent],
    ) -> List[AudioEventCorrelation]:
        """Correlate current events with historical events.

        Args:
            current_events: Events detected in the current frame.
            history: Recent event history.

        Returns:
            List of event correlations.
        """
        correlations: List[AudioEventCorrelation] = []

        if not current_events or not history:
            return correlations

        window_ms = self.config.correlation_window_ms

        for current in current_events:
            for past in history:
                gap_ms = abs(current.timestamp_ms - past.timestamp_ms)
                if gap_ms > window_ms:
                    continue

                # Compute correlation score
                score = self._compute_correlation_score(current, past, gap_ms)

                if score > 0.1:  # Minimum correlation threshold
                    likely_same = (
                        current.event_type == past.event_type
                        and gap_ms < window_ms * 0.5
                        and score > 0.5
                    )
                    correlations.append(AudioEventCorrelation(
                        event_a=current,
                        event_b=past,
                        correlation_score=score,
                        temporal_gap_ms=gap_ms,
                        likely_same_source=likely_same,
                    ))

        # Sort by correlation score descending
        correlations.sort(key=lambda c: c.correlation_score, reverse=True)
        return correlations

    def _compute_correlation_score(
        self,
        event_a: AudioEvent,
        event_b: AudioEvent,
        gap_ms: float,
    ) -> float:
        """Compute correlation score between two events."""
        score = 0.0
        window = self.config.correlation_window_ms

        # Temporal proximity (closer = higher)
        temporal_factor = max(0.0, 1.0 - gap_ms / window)
        score += 0.3 * temporal_factor

        # Same event type bonus
        if event_a.event_type == event_b.event_type:
            score += 0.4

        # Similar energy levels
        energy_diff = abs(event_a.energy_db - event_b.energy_db)
        energy_factor = max(0.0, 1.0 - energy_diff / 30.0)
        score += 0.15 * energy_factor

        # Known co-occurring event pairs
        pair = (event_a.event_type, event_b.event_type)
        co_occur = _CO_OCCURRING_EVENTS.get(pair, 0.0)
        score += 0.15 * co_occur

        return min(1.0, score)

    def _compute_ambient_noise(self, audio: np.ndarray) -> float:
        """Compute ambient noise level in dB.

        Args:
            audio: Preprocessed mono audio.

        Returns:
            Ambient noise level in dB.
        """
        if len(audio) == 0:
            return self.config.noise_floor_db

        rms = np.sqrt(np.mean(audio.astype(np.float64) ** 2))
        if rms < 1e-10:
            return self.config.noise_floor_db

        db = float(20 * np.log10(rms))
        return max(self.config.noise_floor_db, db)

    def _adaptive_threshold_filter(
        self,
        events: List[AudioEvent],
        ambient_db: float,
    ) -> List[AudioEvent]:
        """Filter events using adaptive thresholding based on ambient noise.

        Args:
            events: Detected events.
            ambient_db: Current ambient noise level.

        Returns:
            Filtered list of events.
        """
        if not events:
            return events

        # Calculate adaptive threshold: events must be significantly above ambient
        # For quiet environments, lower the bar; for noisy ones, raise it
        noise_margin = 10.0  # dB above ambient
        min_energy = ambient_db + noise_margin

        filtered = []
        for event in events:
            # Always keep critical events and silence
            if event.is_critical or event.event_type == AudioEventType.SILENCE:
                filtered.append(event)
                continue

            # Non-critical: require event energy above ambient + margin
            if event.energy_db >= min_energy:
                filtered.append(event)
            elif event.confidence >= 0.7:
                # High-confidence events pass even if quieter
                filtered.append(event)
            else:
                logger.debug(
                    "Filtered event %s (energy=%.1f < threshold=%.1f)",
                    event.event_type.value,
                    event.energy_db,
                    min_energy,
                )

        return filtered

    def _compute_event_density(self, current_ts: float) -> float:
        """Compute event density (events per second) over recent history."""
        if not self._event_history:
            return 0.0

        window_ms = self.config.correlation_window_ms
        recent = [
            e for e in self._event_history
            if (current_ts - e.timestamp_ms) <= window_ms
            and e.event_type != AudioEventType.SILENCE
        ]

        if not recent or window_ms <= 0:
            return 0.0

        return len(recent) / (window_ms / 1000.0)

    def health(self) -> Dict[str, Any]:
        """Get health status of the enhanced detector."""
        avg_latency = 0.0
        if self._total_detections > 0:
            avg_latency = self._total_latency_ms / self._total_detections

        avg_ambient = self.config.noise_floor_db
        if self._ambient_history:
            avg_ambient = sum(self._ambient_history) / len(self._ambient_history)

        return {
            "total_detections": self._total_detections,
            "average_latency_ms": round(avg_latency, 1),
            "event_history_size": len(self._event_history),
            "multi_channel": self.config.multi_channel,
            "adaptive_threshold": self.config.adaptive_threshold,
            "average_ambient_db": round(avg_ambient, 1),
            "base_detector_health": self._base_detector.health(),
        }


def create_enhanced_detector(
    config: Optional[EnhancedAudioConfig] = None,
) -> EnhancedAudioDetector:
    """Factory function to create an EnhancedAudioDetector.

    Args:
        config: Optional enhanced audio configuration.

    Returns:
        Configured EnhancedAudioDetector.
    """
    return EnhancedAudioDetector(config=config)
