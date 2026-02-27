"""Tests for infrastructure.resilience.retry_policy module."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from infrastructure.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    clear_registry,
    register_circuit_breaker,
)
from infrastructure.resilience.retry_policy import (
    RetryConfig,
    RetryPolicy,
    get_retry_policy,
    with_retry,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean_registry():
    clear_registry()
    yield
    clear_registry()


# ---------------------------------------------------------------------------
# Basic retry behaviour
# ---------------------------------------------------------------------------

class TestRetryPolicy:
    """Core retry logic."""

    async def test_no_retry_on_success(self):
        call_count = 0

        async def fn() -> str:
            nonlocal call_count
            call_count += 1
            return "ok"

        policy = RetryPolicy(RetryConfig(max_retries=3, base_delay_s=0.01))
        result = await policy.execute(fn)
        assert result == "ok"
        assert call_count == 1

    async def test_retries_on_transient_error(self):
        call_count = 0

        async def fn() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("transient")
            return "recovered"

        policy = RetryPolicy(RetryConfig(max_retries=3, base_delay_s=0.01))
        result = await policy.execute(fn, service_name="test")
        assert result == "recovered"
        assert call_count == 3

    async def test_raises_after_max_retries(self):
        async def fn() -> str:
            raise ConnectionError("always fails")

        policy = RetryPolicy(RetryConfig(max_retries=2, base_delay_s=0.01))
        with pytest.raises(ConnectionError, match="always fails"):
            await policy.execute(fn, service_name="test")

    async def test_no_retry_on_permanent_error(self):
        """Permanent errors (e.g. from 400 status) should not be retried."""
        call_count = 0

        class FakeHTTPError(Exception):
            def __init__(self):
                self.response = type("R", (), {"status_code": 400})()

        async def fn() -> str:
            nonlocal call_count
            call_count += 1
            raise FakeHTTPError()

        policy = RetryPolicy(RetryConfig(max_retries=3, base_delay_s=0.01))
        with pytest.raises(FakeHTTPError):
            await policy.execute(fn, service_name="test")
        assert call_count == 1  # No retries

    async def test_no_retry_on_auth_error(self):
        """Auth errors (401/403) should not be retried."""
        call_count = 0

        class FakeAuthError(Exception):
            def __init__(self):
                self.response = type("R", (), {"status_code": 401})()

        async def fn() -> str:
            nonlocal call_count
            call_count += 1
            raise FakeAuthError()

        policy = RetryPolicy(RetryConfig(max_retries=3, base_delay_s=0.01))
        with pytest.raises(FakeAuthError):
            await policy.execute(fn, service_name="test")
        assert call_count == 1

    async def test_zero_retries_means_no_retry(self):
        call_count = 0

        async def fn() -> str:
            nonlocal call_count
            call_count += 1
            raise ConnectionError("fail")

        policy = RetryPolicy(RetryConfig(max_retries=0))
        with pytest.raises(ConnectionError):
            await policy.execute(fn)
        assert call_count == 1


# ---------------------------------------------------------------------------
# Circuit breaker integration
# ---------------------------------------------------------------------------

class TestRetryWithCircuitBreaker:
    """Retry skips when circuit breaker is open."""

    async def test_skips_retry_when_circuit_open(self):
        # Register and trip a circuit breaker
        cb = register_circuit_breaker(
            "cb-retry-test",
            config=CircuitBreakerConfig(failure_threshold=1, reset_timeout_s=60),
        )
        await cb.trip()

        call_count = 0

        async def fn() -> str:
            nonlocal call_count
            call_count += 1
            raise ConnectionError("fail")

        policy = RetryPolicy(RetryConfig(max_retries=3, base_delay_s=0.01))
        with pytest.raises(ConnectionError):
            await policy.execute(fn, service_name="cb-retry-test")
        assert call_count == 1  # No retries because circuit is open

    async def test_circuit_breaker_open_error_not_retried(self):
        async def fn() -> str:
            raise CircuitBreakerOpenError("svc", 0.0)

        policy = RetryPolicy(RetryConfig(max_retries=3, base_delay_s=0.01))
        with pytest.raises(CircuitBreakerOpenError):
            await policy.execute(fn)


# ---------------------------------------------------------------------------
# Backoff computation
# ---------------------------------------------------------------------------

class TestBackoffComputation:
    """Exponential backoff with jitter."""

    async def test_delay_increases_exponentially(self):
        policy = RetryPolicy(RetryConfig(
            max_retries=3,
            base_delay_s=0.1,
            max_delay_s=10.0,
            jitter_factor=0.0,  # No jitter for predictable testing
        ))
        d1 = policy._compute_delay(1, 1.0)
        d2 = policy._compute_delay(2, 1.0)
        d3 = policy._compute_delay(3, 1.0)
        assert d1 == pytest.approx(0.1, abs=0.01)
        assert d2 == pytest.approx(0.2, abs=0.01)
        assert d3 == pytest.approx(0.4, abs=0.01)

    async def test_delay_capped_at_max(self):
        policy = RetryPolicy(RetryConfig(
            base_delay_s=1.0,
            max_delay_s=5.0,
            jitter_factor=0.0,
        ))
        d = policy._compute_delay(10, 1.0)
        assert d <= 5.0

    async def test_backoff_multiplier_applied(self):
        policy = RetryPolicy(RetryConfig(
            base_delay_s=1.0,
            max_delay_s=100.0,
            jitter_factor=0.0,
        ))
        d_normal = policy._compute_delay(1, 1.0)
        d_triple = policy._compute_delay(1, 3.0)
        assert d_triple == pytest.approx(d_normal * 3.0, abs=0.01)


# ---------------------------------------------------------------------------
# Per-service configs
# ---------------------------------------------------------------------------

class TestServiceConfigs:
    """get_retry_policy returns service-specific configs."""

    def test_deepgram_config(self):
        policy = get_retry_policy("deepgram")
        assert policy.config.max_retries == 2
        assert policy.config.base_delay_s == 0.5

    def test_ollama_config(self):
        policy = get_retry_policy("ollama_reasoning")
        assert policy.config.max_retries == 3
        assert policy.config.base_delay_s == 1.0

    def test_tavus_config(self):
        policy = get_retry_policy("tavus")
        assert policy.config.max_retries == 1

    def test_unknown_service_gets_defaults(self):
        policy = get_retry_policy("unknown_service")
        assert policy.config.max_retries == 3  # default


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------

class TestRetryDecorator:
    """@with_retry decorator."""

    async def test_decorator_retries(self):
        call_count = 0

        @with_retry("deepgram", max_retries=2, base_delay_s=0.01)
        async def my_fn() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("transient")
            return "ok"

        result = await my_fn()
        assert result == "ok"
        assert call_count == 2

    async def test_decorator_preserves_name(self):
        @with_retry("test")
        async def important_fn() -> None:
            pass

        assert important_fn.__name__ == "important_fn"

    async def test_decorator_exposes_metadata(self):
        @with_retry("deepgram", max_retries=5)
        async def my_fn() -> None:
            pass

        assert my_fn.retry_service == "deepgram"  # type: ignore[attr-defined]
        assert my_fn.retry_config.max_retries == 5  # type: ignore[attr-defined]
