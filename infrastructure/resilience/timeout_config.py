"""
Timeout standardization utilities for external service calls.

This module provides:
- TimeoutConfig: Centralized timeout values from settings
- with_timeout: Decorator for sync functions with timeout protection
- with_async_timeout: Decorator for async functions with asyncio.wait_for protection
- timeout context managers for ad-hoc timeout wrapping

All external I/O operations MUST be wrapped with these utilities per AGENTS.md:
"Never ignore async timeouts; wrap I/O and external calls in asyncio.wait_for()."
"""

from __future__ import annotations

import asyncio
import functools
import logging
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, TypeVar

from shared.config.settings import CONFIG

logger = logging.getLogger(__name__)

# Type variables for generic decorators
F = TypeVar("F", bound=Callable[..., Any])
T = TypeVar("T")

# Sentinel value to distinguish 'no fallback' from 'fallback=None'
_NO_FALLBACK = object()


@dataclass(frozen=True)
class TimeoutConfig:
    """
    Centralized timeout configuration values.

    All values are in seconds and sourced from shared/config/settings.py.
    Use these constants instead of hardcoding timeout values.
    """

    # Speech services
    STT: float = field(default_factory=lambda: CONFIG.get("STT_TIMEOUT_S", 2.0))
    TTS: float = field(default_factory=lambda: CONFIG.get("TTS_TIMEOUT_S", 2.0))

    # LLM services
    LLM: float = field(default_factory=lambda: CONFIG.get("LLM_TIMEOUT_S", 10.0))

    # Search services
    SEARCH: float = field(default_factory=lambda: CONFIG.get("SEARCH_TIMEOUT_S", 5.0))

    # Avatar services
    AVATAR: float = field(default_factory=lambda: CONFIG.get("AVATAR_TIMEOUT_S", 5.0))

    # LiveKit operations
    LIVEKIT: float = field(default_factory=lambda: CONFIG.get("LIVEKIT_TIMEOUT_S", 3.0))

    # Default fallback
    DEFAULT: float = field(default_factory=lambda: CONFIG.get("DEFAULT_EXTERNAL_TIMEOUT_S", 5.0))


# Global instance for convenience
_timeout_config: Optional[TimeoutConfig] = None


def get_timeout_config() -> TimeoutConfig:
    """Get the global timeout configuration instance."""
    global _timeout_config
    if _timeout_config is None:
        _timeout_config = TimeoutConfig()
    return _timeout_config


def reset_timeout_config() -> None:
    """Reset the global timeout config (for testing)."""
    global _timeout_config
    _timeout_config = None


def get_timeout(service: str) -> float:
    """
    Get timeout value for a specific service.

    Args:
        service: Service name (stt, tts, llm, search, avatar, livekit, default)

    Returns:
        Timeout in seconds
    """
    service_lower = service.lower()

    # Map service names to config keys
    timeout_map = {
        "stt": CONFIG.get("STT_TIMEOUT_S", 2.0),
        "tts": CONFIG.get("TTS_TIMEOUT_S", 2.0),
        "llm": CONFIG.get("LLM_TIMEOUT_S", 10.0),
        "search": CONFIG.get("SEARCH_TIMEOUT_S", 5.0),
        "avatar": CONFIG.get("AVATAR_TIMEOUT_S", 5.0),
        "livekit": CONFIG.get("LIVEKIT_TIMEOUT_S", 3.0),
        "default": CONFIG.get("DEFAULT_EXTERNAL_TIMEOUT_S", 5.0),
    }

    return timeout_map.get(service_lower, timeout_map["default"])


class TimeoutError(Exception):
    """Custom timeout error for service operations."""

    def __init__(
        self,
        message: str = "Operation timed out",
        service: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ):
        self.service = service
        self.timeout_seconds = timeout_seconds
        detail = f" [{service}]" if service else ""
        duration = f" after {timeout_seconds}s" if timeout_seconds else ""
        super().__init__(f"{message}{detail}{duration}")


