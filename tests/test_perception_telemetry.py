"""
Tests for perception_telemetry.py
==================================
Covers FrameLog schema, JSON emission, MetricsAccumulator,
and degraded-latency meta tracking.
"""

from __future__ import annotations

import json
import logging

import pytest

from application.pipelines.perception_telemetry import (
    DetectionEntry,
    FrameLog,
    MetaEntry,
    MetricsAccumulator,
    QREntry,
    TTSEntry,
    emit_frame_log,
    get_metrics,
)


# ---------------------------------------------------------------------------
# FrameLog Schema
# ---------------------------------------------------------------------------

class TestFrameLogSchema:
    """Verify FrameLog produces valid JSON with all mandatory fields."""

    def test_all_fields_present(self):
        log = FrameLog(frame_id="test_001", device="cpu", venv=True)
        d = log.to_dict()
        required_keys = {"ts", "frame_id", "device", "venv", "num_dets",
                          "detections", "qr", "tts", "errors", "meta"}
        assert required_keys.issubset(d.keys())

    def test_json_serialisable(self):
        log = FrameLog(
            frame_id="test_002",
            device="cuda",
            venv=True,
            num_dets=2,
            detections=[
                DetectionEntry(label="person", conf=0.85, bbox=[10, 20, 100, 200]),
                DetectionEntry(label="chair", conf=0.55, bbox=[200, 50, 300, 350]),
            ],
            qr=QREntry(found=True, decoded="https://example.com", method="pyzbar"),
            tts=TTSEntry(last_output="Two people ahead.", engine="local", latency_ms=45),
        )
        j = log.to_json()
        parsed = json.loads(j)
        assert parsed["frame_id"] == "test_002"
        assert parsed["num_dets"] == 2
        assert len(parsed["detections"]) == 2
        assert parsed["qr"]["found"] is True
        assert parsed["tts"]["engine"] == "local"

    def test_default_timestamp_set(self):
        log = FrameLog(frame_id="test_003")
        assert log.ts != ""
        assert "T" in log.ts  # ISO 8601

    def test_meta_fields(self):
        meta = MetaEntry(
            conflicts=[{"original_label": "bottle", "alternative": "smartphone"}],
            alerts=[{"type": "repeated_misclassification"}],
            degraded_latency=True,
            tts_fallback=True,
        )
        log = FrameLog(frame_id="test_004", meta=meta)
        d = log.to_dict()
        assert d["meta"]["degraded_latency"] is True
        assert d["meta"]["tts_fallback"] is True
        assert len(d["meta"]["conflicts"]) == 1
        assert len(d["meta"]["alerts"]) == 1


# ---------------------------------------------------------------------------
# Emit
# ---------------------------------------------------------------------------

class TestEmitFrameLog:

    def test_emit_does_not_raise(self):
        log = FrameLog(frame_id="emit_test")
        # Should not raise even if logger is unconfigured
        emit_frame_log(log)

    def test_emit_logs_json(self, caplog):
        log = FrameLog(frame_id="emit_log_test", num_dets=3)
        with caplog.at_level(logging.INFO, logger="perception-telemetry"):
            emit_frame_log(log)
        assert any("emit_log_test" in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# MetricsAccumulator
# ---------------------------------------------------------------------------

class TestMetricsAccumulator:

    def test_initial_state(self):
        m = MetricsAccumulator()
        assert m.total_frames == 0
        assert m.avg_latency_ms == 0.0
        assert m.misclassification_rate == 0.0

    def test_record_frames(self):
        m = MetricsAccumulator(window=10)
        m.record_frame(100.0)
        m.record_frame(200.0)
        assert m.total_frames == 2
        assert m.avg_latency_ms == pytest.approx(150.0)

    def test_degraded_count(self):
        m = MetricsAccumulator()
        m.record_frame(100.0, degraded=False)
        m.record_frame(300.0, degraded=True)
        assert m.degraded_frames == 1

    def test_tts_failures(self):
        m = MetricsAccumulator()
        m.record_tts_failure()
        m.record_tts_failure()
        assert m.tts_failures == 2

    def test_misclassification_rate(self):
        m = MetricsAccumulator()
        m.record_frame(100.0)
        m.record_frame(100.0)
        m.record_misclass_alert()
        assert m.misclassification_rate == pytest.approx(0.5)

    def test_to_dict(self):
        m = MetricsAccumulator()
        m.record_frame(120.0, degraded=True)
        m.record_tts_failure()
        d = m.to_dict()
        assert d["total_frames_processed"] == 1
        assert d["degraded_latency_frames"] == 1
        assert d["tts_failures"] == 1
        assert "avg_latency_ms" in d
        assert "misclassification_rate" in d

    def test_rolling_window(self):
        m = MetricsAccumulator(window=3)
        m.record_frame(100.0)
        m.record_frame(200.0)
        m.record_frame(300.0)
        m.record_frame(400.0)  # first (100) should be evicted
        assert m.avg_latency_ms == pytest.approx(300.0)


# ---------------------------------------------------------------------------
# Degraded Latency Meta
# ---------------------------------------------------------------------------

class TestDegradedLatencyMeta:

    def test_degraded_latency_flag(self):
        """FrameLog should carry degraded_latency=true when set."""
        meta = MetaEntry(degraded_latency=True)
        log = FrameLog(frame_id="degrade_test", meta=meta)
        d = log.to_dict()
        assert d["meta"]["degraded_latency"] is True

    def test_not_degraded_by_default(self):
        log = FrameLog(frame_id="normal_test")
        d = log.to_dict()
        assert d["meta"]["degraded_latency"] is False
