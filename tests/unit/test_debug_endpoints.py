"""
Unit tests — Debug & Braille API Endpoints
=============================================

Tests FastAPI debug endpoints using httpx test client.
Debug-gated endpoints require DEBUG_ENDPOINTS_ENABLED=true and a valid token.
"""

import os
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """Create TestClient with debug endpoints enabled and auth token set."""
    os.environ["DEBUG_ENDPOINTS_ENABLED"] = "true"
    os.environ["DEBUG_AUTH_TOKEN"] = "test-debug-token-12345"

    # Reload the module-level variables in api_server
    import importlib
    import api_server
    importlib.reload(api_server)
    from api_server import app

    return TestClient(app)


@pytest.fixture(scope="module")
def auth_headers():
    """Bearer token header for debug-gated endpoints."""
    return {"Authorization": "Bearer test-debug-token-12345"}


class TestHealthEndpoints:

    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_health_camera(self, client):
        resp = client.get("/health/camera")
        assert resp.status_code == 200

    def test_health_orchestrator(self, client):
        resp = client.get("/health/orchestrator")
        assert resp.status_code == 200

    def test_health_workers(self, client):
        resp = client.get("/health/workers")
        assert resp.status_code == 200


class TestDebugEndpoints:

    def test_debug_perception_frame(self, client, auth_headers):
        resp = client.post("/debug/perception_frame", headers=auth_headers)
        assert resp.status_code == 200

    def test_debug_stale_check(self, client, auth_headers):
        resp = client.post("/debug/stale_check", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "stale_frame_risk_points" in data

    def test_debug_braille_frame(self, client, auth_headers):
        resp = client.get("/debug/braille_frame", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data

    def test_debug_ocr_install(self, client, auth_headers):
        resp = client.get("/debug/ocr_install", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "easyocr_available" in data or "error" in data


class TestMemoryConsent:

    def test_consent_opt_in(self, client):
        resp = client.post("/memory/consent", json={"opt_in": True, "device_id": "test_device"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["consent_recorded"] is True, f"Unexpected response: {data}"
        assert "timestamp" in data
        assert "current_settings" in data
        assert data["current_settings"]["memory_enabled"] is True

    def test_consent_opt_out(self, client):
        resp = client.post("/memory/consent", json={"opt_in": False, "device_id": "test_out_device"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["consent_recorded"] is True, f"Unexpected response: {data}"
        assert data["current_settings"]["memory_enabled"] is False


class TestBrailleEndpoint:

    def test_braille_read(self, client):
        resp = client.post("/braille/read")
        assert resp.status_code == 200


class TestSessionLogs:

    def test_create_session(self, client, auth_headers):
        resp = client.post("/logs/session", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data

    def test_list_sessions(self, client, auth_headers):
        resp = client.get("/logs/sessions", headers=auth_headers)
        assert resp.status_code == 200