def with_async_timeout(
    timeout: Optional[float] = None,
    service: Optional[str] = None,
    on_timeout: Optional[Callable[[], T]] = None,
) -> Callable[[F], F]:
    """
    Decorator to wrap async functions with asyncio.wait_for timeout protection.

    Args:
        timeout: Timeout in seconds. If None, uses service-specific or default timeout.
        service: Service name for timeout lookup and error messages.
        on_timeout: Optional callback to execute on timeout (returns fallback value).

    Returns:
        Decorated function with timeout protection.

    Usage:
        @with_async_timeout(service="stt")
        async def transcribe(audio: bytes) -> str:
            ...

        @with_async_timeout(timeout=5.0, service="search", on_timeout=lambda: [])
        async def search(query: str) -> list:
            ...
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Determine timeout value
            effective_timeout = timeout
            if effective_timeout is None:
                effective_timeout = get_timeout(service) if service else get_timeout("default")

            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=effective_timeout,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "Async operation timed out",
                    extra={
                        "function": func.__name__,
                        "service": service,
                        "timeout_seconds": effective_timeout,
                    },
                )
                if on_timeout is not None:
                    return on_timeout()
                raise TimeoutError(
                    message=f"Async operation '{func.__name__}' timed out",
                    service=service,
                    timeout_seconds=effective_timeout,
                )

        return wrapper  # type: ignore

    return decorator


def with_timeout(
    timeout: Optional[float] = None,
    service: Optional[str] = None,
    on_timeout: Optional[Callable[[], T]] = None,
) -> Callable[[F], F]:
    """
    Decorator to wrap sync functions with timeout protection.

    Uses ThreadPoolExecutor for cross-platform timeout support.
    For async functions, use with_async_timeout instead.

    Args:
        timeout: Timeout in seconds. If None, uses service-specific or default timeout.
        service: Service name for timeout lookup and error messages.
        on_timeout: Optional callback to execute on timeout (returns fallback value).

    Returns:
        Decorated function with timeout protection.

    Usage:
        @with_timeout(service="tts")
        def synthesize(text: str) -> bytes:
            ...
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Determine timeout value
            effective_timeout = timeout
            if effective_timeout is None:
                effective_timeout = get_timeout(service) if service else get_timeout("default")

            # Use ThreadPoolExecutor for cross-platform timeout
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func, *args, **kwargs)
                try:
                    return future.result(timeout=effective_timeout)
                except FuturesTimeoutError:
                    logger.warning(
                        "Sync operation timed out",
                        extra={
                            "function": func.__name__,
                            "service": service,
                            "timeout_seconds": effective_timeout,
                        },
                    )
                    if on_timeout is not None:
                        return on_timeout()
                    raise TimeoutError(
                        message=f"Sync operation '{func.__name__}' timed out",
                        service=service,
                        timeout_seconds=effective_timeout,
                    )

        return wrapper  # type: ignore

    return decorator


class AsyncTimeoutContext:
    """
    Async context manager for ad-hoc timeout wrapping.

    Usage:
        async with AsyncTimeoutContext(timeout=5.0, service="search"):
            result = await some_async_operation()
    """

    def __init__(
        self,
        timeout: Optional[float] = None,
        service: Optional[str] = None,
    ):
        self.timeout = timeout or get_timeout(service or "default")
        self.service = service
        self._task: Optional[asyncio.Task] = None

    async def __aenter__(self) -> "AsyncTimeoutContext":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        if exc_type is asyncio.TimeoutError:
            logger.warning(
                "Context timeout reached",
                extra={
                    "service": self.service,
                    "timeout_seconds": self.timeout,
                },
            )
            raise TimeoutError(
                message="Context operation timed out",
                service=self.service,
                timeout_seconds=self.timeout,
            )
        return False


async def run_with_timeout(
    coro: Any,
    timeout: Optional[float] = None,
    service: Optional[str] = None,
    fallback: Any = _NO_FALLBACK,
) -> Any:
    """
    Run a coroutine with timeout protection.

    Args:
        coro: Coroutine to execute
        timeout: Timeout in seconds
        service: Service name for timeout lookup
        fallback: Value to return on timeout (if not provided, raises TimeoutError)

    Returns:
        Result of the coroutine or fallback value

    Usage:
        result = await run_with_timeout(
            fetch_data(),
            service="search",
            fallback=[]
        )
    """
    effective_timeout = timeout
    if effective_timeout is None:
        effective_timeout = get_timeout(service) if service else get_timeout("default")

    try:
        return await asyncio.wait_for(coro, timeout=effective_timeout)
    except asyncio.TimeoutError:
        logger.warning(
            "run_with_timeout timed out",
            extra={
                "service": service,
                "timeout_seconds": effective_timeout,
            },
        )
        if fallback is not _NO_FALLBACK:
            return fallback
        raise TimeoutError(
            message="Operation timed out",
            service=service,
            timeout_seconds=effective_timeout,
        )


def run_sync_with_timeout(
    func: Callable[..., T],
    *args: Any,
    timeout: Optional[float] = None,
    service: Optional[str] = None,
    fallback: Any = _NO_FALLBACK,
    **kwargs: Any,
) -> T:
    """
    Run a sync function with timeout protection.

    Args:
        func: Function to execute
        *args: Positional arguments for func
        timeout: Timeout in seconds
        service: Service name for timeout lookup
        fallback: Value to return on timeout (if not provided, raises TimeoutError)
        **kwargs: Keyword arguments for func

    Returns:
        Result of the function or fallback value

    Usage:
        result = run_sync_with_timeout(
            blocking_operation,
            arg1, arg2,
            service="tts",
            fallback=b""
        )
    """
    effective_timeout = timeout
    if effective_timeout is None:
        effective_timeout = get_timeout(service) if service else get_timeout("default")

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=effective_timeout)
        except FuturesTimeoutError:
            logger.warning(
                "run_sync_with_timeout timed out",
                extra={
                    "function": func.__name__,
                    "service": service,
                    "timeout_seconds": effective_timeout,
                },
            )
            if fallback is not _NO_FALLBACK:
                return fallback
            raise TimeoutError(
                message=f"Sync operation '{func.__name__}' timed out",
                service=service,
                timeout_seconds=effective_timeout,
            )


__all__ = [
    # Config
    "TimeoutConfig",
    "get_timeout_config",
    "reset_timeout_config",
    "get_timeout",
    # Errors
    "TimeoutError",
    # Decorators
    "with_async_timeout",
    "with_timeout",
    # Context managers
    "AsyncTimeoutContext",
    # Utility functions
    "run_with_timeout",
    "run_sync_with_timeout",
]
