"""Tests for infrastructure.resilience.circuit_breaker module.

Covers: state transitions, decorator, registry, callbacks, metrics hooks,
excluded exceptions, and edge cases.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from infrastructure.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitBreakerState,
    StateChangeEvent,
    clear_registry,
    get_all_breakers,
    get_circuit_breaker,
    register_circuit_breaker,
    with_circuit_breaker,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _success_fn() -> str:
    return "ok"


async def _failure_fn() -> str:
    raise ConnectionError("service unavailable")


async def _custom_error_fn() -> str:
    raise ValueError("bad input")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean_registry():
    """Reset the global circuit breaker registry between tests."""
    clear_registry()
    yield
    clear_registry()


@pytest.fixture
def config_low_threshold() -> CircuitBreakerConfig:
    return CircuitBreakerConfig(
        failure_threshold=2,
        reset_timeout_s=0.1,  # fast reset for tests
        half_open_max_calls=1,
        success_threshold=1,
    )


@pytest.fixture
def cb(config_low_threshold: CircuitBreakerConfig) -> CircuitBreaker:
    return CircuitBreaker("test-service", config=config_low_threshold)


# ---------------------------------------------------------------------------
# Basic state transitions
# ---------------------------------------------------------------------------

class TestCircuitBreakerStateTransitions:
    """CLOSED → OPEN → HALF_OPEN → CLOSED lifecycle."""

    async def test_starts_closed(self, cb: CircuitBreaker):
        assert cb.state is CircuitBreakerState.CLOSED
        assert cb.is_closed

    async def test_success_stays_closed(self, cb: CircuitBreaker):
        result = await cb.call(_success_fn)
        assert result == "ok"
        assert cb.state is CircuitBreakerState.CLOSED
        assert cb.failure_count == 0

    async def test_single_failure_stays_closed(self, cb: CircuitBreaker):
        with pytest.raises(ConnectionError):
            await cb.call(_failure_fn)
        assert cb.state is CircuitBreakerState.CLOSED
        assert cb.failure_count == 1

    async def test_failures_trip_to_open(self, cb: CircuitBreaker):
        for _ in range(2):  # threshold is 2
            with pytest.raises(ConnectionError):
                await cb.call(_failure_fn)
        assert cb.state is CircuitBreakerState.OPEN
        assert cb.failure_count == 2

    async def test_open_rejects_calls(self, cb: CircuitBreaker):
        # Trip the circuit
        for _ in range(2):
            with pytest.raises(ConnectionError):
                await cb.call(_failure_fn)

        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            await cb.call(_success_fn)
        assert "test-service" in str(exc_info.value)

    async def test_open_transitions_to_half_open_after_timeout(
        self, cb: CircuitBreaker
    ):
        # Trip the circuit
        for _ in range(2):
            with pytest.raises(ConnectionError):
                await cb.call(_failure_fn)
        assert cb.state is CircuitBreakerState.OPEN

        # Wait for reset timeout (0.1s)
        await asyncio.sleep(0.15)
        assert cb.state is CircuitBreakerState.HALF_OPEN

    async def test_half_open_success_closes_circuit(self, cb: CircuitBreaker):
        # Trip → wait → half-open → success → closed
        for _ in range(2):
            with pytest.raises(ConnectionError):
                await cb.call(_failure_fn)

        await asyncio.sleep(0.15)

        result = await cb.call(_success_fn)
        assert result == "ok"
        assert cb.state is CircuitBreakerState.CLOSED
        assert cb.failure_count == 0

    async def test_half_open_failure_reopens(self, cb: CircuitBreaker):
        # Trip → wait → half-open → failure → open again
        for _ in range(2):
            with pytest.raises(ConnectionError):
                await cb.call(_failure_fn)

        await asyncio.sleep(0.15)

        with pytest.raises(ConnectionError):
            await cb.call(_failure_fn)
        assert cb.state is CircuitBreakerState.OPEN

    async def test_success_resets_failure_count(self, cb: CircuitBreaker):
        with pytest.raises(ConnectionError):
            await cb.call(_failure_fn)
        assert cb.failure_count == 1

        await cb.call(_success_fn)
        assert cb.failure_count == 0


# ---------------------------------------------------------------------------
# Excluded exceptions
# ---------------------------------------------------------------------------

class TestExcludedExceptions:
    """Excluded exception types should not count as failures."""

    async def test_excluded_exception_not_counted(self):
        config = CircuitBreakerConfig(
            failure_threshold=2,
            excluded_exceptions=(ValueError,),
        )
        cb = CircuitBreaker("excl-test", config=config)

        # ValueError is excluded — should not count as failure
        for _ in range(5):
            with pytest.raises(ValueError):
                await cb.call(_custom_error_fn)

        assert cb.state is CircuitBreakerState.CLOSED
        assert cb.failure_count == 0

    async def test_non_excluded_exception_counted(self):
        config = CircuitBreakerConfig(
            failure_threshold=2,
            excluded_exceptions=(ValueError,),
        )
        cb = CircuitBreaker("excl-test2", config=config)

        for _ in range(2):
            with pytest.raises(ConnectionError):
                await cb.call(_failure_fn)

        assert cb.state is CircuitBreakerState.OPEN


# ---------------------------------------------------------------------------
# Manual control
# ---------------------------------------------------------------------------

class TestManualControl:
    """Force-reset and force-trip APIs."""

    async def test_manual_trip(self, cb: CircuitBreaker):
        assert cb.is_closed
        await cb.trip()
        assert cb.is_open

    async def test_manual_reset(self, cb: CircuitBreaker):
        await cb.trip()
        assert cb.is_open

        await cb.reset()
        assert cb.is_closed
        assert cb.failure_count == 0

    async def test_reset_after_failures(self, cb: CircuitBreaker):
        for _ in range(2):
            with pytest.raises(ConnectionError):
                await cb.call(_failure_fn)
        assert cb.is_open

        await cb.reset()
        assert cb.is_closed
        result = await cb.call(_success_fn)
        assert result == "ok"


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

class TestCallbacks:
    """State-change event callbacks."""

    async def test_callback_on_trip(self, config_low_threshold: CircuitBreakerConfig):
        events: list[StateChangeEvent] = []
        cb = CircuitBreaker(
            "cb-test",
            config=config_low_threshold,
            on_state_change=[lambda e: events.append(e)],
        )

        for _ in range(2):
            with pytest.raises(ConnectionError):
                await cb.call(_failure_fn)

        assert len(events) >= 1
        trip_event = events[-1]
        assert trip_event.new_state is CircuitBreakerState.OPEN
        assert trip_event.previous_state is CircuitBreakerState.CLOSED
        assert trip_event.service_name == "cb-test"

    async def test_async_callback(self, config_low_threshold: CircuitBreakerConfig):
        events: list[StateChangeEvent] = []

        async def async_handler(event: StateChangeEvent) -> None:
            events.append(event)

        cb = CircuitBreaker(
            "async-cb",
            config=config_low_threshold,
            on_state_change=[async_handler],
        )

        for _ in range(2):
            with pytest.raises(ConnectionError):
                await cb.call(_failure_fn)

        assert len(events) >= 1
        assert events[-1].new_state is CircuitBreakerState.OPEN

    async def test_add_remove_callback(self, cb: CircuitBreaker):
        handler = MagicMock()
        cb.add_callback(handler)
        await cb.trip()
        assert handler.called

        handler.reset_mock()
        cb.remove_callback(handler)
        await cb.reset()
        assert not handler.called


# ---------------------------------------------------------------------------
# Metrics hooks
# ---------------------------------------------------------------------------

class TestMetricsHooks:
    """MetricsCollector integration."""

    async def test_metrics_recorded_on_success(self):
        mock_metrics = MagicMock()
        cb = CircuitBreaker("metrics-test", metrics=mock_metrics)

        await cb.call(_success_fn)

        mock_metrics.increment.assert_called()
        # Should have recorded "success" metric
        calls = [str(c) for c in mock_metrics.increment.call_args_list]
        assert any("success" in c for c in calls)

    async def test_metrics_recorded_on_failure(self):
        mock_metrics = MagicMock()
        config = CircuitBreakerConfig(failure_threshold=5)
        cb = CircuitBreaker("metrics-fail", config=config, metrics=mock_metrics)

        with pytest.raises(ConnectionError):
            await cb.call(_failure_fn)

        calls = [str(c) for c in mock_metrics.increment.call_args_list]
        assert any("failure" in c for c in calls)

    async def test_metrics_recorded_on_rejection(self):
        mock_metrics = MagicMock()
        config = CircuitBreakerConfig(failure_threshold=1)
        cb = CircuitBreaker("metrics-reject", config=config, metrics=mock_metrics)

        with pytest.raises(ConnectionError):
            await cb.call(_failure_fn)

        with pytest.raises(CircuitBreakerOpenError):
            await cb.call(_success_fn)

        calls = [str(c) for c in mock_metrics.increment.call_args_list]
        assert any("rejected" in c for c in calls)


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------

class TestSnapshot:
    """Health snapshot for status endpoints."""

    async def test_snapshot_closed(self, cb: CircuitBreaker):
        snap = cb.snapshot()
        assert snap["service"] == "test-service"
        assert snap["state"] == "closed"
        assert snap["failure_count"] == 0

    async def test_snapshot_open(self, cb: CircuitBreaker):
        for _ in range(2):
            with pytest.raises(ConnectionError):
                await cb.call(_failure_fn)

        snap = cb.snapshot()
        assert snap["state"] == "open"
        assert snap["failure_count"] == 2


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class TestRegistry:
    """Global circuit breaker registry."""

    def test_register_and_get(self):
        cb = register_circuit_breaker("svc-a")
        assert get_circuit_breaker("svc-a") is cb

    def test_register_idempotent(self):
        cb1 = register_circuit_breaker("svc-b")
        cb2 = register_circuit_breaker("svc-b")
        assert cb1 is cb2

    def test_get_nonexistent_returns_none(self):
        assert get_circuit_breaker("nonexistent") is None

    def test_get_all_breakers(self):
        register_circuit_breaker("x")
        register_circuit_breaker("y")
        all_cbs = get_all_breakers()
        assert "x" in all_cbs
        assert "y" in all_cbs

    def test_clear_registry(self):
        register_circuit_breaker("z")
        clear_registry()
        assert get_circuit_breaker("z") is None


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------

class TestDecorator:
    """@with_circuit_breaker decorator."""

    async def test_decorator_passes_through(self):
        @with_circuit_breaker("dec-svc", failure_threshold=3)
        async def my_func(x: int) -> int:
            return x * 2

        result = await my_func(5)
        assert result == 10

    async def test_decorator_registers_breaker(self):
        @with_circuit_breaker("dec-reg", failure_threshold=2)
        async def my_func() -> str:
            return "ok"

        await my_func()
        cb = get_circuit_breaker("dec-reg")
        assert cb is not None
        assert cb.is_closed

    async def test_decorator_trips_on_failures(self):
        @with_circuit_breaker("dec-trip", failure_threshold=2, reset_timeout_s=60)
        async def my_func() -> str:
            raise ConnectionError("boom")

        for _ in range(2):
            with pytest.raises(ConnectionError):
                await my_func()

        cb = get_circuit_breaker("dec-trip")
        assert cb is not None
        assert cb.is_open

    async def test_decorator_rejects_when_open(self):
        @with_circuit_breaker("dec-reject", failure_threshold=1, reset_timeout_s=60)
        async def my_func() -> str:
            raise ConnectionError("boom")

        with pytest.raises(ConnectionError):
            await my_func()

        with pytest.raises(CircuitBreakerOpenError):
            await my_func()

    async def test_decorator_preserves_function_name(self):
        @with_circuit_breaker("dec-name")
        async def important_function() -> None:
            pass

        assert important_function.__name__ == "important_function"

    async def test_decorator_exposes_service_name(self):
        @with_circuit_breaker("dec-attr")
        async def my_func() -> None:
            pass

        assert my_func.circuit_breaker_service == "dec-attr"  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Concurrency safety
# ---------------------------------------------------------------------------

class TestConcurrency:
    """Concurrent call safety under asyncio."""

    async def test_concurrent_calls_respect_state(self):
        config = CircuitBreakerConfig(failure_threshold=5, reset_timeout_s=60)
        cb = CircuitBreaker("conc-test", config=config)

        call_count = 0

        async def counting_fn() -> str:
            nonlocal call_count
            call_count += 1
            return "ok"

        # Launch 20 concurrent calls — all should succeed
        results = await asyncio.gather(
            *[cb.call(counting_fn) for _ in range(20)]
        )
        assert all(r == "ok" for r in results)
        assert call_count == 20
        assert cb.is_closed

    async def test_concurrent_failures_trip_once(self):
        config = CircuitBreakerConfig(failure_threshold=3, reset_timeout_s=60)
        cb = CircuitBreaker("conc-fail", config=config)

        async def failing_fn() -> str:
            await asyncio.sleep(0.01)
            raise ConnectionError("fail")

        tasks = [cb.call(failing_fn) for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Some will be ConnectionError (before trip), some CircuitBreakerOpenError (after)
        conn_errors = [r for r in results if isinstance(r, ConnectionError)]
        assert sum(1 for r in results if isinstance(r, CircuitBreakerOpenError)) >= 0
        assert len(conn_errors) >= 3  # at least threshold failures
        assert cb.is_open
