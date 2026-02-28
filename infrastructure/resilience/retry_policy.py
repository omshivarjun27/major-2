"""Reusable retry mechanism with exponential backoff and jitter.

Provides a decorator and callable wrapper for retrying async operations
with configurable parameters.  Integrates with the circuit breaker so
retries only occur while the circuit is CLOSED or HALF_OPEN.

Architecture constraint: imports from ``shared/`` only (plus sibling
resilience modules within ``infrastructure/resilience/``).

Usage::

    @with_retry("deepgram", max_retries=2, base_delay_s=0.5)
    async def call_deepgram(audio: bytes) -> str:
        ...

    # — or programmatic —
    policy = RetryPolicy(max_retries=3, base_delay_s=1.0)
    result = await policy.execute(some_fn, arg1, service_name="ollama")
"""

from __future__ import annotations

import asyncio
import functools
import logging
import random
from dataclasses import dataclass
from typing import Any, Callable, Optional

from infrastructure.resilience.circuit_breaker import (
    CircuitBreakerOpenError,
    get_circuit_breaker,
)
from infrastructure.resilience.error_classifier import (
    classify_error,
)
from shared.config.settings import get_retry_config as get_retry_config_from_settings

logger = logging.getLogger("resilience.retry_policy")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RetryConfig:
    """Immutable retry configuration."""

    max_retries: int = 3
    """Maximum number of retry attempts (0 = no retries)."""

    base_delay_s: float = 1.0
    """Base delay between retries (seconds)."""

    max_delay_s: float = 30.0
    """Maximum delay cap (seconds)."""

    jitter_factor: float = 0.5
    """Jitter factor (0.0 = no jitter, 1.0 = full jitter)."""

    retry_on: tuple[type[BaseException], ...] = (Exception,)
    """Exception types eligible for retry."""

    no_retry_on: tuple[type[BaseException], ...] = ()
    """Exception types that should never be retried."""


# ---------------------------------------------------------------------------
# Retry policy
# ---------------------------------------------------------------------------


