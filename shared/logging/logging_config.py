"""
Structured JSON Logging Configuration
======================================

Provides a JSON formatter and configurator so every module in the
pipeline emits machine-parseable log lines.

Usage at application entry-point::

    from shared.logging.logging_config import configure_logging
    configure_logging(level="INFO", json_output=True)

Each log record is a single JSON object with these fields:

    timestamp   – ISO-8601 UTC
    level       – DEBUG | INFO | WARNING | ERROR | CRITICAL
    logger      – logger name (e.g. "vqa-perception", "ocr-engine")
    message     – formatted log string
    event       – optional structured event tag
    component   – optional component tag
    frame_id    – optional frame identifier
    session_id  – optional session identifier
    latency_ms  – optional numeric latency
    extra       – any extra JSON-serialisable data
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# ── PII Scrubbing Patterns ────────────────────────────────────────────
_PII_PATTERNS = [
    # Email addresses
    (re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"), "[EMAIL_REDACTED]"),
    # IP addresses (v4)
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[IP_REDACTED]"),
    # Face embedding IDs (fid_<hex>)
    (re.compile(r"\bfid_[a-f0-9]{8,}\b"), "[FACE_ID_REDACTED]"),
    # API key patterns (sk_, key_, api_key= etc.)
    (re.compile(r"\b(sk_[a-zA-Z0-9]{20,})\b"), "[API_KEY_REDACTED]"),
    (re.compile(r"\b(API[a-zA-Z0-9]{10,})\b"), "[API_KEY_REDACTED]"),
    # Bearer tokens
    (re.compile(r"Bearer\s+[a-zA-Z0-9._\-]+"), "Bearer [TOKEN_REDACTED]"),
    # Deepgram-style keys (dg_ prefix)
    (re.compile(r"\bdg_[a-zA-Z0-9]{10,}\b"), "[API_KEY_REDACTED]"),
    # Generic long hex strings (likely API keys/secrets, 32+ chars)
    (re.compile(r"\b[a-f0-9]{32,}\b"), "[HEX_SECRET_REDACTED]"),
    # Key=value patterns for named secrets in log messages
    (re.compile(
        r"(?i)((?:api[_-]?key|api[_-]?secret|token|password|secret)"
        r"\s*[=:]\s*)['\"]?([a-zA-Z0-9_\-./+]{8,})['\"]?"
    ), r"\1[REDACTED]"),
    # WebSocket URLs with credentials
    (re.compile(r"(wss?://[^:]+:)[a-zA-Z0-9_\-]+(@)"), r"\1[REDACTED]\2"),
]


class PIIScrubFilter(logging.Filter):
    """Logging filter that scrubs PII patterns from log messages.

    Redacts emails, IP addresses, face IDs, API keys, and bearer tokens.
    Enabled by default; can be disabled for diagnostics mode.
    """

    def __init__(self, enabled: bool = True):
        super().__init__()
        self.enabled = enabled

    def filter(self, record: logging.LogRecord) -> bool:
        if not self.enabled:
            return True
        # Scrub the main message
        msg = record.getMessage()
        for pattern, replacement in _PII_PATTERNS:
            msg = pattern.sub(replacement, msg)
        record.msg = msg
        record.args = None  # prevent re-formatting
        return True


class StructuredJSONFormatter(logging.Formatter):
    """Emit each log record as a single-line JSON object.

    Extra context can be attached via ``logger.info("msg", extra={...})``.
    Recognised extra keys are promoted to top-level fields; everything
    else is nested under ``"extra"``.
    """

    # Keys that are promoted to the top level of the JSON record
    PROMOTED_KEYS = frozenset({
        "event", "component", "frame_id", "session_id",
        "latency_ms", "detections_count", "error_type",
    })

    def format(self, record: logging.LogRecord) -> str:
        # Base payload
        payload: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Promote known extra fields
        extras: Dict[str, Any] = {}
        for key in self.PROMOTED_KEYS:
            val = getattr(record, key, None)
            if val is not None:
                payload[key] = val

        # Collect remaining extras (ignore standard LogRecord attributes)
        _standard = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__)
        _standard |= self.PROMOTED_KEYS
        for key, val in record.__dict__.items():
            if key.startswith("_") or key in _standard:
                continue
            # Skip internal logging fields
            if key in (
                "name", "msg", "args", "created", "relativeCreated",
                "exc_info", "exc_text", "stack_info", "lineno", "funcName",
                "pathname", "filename", "module", "thread", "threadName",
                "process", "processName", "msecs", "levelno", "levelname",
                "message", "taskName",
            ):
                continue
            extras[key] = _safe_serialize(val)

        if extras:
            payload["extra"] = extras

        # Exception info
        if record.exc_info and record.exc_info[1]:
            payload["error"] = str(record.exc_info[1])
            payload["error_type"] = type(record.exc_info[1]).__name__

        return json.dumps(payload, default=str, ensure_ascii=False)


def _safe_serialize(obj: Any) -> Any:
    """Make an object JSON-serialisable."""
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_safe_serialize(v) for v in obj]
    if isinstance(obj, dict):
        return {str(k): _safe_serialize(v) for k, v in obj.items()}
    return str(obj)


class HumanReadableFormatter(logging.Formatter):
    """Readable coloured formatter for local development."""

    COLORS = {
        "DEBUG": "\033[36m",      # cyan
        "INFO": "\033[32m",       # green
        "WARNING": "\033[33m",    # yellow
        "ERROR": "\033[31m",      # red
        "CRITICAL": "\033[41m",   # red bg
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime("%H:%M:%S.%f")[:-3]
        prefix = f"{color}{ts} [{record.levelname:>7s}] {record.name}{self.RESET}"

        msg = record.getMessage()

        # Append promoted extras inline
        parts = []
        for key in StructuredJSONFormatter.PROMOTED_KEYS:
            val = getattr(record, key, None)
            if val is not None:
                parts.append(f"{key}={val}")
        suffix = f" | {', '.join(parts)}" if parts else ""

        line = f"{prefix}: {msg}{suffix}"

        if record.exc_info and record.exc_info[1]:
            line += f"\n  Exception: {record.exc_info[1]}"

        return line


def configure_logging(
    level: str = "INFO",
    json_output: Optional[bool] = None,
    pii_scrub: Optional[bool] = None,
) -> None:
    """Configure root logger with structured JSON or human-readable output.

    Parameters
    ----------
    level : str
        Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    json_output : bool | None
        If *True*, emit JSON lines.  If *False*, emit coloured text.
        If *None* (default), auto-detect: JSON when ``LOG_FORMAT=json``
        env-var is set or when stdout is not a TTY.
    pii_scrub : bool | None
        If *True*, redact PII patterns from log output.  If *None*
        (default), enable unless ``PII_SCRUB=false`` env-var is set.
    """
    if json_output is None:
        env = os.environ.get("LOG_FORMAT", "").lower()
        if env == "json":
            json_output = True
        elif env == "text":
            json_output = False
        else:
            json_output = not sys.stdout.isatty()

    if pii_scrub is None:
        pii_scrub = os.environ.get("PII_SCRUB", "true").lower() != "false"

    handler = logging.StreamHandler(sys.stdout)
    if json_output:
        handler.setFormatter(StructuredJSONFormatter())
    else:
        handler.setFormatter(HumanReadableFormatter())

    # Attach PII scrubbing filter (enabled by default)
    handler.addFilter(PIIScrubFilter(enabled=pii_scrub))

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    # Replace existing handlers
    root.handlers = [handler]


# ── Convenience helpers for structured events ─────────────────────────

def log_event(
    logger_name: str,
    event: str,
    *,
    level: int = logging.INFO,
    component: Optional[str] = None,
    frame_id: Optional[str] = None,
    session_id: Optional[str] = None,
    latency_ms: Optional[float] = None,
    detections_count: Optional[int] = None,
    **kwargs: Any,
) -> None:
    """Emit a structured event log entry.

    Example::

        log_event("vqa-perception", "detection_complete",
                  component="yolo_detector", frame_id="frm_42",
                  latency_ms=45.2, detections_count=3)
    """
    extra: Dict[str, Any] = {"event": event}
    if component is not None:
        extra["component"] = component
    if frame_id is not None:
        extra["frame_id"] = frame_id
    if session_id is not None:
        extra["session_id"] = session_id
    if latency_ms is not None:
        extra["latency_ms"] = round(latency_ms, 2)
    if detections_count is not None:
        extra["detections_count"] = detections_count
    extra.update(kwargs)

    logging.getLogger(logger_name).log(level, event, extra=extra)
