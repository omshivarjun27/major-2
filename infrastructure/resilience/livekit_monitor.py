"""LiveKit connection health monitor with circuit breaker.

Provides a passive health monitoring wrapper for LiveKit WebRTC connections.
This monitor does NOT intercept LiveKit SDK calls — it tracks health based on
events reported by the realtime agent (connection successes/failures).

The agent calls ``record_connection_success()`` / ``record_connection_failure()``
to update health state, and queries ``is_healthy()`` before room operations.

Architecture constraint: imports from ``shared/`` only (via circuit_breaker).

Usage::

    from infrastructure.resilience.livekit_monitor import (
        get_livekit_monitor,
        LiveKitMonitor,
    )

    monitor = get_livekit_monitor()

    # On successful connection
    await monitor.record_connection_success()

    # On connection failure
    await monitor.record_connection_failure(error)

    # Pre-flight check
    if not monitor.is_healthy():
        # Skip room join, use fallback
        ...
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Sequence

from infrastructure.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitBreakerState,
    StateChangeCallback,
    StateChangeEvent,
    register_circuit_breaker,
    get_circuit_breaker,
)

logger = logging.getLogger("resilience.livekit_monitor")

# Default configuration for LiveKit circuit breaker
_LIVEKIT_CB_CONFIG = CircuitBreakerConfig(
    failure_threshold=3,
    reset_timeout_s=30.0,
    half_open_max_calls=1,
    success_threshold=1,
)


@dataclass
class ConnectionEvent:
    """Event payload for connection state changes."""

    success: bool
    error: Optional[str] = None
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class LiveKitMonitor:
    """Passive health monitor for LiveKit WebRTC connections.

    This class wraps a circuit breaker to track LiveKit connection health
    without intercepting SDK calls. The realtime agent reports events to
    this monitor, which updates the circuit breaker state accordingly.

    The monitor provides:
    - ``record_connection_success()``: Call when connection/reconnection succeeds
    - ``record_connection_failure()``: Call when connection fails or drops
    - ``is_healthy()``: Pre-flight check for room operations
    - ``snapshot()``: Health status for diagnostics endpoints
    """

    def __init__(
        self,
        config: Optional[CircuitBreakerConfig] = None,
        on_state_change: Optional[Sequence[StateChangeCallback]] = None,
    ) -> None:
        """Initialize the LiveKit monitor.

        Args:
            config: Circuit breaker configuration. Defaults to 3-failure threshold,
                    30s reset timeout.
            on_state_change: Optional callbacks for state transitions.
        """
        self._config = config or _LIVEKIT_CB_CONFIG
        self._callbacks: list[StateChangeCallback] = list(on_state_change or [])

        # Register the circuit breaker in global registry
        self._cb = register_circuit_breaker(
            "livekit",
            config=self._config,
            on_state_change=self._callbacks,
        )

        # Track last events for diagnostics
        self._last_success_time: float = 0.0
        self._last_failure_time: float = 0.0
        self._last_error: Optional[str] = None
        self._total_successes: int = 0
        self._total_failures: int = 0

        logger.info(
            "LiveKit monitor initialized (failure_threshold=%d, reset_timeout=%.1fs)",
            self._config.failure_threshold,
            self._config.reset_timeout_s,
        )

    # -- Public API: Event recording ------------------------------------------

    async def record_connection_success(self) -> None:
        """Record a successful connection or reconnection.

        Call this when:
        - Initial room connection succeeds
        - Reconnection after disconnect succeeds
        - Room join completes successfully
        """
        self._last_success_time = time.time()
        self._total_successes += 1

        # Use the circuit breaker's internal success tracking
        # We simulate a successful "call" by directly updating state
        if self._cb.state is CircuitBreakerState.HALF_OPEN:
            # In half-open, a success should close the circuit
            await self._cb.reset()
            logger.info("LiveKit connection restored — circuit closed")
        elif self._cb.state is CircuitBreakerState.OPEN:
            # If open but success happened, reset
            await self._cb.reset()
            logger.info("LiveKit connection succeeded while circuit open — reset to closed")
        else:
            # Already closed, just log
            logger.debug("LiveKit connection success recorded (circuit: closed)")

    async def record_connection_failure(
        self,
        error: Optional[Exception] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Record a connection failure.

        Call this when:
        - Initial room connection fails
        - Connection drops unexpectedly
        - Reconnection attempt fails
        - Room join fails

        Args:
            error: The exception that caused the failure (optional)
            error_message: A string description of the failure (optional)
        """
        self._last_failure_time = time.time()
        self._total_failures += 1

        # Store error info
        if error is not None:
            self._last_error = f"{type(error).__name__}: {error}"
        elif error_message is not None:
            self._last_error = error_message
        else:
            self._last_error = "Unknown connection failure"

        logger.warning("LiveKit connection failure: %s", self._last_error)

        # Manually increment failure count and potentially trip the circuit
        # We can't use cb.call() since we're not wrapping a function call
        current_state = self._cb.state

        if current_state is CircuitBreakerState.CLOSED:
            # Increment failure count
            self._cb._failure_count += 1
            self._cb._last_failure_time = time.monotonic()

            if self._cb._failure_count >= self._config.failure_threshold:
                await self._cb.trip()
                logger.warning(
                    "LiveKit circuit tripped after %d failures",
                    self._cb._failure_count,
                )

        elif current_state is CircuitBreakerState.HALF_OPEN:
            # Failure in half-open immediately trips back to open
            await self._cb.trip()
            logger.warning("LiveKit circuit re-tripped from half-open state")

        # If already open, just log (timeout handles transition to half-open)
        else:
            logger.debug("LiveKit failure recorded while circuit already open")

    # -- Public API: Health queries -------------------------------------------

    def is_healthy(self) -> bool:
        """Check if LiveKit connections are healthy.

        Returns True if the circuit is CLOSED (healthy).
        Returns False if the circuit is OPEN or HALF_OPEN.

        Use this for pre-flight checks before attempting room operations.
        """
        state = self._cb.state
        return state is CircuitBreakerState.CLOSED

    def is_degraded(self) -> bool:
        """Check if connections are degraded (half-open probing).

        Returns True if the circuit is HALF_OPEN — connections may work
        but the system is still probing after a failure period.
        """
        return self._cb.state is CircuitBreakerState.HALF_OPEN

    def is_unavailable(self) -> bool:
        """Check if LiveKit is considered unavailable.

        Returns True if the circuit is OPEN — recent failures have
        exceeded the threshold and the system is waiting before retry.
        """
        return self._cb.state is CircuitBreakerState.OPEN

    @property
    def state(self) -> CircuitBreakerState:
        """Get the current circuit breaker state."""
        return self._cb.state

    @property
    def failure_count(self) -> int:
        """Get the current consecutive failure count."""
        return self._cb.failure_count

    # -- Callback management --------------------------------------------------

    def add_callback(self, callback: StateChangeCallback) -> None:
        """Add a state-change callback.

        Callbacks are invoked on CLOSED → OPEN, OPEN → HALF_OPEN,
        and HALF_OPEN → CLOSED/OPEN transitions.
        """
        self._cb.add_callback(callback)
        self._callbacks.append(callback)

    def remove_callback(self, callback: StateChangeCallback) -> None:
        """Remove a previously registered callback."""
        self._cb.remove_callback(callback)
        self._callbacks = [c for c in self._callbacks if c is not callback]

    # -- Diagnostics ----------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        """Get a snapshot of monitor state for health endpoints.

        Returns a dict with circuit breaker state plus LiveKit-specific
        metrics like last success/failure times.
        """
        cb_snapshot = self._cb.snapshot()
        return {
            **cb_snapshot,
            "last_success_time": self._last_success_time,
            "last_failure_time": self._last_failure_time,
            "last_error": self._last_error,
            "total_successes": self._total_successes,
            "total_failures": self._total_failures,
            "is_healthy": self.is_healthy(),
            "is_degraded": self.is_degraded(),
            "is_unavailable": self.is_unavailable(),
        }

    # -- Manual control -------------------------------------------------------

    async def reset(self) -> None:
        """Force-reset the circuit to closed state.

        Use this for manual recovery after known issues are resolved.
        """
        await self._cb.reset()
        self._last_error = None
        logger.info("LiveKit monitor manually reset to healthy state")

    async def trip(self) -> None:
        """Force-trip the circuit to open state.

        Use this during known outages to prevent connection attempts.
        """
        await self._cb.trip()
        logger.warning("LiveKit monitor manually tripped to unavailable state")


# ---------------------------------------------------------------------------
# Module-level singleton access
# ---------------------------------------------------------------------------

_monitor: Optional[LiveKitMonitor] = None


def get_livekit_monitor(
    config: Optional[CircuitBreakerConfig] = None,
    on_state_change: Optional[Sequence[StateChangeCallback]] = None,
) -> LiveKitMonitor:
    """Get or create the LiveKit monitor singleton.

    On first call, creates the monitor with the provided config.
    Subsequent calls return the existing monitor (config is ignored).
    """
    global _monitor
    if _monitor is None:
        _monitor = LiveKitMonitor(
            config=config,
            on_state_change=on_state_change,
        )
    return _monitor


def clear_monitor() -> None:
    """Clear the monitor singleton (for testing)."""
    global _monitor
    _monitor = None


__all__ = [
    "LiveKitMonitor",
    "ConnectionEvent",
    "get_livekit_monitor",
    "clear_monitor",
    "CircuitBreakerState",
    "CircuitBreakerOpenError",
]
