"""
NFR Test #127 — Access Control Fuzzing
========================================

Fuzzes debug endpoints with invalid credentials, malformed headers,
and boundary inputs to verify access control holds.
"""

import os
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """Create test client with debug endpoints enabled."""
    os.environ["DEBUG_ENDPOINTS_ENABLED"] = "true"
    os.environ["DEBUG_AUTH_TOKEN"] = "correct-token-xyz"

    import importlib
    import api_server
    importlib.reload(api_server)
    from api_server import app
    return TestClient(app)


# Endpoints that require debug auth
DEBUG_ENDPOINTS = [
    ("POST", "/debug/perception_frame"),
    ("POST", "/debug/stale_check"),
    ("GET", "/debug/braille_frame"),
    ("GET", "/debug/ocr_install"),
    ("GET", "/logs/sessions"),
    ("POST", "/logs/session"),
]


class TestAccessControlFuzz:

    def test_no_auth_header_returns_401(self, client):
        """Requests without Authorization header should get 401."""
        for method, path in DEBUG_ENDPOINTS:
            resp = getattr(client, method.lower())(path)
            assert resp.status_code == 401, (
                f"{method} {path} returned {resp.status_code} without auth header"
            )

    def test_wrong_token_returns_401(self, client):
        """Requests with wrong token should get 401."""
        headers = {"Authorization": "Bearer wrong-token"}
        for method, path in DEBUG_ENDPOINTS:
            resp = getattr(client, method.lower())(path, headers=headers)
            assert resp.status_code == 401, (
                f"{method} {path} returned {resp.status_code} with wrong token"
            )

    def test_empty_bearer_returns_401(self, client):
        """Empty Bearer token should get 401."""
        headers = {"Authorization": "Bearer "}
        for method, path in DEBUG_ENDPOINTS:
            resp = getattr(client, method.lower())(path, headers=headers)
            assert resp.status_code == 401, (
                f"{method} {path} returned {resp.status_code} with empty Bearer"
            )

    def test_non_bearer_scheme_returns_401(self, client):
        """Using 'Basic' instead of 'Bearer' should get 401."""
        headers = {"Authorization": "Basic correct-token-xyz"}
        for method, path in DEBUG_ENDPOINTS:
            resp = getattr(client, method.lower())(path, headers=headers)
            assert resp.status_code == 401, (
                f"{method} {path} accepted non-Bearer auth scheme"
            )

    def test_correct_token_returns_200(self, client):
        """Requests with correct token should succeed."""
        headers = {"Authorization": "Bearer correct-token-xyz"}
        for method, path in DEBUG_ENDPOINTS:
            resp = getattr(client, method.lower())(path, headers=headers)
            assert resp.status_code == 200, (
                f"{method} {path} returned {resp.status_code} with correct token"
            )

    def test_debug_disabled_returns_403(self):
        """When DEBUG_ENDPOINTS_ENABLED=false, all debug endpoints return 403."""
        os.environ["DEBUG_ENDPOINTS_ENABLED"] = "false"
        os.environ["DEBUG_AUTH_TOKEN"] = "some-token"

        import importlib
        import api_server
        importlib.reload(api_server)
        from api_server import app
        c = TestClient(app)

        headers = {"Authorization": "Bearer some-token"}
        for method, path in DEBUG_ENDPOINTS:
            resp = getattr(c, method.lower())(path, headers=headers)
            assert resp.status_code == 403, (
                f"{method} {path} returned {resp.status_code} when debug disabled"
            )

        # Restore for other tests — must reload api_server too
        os.environ["DEBUG_ENDPOINTS_ENABLED"] = "true"
        os.environ["DEBUG_AUTH_TOKEN"] = "correct-token-xyz"
        importlib.reload(api_server)

    def test_sql_injection_in_token(self, client):
        """SQL injection patterns in token should be rejected."""
        payloads = [
            "' OR 1=1 --",
            "'; DROP TABLE users; --",
            "\" OR \"\"=\"",
            "<script>alert(1)</script>",
        ]
        for payload in payloads:
            headers = {"Authorization": f"Bearer {payload}"}
            for method, path in DEBUG_ENDPOINTS:
                resp = getattr(client, method.lower())(path, headers=headers)
                assert resp.status_code == 401, (
                    f"Injection payload accepted on {method} {path}: {payload}"
                )

    def test_health_endpoints_no_auth_required(self, client):
        """Health endpoints should NOT require authentication."""
        public_endpoints = ["/health", "/health/camera", "/health/orchestrator", "/health/workers"]
        for path in public_endpoints:
            resp = client.get(path)
            assert resp.status_code == 200, (
                f"Public endpoint {path} returned {resp.status_code} — should be 200"
            )
