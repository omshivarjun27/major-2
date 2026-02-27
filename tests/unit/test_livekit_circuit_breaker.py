"""Tests for LiveKit circuit breaker / health monitor.

Validates the passive health monitoring wrapper for LiveKit WebRTC connections.
The monitor tracks connection events and uses a circuit breaker for health state.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from infrastructure.resilience.circuit_breaker import (
    CircuitBreakerConfig,
    CircuitBreakerState,
    StateChangeEvent,
    clear_registry,
    get_circuit_breaker,
)
from infrastructure.resilience.livekit_monitor import (
    ConnectionEvent,
    LiveKitMonitor,
    clear_monitor,
    get_livekit_monitor,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_state():
    """Reset global state between tests."""
    clear_registry()
    clear_monitor()
    yield
    clear_registry()
    clear_monitor()


@pytest.fixture
def monitor() -> LiveKitMonitor:
    """Create a fresh LiveKit monitor for each test."""
    return LiveKitMonitor()


@pytest.fixture
def fast_monitor() -> LiveKitMonitor:
    """Create a monitor with fast timeouts for testing."""
    config = CircuitBreakerConfig(
        failure_threshold=2,
        reset_timeout_s=0.1,  # 100ms for fast tests
        half_open_max_calls=1,
        success_threshold=1,
    )
    return LiveKitMonitor(config=config)


# ---------------------------------------------------------------------------
# Tests — Initialization
# ---------------------------------------------------------------------------


class TestLiveKitMonitorInit:
    """Circuit breaker registration on monitor init."""

    async def test_cb_registered_on_init(self, monitor: LiveKitMonitor) -> None:
        """Monitor registers 'livekit' circuit breaker on creation."""
        cb = get_circuit_breaker("livekit")
        assert cb is not None
        assert cb.state is CircuitBreakerState.CLOSED

    async def test_default_config_values(self, monitor: LiveKitMonitor) -> None:
        """Default config has expected thresholds."""
        assert monitor._config.failure_threshold == 3
        assert monitor._config.reset_timeout_s == 30.0
        assert monitor._config.half_open_max_calls == 1

    async def test_custom_config_applied(self) -> None:
        """Custom config overrides defaults."""
        config = CircuitBreakerConfig(
            failure_threshold=5,
            reset_timeout_s=60.0,
        )
        monitor = LiveKitMonitor(config=config)
        assert monitor._config.failure_threshold == 5
        assert monitor._config.reset_timeout_s == 60.0

    async def test_initial_state_is_healthy(self, monitor: LiveKitMonitor) -> None:
        """New monitor starts in healthy state."""
        assert monitor.is_healthy() is True
        assert monitor.is_degraded() is False
        assert monitor.is_unavailable() is False
        assert monitor.state is CircuitBreakerState.CLOSED


# ---------------------------------------------------------------------------
# Tests — Success recording
# ---------------------------------------------------------------------------


class TestConnectionSuccess:
    """Recording successful connections."""

    async def test_success_updates_timestamp(self, monitor: LiveKitMonitor) -> None:
        """Recording success updates last_success_time."""
        assert monitor._last_success_time == 0.0
        await monitor.record_connection_success()
        assert monitor._last_success_time > 0.0

    async def test_success_increments_counter(self, monitor: LiveKitMonitor) -> None:
        """Recording success increments total_successes."""
        assert monitor._total_successes == 0
        await monitor.record_connection_success()
        assert monitor._total_successes == 1
        await monitor.record_connection_success()
        assert monitor._total_successes == 2

    async def test_success_keeps_circuit_closed(self, monitor: LiveKitMonitor) -> None:
        """Success while closed keeps circuit closed."""
        await monitor.record_connection_success()
        assert monitor.is_healthy() is True
        assert monitor.state is CircuitBreakerState.CLOSED

    async def test_success_in_half_open_closes_circuit(
        self, fast_monitor: LiveKitMonitor
    ) -> None:
        """Success while half-open transitions to closed."""
        # Trip the circuit
        await fast_monitor.record_connection_failure()
        await fast_monitor.record_connection_failure()
        assert fast_monitor.is_unavailable() is True

        # Wait for reset timeout to transition to half-open
        await asyncio.sleep(0.15)
        assert fast_monitor.state is CircuitBreakerState.HALF_OPEN

        # Success should close the circuit
        await fast_monitor.record_connection_success()
        assert fast_monitor.is_healthy() is True
        assert fast_monitor.state is CircuitBreakerState.CLOSED

    async def test_success_while_open_resets_circuit(
        self, fast_monitor: LiveKitMonitor
    ) -> None:
        """Success while open immediately resets to closed."""
        # Trip the circuit
        await fast_monitor.record_connection_failure()
        await fast_monitor.record_connection_failure()
        assert fast_monitor.is_unavailable() is True

        # Don't wait for timeout — record success immediately
        await fast_monitor.record_connection_success()
        assert fast_monitor.is_healthy() is True


# ---------------------------------------------------------------------------
# Tests — Failure recording
# ---------------------------------------------------------------------------


class TestConnectionFailure:
    """Recording connection failures."""

    async def test_failure_updates_timestamp(self, monitor: LiveKitMonitor) -> None:
        """Recording failure updates last_failure_time."""
        assert monitor._last_failure_time == 0.0
        await monitor.record_connection_failure()
        assert monitor._last_failure_time > 0.0

    async def test_failure_increments_counter(self, monitor: LiveKitMonitor) -> None:
        """Recording failure increments total_failures."""
        assert monitor._total_failures == 0
        await monitor.record_connection_failure()
        assert monitor._total_failures == 1
        await monitor.record_connection_failure()
        assert monitor._total_failures == 2

    async def test_failure_stores_error_from_exception(
        self, monitor: LiveKitMonitor
    ) -> None:
        """Exception is stored as last_error."""
        error = ConnectionError("WebSocket closed")
        await monitor.record_connection_failure(error=error)
        assert monitor._last_error is not None
        assert "ConnectionError" in monitor._last_error
        assert "WebSocket closed" in monitor._last_error

    async def test_failure_stores_error_from_message(
        self, monitor: LiveKitMonitor
    ) -> None:
        """Error message is stored as last_error."""
        await monitor.record_connection_failure(error_message="Room join timeout")
        assert monitor._last_error == "Room join timeout"

    async def test_single_failure_keeps_circuit_closed(
        self, monitor: LiveKitMonitor
    ) -> None:
        """Single failure doesn't trip circuit (threshold=3)."""
        await monitor.record_connection_failure()
        assert monitor.is_healthy() is True
        assert monitor.failure_count == 1

    async def test_threshold_failures_trip_circuit(
        self, monitor: LiveKitMonitor
    ) -> None:
        """Reaching threshold trips the circuit."""
        await monitor.record_connection_failure()
        await monitor.record_connection_failure()
        assert monitor.is_healthy() is True  # Still below threshold

        await monitor.record_connection_failure()  # Third failure
        assert monitor.is_unavailable() is True
        assert monitor.state is CircuitBreakerState.OPEN

    async def test_failure_in_half_open_trips_circuit(
        self, fast_monitor: LiveKitMonitor
    ) -> None:
        """Failure while half-open immediately trips back to open."""
        # Trip the circuit
        await fast_monitor.record_connection_failure()
        await fast_monitor.record_connection_failure()

        # Wait for half-open
        await asyncio.sleep(0.15)
        assert fast_monitor.state is CircuitBreakerState.HALF_OPEN

        # Failure in half-open should trip back to open
        await fast_monitor.record_connection_failure()
        assert fast_monitor.is_unavailable() is True
        assert fast_monitor.state is CircuitBreakerState.OPEN


