"""
Tests for Runtime Diagnostics Module
=====================================
"""

import asyncio
import json
import math
import os
import struct
import sys
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.utils.runtime_diagnostics import (
    VALID_SAMPLE_RATES,
    RuntimeDiagnostics,
    SystemStatus,
    TTSDiagnostics,
    TTSEventLog,
    TTSPreflightResult,
    VQADiagnostics,
    VQAPreflightResult,
    VQASkipCode,
    analyze_audio_chunk,
    apply_soft_fade,
    get_diagnostics,
    normalize_audio,
)

# ============================================================================
# Audio Utilities
# ============================================================================

class TestAnalyzeAudioChunk:
    """Tests for analyze_audio_chunk."""

    def test_empty_bytes(self):
        result = analyze_audio_chunk(b"")
        assert result == {"rms": 0.0, "peak": 0.0, "clipping_pct": 0.0}

    def test_silence(self):
        # 100 samples of silence
        audio = struct.pack("<100h", *([0] * 100))
        result = analyze_audio_chunk(audio)
        assert result["rms"] == 0.0
        assert result["peak"] == 0.0
        assert result["clipping_pct"] == 0.0

    def test_max_amplitude_detection(self):
        # Samples at max amplitude (clipping)
        audio = struct.pack("<100h", *([32767] * 100))
        result = analyze_audio_chunk(audio)
        assert result["peak"] > 0.99
        assert result["clipping_pct"] > 0.0

    def test_moderate_signal(self):
        # Sine-like signal at 50% amplitude
        samples = [int(16383 * math.sin(2 * math.pi * i / 40)) for i in range(200)]
        audio = struct.pack(f"<{len(samples)}h", *samples)
        result = analyze_audio_chunk(audio)
        assert 0.0 < result["rms"] < 1.0
        assert 0.0 < result["peak"] < 1.0
        assert result["clipping_pct"] == 0.0


class TestApplySoftFade:
    """Tests for apply_soft_fade."""

    def test_empty_audio(self):
        assert apply_soft_fade(b"") == b""

    def test_short_audio_unchanged(self):
        short = struct.pack("<2h", 100, 200)
        assert apply_soft_fade(short) == short

    def test_fade_applied(self):
        # 100 samples at constant value
        samples = [10000] * 100
        audio = struct.pack("<100h", *samples)
        faded = apply_soft_fade(audio, fade_ms=4.0, sample_rate=16000)
        # First sample should be near zero due to fade-in
        result_samples = struct.unpack("<100h", faded)
        assert result_samples[0] < samples[0]  # Fade-in reduces start
        assert result_samples[-1] < samples[-1]  # Fade-out reduces end
        # Middle should be near original
        mid = len(result_samples) // 2
        assert result_samples[mid] == samples[mid]


class TestNormalizeAudio:
    """Tests for normalize_audio."""

    def test_empty_audio(self):
        assert normalize_audio(b"") == b""

    def test_silence_unchanged(self):
        audio = struct.pack("<100h", *([0] * 100))
        assert normalize_audio(audio) == audio

    def test_quiet_signal_amplified(self):
        # Very quiet signal
        samples = [100] * 100
        audio = struct.pack("<100h", *samples)
        normalized = normalize_audio(audio, target_rms=0.3)
        result = struct.unpack("<100h", normalized)
        assert result[50] > samples[50]  # Should be amplified

    def test_no_clipping_after_normalization(self):
        samples = [int(20000 * math.sin(2 * math.pi * i / 20)) for i in range(200)]
        audio = struct.pack(f"<{len(samples)}h", *samples)
        normalized = normalize_audio(audio, target_rms=0.5)
        result = struct.unpack(f"<{len(samples)}h", normalized)
        assert all(-32768 <= s <= 32767 for s in result)


# ============================================================================
# TTS Diagnostics
# ============================================================================

