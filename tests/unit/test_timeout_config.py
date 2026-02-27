"""
Unit tests for infrastructure/resilience/timeout_config.py

Tests timeout standardization utilities including:
- TimeoutConfig class
- get_timeout() helper
- with_async_timeout decorator
- with_timeout decorator
- run_with_timeout() function
- run_sync_with_timeout() function
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

from infrastructure.resilience.timeout_config import (
    AsyncTimeoutContext,
    TimeoutConfig,
    TimeoutError,
    get_timeout,
    get_timeout_config,
    reset_timeout_config,
    run_sync_with_timeout,
    run_with_timeout,
    with_async_timeout,
    with_timeout,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def reset_config():
    """Reset global timeout config before each test."""
    reset_timeout_config()
    yield
    reset_timeout_config()


# ============================================================================
# TimeoutConfig Tests
# ============================================================================


class TestTimeoutConfig:
    """Tests for TimeoutConfig dataclass."""

    def test_timeout_config_has_all_services(self):
        """TimeoutConfig should have all expected service timeout values."""
        config = TimeoutConfig()
        assert hasattr(config, "STT")
        assert hasattr(config, "TTS")
        assert hasattr(config, "LLM")
        assert hasattr(config, "SEARCH")
        assert hasattr(config, "AVATAR")
        assert hasattr(config, "LIVEKIT")
        assert hasattr(config, "DEFAULT")

    def test_timeout_config_default_values(self):
        """TimeoutConfig should have reasonable default values."""
        config = TimeoutConfig()
        assert config.STT > 0
        assert config.TTS > 0
        assert config.LLM > 0
        assert config.SEARCH > 0
        assert config.AVATAR > 0
        assert config.LIVEKIT > 0
        assert config.DEFAULT > 0

    def test_get_timeout_config_singleton(self):
        """get_timeout_config should return same instance."""
        config1 = get_timeout_config()
        config2 = get_timeout_config()
        assert config1 is config2

    def test_reset_timeout_config(self):
        """reset_timeout_config should clear cached instance."""
        config1 = get_timeout_config()
        reset_timeout_config()
        config2 = get_timeout_config()
        # New instance created after reset
        assert config1 is not config2


# ============================================================================
# get_timeout Tests
# ============================================================================


class TestGetTimeout:
    """Tests for get_timeout helper function."""

    def test_get_timeout_stt(self):
        """Should return STT timeout for 'stt' service."""
        timeout = get_timeout("stt")
        assert timeout > 0
        assert isinstance(timeout, float)

    def test_get_timeout_tts(self):
        """Should return TTS timeout for 'tts' service."""
        timeout = get_timeout("tts")
        assert timeout > 0

    def test_get_timeout_llm(self):
        """Should return LLM timeout for 'llm' service."""
        timeout = get_timeout("llm")
        assert timeout > 0

    def test_get_timeout_search(self):
        """Should return search timeout for 'search' service."""
        timeout = get_timeout("search")
        assert timeout > 0

    def test_get_timeout_avatar(self):
        """Should return avatar timeout for 'avatar' service."""
        timeout = get_timeout("avatar")
        assert timeout > 0

    def test_get_timeout_livekit(self):
        """Should return livekit timeout for 'livekit' service."""
        timeout = get_timeout("livekit")
        assert timeout > 0

    def test_get_timeout_default(self):
        """Should return default timeout for 'default' service."""
        timeout = get_timeout("default")
        assert timeout > 0

    def test_get_timeout_unknown_service_uses_default(self):
        """Unknown service should fallback to default timeout."""
        default_timeout = get_timeout("default")
        unknown_timeout = get_timeout("unknown_service_xyz")
        assert unknown_timeout == default_timeout

    def test_get_timeout_case_insensitive(self):
        """Service names should be case insensitive."""
        assert get_timeout("STT") == get_timeout("stt")
        assert get_timeout("TTS") == get_timeout("tts")
        assert get_timeout("LLM") == get_timeout("llm")


# ============================================================================
# TimeoutError Tests
# ============================================================================


class TestTimeoutError:
    """Tests for custom TimeoutError exception."""

    def test_timeout_error_basic(self):
        """Basic TimeoutError should work."""
        error = TimeoutError("Test timeout")
        assert "Test timeout" in str(error)

    def test_timeout_error_with_service(self):
        """TimeoutError with service should include service name."""
        error = TimeoutError("Timed out", service="stt")
        assert "stt" in str(error)
        assert error.service == "stt"

    def test_timeout_error_with_timeout_seconds(self):
        """TimeoutError with timeout_seconds should include duration."""
        error = TimeoutError("Timed out", timeout_seconds=5.0)
        assert "5.0s" in str(error)
        assert error.timeout_seconds == 5.0

    def test_timeout_error_with_all_fields(self):
        """TimeoutError with all fields should include all info."""
        error = TimeoutError("Timed out", service="tts", timeout_seconds=2.0)
        error_str = str(error)
        assert "tts" in error_str
        assert "2.0s" in error_str


# ============================================================================
# with_async_timeout Decorator Tests
# ============================================================================


class TestWithAsyncTimeout:
    """Tests for with_async_timeout decorator."""

    async def test_async_timeout_completes_before_timeout(self):
        """Function completing before timeout should return normally."""
        @with_async_timeout(timeout=1.0, service="test")
        async def fast_func():
            await asyncio.sleep(0.01)
            return "success"

        result = await fast_func()
        assert result == "success"

    async def test_async_timeout_raises_on_timeout(self):
        """Function exceeding timeout should raise TimeoutError."""
        @with_async_timeout(timeout=0.05, service="test")
        async def slow_func():
            await asyncio.sleep(1.0)
            return "should not reach"

        with pytest.raises(TimeoutError) as exc_info:
            await slow_func()
        assert "test" in str(exc_info.value)

    async def test_async_timeout_uses_service_timeout(self):
        """Should use service-specific timeout when timeout not specified."""
        @with_async_timeout(service="stt")
        async def stt_func():
            await asyncio.sleep(0.01)
            return "done"

        result = await stt_func()
        assert result == "done"

    async def test_async_timeout_with_fallback(self):
        """Should call on_timeout callback and return its value."""
        @with_async_timeout(timeout=0.05, service="test", on_timeout=lambda: "fallback")
        async def slow_func():
            await asyncio.sleep(1.0)
            return "should not reach"

        result = await slow_func()
        assert result == "fallback"

    async def test_async_timeout_preserves_function_name(self):
        """Decorated function should preserve original name."""
        @with_async_timeout(timeout=1.0)
        async def my_function():
            pass

        assert my_function.__name__ == "my_function"

    async def test_async_timeout_passes_args(self):
        """Should correctly pass positional and keyword arguments."""
        @with_async_timeout(timeout=1.0)
        async def add(a, b, extra=0):
            return a + b + extra

        result = await add(1, 2, extra=3)
        assert result == 6


# ============================================================================
# with_timeout Decorator Tests
# ============================================================================


class TestWithTimeout:
    """Tests for with_timeout decorator (sync functions)."""

    def test_sync_timeout_completes_before_timeout(self):
        """Function completing before timeout should return normally."""
        @with_timeout(timeout=1.0, service="test")
        def fast_func():
            time.sleep(0.01)
            return "success"

        result = fast_func()
        assert result == "success"

    def test_sync_timeout_raises_on_timeout(self):
        """Function exceeding timeout should raise TimeoutError."""
        @with_timeout(timeout=0.1, service="test")
        def slow_func():
            time.sleep(2.0)
            return "should not reach"

        with pytest.raises(TimeoutError) as exc_info:
            slow_func()
        assert "test" in str(exc_info.value)

    def test_sync_timeout_with_fallback(self):
        """Should call on_timeout callback and return its value."""
        @with_timeout(timeout=0.1, service="test", on_timeout=lambda: "fallback")
        def slow_func():
            time.sleep(2.0)
            return "should not reach"

        result = slow_func()
        assert result == "fallback"

    def test_sync_timeout_preserves_function_name(self):
        """Decorated function should preserve original name."""
        @with_timeout(timeout=1.0)
        def my_function():
            pass

        assert my_function.__name__ == "my_function"


# ============================================================================
# run_with_timeout Tests
# ============================================================================


class TestRunWithTimeout:
    """Tests for run_with_timeout utility function."""

    async def test_run_with_timeout_success(self):
        """Successful coroutine should return its result."""
        async def quick_coro():
            await asyncio.sleep(0.01)
            return "done"

        result = await run_with_timeout(quick_coro(), timeout=1.0)
        assert result == "done"

    async def test_run_with_timeout_raises_on_timeout(self):
        """Slow coroutine should raise TimeoutError."""
        async def slow_coro():
            await asyncio.sleep(2.0)
            return "should not reach"

        with pytest.raises(TimeoutError):
            await run_with_timeout(slow_coro(), timeout=0.05, service="test")

    async def test_run_with_timeout_returns_fallback(self):
        """Should return fallback value on timeout."""
        async def slow_coro():
            await asyncio.sleep(2.0)
            return "should not reach"

        result = await run_with_timeout(
            slow_coro(),
            timeout=0.05,
            fallback="fallback_value"
        )
        assert result == "fallback_value"

    async def test_run_with_timeout_uses_service_timeout(self):
        """Should use service-specific timeout."""
        async def quick_coro():
            await asyncio.sleep(0.01)
            return "done"

        result = await run_with_timeout(quick_coro(), service="search")
        assert result == "done"


# ============================================================================
# run_sync_with_timeout Tests
# ============================================================================


class TestRunSyncWithTimeout:
    """Tests for run_sync_with_timeout utility function."""

    def test_run_sync_with_timeout_success(self):
        """Successful function should return its result."""
        def quick_func(x, y):
            return x + y

        result = run_sync_with_timeout(quick_func, 1, 2, timeout=1.0)
        assert result == 3

    def test_run_sync_with_timeout_raises_on_timeout(self):
        """Slow function should raise TimeoutError."""
        def slow_func():
            time.sleep(2.0)
            return "should not reach"

        with pytest.raises(TimeoutError):
            run_sync_with_timeout(slow_func, timeout=0.1, service="test")

    def test_run_sync_with_timeout_returns_fallback(self):
        """Should return fallback value on timeout."""
        def slow_func():
            time.sleep(2.0)
            return "should not reach"

        result = run_sync_with_timeout(
            slow_func,
            timeout=0.1,
            fallback="fallback_value"
        )
        assert result == "fallback_value"

    def test_run_sync_with_timeout_passes_kwargs(self):
        """Should pass keyword arguments correctly."""
        def func_with_kwargs(a, b=10):
            return a + b

        result = run_sync_with_timeout(func_with_kwargs, 5, b=20, timeout=1.0)
        assert result == 25


# ============================================================================
# AsyncTimeoutContext Tests
# ============================================================================


class TestAsyncTimeoutContext:
    """Tests for AsyncTimeoutContext context manager."""

    async def test_context_success(self):
        """Operations within timeout should complete normally."""
        async with AsyncTimeoutContext(timeout=1.0, service="test"):
            await asyncio.sleep(0.01)
            result = "success"
        assert result == "success"

    async def test_context_stores_timeout_and_service(self):
        """Context should store timeout and service values."""
        ctx = AsyncTimeoutContext(timeout=5.0, service="search")
        assert ctx.timeout == 5.0
        assert ctx.service == "search"


# ============================================================================
# Integration Tests
# ============================================================================


class TestTimeoutIntegration:
    """Integration tests for timeout utilities."""

    async def test_decorator_with_exception_propagates(self):
        """Exceptions other than timeout should propagate normally."""
        @with_async_timeout(timeout=1.0)
        async def raises_error():
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            await raises_error()

    def test_sync_decorator_with_exception_propagates(self):
        """Sync exceptions other than timeout should propagate normally."""
        @with_timeout(timeout=1.0)
        def raises_error():
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            raises_error()

    async def test_timeout_config_from_settings(self):
        """Timeouts should be configurable via settings."""
        # Verify we can get timeout from config
        stt_timeout = get_timeout("stt")
        tts_timeout = get_timeout("tts")
        
        # Both should be positive numbers
        assert stt_timeout > 0
        assert tts_timeout > 0
        
        # STT/TTS are typically shorter than LLM
        llm_timeout = get_timeout("llm")
        assert llm_timeout >= stt_timeout

    async def test_multiple_concurrent_timeouts(self):
        """Multiple concurrent operations should have independent timeouts."""
        @with_async_timeout(timeout=0.5, service="test")
        async def operation(delay: float, name: str):
            await asyncio.sleep(delay)
            return name

        # Run multiple operations concurrently
        results = await asyncio.gather(
            operation(0.01, "fast1"),
            operation(0.02, "fast2"),
            operation(0.01, "fast3"),
        )
        assert results == ["fast1", "fast2", "fast3"]


# ============================================================================
# Edge Cases
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    async def test_zero_timeout_immediate_timeout(self):
        """Zero or very small timeout should timeout immediately."""
        @with_async_timeout(timeout=0.001)
        async def any_func():
            await asyncio.sleep(0.1)
            return "done"

        with pytest.raises(TimeoutError):
            await any_func()

    def test_none_timeout_uses_default(self):
        """None timeout should use default service timeout."""
        @with_timeout(timeout=None, service="default")
        def func():
            return "done"

        result = func()
        assert result == "done"

    async def test_none_service_uses_default(self):
        """None service should use default timeout."""
        @with_async_timeout(timeout=None, service=None)
        async def func():
            await asyncio.sleep(0.01)
            return "done"

        result = await func()
        assert result == "done"

    async def test_fallback_can_be_none(self):
        """None should be valid fallback value."""
        async def slow():
            await asyncio.sleep(1.0)
            return "not none"

        result = await run_with_timeout(slow(), timeout=0.05, fallback=None)
        assert result is None

    async def test_fallback_can_be_empty_list(self):
        """Empty list should be valid fallback value."""
        async def slow():
            await asyncio.sleep(1.0)
            return ["items"]

        result = await run_with_timeout(slow(), timeout=0.05, fallback=[])
        assert result == []

    async def test_fallback_can_be_empty_dict(self):
        """Empty dict should be valid fallback value."""
        async def slow():
            await asyncio.sleep(1.0)
            return {"key": "value"}

        result = await run_with_timeout(slow(), timeout=0.05, fallback={})
        assert result == {}