# ---------------------------------------------------------------------------
# Tests — Health queries
# ---------------------------------------------------------------------------


class TestHealthQueries:
    """Health state queries."""

    async def test_is_healthy_when_closed(self, monitor: LiveKitMonitor) -> None:
        """is_healthy returns True when circuit is closed."""
        assert monitor.is_healthy() is True

    async def test_is_healthy_false_when_open(
        self, fast_monitor: LiveKitMonitor
    ) -> None:
        """is_healthy returns False when circuit is open."""
        await fast_monitor.record_connection_failure()
        await fast_monitor.record_connection_failure()
        assert fast_monitor.is_healthy() is False

    async def test_is_healthy_false_when_half_open(
        self, fast_monitor: LiveKitMonitor
    ) -> None:
        """is_healthy returns False when circuit is half-open."""
        await fast_monitor.record_connection_failure()
        await fast_monitor.record_connection_failure()
        await asyncio.sleep(0.15)
        assert fast_monitor.state is CircuitBreakerState.HALF_OPEN
        assert fast_monitor.is_healthy() is False

    async def test_is_degraded_when_half_open(
        self, fast_monitor: LiveKitMonitor
    ) -> None:
        """is_degraded returns True when circuit is half-open."""
        await fast_monitor.record_connection_failure()
        await fast_monitor.record_connection_failure()
        await asyncio.sleep(0.15)
        assert fast_monitor.is_degraded() is True

    async def test_is_unavailable_when_open(
        self, fast_monitor: LiveKitMonitor
    ) -> None:
        """is_unavailable returns True when circuit is open."""
        await fast_monitor.record_connection_failure()
        await fast_monitor.record_connection_failure()
        assert fast_monitor.is_unavailable() is True