class TestTTSDiagnostics:
    """Tests for TTSDiagnostics class."""

    def test_preflight_valid_config(self):
        diag = TTSDiagnostics()
        result = diag.preflight(
            provider="elevenlabs",
            model="eleven_turbo_v2_5",
            voice_id="test_voice",
            sample_rate=44100,
            codec="mp3",
        )
        assert result.ready is True
        assert result.sample_rate_match is True
        assert result.codec_compatible is True
        assert result.provider == "elevenlabs"

    def test_preflight_invalid_sample_rate(self):
        diag = TTSDiagnostics()
        result = diag.preflight(sample_rate=12345)
        assert result.ready is False
        assert len(result.errors) > 0

    def test_preflight_valid_sample_rates(self):
        diag = TTSDiagnostics()
        for sr in VALID_SAMPLE_RATES:
            result = diag.preflight(sample_rate=sr)
            assert result.sample_rate_match is True, f"Failed for {sr}"

    def test_stream_events(self):
        diag = TTSDiagnostics()
        start_evt = diag.on_stream_start(sample_rate=16000, codec="pcm16")
        assert start_evt.event == "stream_start"

        chunk_evt = diag.on_chunk_sent()
        assert chunk_evt.event == "chunk_sent"
        assert chunk_evt.chunks_sent == 1

        diag.on_chunk_played()
        end_evt = diag.on_stream_end()
        assert end_evt.event == "stream_end"
        assert end_evt.chunks_sent == 1
        assert end_evt.chunks_played == 1

    def test_error_and_retry(self):
        diag = TTSDiagnostics()
        diag._max_retries = 2
        diag.on_error("TIMEOUT", "Connection timed out")
        assert diag.should_retry() is True
        diag.on_error("TIMEOUT", "Still timing out")
        assert diag.should_retry() is False

    def test_debug_summary(self):
        diag = TTSDiagnostics()
        diag.on_stream_start()
        diag.on_chunk_sent()
        diag.on_chunk_sent()
        diag.on_chunk_played()
        summary = diag.get_debug_summary()
        assert summary["component"] == "tts"
        assert summary["chunks_sent"] == 2
        assert summary["chunks_played"] == 1

    def test_event_log_to_dict(self):
        evt = TTSEventLog(
            event="stream_start",
            timestamp=time.time(),
            sample_rate=16000,
            codec="pcm16",
            chunk_ms=40,
        )
        d = evt.to_dict()
        assert d["component"] == "tts"
        assert d["event"] == "stream_start"
        assert "waveform_stats" in d

    def test_jitter_calculation(self):
        diag = TTSDiagnostics()
        diag._chunk_times = [40, 42, 38, 41, 39]  # Very low jitter
        jitter = diag._compute_jitter()
        assert jitter < 5  # Should be ~1.4ms

        diag._chunk_times = [10, 80, 10, 80]  # High jitter
        jitter = diag._compute_jitter()
        assert jitter > 30

    def test_clipping_detection_in_chunk(self):
        diag = TTSDiagnostics()
        # Create clipping audio
        audio = struct.pack("<100h", *([32767] * 100))
        evt = diag.on_chunk_sent(chunk_bytes=audio, sample_rate=16000)
        assert evt.waveform_clipping_pct > 0.0
        assert evt.waveform_peak > 0.99


# ============================================================================
# VQA Diagnostics
# ============================================================================

