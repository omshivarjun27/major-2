"""Tests for Tavus circuit breaker integration.

Validates that TavusAdapter correctly wires the circuit breaker for
silent degradation when the Tavus API is unavailable.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from infrastructure.resilience.circuit_breaker import (
    CircuitBreakerState,
    clear_registry,
    get_circuit_breaker,
)
from infrastructure.tavus.adapter import (
    TavusAdapter,
    TavusConfig,
    _TAVUS_CB_CONFIG,
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
def enabled_config() -> TavusConfig:
    """Config with Tavus enabled."""
    return TavusConfig(
        enabled=True,
        api_key="test-key",
        replica_id="test-replica",
        persona_id="test-persona",
    )


@pytest.fixture
def disabled_config() -> TavusConfig:
    """Config with Tavus disabled."""
    return TavusConfig(enabled=False)


# ---------------------------------------------------------------------------
# Tests — Initialization
# ---------------------------------------------------------------------------


class TestTavusCircuitBreakerInit:
    """Circuit breaker registration on adapter init."""

    async def test_cb_registered_when_enabled(self, enabled_config: TavusConfig) -> None:
        """Circuit breaker is registered when Tavus is enabled."""
        adapter = TavusAdapter(config=enabled_config)
        assert adapter._cb is not None
        cb = get_circuit_breaker("tavus")
        assert cb is not None
        assert cb.state is CircuitBreakerState.CLOSED

    async def test_cb_not_registered_when_disabled(
        self, disabled_config: TavusConfig
    ) -> None:
        """Circuit breaker is NOT registered when Tavus is disabled (no overhead)."""
        adapter = TavusAdapter(config=disabled_config)
        assert adapter._cb is None
        cb = get_circuit_breaker("tavus")
        assert cb is None

    async def test_cb_config_values(self, enabled_config: TavusConfig) -> None:
        """Circuit breaker uses correct conservative thresholds."""
        adapter = TavusAdapter(config=enabled_config)
        assert adapter._cb is not None
        assert adapter._cb.config.failure_threshold == 2
        assert adapter._cb.config.reset_timeout_s == 60.0


# ---------------------------------------------------------------------------
# Tests — Connect with circuit breaker
# ---------------------------------------------------------------------------


class TestConnectWithCircuitBreaker:
    """Connect method respects circuit breaker state."""

    async def test_connect_disabled_returns_false(
        self, disabled_config: TavusConfig
    ) -> None:
        """Connect returns False when disabled (no CB check needed)."""
        adapter = TavusAdapter(config=disabled_config)
        result = await adapter.connect()
        assert result is False

    async def test_connect_open_circuit_fast_fails(
        self, enabled_config: TavusConfig
    ) -> None:
        """Connect returns False immediately when circuit is open."""
        adapter = TavusAdapter(config=enabled_config)

        # Manually trip the circuit
        await adapter._cb.trip()
        assert adapter._is_circuit_open() is True

        # Connect should fast-fail without making any HTTP calls
        result = await adapter.connect()
        assert result is False

    async def test_connect_success_records_success(
        self, enabled_config: TavusConfig
    ) -> None:
        """Successful connect resets failure count."""
        adapter = TavusAdapter(config=enabled_config)

        # Simulate a prior failure
        adapter._cb._failure_count = 1

        # Mock successful API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "conversation_id": "conv-123",
            "conversation_url": "",
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await adapter.connect()

        assert result is True
        assert adapter._cb._failure_count == 0

    async def test_connect_failure_records_failure(
        self, enabled_config: TavusConfig
    ) -> None:
        """Failed connect increments failure count."""
        adapter = TavusAdapter(config=enabled_config)
        assert adapter._cb._failure_count == 0

        # Mock failed API response
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Server Error")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await adapter.connect()

        assert result is False
        assert adapter._cb._failure_count == 1

    async def test_connect_repeated_failures_trip_circuit(
        self, enabled_config: TavusConfig
    ) -> None:
        """Repeated connect failures trip the circuit."""
        adapter = TavusAdapter(config=enabled_config)

        # Mock failed API response
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Server Error")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            await adapter.connect()  # First failure
            await adapter.connect()  # Second failure -> trips circuit

        assert adapter._cb.state is CircuitBreakerState.OPEN


# ---------------------------------------------------------------------------
# Tests — Send narration with circuit breaker
# ---------------------------------------------------------------------------


class TestSendNarrationWithCircuitBreaker:
    """send_narration respects circuit breaker state."""

    async def test_send_disabled_returns_false(
        self, disabled_config: TavusConfig
    ) -> None:
        """send_narration returns False when disabled."""
        adapter = TavusAdapter(config=disabled_config)
        result = await adapter.send_narration("Hello")
        assert result is False

    async def test_send_open_circuit_fast_fails(
        self, enabled_config: TavusConfig
    ) -> None:
        """send_narration returns False immediately when circuit is open."""
        adapter = TavusAdapter(config=enabled_config)
        await adapter._cb.trip()

        result = await adapter.send_narration("Hello")
        assert result is False

    async def test_send_ws_success_records_success(
        self, enabled_config: TavusConfig
    ) -> None:
        """Successful WS send records success."""
        adapter = TavusAdapter(config=enabled_config)
        adapter._cb._failure_count = 1

        # Mock WebSocket
        mock_ws = AsyncMock()
        mock_ws.closed = False
        mock_ws.send_str = AsyncMock()
        adapter._ws = mock_ws

        result = await adapter.send_narration("Hello")
        assert result is True
        assert adapter._cb._failure_count == 0

    async def test_send_ws_failure_records_failure(
        self, enabled_config: TavusConfig
    ) -> None:
        """Failed WS send records failure."""
        adapter = TavusAdapter(config=enabled_config)

        # Mock WebSocket that raises on send
        mock_ws = AsyncMock()
        mock_ws.closed = False
        mock_ws.send_str = AsyncMock(side_effect=Exception("WS error"))
        adapter._ws = mock_ws

        result = await adapter.send_narration("Hello")
        assert result is False
        assert adapter._cb._failure_count == 1


# ---------------------------------------------------------------------------
# Tests — REST send with circuit breaker
# ---------------------------------------------------------------------------


class TestRestSendWithCircuitBreaker:
    """_send_rest respects circuit breaker state."""

    async def test_rest_send_open_circuit_fast_fails(
        self, enabled_config: TavusConfig
    ) -> None:
        """_send_rest returns False immediately when circuit is open."""
        adapter = TavusAdapter(config=enabled_config)
        adapter._conversation_id = "conv-123"
        await adapter._cb.trip()

        result = await adapter._send_rest("Hello")
        assert result is False

    async def test_rest_send_success_records_success(
        self, enabled_config: TavusConfig
    ) -> None:
        """Successful REST send records success."""
        adapter = TavusAdapter(config=enabled_config)
        adapter._conversation_id = "conv-123"
        adapter._cb._failure_count = 1

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await adapter._send_rest("Hello")

        assert result is True
        assert adapter._cb._failure_count == 0

    async def test_rest_send_failure_records_failure(
        self, enabled_config: TavusConfig
    ) -> None:
        """Failed REST send records failure."""
        adapter = TavusAdapter(config=enabled_config)
        adapter._conversation_id = "conv-123"

        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_response):
            with patch("aiohttp.ClientSession", return_value=mock_session):
                result = await adapter._send_rest("Hello")

        assert result is False
        assert adapter._cb._failure_count == 1


# ---------------------------------------------------------------------------
# Tests — Health endpoint
# ---------------------------------------------------------------------------


class TestHealthWithCircuitBreaker:
    """Health endpoint includes circuit breaker state."""

    async def test_health_includes_cb_when_enabled(
        self, enabled_config: TavusConfig
    ) -> None:
        """Health includes circuit breaker snapshot when enabled."""
        adapter = TavusAdapter(config=enabled_config)
        health = adapter.health()

        assert "circuit_breaker" in health
        assert health["circuit_breaker"] is not None
        assert health["circuit_breaker"]["state"] == "closed"
        assert health["circuit_breaker"]["service"] == "tavus"

    async def test_health_cb_none_when_disabled(
        self, disabled_config: TavusConfig
    ) -> None:
        """Health shows circuit_breaker=None when disabled."""
        adapter = TavusAdapter(config=disabled_config)
        health = adapter.health()

        assert health["circuit_breaker"] is None

    async def test_health_reflects_open_state(
        self, enabled_config: TavusConfig
    ) -> None:
        """Health reflects open circuit state."""
        adapter = TavusAdapter(config=enabled_config)
        await adapter._cb.trip()

        health = adapter.health()
        assert health["circuit_breaker"]["state"] == "open"


# ---------------------------------------------------------------------------
# Tests — Silent degradation
# ---------------------------------------------------------------------------


class TestSilentDegradation:
    """Circuit breaker enables silent degradation."""

    async def test_degraded_adapter_returns_false_silently(
        self, enabled_config: TavusConfig
    ) -> None:
        """When circuit is open, all methods return False without error."""
        adapter = TavusAdapter(config=enabled_config)
        await adapter._cb.trip()

        # All these should return False silently, no exceptions
        assert await adapter.connect() is False
        assert await adapter.send_narration("Test") is False

        # No conversation_id, so this returns False anyway
        adapter._conversation_id = "conv-123"
        assert await adapter._send_rest("Test") is False

    async def test_circuit_recovers_after_timeout(
        self, enabled_config: TavusConfig
    ) -> None:
        """Circuit transitions to half-open after reset timeout."""
        # Clear registry first to ensure clean state
        clear_registry()

        # Manually register with fast timeout before creating adapter
        from infrastructure.resilience.circuit_breaker import CircuitBreakerConfig, register_circuit_breaker
        fast_cb_config = CircuitBreakerConfig(
            failure_threshold=2,
            reset_timeout_s=0.1,  # 100ms for testing
        )
        cb = register_circuit_breaker("tavus", config=fast_cb_config)

        # Now create adapter - it will get the existing CB from registry
        fast_config = TavusConfig(
            enabled=True,
            api_key="test",
            replica_id="test",
        )
        adapter = TavusAdapter(config=fast_config)
        # The adapter should have picked up our pre-registered CB
        assert adapter._cb is cb

        # Trip the circuit
        await adapter._cb.trip()
        assert adapter._cb.state is CircuitBreakerState.OPEN

        # Wait for timeout
        await asyncio.sleep(0.15)
        assert adapter._cb.state is CircuitBreakerState.HALF_OPEN
