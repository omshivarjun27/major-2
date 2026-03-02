"""Audio event detection edge cases: silence, noise, boundary conditions, features."""

from __future__ import annotations

import numpy as np
import pytest

from core.audio.audio_event_detector import (
    CRITICAL_EVENTS,
    AudioEvent,
    AudioEventConfig,
    AudioEventDetector,
    AudioEventType,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _silence(n: int = 16000) -> np.ndarray:
    """Generate silent audio (all zeros)."""
    return np.zeros(n, dtype=np.float32)


def _white_noise(n: int = 16000, amplitude: float = 0.5) -> np.ndarray:
    """Generate white noise audio."""
    return (np.random.rand(n).astype(np.float32) - 0.5) * 2 * amplitude


def _sine_wave(freq: float = 440.0, sr: int = 16000, duration: float = 1.0) -> np.ndarray:
    """Generate a pure sine wave."""
    t = np.linspace(0, duration, int(sr * duration), dtype=np.float32)
    return np.sin(2 * np.pi * freq * t).astype(np.float32)


def _int16_audio(n: int = 16000) -> np.ndarray:
    """Generate int16 audio samples."""
    return np.random.randint(-32768, 32767, n, dtype=np.int16)


# ===========================================================================
# AudioEventConfig edge cases
# ===========================================================================


class TestAudioEventConfigEdgeCases:
    """Edge cases for AudioEventConfig."""

    def test_default_config_values(self):
        """Default config should have sane values."""
        cfg = AudioEventConfig()
        assert cfg.sample_rate == 16000
        assert cfg.min_confidence == 0.3
        assert cfg.n_mfcc == 13

    def test_custom_config(self):
        """Custom config values should be stored."""
        cfg = AudioEventConfig(sample_rate=44100, min_confidence=0.5, n_mel=80)
        assert cfg.sample_rate == 44100
        assert cfg.n_mel == 80

    def test_zero_min_confidence(self):
        """Zero min_confidence should be allowed."""
        cfg = AudioEventConfig(min_confidence=0.0)
        assert cfg.min_confidence == 0.0


# ===========================================================================
# AudioEvent data structure edge cases
# ===========================================================================


class TestAudioEventEdgeCases:
    """Edge cases for AudioEvent data structure."""

    def test_to_dict_keys(self):
        """to_dict should include all expected keys."""
        evt = AudioEvent(
            event_type=AudioEventType.CAR_HORN,
            confidence=0.8,
            energy_db=-10.0,
            timestamp_ms=1000.0,
            duration_ms=500.0,
            is_critical=True,
        )
        d = evt.to_dict()
        assert "event_type" in d
        assert "confidence" in d
        assert "is_critical" in d
        assert d["is_critical"] is True

    def test_critical_event_cue(self):
        """Critical events should have non-empty user_cue."""
        for evt_type in CRITICAL_EVENTS:
            evt = AudioEvent(
                event_type=evt_type,
                confidence=0.9,
                energy_db=-5.0,
                timestamp_ms=0.0,
            )
            assert evt.user_cue != "", f"Missing cue for {evt_type}"

    def test_silence_event_has_no_cue(self):
        """SILENCE event should have empty user_cue."""
        evt = AudioEvent(
            event_type=AudioEventType.SILENCE,
            confidence=0.9,
            energy_db=-60.0,
            timestamp_ms=0.0,
        )
        assert evt.user_cue == ""

    def test_unknown_event_has_no_cue(self):
        """UNKNOWN event should have empty user_cue."""
        evt = AudioEvent(
            event_type=AudioEventType.UNKNOWN,
            confidence=0.3,
            energy_db=-20.0,
            timestamp_ms=0.0,
        )
        assert evt.user_cue == ""

    def test_to_dict_rounds_values(self):
        """to_dict should round floating point values."""
        evt = AudioEvent(
            event_type=AudioEventType.VOICE,
            confidence=0.77777,
            energy_db=-15.4321,
            timestamp_ms=1000.0,
            duration_ms=123.456789,
        )
        d = evt.to_dict()
        assert d["confidence"] == 0.778
        assert d["energy_db"] == -15.4
        assert d["duration_ms"] == 123.5


# ===========================================================================
# AudioEventDetector edge cases
# ===========================================================================


class TestAudioEventDetectorEdgeCases:
    """Edge cases for AudioEventDetector detection."""

    def test_detect_silence(self):
        """Silent audio should return SILENCE event."""
        detector = AudioEventDetector()
        events = detector.detect(_silence())
        assert len(events) >= 1
        assert events[0].event_type == AudioEventType.SILENCE

    def test_detect_very_short_audio(self):
        """Audio shorter than 100 samples should return empty list."""
        detector = AudioEventDetector()
        short = np.zeros(50, dtype=np.float32)
        events = detector.detect(short)
        assert events == []

    def test_detect_empty_array(self):
        """Empty array should return empty list."""
        detector = AudioEventDetector()
        events = detector.detect(np.array([], dtype=np.float32))
        assert events == []

    def test_detect_int16_audio(self):
        """int16 audio should be normalized and processed."""
        detector = AudioEventDetector()
        events = detector.detect(_int16_audio())
        assert isinstance(events, list)

    def test_detect_2d_audio_flattened(self):
        """2D audio array should be flattened."""
        detector = AudioEventDetector()
        audio_2d = np.random.rand(2, 8000).astype(np.float32)
        events = detector.detect(audio_2d)
        assert isinstance(events, list)

    def test_detect_white_noise(self):
        """White noise should produce detection events."""
        detector = AudioEventDetector()
        events = detector.detect(_white_noise(amplitude=0.8))
        assert len(events) >= 1

    def test_detect_high_frequency_sine(self):
        """High-frequency sine should not crash detector."""
        detector = AudioEventDetector()
        audio = _sine_wave(freq=8000.0)
        events = detector.detect(audio)
        assert isinstance(events, list)

    def test_detect_low_frequency_sine(self):
        """Low-frequency sine should be detected."""
        detector = AudioEventDetector()
        audio = _sine_wave(freq=100.0, duration=1.0) * 0.8
        events = detector.detect(audio)
        assert isinstance(events, list)

    def test_detect_auto_timestamp(self):
        """Zero timestamp should be auto-filled."""
        detector = AudioEventDetector()
        events = detector.detect(_white_noise(), timestamp_ms=0)
        if events:
            assert events[0].timestamp_ms > 0

    def test_detect_custom_timestamp(self):
        """Custom timestamp should be preserved."""
        detector = AudioEventDetector()
        events = detector.detect(_white_noise(), timestamp_ms=42000.0)
        if events:
            assert events[0].timestamp_ms == 42000.0

    def test_events_sorted_by_confidence(self):
        """Events should be sorted by confidence (highest first)."""
        detector = AudioEventDetector()
        events = detector.detect(_white_noise(amplitude=0.9))
        if len(events) > 1:
            for i in range(len(events) - 1):
                assert events[i].confidence >= events[i + 1].confidence

    def test_min_confidence_filters_events(self):
        """Events below min_confidence should be filtered out."""
        cfg = AudioEventConfig(min_confidence=0.99)
        detector = AudioEventDetector(cfg)
        events = detector.detect(_white_noise())
        # With very high threshold, most heuristic scores should be filtered
        for evt in events:
            assert evt.confidence >= 0.99 or evt.event_type == AudioEventType.SILENCE

    def test_health_returns_dict(self):
        """health() should return a dict with expected keys."""
        detector = AudioEventDetector()
        h = detector.health()
        assert "model_loaded" in h
        assert "config" in h
        assert h["model_loaded"] is False  # no model path given

    def test_energy_db_silent_audio(self):
        """_energy_db of near-zero audio should be very negative."""
        db = AudioEventDetector._energy_db(np.full(100, 1e-12, dtype=np.float32))
        assert db < -60

    def test_energy_db_full_scale(self):
        """_energy_db of full-scale audio should be near 0 dB."""
        db = AudioEventDetector._energy_db(np.ones(100, dtype=np.float32))
        assert abs(db) < 1.0  # should be ~0 dB

    def test_nonexistent_model_path(self):
        """Nonexistent model path should fallback gracefully."""
        cfg = AudioEventConfig(model_path="/nonexistent/model.pt")
        detector = AudioEventDetector(cfg)
        assert detector._model is None
        events = detector.detect(_white_noise())
        assert isinstance(events, list)


# ===========================================================================
# AudioEventType enum edge cases
# ===========================================================================


class TestAudioEventTypeEdgeCases:
    """Edge cases for AudioEventType enum."""

    def test_all_types_have_string_values(self):
        """Every AudioEventType should have a non-empty string value."""
        for et in AudioEventType:
            assert isinstance(et.value, str)
            assert len(et.value) > 0

    def test_critical_events_are_valid_types(self):
        """CRITICAL_EVENTS should all be valid AudioEventType members."""
        for evt in CRITICAL_EVENTS:
            assert isinstance(evt, AudioEventType)

    def test_type_from_string(self):
        """AudioEventType should be constructible from value string."""
        et = AudioEventType("car_horn")
        assert et == AudioEventType.CAR_HORN

    def test_invalid_string_raises(self):
        """Invalid string should raise ValueError."""
        with pytest.raises(ValueError):
            AudioEventType("nonexistent_event")
