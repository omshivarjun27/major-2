"""
Integration Tests for VQA API
=============================
"""

import base64
import io
import sys

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

sys.path.insert(0, str(__file__).rsplit("\\", 2)[0])


# ============================================================================
# Test App Setup
# ============================================================================

def create_test_app():
    """Create FastAPI app for testing."""
    from fastapi import FastAPI

    from core.vqa.api_endpoints import init_vqa_api, router

    app = FastAPI(title="VQA Test App")
    app.include_router(router)

    # Initialize with mock detector
    init_vqa_api(
        llm_client=None,  # No LLM for tests
        use_mock_detector=True,
    )

    return app


@pytest.fixture
def app():
    """Create test app fixture."""
    return create_test_app()


@pytest.fixture
def client(app):
    """Create async test client (sync fixture to avoid pytest-asyncio FixtureDef bug)."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
def sample_image_base64():
    """Create sample base64 encoded image."""
    img = Image.new("RGB", (640, 480), color=(128, 128, 128))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


# ============================================================================
# Health Endpoint Tests
# ============================================================================

class TestHealthEndpoint:
    """Tests for /vqa/health endpoint."""

    @pytest.mark.asyncio
    async def test_health_returns_200(self, client):
        response = await client.get("/vqa/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_response_structure(self, client):
        response = await client.get("/vqa/health")
        data = response.json()

        assert "status" in data
        assert "perception_ready" in data
        assert "memory_entries" in data


# ============================================================================
# Perception Endpoint Tests
# ============================================================================

class TestPerceptionEndpoint:
    """Tests for /vqa/perception/frame endpoint."""

    @pytest.mark.asyncio
    async def test_perception_returns_200(self, client, sample_image_base64):
        response = await client.post(
            "/vqa/perception/frame",
            json={"image_base64": sample_image_base64},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_perception_response_structure(self, client, sample_image_base64):
        response = await client.post(
            "/vqa/perception/frame",
            json={"image_base64": sample_image_base64},
        )
        data = response.json()

        assert "session_id" in data
        assert "timestamp" in data
        assert "detections" in data
        assert "obstacles" in data
        assert "summary" in data
        assert "processing_time_ms" in data

    @pytest.mark.asyncio
    async def test_perception_detections_structure(self, client, sample_image_base64):
        response = await client.post(
            "/vqa/perception/frame",
            json={"image_base64": sample_image_base64},
        )
        data = response.json()

        for det in data["detections"]:
            assert "id" in det
            assert "class" in det
            assert "confidence" in det
            assert "bbox" in det
            assert 0 <= det["confidence"] <= 1

    @pytest.mark.asyncio
    async def test_perception_obstacles_structure(self, client, sample_image_base64):
        response = await client.post(
            "/vqa/perception/frame",
            json={"image_base64": sample_image_base64},
        )
        data = response.json()

        for obs in data["obstacles"]:
            assert "id" in obs
            assert "class" in obs
            assert "distance_m" in obs
            assert "direction" in obs
            assert "priority" in obs
            assert "action" in obs

    @pytest.mark.asyncio
    async def test_perception_with_session_id(self, client, sample_image_base64):
        response = await client.post(
            "/vqa/perception/frame",
            json={
                "image_base64": sample_image_base64,
                "session_id": "test_session_123",
            },
        )
        data = response.json()

        assert data["session_id"] == "test_session_123"

    @pytest.mark.asyncio
    async def test_perception_invalid_image(self, client):
        response = await client.post(
            "/vqa/perception/frame",
            json={"image_base64": "invalid_base64"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_perception_latency(self, client, sample_image_base64):
        import time
        start = time.time()

        response = await client.post(
            "/vqa/perception/frame",
            json={"image_base64": sample_image_base64},
        )

        elapsed_ms = (time.time() - start) * 1000
        data = response.json()

        # Processing time should be reported
        assert data["processing_time_ms"] > 0

        # Total request should be under 500ms (with mock detector)
        assert elapsed_ms < 500


# ============================================================================
# VQA Ask Endpoint Tests
# ============================================================================

class TestVQAAskEndpoint:
    """Tests for /vqa/ask endpoint."""

    @pytest.mark.asyncio
    async def test_ask_returns_200(self, client, sample_image_base64):
        response = await client.post(
            "/vqa/ask",
            json={
                "question": "What is ahead?",
                "image_base64": sample_image_base64,
            },
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_ask_response_structure(self, client, sample_image_base64):
        response = await client.post(
            "/vqa/ask",
            json={
                "question": "What obstacles are there?",
                "image_base64": sample_image_base64,
            },
        )
        data = response.json()

        assert "answer" in data
        assert "confidence" in data
        assert "source" in data
        assert "processing_time_ms" in data

    @pytest.mark.asyncio
    async def test_ask_without_image(self, client):
        response = await client.post(
            "/vqa/ask",
            json={
                "question": "Is the path clear?",
                "session_id": "existing_session",
            },
        )
        # Should work with fallback
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_ask_uses_fallback_without_llm(self, client, sample_image_base64):
        response = await client.post(
            "/vqa/ask",
            json={
                "question": "What is ahead?",
                "image_base64": sample_image_base64,
            },
        )
        data = response.json()

        # Without LLM client, should use fallback
        assert data["source"] in ["fallback", "error"]


# ============================================================================
# Session Endpoint Tests
# ============================================================================

class TestSessionEndpoints:
    """Tests for session-related endpoints."""

    @pytest.mark.asyncio
    async def test_replay_returns_404_for_unknown_session(self, client):
        response = await client.get("/vqa/session/unknown_session_123/replay")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_replay_after_perception(self, client, sample_image_base64):
        # First, create a perception entry
        session_id = "replay_test_session"
        await client.post(
            "/vqa/perception/frame",
            json={
                "image_base64": sample_image_base64,
                "session_id": session_id,
            },
        )

        # Then get replay
        response = await client.get(f"/vqa/session/{session_id}/replay")
        assert response.status_code == 200

        data = response.json()
        assert "session" in data
        assert "entries" in data
        assert len(data["entries"]) >= 1

    @pytest.mark.asyncio
    async def test_delete_session(self, client, sample_image_base64):
        session_id = "delete_test_session"

        # Create session
        await client.post(
            "/vqa/perception/frame",
            json={
                "image_base64": sample_image_base64,
                "session_id": session_id,
            },
        )

        # Delete session
        response = await client.delete(f"/vqa/session/{session_id}")
        assert response.status_code == 200

        # Verify deleted
        response = await client.get(f"/vqa/session/{session_id}/replay")
        assert response.status_code == 404


# ============================================================================
# Metrics Endpoint Tests
# ============================================================================

class TestMetricsEndpoint:
    """Tests for /vqa/metrics endpoint."""

    @pytest.mark.asyncio
    async def test_metrics_returns_200(self, client):
        response = await client.get("/vqa/metrics")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_metrics_response_structure(self, client):
        response = await client.get("/vqa/metrics")
        data = response.json()

        assert "avg_perception_ms" in data
        assert "avg_vqa_ms" in data
        assert "cache_hit_rate" in data
        assert "total_requests" in data


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
