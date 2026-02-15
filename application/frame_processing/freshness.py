"""
Freshness
=========
Timestamp validation helpers and stale-frame assertions.

Provides decorators and functions to enforce the LIVE_FRAME_MAX_AGE_MS
contract at every point where user-facing output is generated.
"""

from __future__ import annotations

import functools
import logging
import time
from typing import Any, Optional

logger = logging.getLogger("freshness")

# ── Default budget ────────────────────────────────────────────────────────
LIVE_FRAME_MAX_AGE_MS: float = 500.0

FALLBACK_MESSAGE = "I can't see clearly right now — please hold the camera steady."
CAMERA_FALLBACK = "Camera feed interrupted — please check camera or grant permission."
DECODE_FALLBACK = "I detected something but couldn't decode it — please try again."
REPEATED_FAILURE_HINT = "Try adjusting the lighting, moving closer, or stabilizing the camera."


def set_max_age(ms: float) -> None:
    """Update the global freshness budget."""
    global LIVE_FRAME_MAX_AGE_MS
    LIVE_FRAME_MAX_AGE_MS = max(50, ms)


def frame_age_ms(timestamp_epoch_ms: float) -> float:
    """Calculate age of a frame in milliseconds."""
    return (time.time() * 1000) - timestamp_epoch_ms


def is_frame_fresh(timestamp_epoch_ms: float, max_age_ms: Optional[float] = None) -> bool:
    """Check if a frame timestamp is within the freshness budget."""
    budget = max_age_ms if max_age_ms is not None else LIVE_FRAME_MAX_AGE_MS
    return frame_age_ms(timestamp_epoch_ms) <= budget


def assert_fresh(timestamp_epoch_ms: float, max_age_ms: Optional[float] = None, context: str = "") -> None:
    """Assert that a frame is fresh. Raises ValueError if stale.

    This should be called at the point of generating user-facing output.
    """
    budget = max_age_ms if max_age_ms is not None else LIVE_FRAME_MAX_AGE_MS
    age = frame_age_ms(timestamp_epoch_ms)
    if age > budget:
        msg = (f"Stale frame: age={age:.0f}ms > budget={budget:.0f}ms"
               f"{' (' + context + ')' if context else ''}")
        logger.warning(msg)
        raise ValueError(msg)


def freshness_gate(timestamp_epoch_ms: float, short_cue: str, max_age_ms: Optional[float] = None) -> str:
    """Gate a short_cue through freshness validation.

    Returns the cue if fresh, or a safe fallback message if stale.
    This is the recommended way to validate output right before speaking.
    """
    budget = max_age_ms if max_age_ms is not None else LIVE_FRAME_MAX_AGE_MS
    age = frame_age_ms(timestamp_epoch_ms)
    if age <= budget:
        return short_cue
    logger.warning("Freshness gate blocked output: age=%.0fms > budget=%.0fms", age, budget)
    return FALLBACK_MESSAGE


def safe_output(
    short_cue: str,
    timestamp_epoch_ms: Optional[float] = None,
    is_historical: bool = False,
    max_age_ms: Optional[float] = None,
) -> str:
    """Produce safe user-facing output.

    - If ``is_historical`` is True, returns the cue without freshness check.
    - If no timestamp, returns fallback.
    - Otherwise, applies freshness gate.
    """
    if is_historical:
        return short_cue

    if timestamp_epoch_ms is None:
        logger.warning("Output generated without frame timestamp — returning fallback")
        return FALLBACK_MESSAGE

    return freshness_gate(timestamp_epoch_ms, short_cue, max_age_ms)


def validate_scene_graph_freshness(scene_graph: Any, max_age_ms: Optional[float] = None) -> bool:
    """Check if a scene_graph object is fresh.

    Looks for ``timestamp_epoch_ms`` or ``frame_timestamp_ms`` attribute.
    """
    ts = getattr(scene_graph, "timestamp_epoch_ms", None) or getattr(scene_graph, "frame_timestamp_ms", None)
    if ts is None:
        return False
    return is_frame_fresh(ts, max_age_ms)


# ── Decorator for output-producing functions ─────────────────────────────


def require_fresh_frame(max_age_ms: Optional[float] = None):
    """Decorator that ensures the first argument (frame/timestamp) is fresh.

    Can be applied to functions that accept a ``timestamp_epoch_ms``
    keyword argument or a ``frame`` object with that attribute.
    """
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            # Try to find timestamp
            ts = kwargs.get("timestamp_epoch_ms")
            if ts is None:
                frame = kwargs.get("frame") or (args[0] if args else None)
                ts = getattr(frame, "timestamp_epoch_ms", None)
            if ts is not None:
                budget = max_age_ms if max_age_ms is not None else LIVE_FRAME_MAX_AGE_MS
                if not is_frame_fresh(ts, budget):
                    return FALLBACK_MESSAGE
            return await fn(*args, **kwargs)
        return wrapper
    return decorator