# ---------------------------------------------------------------------------
# Tests — State-change callbacks
# ---------------------------------------------------------------------------


class TestStateChangeCallbacks:
    """Callback invocation on state transitions."""

    async def test_callback_on_circuit_trip(self) -> None:
        """Callback fires when circuit trips to open."""
        events: list[StateChangeEvent] = []

        def capture_event(event: StateChangeEvent) -> None:
            events.append(event)

        config = CircuitBreakerConfig(failure_threshold=2, reset_timeout_s=0.1)
        monitor = LiveKitMonitor(config=config, on_state_change=[capture_event])

        await monitor.record_connection_failure()
        await monitor.record_connection_failure()

        # Should have received a state change event
        assert len(events) == 1
        assert events[0].previous_state is CircuitBreakerState.CLOSED
        assert events[0].new_state is CircuitBreakerState.OPEN
        assert events[0].service_name == "livekit"

    async def test_callback_on_circuit_reset(self) -> None:
        """Callback fires when circuit resets to closed."""
        events: list[StateChangeEvent] = []

        def capture_event(event: StateChangeEvent) -> None:
            events.append(event)

        config = CircuitBreakerConfig(failure_threshold=2, reset_timeout_s=0.1)
        monitor = LiveKitMonitor(config=config, on_state_change=[capture_event])

        # Trip the circuit
        await monitor.record_connection_failure()
        await monitor.record_connection_failure()

        # Reset it
        await monitor.reset()

        # Should have two events: trip and reset
        assert len(events) == 2
        assert events[1].new_state is CircuitBreakerState.CLOSED

    async def test_add_callback_dynamically(self, monitor: LiveKitMonitor) -> None:
        """Callbacks can be added after creation."""
        events: list[StateChangeEvent] = []

        def capture_event(event: StateChangeEvent) -> None:
            events.append(event)

        monitor.add_callback(capture_event)

        # Trip the circuit
        await monitor.record_connection_failure()
        await monitor.record_connection_failure()
        await monitor.record_connection_failure()

        assert len(events) == 1
        assert events[0].new_state is CircuitBreakerState.OPEN

    async def test_remove_callback(self, monitor: LiveKitMonitor) -> None:
        """Callbacks can be removed."""
        events: list[StateChangeEvent] = []

        def capture_event(event: StateChangeEvent) -> None:
            events.append(event)

        monitor.add_callback(capture_event)
        monitor.remove_callback(capture_event)

        # Trip the circuit
        await monitor.record_connection_failure()
        await monitor.record_connection_failure()
        await monitor.record_connection_failure()

        # Callback was removed, should not have captured events
        assert len(events) == 0


