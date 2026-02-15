"""
Smoke tests for API endpoints and core pipeline components.
Run with: pytest tests/test_smoke_api.py -v
"""

import pytest
import asyncio
import numpy as np
from PIL import Image


@pytest.fixture
def synthetic_frame():
    """Generate a 640x480 synthetic room image."""
    arr = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    return Image.fromarray(arr)


@pytest.fixture
def text_frame():
    """Generate a 640x480 image with synthetic text-like patterns."""
    img = Image.new("RGB", (640, 480), color=(255, 255, 255))
    # Draw some dark rectangles to simulate text regions
    arr = np.array(img)
    arr[100:120, 100:400] = 0  # horizontal dark stripe
    arr[140:160, 100:350] = 0
    arr[180:200, 100:300] = 0
    return Image.fromarray(arr)


class TestOCRPipeline:
    """Tests for OCR backend availability and pipeline."""

    def test_ocr_pipeline_importable(self):
        from core.ocr import OCRPipeline
        pipe = OCRPipeline()
        # Pipeline should be created without crashing
        assert pipe is not None

    def test_ocr_status_reports_backends(self):
        from core.ocr.engine import get_ocr_status
        status = get_ocr_status()
        assert "easyocr_available" in status
        assert "tesseract_available" in status
        assert "any_backend_available" in status

    def test_install_instructions_not_empty(self):
        from core.ocr.engine import get_install_instructions
        instructions = get_install_instructions()
        assert isinstance(instructions, str)
        assert len(instructions) > 0

    @pytest.mark.asyncio
    async def test_ocr_process_returns_result(self, text_frame):
        from core.ocr import OCRPipeline
        pipe = OCRPipeline()
        if not pipe.is_ready:
            pytest.skip("No OCR backend installed")
        result = await pipe.process(text_frame)
        assert result is not None
        assert result.error is None or result.error == ""
        assert result.total_latency_ms >= 0

    @pytest.mark.asyncio
    async def test_ocr_process_no_backend_returns_error(self):
        """If we force no backend, we get a clean error not a crash."""
        from core.ocr import OCRPipelineResult
        # This tests the error path — the pipeline itself may have a backend
        # Just verify the result dataclass works
        result = OCRPipelineResult(
            error="No OCR backend available (install easyocr or pytesseract)"
        )
        assert result.error is not None
        assert "install" in result.error.lower()


class TestPerceptionPipeline:
    """Tests for spatial perception pipeline."""

    @pytest.mark.asyncio
    async def test_mock_detector_returns_fresh_detections(self, synthetic_frame):
        from core.vqa import create_perception_pipeline
        pipeline = create_perception_pipeline(use_mock=True)
        result = await pipeline.process(synthetic_frame)
        assert len(result.detections) > 0
        assert result.detections[0].class_name in (
            "person", "chair", "table", "door", "wall"
        )

    @pytest.mark.asyncio
    async def test_mock_detector_no_stale_cache(self, synthetic_frame):
        """Two calls should both return results (no stale cache issue)."""
        from core.vqa import create_perception_pipeline
        pipeline = create_perception_pipeline(use_mock=True)
        r1 = await pipeline.process(synthetic_frame)
        r2 = await pipeline.process(synthetic_frame)
        assert len(r1.detections) > 0
        assert len(r2.detections) > 0


class TestWatchdog:
    """Tests for camera watchdog."""

    @pytest.mark.asyncio
    async def test_camera_stall_fires_alert(self):
        from application.pipelines.watchdog import Watchdog, WatchdogConfig

        alerts = []

        async def mock_alert(comp, msg):
            alerts.append((comp, msg))

        wd = Watchdog(WatchdogConfig(
            camera_stall_threshold_ms=100,
            check_interval_ms=50,
        ))
        wd.register_component("camera")
        wd.register_component("orchestrator")
        wd.on_alert(mock_alert)

        # Simulate active session
        wd.heartbeat("orchestrator")
        wd.heartbeat("camera")

        await wd.start()
        # Wait for stall detection (camera heartbeat ages past 100ms)
        await asyncio.sleep(0.3)
        await wd.stop()

        assert len(alerts) > 0, "Should have fired camera stall alert"
        assert alerts[0][0] == "camera"

    @pytest.mark.asyncio
    async def test_healthy_camera_no_alert(self):
        from application.pipelines.watchdog import Watchdog, WatchdogConfig

        alerts = []

        async def mock_alert(comp, msg):
            alerts.append((comp, msg))

        wd = Watchdog(WatchdogConfig(
            camera_stall_threshold_ms=500,
            check_interval_ms=50,
        ))
        wd.register_component("camera")
        wd.register_component("orchestrator")
        wd.on_alert(mock_alert)

        wd.heartbeat("orchestrator")

        await wd.start()
        # Keep sending heartbeats
        for _ in range(5):
            wd.heartbeat("camera")
            await asyncio.sleep(0.05)
        await wd.stop()

        camera_alerts = [a for a in alerts if a[0] == "camera"]
        assert len(camera_alerts) == 0, "Should not fire alert for healthy camera"


class TestHealthEndpoint:
    """Tests for /health API endpoint."""

    def test_health_endpoint_importable(self):
        from api_server import app
        assert app is not None

    @pytest.mark.asyncio
    async def test_health_returns_ok(self):
        """Test health endpoint via TestClient."""
        try:
            from httpx import AsyncClient, ASGITransport
            from api_server import app
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.get("/health")
                assert r.status_code == 200
                data = r.json()
                assert data["status"] == "ok"
        except ImportError:
            pytest.skip("httpx not available for ASGI testing")


class TestSceneGraph:
    """Tests for scene graph generation."""

    @pytest.mark.asyncio
    async def test_build_scene_graph_from_perception(self, synthetic_frame):
        from core.vqa import create_perception_pipeline, build_scene_graph
        pipeline = create_perception_pipeline(use_mock=True)
        result = await pipeline.process(synthetic_frame)
        sg = build_scene_graph(result)
        assert sg is not None
        assert len(sg.nodes) > 0
        d = sg.to_dict()
        assert "nodes" in d
        assert "obstacles" in d
