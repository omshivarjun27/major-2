"""NFR: Debug Endpoint Access Control — verifies /debug/* endpoints require auth."""

from __future__ import annotations

import os
import sys

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class TestDebugAccessControl:
    """Verify debug endpoints are gated behind auth.

    Tests the require_debug_auth dependency directly rather than through
    TestClient to avoid module-level caching and version-specific issues.
    """

    def test_require_debug_auth_exists(self):
        """api_server should export a require_debug_auth dependency."""
        import inspect

        from api_server import require_debug_auth
        assert inspect.iscoroutinefunction(require_debug_auth)

    def test_debug_disabled_raises_403(self, monkeypatch):
        """When DEBUG_ENDPOINTS_ENABLED=false, dependency should raise 403."""
        monkeypatch.setattr("api_server._DEBUG_ENABLED", False)
        monkeypatch.setattr("api_server._DEBUG_TOKEN", "some-token")

        import asyncio

        from api_server import require_debug_auth
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                require_debug_auth(authorization="Bearer some-token")
            )
        assert exc_info.value.status_code == 403

    def test_missing_token_raises_401(self, monkeypatch):
        """Missing Bearer token should raise 401."""
        monkeypatch.setattr("api_server._DEBUG_ENABLED", True)
        monkeypatch.setattr("api_server._DEBUG_TOKEN", "correct-token")

        import asyncio

        from api_server import require_debug_auth
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                require_debug_auth(authorization=None)
            )
        assert exc_info.value.status_code == 401

    def test_wrong_token_raises_401(self, monkeypatch):
        """Wrong Bearer token should raise 401."""
        monkeypatch.setattr("api_server._DEBUG_ENABLED", True)
        monkeypatch.setattr("api_server._DEBUG_TOKEN", "correct-token")

        import asyncio

        from api_server import require_debug_auth
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                require_debug_auth(authorization="Bearer wrong-token")
            )
        assert exc_info.value.status_code == 401

    def test_correct_token_succeeds(self, monkeypatch):
        """Correct Bearer token should not raise."""
        monkeypatch.setattr("api_server._DEBUG_ENABLED", True)
        monkeypatch.setattr("api_server._DEBUG_TOKEN", "correct-token")

        import asyncio

        from api_server import require_debug_auth

        # Should NOT raise
        result = asyncio.get_event_loop().run_until_complete(
            require_debug_auth(authorization="Bearer correct-token")
        )
        # require_debug_auth returns None on success
        assert result is None

    def test_debug_endpoints_have_auth_dependency(self):
        """All /debug/* and /logs/* routes should have require_debug_auth dependency."""
        from api_server import app, require_debug_auth

        debug_routes = [
            r for r in app.routes
            if hasattr(r, "path") and (
                r.path.startswith("/debug/") or r.path.startswith("/logs/")
            )
        ]
        assert len(debug_routes) > 0, "No /debug/ or /logs/ routes found"

        for route in debug_routes:
            deps = getattr(route, "dependencies", [])
            dep_callables = [d.dependency for d in deps]
            assert require_debug_auth in dep_callables, \
                f"Route {route.path} missing require_debug_auth dependency"

    def test_health_has_no_auth_dependency(self):
        """The /health endpoint should NOT have auth dependency."""
        from api_server import app, require_debug_auth

        health_routes = [
            r for r in app.routes
            if hasattr(r, "path") and r.path == "/health"
        ]
        assert len(health_routes) > 0
        for route in health_routes:
            deps = getattr(route, "dependencies", [])
            dep_callables = [d.dependency for d in deps]
            assert require_debug_auth not in dep_callables
