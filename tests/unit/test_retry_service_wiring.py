"""Tests for retry policy service wiring.

Validates that retry policies are correctly wired into service adapters
and interact properly with circuit breakers.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from infrastructure.resilience.circuit_breaker import (
    clear_registry,
    register_circuit_breaker,
)
from infrastructure.resilience.retry_policy import (
    SERVICE_RETRY_CONFIGS,
    RetryConfig,
    RetryPolicy,
    get_retry_policy,
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


# ---------------------------------------------------------------------------
# Tests — Service configs exist
# ---------------------------------------------------------------------------


class TestServiceRetryConfigs:
    """Verify retry configs exist for all services."""

    def test_all_services_have_configs(self) -> None:
        """All expected services have retry configs."""
        expected_services = [
            "deepgram",
            "livekit",
            "ollama_reasoning",
            "ollama_embedding",
            "duckduckgo",
            "elevenlabs",
            "tavus",
        ]
        for service in expected_services:
            assert service in SERVICE_RETRY_CONFIGS, f"Missing config for {service}"

    def test_realtime_services_have_tight_retries(self) -> None:
        """Real-time services have fewer retries and shorter delays."""
        realtime_services = ["deepgram", "livekit", "elevenlabs"]
        for service in realtime_services:
            config = SERVICE_RETRY_CONFIGS[service]
            assert config.max_retries <= 2, f"{service} should have <= 2 retries"
            assert config.base_delay_s <= 1.0, f"{service} should have base delay <= 1s"

    def test_batch_services_have_more_retries(self) -> None:
        """Batch services have more patience."""
        batch_services = ["ollama_reasoning", "ollama_embedding", "duckduckgo"]
        for service in batch_services:
            config = SERVICE_RETRY_CONFIGS[service]
            assert config.max_retries >= 3, f"{service} should have >= 3 retries"

    def test_optional_services_have_minimal_retries(self) -> None:
        """Optional services have minimal retries."""
        config = SERVICE_RETRY_CONFIGS["tavus"]
        assert config.max_retries == 1, "Tavus should have minimal retries"


# ---------------------------------------------------------------------------
# Tests — Retry policy and circuit breaker interaction
# ---------------------------------------------------------------------------


class TestRetryCircuitBreakerInteraction:
    """Verify retries stop when circuit breaker is open."""

    async def test_retry_stops_when_circuit_open(self) -> None:
        """RetryPolicy stops retrying when circuit breaker is OPEN."""
        # Register a circuit breaker
        cb = register_circuit_breaker("test_service")

        # Create retry policy
        policy = RetryPolicy(RetryConfig(max_retries=3, base_delay_s=0.01))

        # Track call count
        call_count = 0

        async def failing_fn():
            nonlocal call_count
            call_count += 1
            # Trip circuit on second call
            if call_count == 2:
                await cb.trip()
            raise RuntimeError("Test error")

        # Execute should fail after circuit trips
        with pytest.raises(RuntimeError):
            await policy.execute(failing_fn, service_name="test_service")

        # Should have tried twice: initial + 1 retry before circuit tripped
        # Then stopped because circuit is open
        assert call_count == 2

    async def test_retry_continues_when_circuit_closed(self) -> None:
        """RetryPolicy continues retrying when circuit is CLOSED."""
        # Register a circuit breaker (stays closed)
        register_circuit_breaker("test_service")

        # Create retry policy with 2 retries
        policy = RetryPolicy(RetryConfig(max_retries=2, base_delay_s=0.01))

        call_count = 0

        async def eventually_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("Temporary error")
            return "success"

        result = await policy.execute(eventually_succeeds, service_name="test_service")

        assert result == "success"
        assert call_count == 3  # Initial + 2 retries

    async def test_circuit_breaker_open_error_not_retried(self) -> None:
        """CircuitBreakerOpenError is never retried."""
        from infrastructure.resilience.circuit_breaker import CircuitBreakerOpenError

        policy = RetryPolicy(RetryConfig(max_retries=3, base_delay_s=0.01))

        call_count = 0

        async def raises_cb_open():
            nonlocal call_count
            call_count += 1
            raise CircuitBreakerOpenError("test", 0.0)

        with pytest.raises(CircuitBreakerOpenError):
            await policy.execute(raises_cb_open)

        assert call_count == 1  # No retries


# ---------------------------------------------------------------------------
# Tests — Adapter wiring verification
# ---------------------------------------------------------------------------


class TestAdapterWiring:
    """Verify adapters have retry policy wired."""

    async def test_ollama_has_retry_policy(self) -> None:
        """Ollama handler has retry policy wired."""
        config = {
            "OLLAMA_VL_API_KEY": "test",
            "OLLAMA_VL_MODEL_ID": "test",
            "MAX_TOKENS": 100,
            "TEMPERATURE": 0.0,
        }
        timeout_cfg = {"connect": 5, "read": 30, "total": 60}

        with (
            patch("infrastructure.llm.ollama.handler.get_config", return_value=config),
            patch("infrastructure.llm.ollama.handler.get_llm_timeout_config", return_value=timeout_cfg),
        ):
            from infrastructure.llm.ollama.handler import OllamaHandler
            handler = OllamaHandler()

            assert handler._retry_policy is not None
            assert handler._retry_policy.config.max_retries == 3
            await handler.close()

    async def test_internet_search_has_retry_policy(self) -> None:
        """InternetSearch has retry policy wired."""
        with patch(
            "infrastructure.llm.internet_search.InternetSearch._initialize_search_tools"
        ):
            from infrastructure.llm.internet_search import InternetSearch
            search = InternetSearch()

            assert hasattr(search, "_retry_policy")
            assert search._retry_policy is not None
            assert search._retry_policy.config.max_retries == 3

    async def test_tts_manager_has_retry_policy(self) -> None:
        """TTSManager has retry policy wired."""
        from infrastructure.speech.elevenlabs.tts_manager import TTSManager

        mgr = TTSManager()

        assert hasattr(mgr, "_retry_policy")
        assert mgr._retry_policy is not None
        assert mgr._retry_policy.config.max_retries == 2

    async def test_tavus_adapter_has_retry_policy_when_enabled(self) -> None:
        """TavusAdapter has retry policy when enabled."""
        from infrastructure.tavus.adapter import TavusAdapter, TavusConfig

        config = TavusConfig(
            enabled=True,
            api_key="test",
            replica_id="test",
        )
        adapter = TavusAdapter(config=config)

        assert adapter._retry_policy is not None
        assert adapter._retry_policy.config.max_retries == 1

    async def test_tavus_adapter_no_retry_policy_when_disabled(self) -> None:
        """TavusAdapter has no retry policy when disabled."""
        from infrastructure.tavus.adapter import TavusAdapter, TavusConfig

        config = TavusConfig(enabled=False)
        adapter = TavusAdapter(config=config)

        assert adapter._retry_policy is None


# ---------------------------------------------------------------------------
# Tests — get_retry_policy function
# ---------------------------------------------------------------------------


class TestGetRetryPolicy:
    """Test get_retry_policy helper."""

    def test_returns_policy_for_known_service(self) -> None:
        """Returns properly configured policy for known services."""
        policy = get_retry_policy("deepgram")
        assert policy.config.max_retries == 2
        assert policy.config.base_delay_s == 0.5

    def test_returns_default_for_unknown_service(self) -> None:
        """Returns default policy for unknown services."""
        policy = get_retry_policy("unknown_service")
        # Should use RetryConfig defaults
        assert policy.config.max_retries == 3
        assert policy.config.base_delay_s == 1.0
