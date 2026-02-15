"""
Tests for memory_engine extensions — CloudSyncAdapter, EventDetector.
"""

from __future__ import annotations

import numpy as np
import pytest

# ── CloudSyncAdapter ──────────────────────────────────────────────────

from core.memory.cloud_sync import (
    CloudSyncAdapter,
    CloudSyncConfig,
    SyncRecord,
    StubCloudBackend,
)


class TestCloudSyncConfig:
    def test_defaults(self):
        cfg = CloudSyncConfig()
        assert cfg.enabled is False
        assert cfg.provider == "stub"
        assert cfg.batch_size == 50

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("CLOUD_SYNC", "false")
        cfg = CloudSyncConfig.from_env()
        assert cfg.enabled is False


class TestStubCloudBackend:
    @pytest.mark.asyncio
    async def test_connect(self):
        backend = StubCloudBackend()
        assert await backend.connect() is True

    @pytest.mark.asyncio
    async def test_upsert(self):
        backend = StubCloudBackend()
        await backend.connect()
        records = [
            SyncRecord(record_id="r1", embedding=np.random.randn(384).astype(np.float32)),
            SyncRecord(record_id="r2", embedding=np.random.randn(384).astype(np.float32)),
        ]
        count = await backend.upsert(records)
        assert count == 2

    @pytest.mark.asyncio
    async def test_search(self):
        backend = StubCloudBackend()
        await backend.connect()
        emb = np.random.randn(384).astype(np.float32)
        await backend.upsert([SyncRecord(record_id="r1", embedding=emb)])
        results = await backend.search(emb, k=5)
        assert len(results) >= 1
        assert results[0]["record_id"] == "r1"

    @pytest.mark.asyncio
    async def test_delete(self):
        backend = StubCloudBackend()
        await backend.connect()
        emb = np.random.randn(384).astype(np.float32)
        await backend.upsert([SyncRecord(record_id="r1", embedding=emb)])
        count = await backend.delete(["r1"])
        assert count == 1

    def test_health(self):
        backend = StubCloudBackend()
        h = backend.health()
        assert h["provider"] == "stub"


class TestCloudSyncAdapter:
    def test_init_disabled(self):
        adapter = CloudSyncAdapter(CloudSyncConfig(enabled=False))
        assert adapter.enabled is False

    @pytest.mark.asyncio
    async def test_start_disabled(self):
        adapter = CloudSyncAdapter(CloudSyncConfig(enabled=False))
        result = await adapter.start()
        assert result is False

    @pytest.mark.asyncio
    async def test_start_stop_enabled(self):
        adapter = CloudSyncAdapter(CloudSyncConfig(enabled=True, provider="stub"))
        result = await adapter.start()
        assert result is True
        await adapter.stop()

    @pytest.mark.asyncio
    async def test_enqueue_and_search(self):
        adapter = CloudSyncAdapter(CloudSyncConfig(enabled=True, provider="stub", batch_size=2))
        await adapter.start()
        emb = np.random.randn(384).astype(np.float32)
        await adapter.enqueue([SyncRecord(record_id="r1", embedding=emb)])
        await adapter.enqueue([SyncRecord(record_id="r2", embedding=np.random.randn(384).astype(np.float32))])
        # After flushing (batch_size=2), should be searchable
        results = await adapter.search_cloud(emb, k=5)
        await adapter.stop()
        assert isinstance(results, list)

    def test_health(self):
        adapter = CloudSyncAdapter(CloudSyncConfig(enabled=False))
        h = adapter.health()
        assert "enabled" in h


# ── EventDetector ─────────────────────────────────────────────────────

from core.memory.event_detection import (
    EventDetector,
    EventDetectorConfig,
    DetectedEvent,
    EventCategory,
)


class TestEventDetectorConfig:
    def test_defaults(self):
        cfg = EventDetectorConfig()
        assert cfg.min_confidence == 0.3
        assert cfg.auto_summarize is True


class TestEventDetector:
    def test_init(self):
        det = EventDetector()
        assert det is not None

    def test_process_empty_scene(self):
        det = EventDetector()
        events = det.process_scene({})
        assert events == []

    def test_detect_obstacle(self):
        det = EventDetector()
        scene = {
            "objects": [
                {"label": "car", "distance_m": 2.0, "confidence": 0.8},
            ],
        }
        events = det.process_scene(scene)
        assert len(events) >= 1
        assert events[0].category == EventCategory.OBSTACLE

    def test_detect_face(self):
        det = EventDetector()
        scene = {
            "faces": [{"name": "Alice", "confidence": 0.9}],
        }
        events = det.process_scene(scene)
        assert len(events) >= 1
        assert events[0].category == EventCategory.FACE

    def test_detect_audio_event(self):
        det = EventDetector()
        scene = {
            "audio_events": [
                {"event_type": "car_horn", "confidence": 0.7, "is_critical": True},
            ],
        }
        events = det.process_scene(scene)
        assert len(events) >= 1
        assert events[0].category == EventCategory.SAFETY

    def test_detect_qr_code(self):
        det = EventDetector()
        scene = {
            "qr_codes": [{"data": "https://example.com", "type": "qr"}],
        }
        events = det.process_scene(scene)
        assert len(events) >= 1
        assert events[0].category == EventCategory.QR_CODE

    def test_detect_landmark(self):
        det = EventDetector()
        scene = {
            "narration": "There is a crosswalk ahead with a traffic light.",
        }
        events = det.process_scene(scene)
        assert len(events) >= 1
        assert events[0].category == EventCategory.LANDMARK

    def test_auto_summary(self):
        det = EventDetector()
        scene = {
            "objects": [{"label": "car", "distance_m": 2.0, "confidence": 0.8}],
            "narration": "Approaching an intersection.",
        }
        det.process_scene(scene)
        summary = det.get_auto_summary()
        assert summary is not None
        assert "Recent scene summary" in summary

    def test_event_to_dict(self):
        ev = DetectedEvent(
            event_id="evt_1",
            category=EventCategory.OBSTACLE,
            summary="Obstacle: car at 2.0m",
            confidence=0.8,
            timestamp_ms=1000,
        )
        d = ev.to_dict()
        assert d["category"] == "obstacle"
        assert d["should_memorize"] is True

    def test_suppression(self):
        det = EventDetector(EventDetectorConfig(obstacle_repeat_window_s=999))
        scene = {
            "objects": [{"label": "car", "distance_m": 2.0, "confidence": 0.8}],
        }
        events1 = det.process_scene(scene)
        events2 = det.process_scene(scene)
        # Second call should be suppressed (same obstacle within window)
        assert len(events2) == 0

    def test_health(self):
        det = EventDetector()
        h = det.health()
        assert "events_detected" in h
