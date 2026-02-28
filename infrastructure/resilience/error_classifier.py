"""Error classification framework for external service failures.

Categorises exceptions and HTTP status codes into actionable classes
that drive circuit-breaker and retry behaviour.

Architecture constraint: imports from ``shared/`` only.

Classification taxonomy::

    TRANSIENT   → retry (network blip, 502/503/504)
    PERMANENT   → fail fast, do NOT retry (400, 404, 422)
    RATE_LIMIT  → backoff with extended delay (429)
    AUTH        → alert, do NOT retry, do NOT trip breaker (401, 403)
    TIMEOUT     → retry with shorter patience (connect/read timeout)
    UNKNOWN     → treat as transient (safe default)
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass
from typing import Optional, Type, Union

logger = logging.getLogger("resilience.error_classifier")


# ---------------------------------------------------------------------------
# Error categories
# ---------------------------------------------------------------------------

class ErrorCategory(enum.Enum):
    """Actionable error classification."""

    TRANSIENT = "transient"
    PERMANENT = "permanent"
    RATE_LIMIT = "rate_limit"
    AUTH = "auth"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Classification result
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ErrorClassification:
    """Result of classifying an error."""

    category: ErrorCategory
    should_retry: bool
    should_count_failure: bool
    should_alert: bool
    backoff_multiplier: float = 1.0
    detail: str = ""


# Pre-built classification results for common categories
_CLASSIFICATIONS = {
    ErrorCategory.TRANSIENT: ErrorClassification(
        category=ErrorCategory.TRANSIENT,
        should_retry=True,
        should_count_failure=True,
        should_alert=False,
        backoff_multiplier=1.0,
        detail="Transient error — safe to retry",
    ),
    ErrorCategory.PERMANENT: ErrorClassification(
        category=ErrorCategory.PERMANENT,
        should_retry=False,
        should_count_failure=False,
        should_alert=False,
        backoff_multiplier=1.0,
        detail="Permanent error — do not retry",
    ),
    ErrorCategory.RATE_LIMIT: ErrorClassification(
        category=ErrorCategory.RATE_LIMIT,
        should_retry=True,
        should_count_failure=True,
        should_alert=False,
        backoff_multiplier=3.0,
        detail="Rate limited — retry with extended backoff",
    ),
    ErrorCategory.AUTH: ErrorClassification(
        category=ErrorCategory.AUTH,
        should_retry=False,
        should_count_failure=False,
        should_alert=True,
        backoff_multiplier=1.0,
        detail="Authentication error — alert operator",
    ),
    ErrorCategory.TIMEOUT: ErrorClassification(
        category=ErrorCategory.TIMEOUT,
        should_retry=True,
        should_count_failure=True,
        should_alert=False,
        backoff_multiplier=1.5,
        detail="Timeout — retry with increased patience",
    ),
    ErrorCategory.UNKNOWN: ErrorClassification(
        category=ErrorCategory.UNKNOWN,
        should_retry=True,
        should_count_failure=True,
        should_alert=False,
        backoff_multiplier=1.0,
        detail="Unknown error — treating as transient",
    ),
}


# ---------------------------------------------------------------------------
# HTTP status code mapping
# ---------------------------------------------------------------------------

_STATUS_MAP: dict[int, ErrorCategory] = {
    # Client errors
    400: ErrorCategory.PERMANENT,
    401: ErrorCategory.AUTH,
    403: ErrorCategory.AUTH,
    404: ErrorCategory.PERMANENT,
    405: ErrorCategory.PERMANENT,
    409: ErrorCategory.PERMANENT,
    410: ErrorCategory.PERMANENT,
    413: ErrorCategory.PERMANENT,
    415: ErrorCategory.PERMANENT,
    422: ErrorCategory.PERMANENT,
    429: ErrorCategory.RATE_LIMIT,
    # Server errors
    500: ErrorCategory.TRANSIENT,
    502: ErrorCategory.TRANSIENT,
    503: ErrorCategory.TRANSIENT,
    504: ErrorCategory.TIMEOUT,
}


# ---------------------------------------------------------------------------
# Exception type mapping
# ---------------------------------------------------------------------------

# Lazy-loaded exception type references to avoid hard dependency on httpx/aiohttp
_TIMEOUT_EXCEPTION_NAMES: set[str] = {
    "TimeoutError",
    "asyncio.TimeoutError",
    "ReadTimeout",
    "ConnectTimeout",
    "PoolTimeout",
    "ReadError",
    "httpx.ReadTimeout",
    "httpx.ConnectTimeout",
    "httpx.PoolTimeout",
    "aiohttp.ServerTimeoutError",
}

_TRANSIENT_EXCEPTION_NAMES: set[str] = {
    "ConnectionError",
    "ConnectionResetError",
    "ConnectionRefusedError",
    "ConnectionAbortedError",
    "ConnectError",
    "httpx.ConnectError",
    "httpx.RemoteProtocolError",
    "aiohttp.ClientConnectorError",
    "aiohttp.ServerDisconnectedError",
    "OSError",
    "BrokenPipeError",
}


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

def classify_error(
    error: BaseException,
    status_code: Optional[int] = None,
    service_name: Optional[str] = None,
) -> ErrorClassification:
    """Classify an error into an actionable category.

    Parameters
    ----------
    error:
        The caught exception.
    status_code:
        HTTP status code, if available (e.g. from ``httpx.HTTPStatusError``).
    service_name:
        Optional service name for logging context.

    Returns
    -------
    ErrorClassification
        Classification with retry/failure/alert guidance.
    """
    # 1. Try HTTP status code first (most precise)
    if status_code is None:
        status_code = _extract_status_code(error)

    if status_code is not None:
        category = _STATUS_MAP.get(status_code)
        if category is not None:
            result = _CLASSIFICATIONS[category]
            logger.debug(
                "Classified %s error (status=%d) as %s for service '%s'",
                type(error).__name__,
                status_code,
                category.value,
                service_name or "unknown",
            )
            return result

        # Default: 4xx → permanent, 5xx → transient
        if 400 <= status_code < 500:
            return _CLASSIFICATIONS[ErrorCategory.PERMANENT]
        if 500 <= status_code < 600:
            return _CLASSIFICATIONS[ErrorCategory.TRANSIENT]

    # 2. Try exception type name matching
    exc_type_name = type(error).__name__
    exc_full_name = f"{type(error).__module__}.{exc_type_name}"

    if exc_type_name in _TIMEOUT_EXCEPTION_NAMES or exc_full_name in _TIMEOUT_EXCEPTION_NAMES:
        return _CLASSIFICATIONS[ErrorCategory.TIMEOUT]

    if isinstance(error, (TimeoutError, asyncio.TimeoutError)):
        return _CLASSIFICATIONS[ErrorCategory.TIMEOUT]

    if exc_type_name in _TRANSIENT_EXCEPTION_NAMES or exc_full_name in _TRANSIENT_EXCEPTION_NAMES:
        return _CLASSIFICATIONS[ErrorCategory.TRANSIENT]

    if isinstance(error, (ConnectionError, OSError)):
        return _CLASSIFICATIONS[ErrorCategory.TRANSIENT]

    # 3. Fallback: unknown → treat as transient (safe default)
    logger.debug(
        "Could not classify %s for service '%s' — defaulting to UNKNOWN",
        type(error).__name__,
        service_name or "unknown",
    )
    return _CLASSIFICATIONS[ErrorCategory.UNKNOWN]


def classify_status_code(status_code: int) -> ErrorClassification:
    """Classify a bare HTTP status code."""
    category = _STATUS_MAP.get(status_code)
    if category is not None:
        return _CLASSIFICATIONS[category]
    if 400 <= status_code < 500:
        return _CLASSIFICATIONS[ErrorCategory.PERMANENT]
    if 500 <= status_code < 600:
        return _CLASSIFICATIONS[ErrorCategory.TRANSIENT]
    return _CLASSIFICATIONS[ErrorCategory.UNKNOWN]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_status_code(error: BaseException) -> Optional[int]:
    """Try to extract an HTTP status code from common exception types."""
    # httpx.HTTPStatusError
    if hasattr(error, "response") and hasattr(error.response, "status_code"):
        return int(error.response.status_code)
    # aiohttp.ClientResponseError
    if hasattr(error, "status"):
        return int(error.status)
    # Generic
    if hasattr(error, "code"):
        try:
            code = int(error.code)
            if 100 <= code < 600:
                return code
        except (ValueError, TypeError):
            pass
    return None


import asyncio  # noqa: E402 — used in isinstance check above