class TestVQADiagnostics:
    """Tests for VQADiagnostics class."""

    @pytest.mark.asyncio
    async def test_preflight_no_pipeline(self):
        diag = VQADiagnostics()
        result = await diag.preflight(vqa_pipeline=None, capture_frame_fn=None)
        assert result.status == "skipped"
        assert result.skip_code == VQASkipCode.SKIP_MODEL_LOAD.value

    @pytest.mark.asyncio
    async def test_preflight_with_mock_pipeline(self):
        mock_pipeline = MagicMock()
        mock_pipeline.process = AsyncMock(return_value=MagicMock())
        diag = VQADiagnostics()
        result = await diag.preflight(vqa_pipeline=mock_pipeline)
        assert result.model_loaded is True
        assert result.frame_ok is True  # Uses synthetic frame

    @pytest.mark.asyncio
    async def test_preflight_camera_timeout(self):
        async def slow_capture():
            await asyncio.sleep(10)
            return None

        diag = VQADiagnostics()
        result = await diag.preflight(
            vqa_pipeline=MagicMock(),
            capture_frame_fn=slow_capture,
            warmup_timeout_s=1.0,
        )
        assert result.skip_code == VQASkipCode.SKIP_TIMEOUT.value

    @pytest.mark.asyncio
    async def test_preflight_camera_empty_frame(self):
        async def empty_capture():
            return None

        diag = VQADiagnostics()
        result = await diag.preflight(
            vqa_pipeline=MagicMock(),
            capture_frame_fn=empty_capture,
        )
        assert result.skip_code == VQASkipCode.SKIP_NO_FRAME.value

    @pytest.mark.asyncio
    async def test_preflight_ready(self):
        """Full end-to-end preflight with mock pipeline passes."""
        mock_pipeline = MagicMock()
        mock_pipeline.process = AsyncMock(return_value=MagicMock())

        # Mock frame with shape
        mock_frame = MagicMock()
        mock_frame.shape = (480, 640, 3)
        mock_frame.dtype = type("dtype", (), {"__str__": lambda self: "uint8"})()

        async def good_capture():
            return mock_frame

        diag = VQADiagnostics()
        result = await diag.preflight(
            vqa_pipeline=mock_pipeline,
            capture_frame_fn=good_capture,
            warmup_timeout_s=5.0,
        )
        assert result.status == "ready"
        assert result.frame_ok is True
        assert result.model_loaded is True
        assert result.warmup_ms >= 0

    def test_skip_codes_have_remediation(self):
        from shared.utils.runtime_diagnostics import SKIP_REMEDIATION
        for code in VQASkipCode:
            assert code in SKIP_REMEDIATION, f"Missing remediation for {code}"

    def test_result_to_dict(self):
        result = VQAPreflightResult(status="ready", message="OK")
        d = result.to_dict()
        assert d["component"] == "vqa"
        assert d["status"] == "ready"
        assert "metrics" in d
        assert "timestamp" in d


# ============================================================================
# RuntimeDiagnostics (Orchestrator)
# ============================================================================

class TestRuntimeDiagnostics:
    """Tests for RuntimeDiagnostics orchestrator."""

    @pytest.mark.asyncio
    async def test_full_preflight_ok(self):
        mock_pipeline = MagicMock()
        mock_pipeline.process = AsyncMock(return_value=MagicMock())

        diag = RuntimeDiagnostics()
        status = await diag.run_all_preflight(
            vqa_pipeline=mock_pipeline,
            tts_sample_rate=44100,
            tts_codec="mp3",
        )
        assert status.system_status in ("OK", "WARN")
        assert status.tts is not None
        assert status.vqa is not None
        assert status.startup_time_ms >= 0

    @pytest.mark.asyncio
    async def test_full_preflight_error(self):
        diag = RuntimeDiagnostics()
        status = await diag.run_all_preflight(
            vqa_pipeline=None,
            tts_sample_rate=99999,  # Invalid
        )
        assert status.system_status == "ERROR"

    @pytest.mark.asyncio
    async def test_system_status_to_json(self):
        diag = RuntimeDiagnostics()
        status = await diag.run_all_preflight(tts_sample_rate=16000)
        j = status.to_json()
        parsed = json.loads(j)
        assert "system_status" in parsed
        assert "components" in parsed
        assert "tts" in parsed["components"]
        assert "vqa" in parsed["components"]

    def test_handle_tts_breaking(self):
        diag = RuntimeDiagnostics()
        diag._system_status = SystemStatus(
            tts=TTSPreflightResult(ready=True, sample_rate=44100)
        )
        result = diag.handle_tts_breaking()
        assert "debug_json" in result
        assert "human_explanation" in result
        assert "action_list" in result
        assert len(result["action_list"]) == 3


class TestSingleton:
    """Tests for the get_diagnostics singleton."""

    def test_returns_same_instance(self):
        d1 = get_diagnostics()
        d2 = get_diagnostics()
        assert d1 is d2

    def test_is_runtime_diagnostics(self):
        d = get_diagnostics()
        assert isinstance(d, RuntimeDiagnostics)
