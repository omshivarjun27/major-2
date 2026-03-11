"""Request correlation and tracing support for structured logging.

Provides async-safe correlation ID management that propagates through
the entire request pipeline from STT input to TTS output.

Task: T-094 - Structured Logging Enhancement
"""

from __future__ import annotations

import contextvars
import functools
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, TypeVar

# Async-safe context variables for correlation
_correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default=""
)
_session_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "session_id", default=""
)
_service_name: contextvars.ContextVar[str] = contextvars.ContextVar(
    "service_name", default="voice-vision"
)
_span_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "span_id", default=""
)
_parent_span_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "parent_span_id", default=""
)

T = TypeVar("T")


def generate_correlation_id() -> str:
    """Generate a new correlation ID.

    Returns:
        UUID-based correlation ID prefixed with 'cor_'
    """
    return f"cor_{uuid.uuid4().hex[:16]}"


def generate_span_id() -> str:
    """Generate a new span ID.

    Returns:
        UUID-based span ID prefixed with 'span_'
    """
    return f"span_{uuid.uuid4().hex[:12]}"


def get_correlation_id() -> str:
    """Get the current correlation ID.

    Returns:
        Current correlation ID or empty string if not set
    """
    return _correlation_id.get()


def set_correlation_id(correlation_id: str) -> contextvars.Token[str]:
    """Set the correlation ID for the current context.

    Args:
        correlation_id: The correlation ID to set

    Returns:
        Token that can be used to reset the value
    """
    return _correlation_id.set(correlation_id)


def get_session_id() -> str:
    """Get the current session ID."""
    return _session_id.get()


def set_session_id(session_id: str) -> contextvars.Token[str]:
    """Set the session ID for the current context."""
    return _session_id.set(session_id)


def get_service_name() -> str:
    """Get the current service name."""
    return _service_name.get()


def set_service_name(service_name: str) -> contextvars.Token[str]:
    """Set the service name for the current context."""
    return _service_name.set(service_name)


def get_span_id() -> str:
    """Get the current span ID."""
    return _span_id.get()


def get_parent_span_id() -> str:
    """Get the current parent span ID."""
    return _parent_span_id.get()


@dataclass
class LogContext:
    """Logging context with correlation and tracing information.

    Use as a context manager to automatically set and reset context:

        async with LogContext(correlation_id="cor_abc123", session_id="ses_xyz"):
            # All logs in this block will include correlation_id and session_id
            logger.info("Processing request")
    """

    correlation_id: str = ""
    session_id: str = ""
    service_name: str = ""
    span_id: str = ""
    parent_span_id: str = ""

    # Internal tokens for cleanup
    _tokens: Dict[str, Any] = field(default_factory=dict, repr=False)

    def __enter__(self) -> "LogContext":
        """Enter context and set context variables."""
        if self.correlation_id:
            self._tokens["correlation_id"] = _correlation_id.set(self.correlation_id)
        elif not get_correlation_id():
            # Auto-generate if not provided and none exists
            self._tokens["correlation_id"] = _correlation_id.set(generate_correlation_id())
            self.correlation_id = get_correlation_id()

        if self.session_id:
            self._tokens["session_id"] = _session_id.set(self.session_id)

        if self.service_name:
            self._tokens["service_name"] = _service_name.set(self.service_name)

        if self.span_id:
            self._tokens["span_id"] = _span_id.set(self.span_id)
        elif not get_span_id():
            self._tokens["span_id"] = _span_id.set(generate_span_id())
            self.span_id = get_span_id()

        if self.parent_span_id:
            self._tokens["parent_span_id"] = _parent_span_id.set(self.parent_span_id)

        return self

    def __exit__(self, *exc_info: Any) -> None:
        """Exit context and reset context variables."""
        for key, token in self._tokens.items():
            getattr(globals()[f"_{key}"], "reset")(token)

    async def __aenter__(self) -> "LogContext":
        """Async enter context."""
        return self.__enter__()

    async def __aexit__(self, *exc_info: Any) -> None:
        """Async exit context."""
        return self.__exit__(*exc_info)

    def child_context(self, **overrides: Any) -> "LogContext":
        """Create a child context inheriting current values.

        The child gets a new span_id with current span as parent.

        Args:
            **overrides: Values to override in child context

        Returns:
            New LogContext with inherited and overridden values
        """
        return LogContext(
            correlation_id=overrides.get("correlation_id", self.correlation_id or get_correlation_id()),
            session_id=overrides.get("session_id", self.session_id or get_session_id()),
            service_name=overrides.get("service_name", self.service_name or get_service_name()),
            span_id=generate_span_id(),
            parent_span_id=self.span_id or get_span_id(),
        )

    def to_dict(self) -> Dict[str, str]:
        """Convert context to dictionary for logging extra."""
        return {
            k: v for k, v in {
                "correlation_id": self.correlation_id or get_correlation_id(),
                "session_id": self.session_id or get_session_id(),
                "service_name": self.service_name or get_service_name(),
                "span_id": self.span_id or get_span_id(),
                "parent_span_id": self.parent_span_id or get_parent_span_id(),
            }.items() if v
        }


class CorrelatedLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that automatically includes correlation context.

    Usage:
        logger = get_correlated_logger("my-component")
        logger.info("Processing request")  # Automatically includes correlation_id, etc.
    """

    def process(
        self,
        msg: str,
        kwargs: Dict[str, Any],
    ) -> tuple[str, Dict[str, Any]]:
        """Process log record to include correlation context."""
        extra = kwargs.get("extra", {})

        # Add correlation context if not already present
        if "correlation_id" not in extra:
            cid = get_correlation_id()
            if cid:
                extra["correlation_id"] = cid

        if "session_id" not in extra:
            sid = get_session_id()
            if sid:
                extra["session_id"] = sid

        if "service_name" not in extra:
            svc = get_service_name()
            if svc:
                extra["service_name"] = svc

        if "span_id" not in extra:
            span = get_span_id()
            if span:
                extra["span_id"] = span

        if "parent_span_id" not in extra:
            pspan = get_parent_span_id()
            if pspan:
                extra["parent_span_id"] = pspan

        kwargs["extra"] = extra
        return msg, kwargs


def get_correlated_logger(name: str) -> CorrelatedLoggerAdapter:
    """Get a logger that automatically includes correlation context.

    Args:
        name: Logger name (e.g., "vqa-pipeline", "speech-stt")

    Returns:
        Logger adapter with automatic correlation context
    """
    return CorrelatedLoggerAdapter(logging.getLogger(name), {})


def correlated(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator that ensures function runs with correlation context.

    If no correlation ID exists, generates one. Useful for entry points.

    Usage:
        @correlated
        def handle_request(request):
            # Correlation ID is now available
            logger.info("Handling request")
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        if not get_correlation_id():
            with LogContext():
                return func(*args, **kwargs)
        return func(*args, **kwargs)

    @functools.wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> T:
        if not get_correlation_id():
            async with LogContext():
                return await func(*args, **kwargs)
        return await func(*args, **kwargs)

    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper  # type: ignore
    return wrapper


def with_span(span_name: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator that creates a child span for the function.

    Args:
        span_name: Name for the span (included in logs)

    Usage:
        @with_span("vision-detection")
        async def detect_objects(frame):
            # Runs in child span context
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            parent_span = get_span_id()
            new_span = generate_span_id()

            token_span = _span_id.set(new_span)
            token_parent = _parent_span_id.set(parent_span)

            logger = get_correlated_logger(span_name)
            logger.debug(f"Starting span: {span_name}")

            try:
                return func(*args, **kwargs)
            finally:
                logger.debug(f"Ending span: {span_name}")
                _span_id.reset(token_span)
                _parent_span_id.reset(token_parent)

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            parent_span = get_span_id()
            new_span = generate_span_id()

            token_span = _span_id.set(new_span)
            token_parent = _parent_span_id.set(parent_span)

            logger = get_correlated_logger(span_name)
            logger.debug(f"Starting span: {span_name}")

            try:
                return await func(*args, **kwargs)
            finally:
                logger.debug(f"Ending span: {span_name}")
                _span_id.reset(token_span)
                _parent_span_id.reset(token_parent)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return wrapper

    return decorator


# ─────────────────────────────────────────────────────────────────────────────
# Request Context Middleware (for FastAPI/Starlette)
# ─────────────────────────────────────────────────────────────────────────────

async def correlation_middleware(request: Any, call_next: Callable) -> Any:
    """FastAPI/Starlette middleware for correlation ID management.

    Extracts correlation ID from X-Correlation-ID header or generates new one.
    Sets correlation context for the entire request lifecycle.
    Adds correlation ID to response headers.

    Usage (FastAPI):
        from starlette.middleware.base import BaseHTTPMiddleware
        app.add_middleware(BaseHTTPMiddleware, dispatch=correlation_middleware)
    """
    # Extract or generate correlation ID
    correlation_id = request.headers.get("X-Correlation-ID", "")
    if not correlation_id:
        correlation_id = generate_correlation_id()

    # Extract session ID if present
    session_id = request.headers.get("X-Session-ID", "")

    async with LogContext(
        correlation_id=correlation_id,
        session_id=session_id,
        service_name="voice-vision-api",
    ):
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response


# ─────────────────────────────────────────────────────────────────────────────
# Enhanced Log Event with Correlation
# ─────────────────────────────────────────────────────────────────────────────

def log_correlated_event(
    logger_name: str,
    event: str,
    *,
    level: int = logging.INFO,
    component: Optional[str] = None,
    frame_id: Optional[str] = None,
    latency_ms: Optional[float] = None,
    **kwargs: Any,
) -> None:
    """Emit a structured event log with automatic correlation context.

    Like log_event() but automatically includes correlation_id, session_id,
    span_id, and service_name from the current context.

    Example:
        log_correlated_event("vqa-pipeline", "detection_complete",
                            component="yolo", latency_ms=45.2)
    """
    logger = get_correlated_logger(logger_name)

    extra: Dict[str, Any] = {"event": event}
    if component is not None:
        extra["component"] = component
    if frame_id is not None:
        extra["frame_id"] = frame_id
    if latency_ms is not None:
        extra["latency_ms"] = round(latency_ms, 2)
    extra.update(kwargs)

    logger.log(level, event, extra=extra)
