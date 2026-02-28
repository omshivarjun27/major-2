"""Deepgram STT resilience wrapper.

Provides passive health monitoring for the Deepgram STT service accessed
via LiveKit plugins. Since we cannot intercept LiveKit SDK calls directly,
this wrapper tracks health based on events reported by the agent layer.

Architecture constraint: imports from shared/ and infrastructure/resilience/ only.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Sequence

from infrastructure.resilience.circuit_breaker import (
    CircuitBreakerConfig,
    CircuitBreakerState,
    StateChangeCallback,
    register_circuit_breaker,
)

logger = logging.getLogger("resilience.deepgram")

# Service-specific defaults
_DEEPGRAM_CONFIG = CircuitBreakerConfig(
    failure_threshold=3,
    reset_timeout_s=15.0,  # Tight timeout for real-time STT
    half_open_max_calls=1,
    success_threshold=1,
)

SERVICE_NAME = "deepgram"


class DeepgramResilience:
    """Passive health monitor for Deepgram STT via circuit breaker.

    Since Deepgram is accessed through LiveKit plugins (not direct HTTP),
    this class does not intercept actual STT calls. Instead, the agent layer
    reports success/failure events, and this class tracks health via the
    global circuit breaker registry.
    """

    def __init__(
        self,
        config: Optional[CircuitBreakerConfig] = None,
        on_state_change: Optional[Sequence[StateChangeCallback]] = None,
    ) -> None:
        self._cb = register_circuit_breaker(
            SERVICE_NAME,
            config=config or _DEEPGRAM_CONFIG,
            on_state_change=on_state_change,
        )

    @property
    def is_available(self) -> bool:
        """True when STT should be attempted (circuit not OPEN)."""
        return self._cb.state is not CircuitBreakerState.OPEN

    @property
    def state(self) -> CircuitBreakerState:
        """Current circuit breaker state."""
        return self._cb.state

    async def record_success(self) -> None:
        """Record a successful STT transcription."""
        await self._ensure_half_open_transition()
        await self._cb._on_success()

    async def record_failure(self, exc: Optional[BaseException] = None) -> None:
        """Record a failed STT transcription."""
        await self._ensure_half_open_transition()
        error = exc or RuntimeError("Deepgram STT failure")
        await self._cb._on_failure(error)

    async def reset(self) -> None:
        """Force-close the circuit (manual recovery)."""
        await self._cb.reset()

    async def trip(self) -> None:
        """Force-open the circuit (known outage)."""
        await self._cb.trip()

    def health(self) -> Dict[str, Any]:
        """Snapshot for health endpoints."""
        return self._cb.snapshot()

    def add_callback(self, cb: StateChangeCallback) -> None:
        """Register a state-change listener."""
        self._cb.add_callback(cb)

    def remove_callback(self, cb: StateChangeCallback) -> None:
        """Remove a previously registered listener."""
        self._cb.remove_callback(cb)

    async def _ensure_half_open_transition(self) -> None:
        """Trigger lazy OPEN -> HALF_OPEN transition if reset timeout elapsed.

        The underlying CircuitBreaker only transitions lazily inside call().
        Since we bypass call() for passive monitoring, we must trigger it
        explicitly before recording success/failure events.
        """
        async with self._cb._lock:
            self._cb._maybe_transition_to_half_open()
            pending = self._cb._pending_half_open_event
            self._cb._pending_half_open_event = None
        if pending:
            await self._cb._emit(*pending)