# ---------------------------------------------------------------------------
# Tests — Snapshot / diagnostics
# ---------------------------------------------------------------------------


class TestSnapshot:
    """Health snapshot for diagnostics."""

    async def test_snapshot_includes_cb_state(self, monitor: LiveKitMonitor) -> None:
        """Snapshot includes circuit breaker state."""
        snapshot = monitor.snapshot()
        assert "state" in snapshot
        assert snapshot["state"] == "closed"
        assert "service" in snapshot
        assert snapshot["service"] == "livekit"

    async def test_snapshot_includes_livekit_metrics(
        self, monitor: LiveKitMonitor
    ) -> None:
        """Snapshot includes LiveKit-specific metrics."""
        await monitor.record_connection_success()
        await monitor.record_connection_failure(error_message="Test error")

        snapshot = monitor.snapshot()
        assert snapshot["total_successes"] == 1
        assert snapshot["total_failures"] == 1
        assert snapshot["last_error"] == "Test error"
        assert snapshot["is_healthy"] is True
        assert snapshot["is_degraded"] is False
        assert snapshot["is_unavailable"] is False

    async def test_snapshot_reflects_open_state(
        self, fast_monitor: LiveKitMonitor
    ) -> None:
        """Snapshot reflects open circuit state."""
        await fast_monitor.record_connection_failure()
        await fast_monitor.record_connection_failure()

        snapshot = fast_monitor.snapshot()
        assert snapshot["state"] == "open"
        assert snapshot["is_healthy"] is False
        assert snapshot["is_unavailable"] is True


# ---------------------------------------------------------------------------
# Tests — Manual control
# ---------------------------------------------------------------------------


class TestManualControl:
    """Manual reset and trip operations."""

    async def test_manual_reset(self, monitor: LiveKitMonitor) -> None:
        """Manual reset clears failure state."""
        # Cause some failures
        await monitor.record_connection_failure()
        await monitor.record_connection_failure()
        await monitor.record_connection_failure()
        assert monitor.is_unavailable() is True

        # Manual reset
        await monitor.reset()
        assert monitor.is_healthy() is True
        assert monitor._last_error is None

    async def test_manual_trip(self, monitor: LiveKitMonitor) -> None:
        """Manual trip forces circuit open."""
        assert monitor.is_healthy() is True
        await monitor.trip()
        assert monitor.is_unavailable() is True
        assert monitor.state is CircuitBreakerState.OPEN


# ---------------------------------------------------------------------------
# Tests — Singleton access
# ---------------------------------------------------------------------------


class TestSingletonAccess:
    """Module-level singleton functions."""

    async def test_get_livekit_monitor_creates_singleton(self) -> None:
        """get_livekit_monitor creates singleton on first call."""
        monitor1 = get_livekit_monitor()
        monitor2 = get_livekit_monitor()
        assert monitor1 is monitor2

    async def test_clear_monitor_removes_singleton(self) -> None:
        """clear_monitor removes singleton."""
        monitor1 = get_livekit_monitor()
        clear_monitor()
        monitor2 = get_livekit_monitor()
        assert monitor1 is not monitor2


# ---------------------------------------------------------------------------
# Tests — ConnectionEvent dataclass
# ---------------------------------------------------------------------------


class TestConnectionEvent:
    """ConnectionEvent dataclass."""

    def test_event_defaults(self) -> None:
        """ConnectionEvent has sensible defaults."""
        event = ConnectionEvent(success=True)
        assert event.success is True
        assert event.error is None
        assert event.timestamp > 0.0

    def test_event_with_error(self) -> None:
        """ConnectionEvent can store error."""
        event = ConnectionEvent(success=False, error="Connection refused")
        assert event.success is False
        assert event.error == "Connection refused"
