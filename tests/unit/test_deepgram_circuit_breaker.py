"""Tests for Deepgram STT circuit breaker resilience wrapper."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from infrastructure.resilience.circuit_breaker import (
    CircuitBreakerConfig,
    CircuitBreakerState,
    StateChangeEvent,
    clear_registry,
    get_circuit_breaker,
)
from infrastructure.speech.deepgram.resilience import DeepgramResilience, SERVICE_NAME


@pytest.fixture(autouse=True)
def clean_registry():
    """Ensure clean circuit breaker registry for each test."""
    clear_registry()
    yield
    clear_registry()


class TestDeepgramResilience:
    """Tests for DeepgramResilience passive health monitor."""

    def test_service_name_is_deepgram(self) -> None:
        """SERVICE_NAME constant should be 'deepgram'."""
        assert SERVICE_NAME == "deepgram"

    def test_registers_circuit_breaker(self) -> None:
        """DeepgramResilience registers a 'deepgram' circuit breaker in the global registry."""
        dr = DeepgramResilience()
        cb = get_circuit_breaker("deepgram")
        assert cb is not None
        assert cb.service_name == "deepgram"

    def test_default_config(self) -> None:
        """Default config uses failure_threshold=3, reset_timeout_s=15."""
        dr = DeepgramResilience()
        cb = get_circuit_breaker("deepgram")
        assert cb is not None
        assert cb.config.failure_threshold == 3
        assert cb.config.reset_timeout_s == 15.0
        assert cb.config.half_open_max_calls == 1
        assert cb.config.success_threshold == 1

    def test_custom_config(self) -> None:
        """Custom config overrides defaults."""
        config = CircuitBreakerConfig(failure_threshold=5, reset_timeout_s=30.0)
        dr = DeepgramResilience(config=config)
        cb = get_circuit_breaker("deepgram")
        assert cb is not None
        assert cb.config.failure_threshold == 5
        assert cb.config.reset_timeout_s == 30.0

    def test_is_available_when_closed(self) -> None:
        """is_available returns True when circuit is CLOSED."""
        dr = DeepgramResilience()
        assert dr.is_available is True

    def test_state_is_closed_initially(self) -> None:
        """State should be CLOSED on fresh instance."""
        dr = DeepgramResilience()
        assert dr.state is CircuitBreakerState.CLOSED

    async def test_record_success(self) -> None:
        """record_success does not trip the circuit."""
        dr = DeepgramResilience()
        await dr.record_success()
        assert dr.is_available is True
        assert dr.state is CircuitBreakerState.CLOSED

    async def test_single_failure_does_not_trip(self) -> None:
        """A single failure should not trip the circuit."""
        dr = DeepgramResilience()
        await dr.record_failure(RuntimeError("timeout"))
        assert dr.is_available is True
        assert dr.state is CircuitBreakerState.CLOSED

    async def test_failures_trip_circuit_after_threshold(self) -> None:
        """Three consecutive failures trip the circuit to OPEN."""
        dr = DeepgramResilience()
        for _ in range(3):
            await dr.record_failure(RuntimeError("timeout"))
        assert dr.is_available is False
        assert dr.state is CircuitBreakerState.OPEN

    async def test_is_available_false_when_open(self) -> None:
        """is_available returns False when circuit is OPEN."""
        dr = DeepgramResilience()
        await dr.trip()
        assert dr.is_available is False

    async def test_success_resets_failure_count(self) -> None:
        """A success in CLOSED state resets the failure counter."""
        dr = DeepgramResilience()
        await dr.record_failure(RuntimeError("err"))
        await dr.record_failure(RuntimeError("err"))
        await dr.record_success()
        # After success, failure count resets — next single failure shouldn't trip
        await dr.record_failure(RuntimeError("err"))
        assert dr.is_available is True

    async def test_half_open_success_closes_circuit(self) -> None:
        """A success in HALF_OPEN state transitions back to CLOSED."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            reset_timeout_s=0.05,  # Very short for testing
            half_open_max_calls=1,
            success_threshold=1,
        )
        dr = DeepgramResilience(config=config)

        # Trip the circuit
        for _ in range(3):
            await dr.record_failure(RuntimeError("err"))
        assert dr.state is CircuitBreakerState.OPEN

        # Wait for reset timeout
        await asyncio.sleep(0.1)
        assert dr.state is CircuitBreakerState.HALF_OPEN

        # Record success to close circuit
        await dr.record_success()
        assert dr.state is CircuitBreakerState.CLOSED
        assert dr.is_available is True

    async def test_half_open_failure_reopens_circuit(self) -> None:
        """A failure in HALF_OPEN state re-opens the circuit."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            reset_timeout_s=0.05,
            half_open_max_calls=1,
            success_threshold=1,
        )
        dr = DeepgramResilience(config=config)

        # Trip the circuit
        for _ in range(3):
            await dr.record_failure(RuntimeError("err"))
        assert dr.state is CircuitBreakerState.OPEN

        # Wait for reset timeout
        await asyncio.sleep(0.1)
        assert dr.state is CircuitBreakerState.HALF_OPEN

        # Failure in half-open re-opens
        await dr.record_failure(RuntimeError("still broken"))
        assert dr.state is CircuitBreakerState.OPEN

    async def test_health_snapshot(self) -> None:
        """health() returns dict with expected keys."""
        dr = DeepgramResilience()
        snap = dr.health()
        assert snap["service"] == "deepgram"
        assert snap["state"] == "closed"
        assert snap["failure_count"] == 0
        assert "config" in snap
        assert snap["config"]["failure_threshold"] == 3
        assert snap["config"]["reset_timeout_s"] == 15.0

    async def test_health_reflects_open_state(self) -> None:
        """health() reflects OPEN state after tripping."""
        dr = DeepgramResilience()
        await dr.trip()
        snap = dr.health()
        assert snap["state"] == "open"

    async def test_reset_forces_closed(self) -> None:
        """reset() forces circuit back to CLOSED."""
        dr = DeepgramResilience()
        await dr.trip()
        assert dr.state is CircuitBreakerState.OPEN
        await dr.reset()
        assert dr.state is CircuitBreakerState.CLOSED
        assert dr.is_available is True

    async def test_trip_forces_open(self) -> None:
        """trip() forces circuit to OPEN."""
        dr = DeepgramResilience()
        assert dr.state is CircuitBreakerState.CLOSED
        await dr.trip()
        assert dr.state is CircuitBreakerState.OPEN
        assert dr.is_available is False

    async def test_state_change_callback_on_trip(self) -> None:
        """Callbacks fire on state transitions."""
        events: list[StateChangeEvent] = []

        def on_change(event: StateChangeEvent) -> None:
            events.append(event)

        dr = DeepgramResilience(on_state_change=[on_change])
        await dr.trip()

        assert len(events) == 1
        assert events[0].service_name == "deepgram"
        assert events[0].previous_state is CircuitBreakerState.CLOSED
        assert events[0].new_state is CircuitBreakerState.OPEN

    async def test_state_change_callback_on_reset(self) -> None:
        """Callbacks fire on reset transitions."""
        events: list[StateChangeEvent] = []

        def on_change(event: StateChangeEvent) -> None:
            events.append(event)

        dr = DeepgramResilience(on_state_change=[on_change])
        await dr.trip()
        await dr.reset()

        assert len(events) == 2
        # First: CLOSED -> OPEN
        assert events[0].new_state is CircuitBreakerState.OPEN
        # Second: OPEN -> CLOSED
        assert events[1].new_state is CircuitBreakerState.CLOSED

    async def test_add_callback_dynamically(self) -> None:
        """add_callback() registers a new listener after construction."""
        events: list[StateChangeEvent] = []

        def on_change(event: StateChangeEvent) -> None:
            events.append(event)

        dr = DeepgramResilience()
        dr.add_callback(on_change)
        await dr.trip()

        assert len(events) == 1
        assert events[0].new_state is CircuitBreakerState.OPEN

    async def test_remove_callback(self) -> None:
        """remove_callback() unregisters a listener."""
        events: list[StateChangeEvent] = []

        def on_change(event: StateChangeEvent) -> None:
            events.append(event)

        dr = DeepgramResilience()
        dr.add_callback(on_change)
        dr.remove_callback(on_change)
        await dr.trip()

        assert len(events) == 0

    async def test_callback_fires_on_failure_trip(self) -> None:
        """Callback fires when failures naturally trip the circuit."""
        events: list[StateChangeEvent] = []

        def on_change(event: StateChangeEvent) -> None:
            events.append(event)

        dr = DeepgramResilience(on_state_change=[on_change])
        for _ in range(3):
            await dr.record_failure(RuntimeError("err"))

        assert len(events) == 1
        assert events[0].previous_state is CircuitBreakerState.CLOSED
        assert events[0].new_state is CircuitBreakerState.OPEN

    async def test_record_failure_default_exception(self) -> None:
        """record_failure() without explicit exc uses RuntimeError."""
        dr = DeepgramResilience()
        # Should not raise — just record failures
        for _ in range(3):
            await dr.record_failure()
        assert dr.state is CircuitBreakerState.OPEN

    def test_singleton_via_registry(self) -> None:
        """Multiple DeepgramResilience instances share the same circuit breaker."""
        dr1 = DeepgramResilience()
        dr2 = DeepgramResilience()
        # Both should reference the same underlying circuit breaker
        assert dr1._cb is dr2._cb

    async def test_singleton_state_shared(self) -> None:
        """State changes in one instance are visible in another."""
        dr1 = DeepgramResilience()
        dr2 = DeepgramResilience()

        await dr1.trip()
        assert dr2.is_available is False
        assert dr2.state is CircuitBreakerState.OPEN

        await dr2.reset()
        assert dr1.is_available is True
        assert dr1.state is CircuitBreakerState.CLOSED

    async def test_async_callback(self) -> None:
        """Async callbacks are properly awaited."""
        events: list[StateChangeEvent] = []

        async def on_change(event: StateChangeEvent) -> None:
            events.append(event)

        dr = DeepgramResilience(on_state_change=[on_change])
        await dr.trip()

        assert len(events) == 1
        assert events[0].new_state is CircuitBreakerState.OPEN

    async def test_health_after_failures(self) -> None:
        """health() reflects failure count after partial failures."""
        dr = DeepgramResilience()
        await dr.record_failure(RuntimeError("err"))
        await dr.record_failure(RuntimeError("err"))

        snap = dr.health()
        assert snap["failure_count"] == 2
        assert snap["state"] == "closed"
