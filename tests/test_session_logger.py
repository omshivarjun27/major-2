"""
Tests for SessionLogger
========================

Covers: create_session, log, get_events, list_sessions,
delete_session, ring-buffer eviction, disk flush, filtering.
"""

import json
import os
import sys
import tempfile
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from apps.cli.session_logger import SessionEvent, SessionLogger


# ============================================================================
# SessionEvent
# ============================================================================


class TestSessionEvent:
    def test_creation(self):
        evt = SessionEvent(
            ts=1000.0,
            event_type="perception",
            payload={"detections": 3},
        )
        assert evt.ts == 1000.0
        assert evt.event_type == "perception"
        assert evt.error is None

    def test_to_dict_minimal(self):
        evt = SessionEvent(ts=1000.0, event_type="vqa", payload={"answer": "hello"})
        d = evt.to_dict()
        assert d["ts"] == 1000.0
        assert d["event_type"] == "vqa"
        assert "latency_ms" not in d
        assert "error" not in d

    def test_to_dict_with_latency_and_error(self):
        evt = SessionEvent(
            ts=1000.0,
            event_type="tts",
            payload={},
            latency_ms=42.567,
            error="TTS failed",
        )
        d = evt.to_dict()
        assert d["latency_ms"] == 42.6
        assert d["error"] == "TTS failed"


# ============================================================================
# SessionLogger
# ============================================================================


class TestSessionLogger:
    def test_create_session(self):
        sl = SessionLogger()
        sid = sl.create_session()
        assert sid.startswith("sess_")
        assert len(sid) == 17  # "sess_" + 12 hex chars

    def test_create_multiple_sessions(self):
        sl = SessionLogger()
        s1 = sl.create_session()
        s2 = sl.create_session()
        assert s1 != s2

    def test_log_and_get_events(self):
        sl = SessionLogger()
        sid = sl.create_session()
        sl.log(sid, "perception", {"count": 5}, latency_ms=30.0)
        sl.log(sid, "vqa", {"answer": "a chair"})
        events = sl.get_events(sid)
        assert len(events) == 2
        assert events[0]["event_type"] == "perception"
        assert events[1]["event_type"] == "vqa"

    def test_log_auto_creates_session(self):
        """Logging to unknown session auto-creates buffer."""
        sl = SessionLogger()
        sl.log("unknown_session", "test", {"data": 1})
        events = sl.get_events("unknown_session")
        assert len(events) == 1

    def test_get_events_filter_by_type(self):
        sl = SessionLogger()
        sid = sl.create_session()
        sl.log(sid, "perception", {"a": 1})
        sl.log(sid, "vqa", {"b": 2})
        sl.log(sid, "perception", {"c": 3})
        events = sl.get_events(sid, event_type="perception")
        assert len(events) == 2
        assert all(e["event_type"] == "perception" for e in events)

    def test_get_events_limit(self):
        sl = SessionLogger()
        sid = sl.create_session()
        for i in range(20):
            sl.log(sid, "test", {"i": i})
        events = sl.get_events(sid, limit=5)
        assert len(events) == 5
        # Should be the LAST 5 events
        assert events[0]["payload"]["i"] == 15

    def test_get_events_unknown_session(self):
        sl = SessionLogger()
        events = sl.get_events("nonexistent")
        assert events == []

    def test_ring_buffer_eviction(self):
        sl = SessionLogger(max_events=5)
        sid = sl.create_session()
        for i in range(10):
            sl.log(sid, "test", {"i": i})
        events = sl.get_events(sid)
        assert len(events) == 5
        # Only last 5 events survive
        assert events[0]["payload"]["i"] == 5
        assert events[-1]["payload"]["i"] == 9

    def test_list_sessions(self):
        sl = SessionLogger()
        s1 = sl.create_session()
        s2 = sl.create_session()
        sl.log(s1, "a", {"x": 1})
        sl.log(s1, "b", {"x": 2})
        sl.log(s2, "c", {"x": 3})
        sessions = sl.list_sessions()
        assert len(sessions) == 2
        ids = {s["session_id"] for s in sessions}
        assert s1 in ids and s2 in ids
        for s in sessions:
            if s["session_id"] == s1:
                assert s["event_count"] == 2
            else:
                assert s["event_count"] == 1

    def test_list_sessions_empty(self):
        sl = SessionLogger()
        assert sl.list_sessions() == []

    def test_delete_session(self):
        sl = SessionLogger()
        sid = sl.create_session()
        sl.log(sid, "test", {})
        assert sl.delete_session(sid) is True
        assert sl.get_events(sid) == []
        assert sl.list_sessions() == []

    def test_delete_nonexistent(self):
        sl = SessionLogger()
        assert sl.delete_session("nope") is False

    def test_disk_flush(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sl = SessionLogger(log_dir=tmpdir)
            sid = sl.create_session()
            sl.log(sid, "perception", {"count": 1}, latency_ms=10.0)
            sl.log(sid, "vqa", {"answer": "yes"})

            logfile = os.path.join(tmpdir, f"{sid}.jsonl")
            assert os.path.exists(logfile)

            with open(logfile, "r", encoding="utf-8") as f:
                lines = f.readlines()
            assert len(lines) == 2
            first = json.loads(lines[0])
            assert first["event_type"] == "perception"
            second = json.loads(lines[1])
            assert second["event_type"] == "vqa"

    def test_event_ts_is_monotonic(self):
        sl = SessionLogger()
        sid = sl.create_session()
        sl.log(sid, "a", {})
        time.sleep(0.01)
        sl.log(sid, "b", {})
        events = sl.get_events(sid)
        assert events[1]["ts"] >= events[0]["ts"]
