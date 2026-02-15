"""
Tests for audio_engine — SoundSourceLocalizer, AudioEventDetector, AudioVisionFuser.
"""

from __future__ import annotations

import numpy as np
import pytest

# ── SoundSourceLocalizer ──────────────────────────────────────────────

from core.audio.ssl import SoundSourceLocalizer, SSLResult, SSLConfig


class TestSSLConfig:
    def test_defaults(self):
        cfg = SSLConfig()
        assert cfg.sample_rate == 16000
        assert cfg.mic_spacing_m == 0.1
        assert cfg.max_sources == 3
        assert cfg.single_mic_mode is False


class TestSoundSourceLocalizer:
    def test_init(self):
        ssl = SoundSourceLocalizer()
        assert ssl is not None

    def test_localize_mono(self):
        ssl = SoundSourceLocalizer(SSLConfig(single_mic_mode=True))
        audio = np.random.randn(16000).astype(np.float32) * 0.1
        results = ssl.localize(audio, timestamp_ms=1000)
        assert isinstance(results, list)

    def test_localize_stereo(self):
        ssl = SoundSourceLocalizer()
        audio = np.random.randn(2, 16000).astype(np.float32) * 0.1
        results = ssl.localize(audio, timestamp_ms=1000)
        assert isinstance(results, list)

    def test_localize_silence(self):
        ssl = SoundSourceLocalizer()
        audio = np.zeros((2, 16000), dtype=np.float32)
        results = ssl.localize(audio, timestamp_ms=1000)
        assert isinstance(results, list)

    def test_ssl_result_direction(self):
        r = SSLResult(
            source_id="s1",
            azimuth_deg=45.0,
            elevation_deg=0.0,
            distance_estimate=2.0,
            energy_db=-10.0,
            confidence=0.8,
            timestamp_ms=1000,
        )
        assert "right" in r.direction_label.lower() or "front" in r.direction_label.lower()

    def test_ssl_result_to_dict(self):
        r = SSLResult(source_id="s1", azimuth_deg=0, elevation_deg=0,
                      distance_estimate="nearby", energy_db=-20, confidence=0.7, timestamp_ms=1000)
        d = r.to_dict()
        assert "azimuth_deg" in d
        assert "source_id" in d
        assert "confidence" in d

    def test_health(self):
        ssl = SoundSourceLocalizer()
        h = ssl.health()
        assert "sample_rate" in h


# ── AudioEventDetector ────────────────────────────────────────────────

from core.audio.audio_event_detector import (
    AudioEventDetector,
    AudioEvent,
    AudioEventConfig,
    AudioEventType,
    CRITICAL_EVENTS,
)


class TestAudioEventConfig:
    def test_defaults(self):
        cfg = AudioEventConfig()
        assert cfg.sample_rate == 16000
        assert cfg.min_confidence == 0.3


class TestAudioEventDetector:
    def test_init(self):
        det = AudioEventDetector()
        assert det is not None

    def test_detect_silence(self):
        det = AudioEventDetector()
        audio = np.zeros(16000, dtype=np.float32)
        events = det.detect(audio, timestamp_ms=1000)
        assert isinstance(events, list)
        if events:
            assert events[0].event_type == AudioEventType.SILENCE

    def test_detect_noise(self):
        det = AudioEventDetector()
        audio = np.random.randn(16000).astype(np.float32) * 0.5
        events = det.detect(audio, timestamp_ms=1000)
        assert isinstance(events, list)

    def test_detect_short_audio(self):
        det = AudioEventDetector()
        audio = np.random.randn(50).astype(np.float32)
        events = det.detect(audio, timestamp_ms=1000)
        assert events == []

    def test_detect_int16(self):
        det = AudioEventDetector()
        audio = (np.random.randn(16000) * 10000).astype(np.int16)
        events = det.detect(audio, timestamp_ms=1000)
        assert isinstance(events, list)

    def test_event_to_dict(self):
        ev = AudioEvent(
            event_type=AudioEventType.CAR_HORN,
            confidence=0.7,
            energy_db=-10,
            timestamp_ms=1000,
            is_critical=True,
        )
        d = ev.to_dict()
        assert d["event_type"] == "car_horn"
        assert d["is_critical"] is True

    def test_event_user_cue(self):
        ev = AudioEvent(
            event_type=AudioEventType.CAR_HORN,
            confidence=0.7,
            energy_db=-10,
            timestamp_ms=1000,
        )
        assert "car horn" in ev.user_cue.lower() or "caution" in ev.user_cue.lower()

    def test_critical_events(self):
        assert AudioEventType.CAR_HORN in CRITICAL_EVENTS
        assert AudioEventType.SIREN in CRITICAL_EVENTS

    def test_health(self):
        det = AudioEventDetector()
        h = det.health()
        assert "model_loaded" in h


