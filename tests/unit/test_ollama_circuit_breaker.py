"""Tests for Ollama LLM circuit breaker integration.

Validates that OllamaHandler correctly wires the shared circuit breaker
and retry policy from infrastructure.resilience.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from infrastructure.resilience.circuit_breaker import (
    CircuitBreakerState,
    clear_registry,
    get_circuit_breaker,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_registry():
    """Reset the global circuit breaker registry between tests."""
    clear_registry()
    yield
    clear_registry()


@pytest.fixture
def mock_config():
    """Mock config to avoid needing real API keys or Ollama running."""
    config = {
        "OLLAMA_VL_API_KEY": "test-key",
        "OLLAMA_VL_MODEL_ID": "test-model",
        "MAX_TOKENS": 100,
        "TEMPERATURE": 0.0,
        "LLM_MAX_RETRIES": 3,
        "LLM_BACKOFF_BASE": 0.01,
        "LLM_MAX_CONNECTIONS": 5,
        "LLM_MAX_KEEPALIVE": 2,
    }
    timeout_cfg = {"connect": 5, "read": 30, "total": 60}
    with (
        patch(
            "infrastructure.llm.ollama.handler.get_config",
            return_value=config,
        ),
        patch(
            "infrastructure.llm.ollama.handler.get_llm_timeout_config",
            return_value=timeout_cfg,
        ),
    ):
        yield config


def _make_handler():
    """Import and instantiate OllamaHandler (import inside to respect mocks)."""
    from infrastructure.llm.ollama.handler import OllamaHandler

    return OllamaHandler()


def _mock_success_response(payload: dict | None = None) -> MagicMock:
    """Return a mock httpx.Response for a successful API call."""
    if payload is None:
        payload = {
            "choices": [
                {
                    "message": {
                        "content": '{"model_choice": "QWEN", "analysis": ""}'
                    }
                }
            ]
        }
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = payload
    return resp


# ---------------------------------------------------------------------------
# Tests — Initialisation
# ---------------------------------------------------------------------------


class TestOllamaCircuitBreakerInit:
    """Circuit breaker registration on handler init."""

    async def test_cb_registered_on_init(self, mock_config: dict) -> None:
        handler = _make_handler()
        assert handler._cb is not None
        cb = get_circuit_breaker("ollama")
        assert cb is not None
        assert cb.state is CircuitBreakerState.CLOSED
        await handler.close()

    async def test_retry_policy_assigned(self, mock_config: dict) -> None:
        handler = _make_handler()
        assert handler._retry_policy is not None
        assert handler._retry_policy.config.max_retries == 3
        await handler.close()

    async def test_missing_api_key_sets_cb_none(self) -> None:
        config = {
            "OLLAMA_VL_API_KEY": "",
            "OLLAMA_VL_MODEL_ID": "m",
            "MAX_TOKENS": 100,
            "TEMPERATURE": 0.0,
        }
        timeout_cfg = {"connect": 5, "read": 30, "total": 60}
        with (
            patch(
                "infrastructure.llm.ollama.handler.get_config",
                return_value=config,
            ),
            patch(
                "infrastructure.llm.ollama.handler.get_llm_timeout_config",
                return_value=timeout_cfg,
            ),
        ):
            handler = _make_handler()
            assert handler._cb is None
            assert handler._retry_policy is None
            assert handler.is_ready is False

    async def test_init_exception_sets_cb_none(self) -> None:
        with patch(
            "infrastructure.llm.ollama.handler.get_config",
            side_effect=RuntimeError("boom"),
        ):
            handler = _make_handler()
            assert handler._cb is None
            assert handler._retry_policy is None
            assert handler.is_ready is False


# ---------------------------------------------------------------------------
# Tests — Request routing
# ---------------------------------------------------------------------------


class TestOllamaRequestRouting:
    """Verify requests flow through CB → retry → HTTP."""

    async def test_successful_request_keeps_circuit_closed(
        self, mock_config: dict
    ) -> None:
        handler = _make_handler()
        handler._verified = True

        mock_resp = _mock_success_response()
        handler.client = AsyncMock()
        handler.client.post = AsyncMock(return_value=mock_resp)

        # Bypass image processing — focus on HTTP/CB flow
        with patch.object(
            handler, "_convert_and_optimize_image",
            new_callable=AsyncMock, return_value="dGVzdA==",
        ):
            choice, analysis, error = await handler.model_choice_with_analysis(
                MagicMock(), "test"
            )

        assert error is None
        assert handler._cb.failure_count == 0
        assert handler._cb.state is CircuitBreakerState.CLOSED
        await handler.close()

    async def test_transient_failure_records_cb_failure(
        self, mock_config: dict
    ) -> None:
        handler = _make_handler()
        handler._verified = True

        handler.client = AsyncMock()
        handler.client.post = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        with patch.object(
            handler, "_convert_and_optimize_image",
            new_callable=AsyncMock, return_value="dGVzdA==",
        ):
            _choice, _analysis, error = await handler.model_choice_with_analysis(
                MagicMock(), "test"
            )

        assert error is not None
        # After retries exhausted, CB should have recorded failures
        assert handler._cb.failure_count > 0
        await handler.close()

    async def test_repeated_failures_trip_circuit(
        self, mock_config: dict
    ) -> None:
        handler = _make_handler()
        handler._verified = True

        handler.client = AsyncMock()
        handler.client.post = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        with patch.object(
            handler, "_convert_and_optimize_image",
            new_callable=AsyncMock, return_value="dGVzdA==",
        ):
            await handler.model_choice_with_analysis(MagicMock(), "test")

        assert handler._cb.state is CircuitBreakerState.OPEN
        await handler.close()

    async def test_open_circuit_fast_fails(self, mock_config: dict) -> None:
        handler = _make_handler()
        handler._verified = True

        # Manually trip the circuit
        await handler._cb.trip()
        assert handler._cb.state is CircuitBreakerState.OPEN

        handler.client = AsyncMock()
        handler.client.post = AsyncMock(return_value=_mock_success_response())

        with patch.object(
            handler, "_convert_and_optimize_image",
            new_callable=AsyncMock, return_value="dGVzdA==",
        ):
            _choice, _analysis, error = await handler.model_choice_with_analysis(
                MagicMock(), "test"
            )

        # Should fail fast — the HTTP client should NOT have been called
        assert error is not None
        assert "OPEN" in error or "circuit" in error.lower()
        handler.client.post.assert_not_called()
        await handler.close()


# ---------------------------------------------------------------------------
# Tests — Health endpoint
# ---------------------------------------------------------------------------


class TestOllamaHealth:
    """Validate the health() snapshot."""

    async def test_health_includes_cb_snapshot(self, mock_config: dict) -> None:
        handler = _make_handler()
        health = handler.health()

        assert "is_ready" in health
        assert "verified" in health
        assert "circuit_breaker" in health
        assert health["circuit_breaker"] is not None
        assert health["circuit_breaker"]["state"] == "closed"
        assert health["circuit_breaker"]["service"] == "ollama"
        await handler.close()

    async def test_health_cb_none_when_not_initialised(self) -> None:
        config = {
            "OLLAMA_VL_API_KEY": "",
            "OLLAMA_VL_MODEL_ID": "m",
            "MAX_TOKENS": 100,
            "TEMPERATURE": 0.0,
        }
        timeout_cfg = {"connect": 5, "read": 30, "total": 60}
        with (
            patch(
                "infrastructure.llm.ollama.handler.get_config",
                return_value=config,
            ),
            patch(
                "infrastructure.llm.ollama.handler.get_llm_timeout_config",
                return_value=timeout_cfg,
            ),
        ):
            handler = _make_handler()
            health = handler.health()
            assert health["circuit_breaker"] is None

    async def test_health_reflects_open_state(self, mock_config: dict) -> None:
        handler = _make_handler()
        await handler._cb.trip()

        health = handler.health()
        assert health["circuit_breaker"]["state"] == "open"
        await handler.close()


# ---------------------------------------------------------------------------
# Tests — _make_request isolation
# ---------------------------------------------------------------------------


class TestMakeRequest:
    """Low-level _make_request method."""

    async def test_make_request_raises_on_http_error(
        self, mock_config: dict
    ) -> None:
        handler = _make_handler()

        error_response = MagicMock(spec=httpx.Response)
        error_response.status_code = 500
        error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=error_response,
        )

        handler.client = AsyncMock()
        handler.client.post = AsyncMock(return_value=error_response)

        with pytest.raises(httpx.HTTPStatusError):
            await handler._make_request("/chat/completions", json={})

        await handler.close()

    async def test_make_request_returns_response_on_success(
        self, mock_config: dict
    ) -> None:
        handler = _make_handler()

        mock_resp = _mock_success_response()
        handler.client = AsyncMock()
        handler.client.post = AsyncMock(return_value=mock_resp)

        result = await handler._make_request("/chat/completions", json={})
        assert result.status_code == 200
        await handler.close()


# ---------------------------------------------------------------------------
# Tests — Fallback path (no CB initialised)
# ---------------------------------------------------------------------------


class TestFallbackWithoutCB:
    """When CB is None, requests go directly without resilience."""

    async def test_direct_call_when_cb_none(self, mock_config: dict) -> None:
        handler = _make_handler()
        handler._cb = None
        handler._retry_policy = None

        mock_resp = _mock_success_response()
        handler.client = AsyncMock()
        handler.client.post = AsyncMock(return_value=mock_resp)

        result = await handler._request_with_retry(
            "/chat/completions", json={}
        )
        assert result.status_code == 200
        handler.client.post.assert_called_once()
        await handler.close()
