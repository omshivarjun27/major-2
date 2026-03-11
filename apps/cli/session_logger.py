"""
Session Logger
==============

Structured JSON session logging for debug / telemetry.

Each session is identified by a UUID.  Events are appended
to an in-memory ring-buffer and can optionally be flushed
to a JSON-lines file on disk.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger("session-logger")


# ============================================================================
# Event
# ============================================================================


@dataclass
class SessionEvent:
    """Single structured log entry."""

    ts: float                       # epoch seconds
    event_type: str                 # e.g. "perception", "vqa", "qr", "tts"
    payload: Dict[str, Any]         # free-form JSON-serialisable data
    latency_ms: Optional[float] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "ts": round(self.ts, 3),
            "event_type": self.event_type,
            "payload": self.payload,
        }
        if self.latency_ms is not None:
            d["latency_ms"] = round(self.latency_ms, 1)
        if self.error:
            d["error"] = self.error
        return d


# ============================================================================
# Session Logger
# ============================================================================


class SessionLogger:
    """Ring-buffer session logger with optional disk flush.

    Parameters
    ----------
    max_events : int
        Maximum events kept in memory per session (oldest are evicted).
    log_dir : str | Path | None
        If set, events are also appended to ``<log_dir>/<session_id>.jsonl``.
    """

    def __init__(
        self,
        max_events: int = 500,
        log_dir: Optional[str] = None,
    ):
        self._max_events = max_events
        self._log_dir = Path(log_dir) if log_dir else None
        if self._log_dir:
            self._log_dir.mkdir(parents=True, exist_ok=True)

        # session_id → deque of SessionEvent
        self._sessions: Dict[str, Deque[SessionEvent]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_session(self) -> str:
        """Start a new session. Returns session id."""
        sid = f"sess_{uuid.uuid4().hex[:12]}"
        self._sessions[sid] = deque(maxlen=self._max_events)
        logger.info("Session created: %s", sid)
        return sid

    def log(
        self,
        session_id: str,
        event_type: str,
        payload: Dict[str, Any],
        latency_ms: Optional[float] = None,
        error: Optional[str] = None,
    ) -> None:
        """Append an event to a session."""
        evt = SessionEvent(
            ts=time.time(),
            event_type=event_type,
            payload=payload,
            latency_ms=latency_ms,
            error=error,
        )

        buf = self._sessions.get(session_id)
        if buf is None:
            # Auto-create session on first log
            buf = deque(maxlen=self._max_events)
            self._sessions[session_id] = buf

        buf.append(evt)

        # Optional disk flush
        if self._log_dir:
            try:
                path = self._log_dir / f"{session_id}.jsonl"
                with open(path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(evt.to_dict()) + "\n")
            except Exception as exc:
                logger.warning("Disk flush failed: %s", exc)

    def get_events(
        self,
        session_id: str,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Retrieve events for a session."""
        buf = self._sessions.get(session_id)
        if buf is None:
            return []
        events = list(buf)
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return [e.to_dict() for e in events[-limit:]]

    def list_sessions(self) -> List[Dict[str, Any]]:
        """Return summary of all known sessions."""
        out = []
        for sid, buf in self._sessions.items():
            out.append({
                "session_id": sid,
                "event_count": len(buf),
                "first_ts": round(buf[0].ts, 3) if buf else None,
                "last_ts": round(buf[-1].ts, 3) if buf else None,
            })
        return out

    def delete_session(self, session_id: str) -> bool:
        """Remove a session from memory."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