# ── AudioVisionFuser ──────────────────────────────────────────────────

from core.audio.audio_fusion import (
    AudioVisionFuser,
    FusedAudioVisualEvent,
    AudioFusionConfig,
    VisualObject,
)


class TestAudioFusionConfig:
    def test_defaults(self):
        cfg = AudioFusionConfig()
        assert cfg.angular_tolerance_deg == 30.0
        assert cfg.temporal_tolerance_ms == 2000.0


class TestAudioVisionFuser:
    def test_init(self):
        fuser = AudioVisionFuser()
        assert fuser is not None

    def test_fuse_empty(self):
        fuser = AudioVisionFuser()
        fused = fuser.fuse()
        assert fused == []

    def test_fuse_audio_only(self):
        fuser = AudioVisionFuser()
        ae = AudioEvent(
            event_type=AudioEventType.CAR_HORN,
            confidence=0.7,
            energy_db=-10,
            timestamp_ms=1000,
            is_critical=True,
        )
        fused = fuser.fuse(audio_events=[ae])
        assert len(fused) >= 1
        assert fused[0].is_critical

    def test_fuse_with_ssl(self):
        fuser = AudioVisionFuser()
        ssl_r = SSLResult(
            source_id="s1", azimuth_deg=-30.0, elevation_deg=0,
            distance_estimate=3.0, energy_db=-15, confidence=0.8, timestamp_ms=1000,
        )
        ae = AudioEvent(
            event_type=AudioEventType.VOICE,
            confidence=0.6,
            energy_db=-15,
            timestamp_ms=1000,
        )
        fused = fuser.fuse(audio_events=[ae], ssl_results=[ssl_r])
        assert len(fused) >= 1

    def test_fuse_with_visual(self):
        fuser = AudioVisionFuser()
        ssl_r = SSLResult(
            source_id="s1", azimuth_deg=0.0, elevation_deg=0,
            distance_estimate=2.0, energy_db=-15, confidence=0.8, timestamp_ms=1000,
        )
        ae = AudioEvent(
            event_type=AudioEventType.VOICE,
            confidence=0.6,
            energy_db=-15,
            timestamp_ms=1000,
        )
        vo = VisualObject(
            label="person",
            bbox=(0.4, 0.2, 0.6, 0.8),
            confidence=0.7,
            timestamp_ms=1000,
        )
        fused = fuser.fuse(audio_events=[ae], ssl_results=[ssl_r], visual_objects=[vo])
        assert len(fused) >= 1

    def test_fused_event_user_cue(self):
        ev = FusedAudioVisualEvent(
            event_id="fav_1",
            spatial_description="Sound from left, approximately 2.0 meters away",
            is_critical=True,
            timestamp_ms=1000,
        )
        assert len(ev.user_cue) > 0

    def test_health(self):
        fuser = AudioVisionFuser()
        h = fuser.health()
        assert "events_produced" in h


# ── Package imports ───────────────────────────────────────────────────

class TestAudioPackageImports:
    def test_audio_engine_imports(self):
        from core.audio import (
            SoundSourceLocalizer,
            SSLResult,
            SSLConfig,
            AudioEventDetector,
            AudioEvent,
            AudioEventConfig,
            AudioVisionFuser,
            FusedAudioVisualEvent,
            AudioFusionConfig,
        )
        assert SoundSourceLocalizer is not None
        assert AudioEventDetector is not None
        assert AudioVisionFuser is not None
