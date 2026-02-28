"""Circuit breaker pattern for external service resilience.

Implements a three-state circuit breaker (CLOSED → OPEN → HALF_OPEN → CLOSED)
with configurable failure thresholds, reset timeouts, event callbacks, and
metrics hooks.  Designed for async-first usage in the real-time pipeline.

Architecture constraint: imports from ``shared/`` only.

Usage::

    cb = CircuitBreaker("deepgram", CircuitBreakerConfig(failure_threshold=3))
    result = await cb.call(some_async_fn, arg1, arg2)

    # — or via decorator —
    @with_circuit_breaker("deepgram", failure_threshold=3, reset_timeout_s=30)
    async def call_deepgram(audio: bytes) -> str:
        ...
"""

from __future__ import annotations

import asyncio
import enum
import functools
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Sequence

from shared.config.settings import get_circuit_breaker_config

logger = logging.getLogger("resilience.circuit_breaker")


# ---------------------------------------------------------------------------
# State enum
# ---------------------------------------------------------------------------


class CircuitBreakerState(enum.Enum):
    """Three canonical circuit-breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CircuitBreakerConfig:
    """Immutable configuration for a single circuit breaker."""

    failure_threshold: int = 3
    """Consecutive failures required to trip the circuit from CLOSED to OPEN."""

    reset_timeout_s: float = 30.0
    """Seconds the circuit stays OPEN before transitioning to HALF_OPEN."""

    half_open_max_calls: int = 1
    """Probe calls allowed while HALF_OPEN."""

    success_threshold: int = 1
    """Consecutive successes in HALF_OPEN required to return to CLOSED."""

    excluded_exceptions: tuple[type[BaseException], ...] = ()
    """Exception types that do NOT count as failures (e.g. validation errors)."""


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class CircuitBreakerError(Exception):
    """Base exception for circuit-breaker related errors."""


class CircuitBreakerOpenError(CircuitBreakerError):
    """Raised when a call is rejected because the circuit is OPEN."""

    def __init__(self, service_name: str, open_since: float) -> None:
        elapsed = time.monotonic() - open_since
        super().__init__(f"Circuit breaker '{service_name}' is OPEN (tripped {elapsed:.1f}s ago)")
        self.service_name = service_name
        self.open_since = open_since


# ---------------------------------------------------------------------------
# State-change event
# ---------------------------------------------------------------------------


@dataclass
class StateChangeEvent:
    """Payload emitted on every state transition."""

    service_name: str
    previous_state: CircuitBreakerState
    new_state: CircuitBreakerState
    failure_count: int
    timestamp: float = field(default_factory=time.time)


# Callback signature: async or sync function accepting a StateChangeEvent
StateChangeCallback = Callable[[StateChangeEvent], Any]


# ---------------------------------------------------------------------------
# Circuit breaker implementation
# ---------------------------------------------------------------------------


class CircuitBreaker:
    """Async-safe circuit breaker for a named external service.

    Thread safety is achieved through ``asyncio.Lock``; the breaker must
    be used within a single event loop.
    """

    def __init__(
        self,
        service_name: str,
        config: Optional[CircuitBreakerConfig] = None,
        on_state_change: Optional[Sequence[StateChangeCallback]] = None,
        metrics: Optional[Any] = None,
    ) -> None:
        self.service_name = service_name
        self.config = config or CircuitBreakerConfig()

        # Internal mutable state (guarded by _lock)
        self._state = CircuitBreakerState.CLOSED
        self._failure_count: int = 0
        self._success_count: int = 0
        self._half_open_calls: int = 0
        self._opened_at: float = 0.0
        self._last_failure_time: float = 0.0
        self._pending_half_open_event: Optional[tuple[CircuitBreakerState, CircuitBreakerState]] = None

        self._lock = asyncio.Lock()
        self._callbacks: list[StateChangeCallback] = list(on_state_change or [])

        # Optional MetricsCollector (from infrastructure.monitoring)
        self._metrics = metrics

    # -- public read-only properties ----------------------------------------

    @property
    def state(self) -> CircuitBreakerState:
        """Current breaker state (may be stale by one reset-timeout tick)."""
        if (
            self._state is CircuitBreakerState.OPEN
            and (time.monotonic() - self._opened_at) >= self.config.reset_timeout_s
        ):
            # Lazily transition to HALF_OPEN on read — actual transition
            # happens inside ``call()`` under the lock.
            return CircuitBreakerState.HALF_OPEN
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    @property
    def is_closed(self) -> bool:
        return self.state is CircuitBreakerState.CLOSED

    @property
    def is_open(self) -> bool:
        return self.state is CircuitBreakerState.OPEN

    # -- core call method ---------------------------------------------------

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute *func* through the circuit breaker.

        Raises ``CircuitBreakerOpenError`` when the circuit is OPEN and
        the reset timeout has not elapsed.
        """
        async with self._lock:
            self._maybe_transition_to_half_open()
            pending_event = self._pending_half_open_event
            self._pending_half_open_event = None

            if self._state is CircuitBreakerState.OPEN:
                self._record_metric("rejected")
                raise CircuitBreakerOpenError(self.service_name, self._opened_at)

            if (
                self._state is CircuitBreakerState.HALF_OPEN
                and self._half_open_calls >= self.config.half_open_max_calls
            ):
                self._record_metric("rejected")
                raise CircuitBreakerOpenError(self.service_name, self._opened_at)

            if self._state is CircuitBreakerState.HALF_OPEN:
                self._half_open_calls += 1

        # Emit pending half-open callback outside the lock
        if pending_event:
            await self._emit(*pending_event)
        # Execute outside lock to avoid blocking other callers
        try:
            result = await func(*args, **kwargs)
        except BaseException as exc:
            if not isinstance(exc, self.config.excluded_exceptions):
                await self._on_failure(exc)
            raise
        else:
            await self._on_success()
            return result

    # -- manual state control -----------------------------------------------

    async def reset(self) -> None:
        """Force-close the circuit (e.g. after manual recovery)."""
        async with self._lock:
            prev = self._state
            self._state = CircuitBreakerState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._half_open_calls = 0
            if prev is not CircuitBreakerState.CLOSED:
                await self._emit(prev, CircuitBreakerState.CLOSED)

    async def trip(self) -> None:
        """Force-open the circuit (e.g. during known outage)."""
        async with self._lock:
            prev = self._state
            self._state = CircuitBreakerState.OPEN
            self._opened_at = time.monotonic()
            self._failure_count = self.config.failure_threshold
            if prev is not CircuitBreakerState.OPEN:
                await self._emit(prev, CircuitBreakerState.OPEN)

    # -- callback management ------------------------------------------------

    def add_callback(self, cb: StateChangeCallback) -> None:
        """Register a state-change listener."""
        self._callbacks.append(cb)

    def remove_callback(self, cb: StateChangeCallback) -> None:
        """Remove a previously registered listener."""
        self._callbacks = [c for c in self._callbacks if c is not cb]

    # -- snapshot for health endpoints --------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        """Non-blocking snapshot for health/status endpoints."""
        return {
            "service": self.service_name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "reset_timeout_s": self.config.reset_timeout_s,
            },
        }

    # -- internal helpers ---------------------------------------------------

    def _maybe_transition_to_half_open(self) -> None:
        """Must be called under ``_lock``."""
        if self._state is not CircuitBreakerState.OPEN:
            return
        elapsed = time.monotonic() - self._opened_at
        if elapsed >= self.config.reset_timeout_s:
            prev = self._state
            self._state = CircuitBreakerState.HALF_OPEN
            self._half_open_calls = 0
            self._success_count = 0
            logger.info(
                "Circuit '%s' OPEN → HALF_OPEN after %.1fs",
                self.service_name,
                elapsed,
            )
            # Store pending callback to emit after lock release
            self._pending_half_open_event = (prev, CircuitBreakerState.HALF_OPEN)

    async def _on_success(self) -> None:
        async with self._lock:
            if self._state is CircuitBreakerState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    prev = self._state
                    self._state = CircuitBreakerState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    self._half_open_calls = 0
                    logger.info(
                        "Circuit '%s' HALF_OPEN → CLOSED (recovered)",
                        self.service_name,
                    )
                    self._record_metric("recovered")
                    await self._emit(prev, CircuitBreakerState.CLOSED)
            elif self._state is CircuitBreakerState.CLOSED:
                # Reset consecutive failure counter on success
                self._failure_count = 0
            self._record_metric("success")

    async def _on_failure(self, exc: BaseException) -> None:
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            self._record_metric("failure")

            if self._state is CircuitBreakerState.HALF_OPEN:
                # Any failure in half-open re-opens the circuit
                prev = self._state
                self._state = CircuitBreakerState.OPEN
                self._opened_at = time.monotonic()
                self._half_open_calls = 0
                logger.warning(
                    "Circuit '%s' HALF_OPEN → OPEN (probe failed: %s)",
                    self.service_name,
                    exc,
                )
                self._record_metric("tripped")
                await self._emit(prev, CircuitBreakerState.OPEN)

            elif self._state is CircuitBreakerState.CLOSED and self._failure_count >= self.config.failure_threshold:
                prev = self._state
                self._state = CircuitBreakerState.OPEN
                self._opened_at = time.monotonic()
                logger.warning(
                    "Circuit '%s' CLOSED → OPEN after %d failures (last: %s)",
                    self.service_name,
                    self._failure_count,
                    exc,
                )
                self._record_metric("tripped")
                await self._emit(prev, CircuitBreakerState.OPEN)

    async def _emit(self, prev: CircuitBreakerState, new: CircuitBreakerState) -> None:
        """Fire all registered callbacks (async or sync)."""
        event = StateChangeEvent(
            service_name=self.service_name,
            previous_state=prev,
            new_state=new,
            failure_count=self._failure_count,
        )
        for cb in self._callbacks:
            try:
                result = cb(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                logger.exception("Callback error for circuit '%s'", self.service_name)

    def _record_metric(self, event_type: str) -> None:
        """Record metric if a MetricsCollector was provided."""
        if self._metrics is None:
            return
        try:
            metric_name = f"circuit_breaker.{self.service_name}.{event_type}"
            self._metrics.increment(metric_name)
            self._metrics.gauge(
                f"circuit_breaker.{self.service_name}.state",
                {"closed": 0, "open": 1, "half_open": 2}.get(self._state.value, -1),
            )
        except Exception:
            pass  # metrics must never break the circuit breaker


# ---------------------------------------------------------------------------
# Global registry
# ---------------------------------------------------------------------------

_registry: Dict[str, CircuitBreaker] = {}
_registry_lock = asyncio.Lock()


def get_circuit_breaker(service_name: str) -> Optional[CircuitBreaker]:
    """Look up a registered circuit breaker by service name.

    Returns ``None`` if no breaker is registered for *service_name*.
    """
    return _registry.get(service_name)


def register_circuit_breaker(
    service_name: str,
    config: Optional[CircuitBreakerConfig] = None,
    on_state_change: Optional[Sequence[StateChangeCallback]] = None,
    metrics: Optional[Any] = None,
    use_config: bool = True,
) -> CircuitBreaker:
    """Create, register, and return a circuit breaker for *service_name*.

    If a breaker already exists for that name, it is returned as-is.

    Args:
        service_name: Unique name for this circuit breaker
        config: Optional explicit config. If None and use_config=True,
                reads from shared/config/settings.py
        on_state_change: Optional callbacks for state transitions
        metrics: Optional MetricsCollector for observability
        use_config: If True and config is None, read from centralized config
    """
    if service_name in _registry:
        return _registry[service_name]

    # If no explicit config provided, try to read from centralized config
    if config is None and use_config:
        cfg = get_circuit_breaker_config(service_name)
        config = CircuitBreakerConfig(
            failure_threshold=cfg["failure_threshold"],
            reset_timeout_s=cfg["reset_timeout_s"],
        )

    cb = CircuitBreaker(
        service_name=service_name,
        config=config,
        on_state_change=on_state_change,
        metrics=metrics,
    )
    _registry[service_name] = cb
    logger.info(
        "Registered circuit breaker: %s (threshold=%d, reset=%.1fs)",
        service_name,
        cb.config.failure_threshold,
        cb.config.reset_timeout_s,
    )
    return cb


def get_all_breakers() -> Dict[str, CircuitBreaker]:
    """Return a read-only view of all registered circuit breakers."""
    return dict(_registry)


def clear_registry() -> None:
    """Remove all registered breakers (for testing)."""
    _registry.clear()


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------


def with_circuit_breaker(
    service_name: str,
    *,
    failure_threshold: Optional[int] = None,
    reset_timeout_s: Optional[float] = None,
    half_open_max_calls: int = 1,
    success_threshold: int = 1,
    excluded_exceptions: tuple[type[BaseException], ...] = (),
) -> Callable[..., Any]:
    """Decorator that wraps an ``async def`` in a per-service circuit breaker.

    The circuit breaker is lazily registered in the global registry on
    first invocation. If failure_threshold or reset_timeout_s are not
    provided, they are read from centralized config.

    Example::

        @with_circuit_breaker("elevenlabs")  # Uses config defaults
        async def synthesize_speech(text: str) -> bytes:
            ...

        @with_circuit_breaker("custom", failure_threshold=5, reset_timeout_s=60)
        async def custom_service():
            ...
    """
    # Read defaults from config if not explicitly provided
    cfg = get_circuit_breaker_config(service_name)
    config = CircuitBreakerConfig(
        failure_threshold=failure_threshold if failure_threshold is not None else cfg["failure_threshold"],
        reset_timeout_s=reset_timeout_s if reset_timeout_s is not None else cfg["reset_timeout_s"],
        half_open_max_calls=half_open_max_calls,
        success_threshold=success_threshold,
        excluded_exceptions=excluded_exceptions,
    )

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            cb = register_circuit_breaker(service_name, config=config)
            return await cb.call(func, *args, **kwargs)

        # Expose the breaker for testing / inspection
        wrapper.circuit_breaker_service = service_name  # type: ignore[attr-defined]
        return wrapper

    return decorator