class RetryPolicy:
    """Async retry executor with exponential backoff, jitter, and
    circuit-breaker awareness.
    """

    def __init__(self, config: Optional[RetryConfig] = None) -> None:
        self.config = config or RetryConfig()

    async def execute(
        self,
        func: Callable[..., Any],
        *args: Any,
        service_name: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Execute *func* with retries according to the configured policy.

        If a circuit breaker is registered for *service_name*, retries
        are skipped when the circuit is OPEN.
        """
        last_exception: Optional[BaseException] = None
        attempts = self.config.max_retries + 1  # initial + retries

        for attempt in range(1, attempts + 1):
            try:
                return await func(*args, **kwargs)
            except CircuitBreakerOpenError:
                raise  # Never retry when circuit is open
            except BaseException as exc:
                last_exception = exc

                # Check if this exception type should NOT be retried
                if isinstance(exc, self.config.no_retry_on):
                    raise

                # Check if this exception type is eligible for retry
                if not isinstance(exc, self.config.retry_on):
                    raise

                # Classify the error for backoff adjustment
                classification = classify_error(exc, service_name=service_name)

                # Don't retry permanent or auth errors
                if not classification.should_retry:
                    raise

                # Check if circuit breaker is open (skip retry)
                if service_name:
                    cb = get_circuit_breaker(service_name)
                    if cb and cb.is_open:
                        logger.debug(
                            "Skipping retry for '%s' — circuit is OPEN",
                            service_name,
                        )
                        raise

                # Last attempt — don't sleep, just raise
                if attempt >= attempts:
                    break

                # Calculate delay with exponential backoff + jitter
                delay = self._compute_delay(attempt, classification.backoff_multiplier)
                logger.info(
                    "Retry %d/%d for '%s' after %.2fs (%s: %s)",
                    attempt,
                    self.config.max_retries,
                    service_name or "unknown",
                    delay,
                    classification.category.value,
                    exc,
                )
                await asyncio.sleep(delay)

        # All retries exhausted
        assert last_exception is not None
        raise last_exception

    def _compute_delay(self, attempt: int, backoff_multiplier: float) -> float:
        """Exponential backoff with jitter.

        delay = min(base * 2^(attempt-1) * multiplier, max_delay)
        jitter = delay * jitter_factor * random()
        """
        exp_delay = self.config.base_delay_s * (2 ** (attempt - 1))
        adjusted = exp_delay * backoff_multiplier
        capped = min(adjusted, self.config.max_delay_s)

        if self.config.jitter_factor > 0:
            jitter = capped * self.config.jitter_factor * random.random()
            return capped - jitter + (jitter * random.random())
        return capped


def _get_service_retry_config(service_name: str) -> RetryConfig:
    """Get retry config for a service, reading from centralized settings.

    First checks if there's a config in settings.py, then falls back to
    hardcoded SERVICE_RETRY_CONFIGS for backwards compatibility.
    """
    # Try to get from centralized config first
    cfg = get_retry_config_from_settings(service_name)
    return RetryConfig(
        max_retries=cfg["max_retries"],
        base_delay_s=cfg["base_delay_s"],
        max_delay_s=cfg["max_delay_s"],
    )


# Legacy hardcoded configs - these are now fallbacks for services
# not explicitly configured in settings.py
SERVICE_RETRY_CONFIGS: dict[str, RetryConfig] = {
    # Real-time services: fewer retries, shorter delays
    "deepgram": RetryConfig(max_retries=2, base_delay_s=0.5, max_delay_s=5.0),
    "livekit": RetryConfig(max_retries=2, base_delay_s=0.5, max_delay_s=5.0),
    # Batch services: more patience
    "ollama_reasoning": RetryConfig(max_retries=3, base_delay_s=1.0, max_delay_s=30.0),
    "ollama_embedding": RetryConfig(max_retries=3, base_delay_s=1.0, max_delay_s=15.0),
    "ollama": RetryConfig(max_retries=3, base_delay_s=1.0, max_delay_s=30.0),  # Alias
    "duckduckgo": RetryConfig(max_retries=3, base_delay_s=1.0, max_delay_s=15.0),
    "elevenlabs": RetryConfig(max_retries=2, base_delay_s=0.5, max_delay_s=10.0),
    # Optional services: minimal retries
    "tavus": RetryConfig(max_retries=1, base_delay_s=1.0, max_delay_s=5.0),
}


def get_retry_policy(service_name: str) -> RetryPolicy:
    """Return a RetryPolicy configured for the named service.

    Reads configuration from shared/config/settings.py first,
    falling back to hardcoded defaults if not found.
    """
    config = _get_service_retry_config(service_name)
    return RetryPolicy(config)


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------


def with_retry(
    service_name: str,
    *,
    max_retries: Optional[int] = None,
    base_delay_s: Optional[float] = None,
    max_delay_s: Optional[float] = None,
    jitter_factor: Optional[float] = None,
) -> Callable[..., Any]:
    """Decorator that adds retry logic to an ``async def``.

    Uses per-service defaults from centralized config (shared/config/settings.py)
    unless overrides are provided.

    Example::

        @with_retry("deepgram")  # Uses config defaults
        async def transcribe(audio: bytes) -> str:
            ...

        @with_retry("custom", max_retries=5, base_delay_s=2.0)
        async def custom_service():
            ...
    """
    base_config = _get_service_retry_config(service_name)
    config = RetryConfig(
        max_retries=max_retries if max_retries is not None else base_config.max_retries,
        base_delay_s=base_delay_s if base_delay_s is not None else base_config.base_delay_s,
        max_delay_s=max_delay_s if max_delay_s is not None else base_config.max_delay_s,
        jitter_factor=jitter_factor if jitter_factor is not None else base_config.jitter_factor,
    )
    policy = RetryPolicy(config)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await policy.execute(func, *args, service_name=service_name, **kwargs)

        wrapper.retry_service = service_name  # type: ignore[attr-defined]
        wrapper.retry_config = config  # type: ignore[attr-defined]
        return wrapper

    return decorator
