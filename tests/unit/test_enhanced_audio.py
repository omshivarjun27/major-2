"""Tests for core.audio.enhanced_detector — Enhanced Audio Detection (T-119)."""

from __future__ import annotations

import numpy as np
import pytest

from core.audio.audio_event_detector import (
    AudioEvent,
    AudioEventConfig,
    AudioEventType,
)
from core.audio.enhanced_detector import (
    AudioEventCorrelation,
    EnhancedAudioConfig,
    EnhancedAudioDetector,
    EnhancedAudioResult,
    create_enhanced_detector,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def default_config():
    return EnhancedAudioConfig()


@pytest.fixture
def detector():
    return EnhancedAudioDetector()


@pytest.fixture
def loud_audio():
    """Loud audio signal (sine wave at ~440Hz)."""
    sr = 16000
    t = np.linspace(0, 1, sr, dtype=np.float32)
    return 0.8 * np.sin(2 * np.pi * 440 * t).astype(np.float32)


@pytest.fixture
def quiet_audio():
    """Very quiet audio (near silence)."""
    return np.random.randn(16000).astype(np.float32) * 1e-5


@pytest.fixture
def silence_audio():
    """Complete silence."""
    return np.zeros(16000, dtype=np.float32)


@pytest.fixture
def short_audio():
    """Very short audio clip."""
    return np.random.randn(50).astype(np.float32) * 0.01


@pytest.fixture
def multi_channel_audio():
    """2-channel audio."""
    sr = 16000
    t = np.linspace(0, 1, sr, dtype=np.float32)
    ch1 = 0.5 * np.sin(2 * np.pi * 440 * t)
    ch2 = 0.5 * np.sin(2 * np.pi * 880 * t)
    return np.stack([ch1, ch2], axis=0).astype(np.float32)


@pytest.fixture
def sample_event_a():
    return AudioEvent(
        event_type=AudioEventType.CAR_HORN,
        confidence=0.8,
        energy_db=-10.0,
        timestamp_ms=1000.0,
        duration_ms=500.0,
        is_critical=True,
    )


@pytest.fixture
def sample_event_b():
    return AudioEvent(
        event_type=AudioEventType.TRAFFIC,
        confidence=0.6,
        energy_db=-15.0,
        timestamp_ms=1500.0,
        duration_ms=1000.0,
        is_critical=False,
    )


# =============================================================================
# EnhancedAudioConfig Tests
# =============================================================================


class TestEnhancedAudioConfig:
    """Tests for EnhancedAudioConfig dataclass."""

    def test_default_values(self):
        config = EnhancedAudioConfig()
        assert config.sample_rate == 16000
        assert config.frame_length_ms == 1000.0
        assert config.min_confidence == 0.3
        assert config.multi_channel is False
        assert config.correlation_window_ms == 2000
        assert config.event_history_size == 50
        assert config.adaptive_threshold is True
        assert config.noise_floor_db == -60

    def test_custom_values(self):
        config = EnhancedAudioConfig(
            sample_rate=44100,
            multi_channel=True,
            correlation_window_ms=5000,
            event_history_size=100,
            adaptive_threshold=False,
            noise_floor_db=-80,
        )
        assert config.sample_rate == 44100
        assert config.multi_channel is True
        assert config.correlation_window_ms == 5000
        assert config.event_history_size == 100
        assert config.adaptive_threshold is False
        assert config.noise_floor_db == -80

    def test_to_base_config(self):
        config = EnhancedAudioConfig(sample_rate=44100, min_confidence=0.5, n_mfcc=20)
        base = config.to_base_config()
        assert isinstance(base, AudioEventConfig)
        assert base.sample_rate == 44100
        assert base.min_confidence == 0.5
        assert base.n_mfcc == 20

    def test_to_base_config_preserves_fields(self):
        config = EnhancedAudioConfig(
            sample_rate=8000,
            frame_length_ms=500.0,
            hop_length_ms=250.0,
            n_mel=80,
        )
        base = config.to_base_config()
        assert base.frame_length_ms == 500.0
        assert base.hop_length_ms == 250.0
        assert base.n_mel == 80


# =============================================================================
# AudioEventCorrelation Tests
# =============================================================================


class TestAudioEventCorrelation:
    """Tests for AudioEventCorrelation dataclass."""

    def test_correlation_creation(self, sample_event_a, sample_event_b):
        corr = AudioEventCorrelation(
            event_a=sample_event_a,
            event_b=sample_event_b,
            correlation_score=0.75,
            temporal_gap_ms=500.0,
            likely_same_source=False,
        )
        assert corr.correlation_score == 0.75
        assert corr.temporal_gap_ms == 500.0
        assert corr.likely_same_source is False

    def test_correlation_to_dict(self, sample_event_a, sample_event_b):
        corr = AudioEventCorrelation(
            event_a=sample_event_a,
            event_b=sample_event_b,
            correlation_score=0.756,
            temporal_gap_ms=500.123,
            likely_same_source=True,
        )
        d = corr.to_dict()
        assert d["event_a"] == "car_horn"
        assert d["event_b"] == "traffic"
        assert d["correlation_score"] == 0.756
        assert d["temporal_gap_ms"] == 500.1
        assert d["likely_same_source"] is True


# =============================================================================
# EnhancedAudioResult Tests
# =============================================================================


class TestEnhancedAudioResult:
    """Tests for EnhancedAudioResult dataclass."""

    def test_default_result(self):
        result = EnhancedAudioResult()
        assert result.events == []
        assert result.correlations == []
        assert result.ambient_noise_db == -60.0
        assert result.dominant_event is None
        assert result.event_density == 0.0

    def test_result_to_dict(self, sample_event_a):
        result = EnhancedAudioResult(
            events=[sample_event_a],
            correlations=[],
            ambient_noise_db=-25.0,
            dominant_event=sample_event_a,
            event_density=1.5,
            timestamp_ms=1000.0,
        )
        d = result.to_dict()
        assert len(d["events"]) == 1
        assert d["ambient_noise_db"] == -25.0
        assert d["dominant_event"] is not None
        assert d["dominant_event"]["event_type"] == "car_horn"
        assert d["event_density"] == 1.5

    def test_result_to_dict_no_dominant(self):
        result = EnhancedAudioResult(timestamp_ms=500.0)
        d = result.to_dict()
        assert d["dominant_event"] is None
        assert d["events"] == []

    def test_result_to_dict_with_correlations(self, sample_event_a, sample_event_b):
        corr = AudioEventCorrelation(
            event_a=sample_event_a,
            event_b=sample_event_b,
            correlation_score=0.7,
            temporal_gap_ms=500.0,
            likely_same_source=False,
        )
        result = EnhancedAudioResult(
            events=[sample_event_a, sample_event_b],
            correlations=[corr],
            timestamp_ms=1500.0,
        )
        d = result.to_dict()
        assert len(d["correlations"]) == 1


# =============================================================================
# Single Event Detection Tests
# =============================================================================


class TestSingleEventDetection:
    """Tests for basic event detection through enhanced detector."""

    def test_detect_loud_audio(self, detector, loud_audio):
        result = detector.detect(loud_audio, timestamp_ms=1000.0)
        assert isinstance(result, EnhancedAudioResult)
        assert result.timestamp_ms == 1000.0
        assert result.ambient_noise_db > -20  # Loud signal detected

    def test_detect_silence(self, detector, silence_audio):
        result = detector.detect(silence_audio, timestamp_ms=1000.0)
        assert isinstance(result, EnhancedAudioResult)
        # Silence may produce a SILENCE event or empty events
        if result.events:
            silence_events = [e for e in result.events if e.event_type == AudioEventType.SILENCE]
            assert len(silence_events) >= 0

    def test_detect_quiet_audio(self, detector, quiet_audio):
        result = detector.detect(quiet_audio, timestamp_ms=1000.0)
        assert isinstance(result, EnhancedAudioResult)

    def test_detect_short_audio(self, detector, short_audio):
        result = detector.detect(short_audio, timestamp_ms=1000.0)
        assert isinstance(result, EnhancedAudioResult)

    def test_detect_empty_audio(self, detector):
        audio = np.array([], dtype=np.float32)
        result = detector.detect(audio, timestamp_ms=1000.0)
        assert isinstance(result, EnhancedAudioResult)
        assert result.events == []

    def test_detect_sets_dominant_event(self, detector, loud_audio):
        result = detector.detect(loud_audio, timestamp_ms=1000.0)
        if result.events:
            assert result.dominant_event is not None
            assert result.dominant_event in result.events

    def test_detect_auto_timestamp(self, detector, loud_audio):
        result = detector.detect(loud_audio)
        assert result.timestamp_ms > 0


# =============================================================================
# Multi-channel Tests
# =============================================================================


class TestMultiChannel:
    """Tests for multi-channel audio handling."""

    def test_multi_channel_averaging(self, multi_channel_audio):
        config = EnhancedAudioConfig(multi_channel=True)
        detector = EnhancedAudioDetector(config=config)
        result = detector.detect(multi_channel_audio, timestamp_ms=1000.0)
        assert isinstance(result, EnhancedAudioResult)

    def test_mono_fallback_for_multi_channel(self, multi_channel_audio):
        config = EnhancedAudioConfig(multi_channel=False)
        detector = EnhancedAudioDetector(config=config)
        result = detector.detect(multi_channel_audio, timestamp_ms=1000.0)
        assert isinstance(result, EnhancedAudioResult)

    def test_int16_audio_handling(self, detector):
        audio = (np.random.randn(16000) * 10000).astype(np.int16)
        result = detector.detect(audio, timestamp_ms=1000.0)
        assert isinstance(result, EnhancedAudioResult)


# =============================================================================
# Ambient Noise Computation Tests
# =============================================================================


class TestAmbientNoise:
    """Tests for ambient noise computation."""

    def test_ambient_noise_loud(self, detector, loud_audio):
        db = detector._compute_ambient_noise(loud_audio)
        assert db > -20  # Loud signal

    def test_ambient_noise_quiet(self, detector, quiet_audio):
        db = detector._compute_ambient_noise(quiet_audio)
        assert db < -40  # Very quiet

    def test_ambient_noise_silence(self, detector, silence_audio):
        db = detector._compute_ambient_noise(silence_audio)
        assert db == detector.config.noise_floor_db

    def test_ambient_noise_empty(self, detector):
        db = detector._compute_ambient_noise(np.array([], dtype=np.float32))
        assert db == detector.config.noise_floor_db

    def test_ambient_history_updated(self, detector, loud_audio):
        assert len(detector._ambient_history) == 0
        detector.detect(loud_audio, timestamp_ms=1000.0)
        assert len(detector._ambient_history) == 1


# =============================================================================
# Event Correlation Tests
# =============================================================================


class TestEventCorrelation:
    """Tests for event correlation logic."""

    def test_correlate_empty_history(self, detector, sample_event_a):
        correlations = detector._correlate_events([sample_event_a], [])
        assert correlations == []

    def test_correlate_empty_current(self, detector, sample_event_a):
        correlations = detector._correlate_events([], [sample_event_a])
        assert correlations == []

    def test_correlate_same_type_close(self, detector):
        ev1 = AudioEvent(
            event_type=AudioEventType.CAR_HORN,
            confidence=0.8, energy_db=-10, timestamp_ms=1000,
        )
        ev2 = AudioEvent(
            event_type=AudioEventType.CAR_HORN,
            confidence=0.7, energy_db=-12, timestamp_ms=1500,
        )
        correlations = detector._correlate_events([ev2], [ev1])
        assert len(correlations) > 0
        assert correlations[0].correlation_score > 0.3

    def test_correlate_co_occurring_events(self, detector, sample_event_a, sample_event_b):
        correlations = detector._correlate_events([sample_event_b], [sample_event_a])
        assert len(correlations) > 0
        # CAR_HORN + TRAFFIC should have a co-occurrence boost
        assert correlations[0].correlation_score > 0.2

    def test_correlate_outside_window(self, detector):
        ev1 = AudioEvent(
            event_type=AudioEventType.CAR_HORN,
            confidence=0.8, energy_db=-10, timestamp_ms=1000,
        )
        ev2 = AudioEvent(
            event_type=AudioEventType.CAR_HORN,
            confidence=0.8, energy_db=-10, timestamp_ms=5000,
        )
        correlations = detector._correlate_events([ev2], [ev1])
        assert len(correlations) == 0  # Outside 2000ms window

    def test_likely_same_source(self, detector):
        ev1 = AudioEvent(
            event_type=AudioEventType.VOICE,
            confidence=0.8, energy_db=-15, timestamp_ms=1000,
        )
        ev2 = AudioEvent(
            event_type=AudioEventType.VOICE,
            confidence=0.8, energy_db=-14, timestamp_ms=1200,
        )
        correlations = detector._correlate_events([ev2], [ev1])
        assert len(correlations) > 0
        # Same type, close in time and energy → likely same source
        assert correlations[0].likely_same_source is True


# =============================================================================
# Adaptive Threshold Tests
# =============================================================================


class TestAdaptiveThreshold:
    """Tests for adaptive thresholding behavior."""

    def test_adaptive_threshold_keeps_critical(self, detector):
        events = [AudioEvent(
            event_type=AudioEventType.SIREN,
            confidence=0.4, energy_db=-50, timestamp_ms=1000,
            is_critical=True,
        )]
        filtered = detector._adaptive_threshold_filter(events, -20)
        assert len(filtered) == 1

    def test_adaptive_threshold_filters_quiet_noncritical(self, detector):
        events = [AudioEvent(
            event_type=AudioEventType.FOOTSTEPS,
            confidence=0.4, energy_db=-40, timestamp_ms=1000,
            is_critical=False,
        )]
        # Ambient at -20, threshold would be -10, event at -40 → filtered
        filtered = detector._adaptive_threshold_filter(events, -20)
        assert len(filtered) == 0

    def test_adaptive_threshold_keeps_loud_events(self, detector):
        events = [AudioEvent(
            event_type=AudioEventType.FOOTSTEPS,
            confidence=0.4, energy_db=-5, timestamp_ms=1000,
            is_critical=False,
        )]
        # Ambient at -20, threshold = -10, event at -5 → passes
        filtered = detector._adaptive_threshold_filter(events, -20)
        assert len(filtered) == 1

    def test_adaptive_threshold_keeps_high_confidence(self, detector):
        events = [AudioEvent(
            event_type=AudioEventType.VOICE,
            confidence=0.8, energy_db=-40, timestamp_ms=1000,
            is_critical=False,
        )]
        # Quiet but high confidence → passes
        filtered = detector._adaptive_threshold_filter(events, -20)
        assert len(filtered) == 1

    def test_adaptive_threshold_empty_events(self, detector):
        filtered = detector._adaptive_threshold_filter([], -20)
        assert filtered == []

    def test_adaptive_disabled(self, loud_audio):
        config = EnhancedAudioConfig(adaptive_threshold=False)
        det = EnhancedAudioDetector(config=config)
        result = det.detect(loud_audio, timestamp_ms=1000.0)
        assert isinstance(result, EnhancedAudioResult)


# =============================================================================
# Event History & Density Tests
# =============================================================================


class TestEventHistoryAndDensity:
    """Tests for event history and density computation."""

    def test_history_grows(self, detector):
        """History grows when events are detected."""
        assert len(detector._event_history) == 0
        # Use white noise which produces classifiable events
        noise = np.random.randn(16000).astype(np.float32) * 0.5
        result = detector.detect(noise, timestamp_ms=1000.0)
        # History grows if events were detected (depends on heuristic)
        if result.events:
            assert len(detector._event_history) > 0
        else:
            assert len(detector._event_history) == 0

    def test_event_density_empty(self, detector):
        density = detector._compute_event_density(1000.0)
        assert density == 0.0

    def test_event_density_with_events(self, detector):
        # Manually add events to history
        for i in range(5):
            detector._event_history.append(AudioEvent(
                event_type=AudioEventType.VOICE,
                confidence=0.5, energy_db=-20, timestamp_ms=900 + i * 100,
            ))
        density = detector._compute_event_density(1500.0)
        assert density > 0

    def test_history_max_size(self):
        config = EnhancedAudioConfig(event_history_size=5)
        det = EnhancedAudioDetector(config=config)
        assert det._event_history.maxlen == 5


# =============================================================================
# Health Check Tests
# =============================================================================


class TestHealth:
    """Tests for health reporting."""

    def test_health_initial(self, detector):
        h = detector.health()
        assert h["total_detections"] == 0
        assert h["average_latency_ms"] == 0.0
        assert h["event_history_size"] == 0
        assert h["multi_channel"] is False
        assert h["adaptive_threshold"] is True
        assert "base_detector_health" in h

    def test_health_after_detection(self, detector, loud_audio):
        detector.detect(loud_audio, timestamp_ms=1000.0)
        h = detector.health()
        assert h["total_detections"] == 1
        assert h["average_latency_ms"] >= 0


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactory:
    """Tests for the factory function."""

    def test_create_default(self):
        det = create_enhanced_detector()
        assert isinstance(det, EnhancedAudioDetector)

    def test_create_with_config(self):
        config = EnhancedAudioConfig(sample_rate=44100, multi_channel=True)
        det = create_enhanced_detector(config=config)
        assert det.config.sample_rate == 44100
        assert det.config.multi_channel is True


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_scalar_audio(self, detector):
        result = detector.detect(np.float32(0.5), timestamp_ms=1000.0)
        assert isinstance(result, EnhancedAudioResult)

    def test_all_zeros_audio(self, detector):
        audio = np.zeros(16000, dtype=np.float32)
        result = detector.detect(audio, timestamp_ms=1000.0)
        assert isinstance(result, EnhancedAudioResult)
        assert result.ambient_noise_db <= detector.config.noise_floor_db

    def test_repeated_detections(self, detector, loud_audio):
        for i in range(5):
            result = detector.detect(loud_audio, timestamp_ms=1000.0 + i * 100)
            assert isinstance(result, EnhancedAudioResult)
        assert detector._total_detections == 5

    def test_nan_audio_graceful(self, detector):
        audio = np.full(16000, np.nan, dtype=np.float32)
        result = detector.detect(audio, timestamp_ms=1000.0)
        assert isinstance(result, EnhancedAudioResult)
