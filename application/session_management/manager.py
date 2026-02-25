"""Session lifecycle management for application sessions."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field

logger = logging.getLogger("session-manager")


@dataclass
class Session:
    """In-memory session record."""

    session_id: str
    created_at: float
    last_accessed: float
    metadata: dict[str, object] = field(default_factory=dict)


class SessionManager:
    """In-memory session lifecycle manager."""

    def __init__(self, max_sessions: int = 100, ttl_seconds: float = 3600.0) -> None:
        self._sessions: dict[str, Session] = {}
        self._max_sessions: int = max(1, max_sessions)
        self._ttl_seconds: float = max(0.0, ttl_seconds)

    def create_session(self, metadata: dict[str, object] | None = None) -> Session:
        """Create a new session with a unique ID."""
        self._cleanup_expired()
        if len(self._sessions) >= self._max_sessions:
            self._evict_oldest()

        now = time.time()
        session_id = str(uuid.uuid4())
        session = Session(
            session_id=session_id,
            created_at=now,
            last_accessed=now,
            metadata=dict(metadata or {}),
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Session | None:
        """Retrieve session by ID. Updates last_accessed. Returns None if expired/missing."""
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if self._is_expired(session):
            _ = self._sessions.pop(session_id, None)
            return None
        session.last_accessed = time.time()
        return session

    def destroy_session(self, session_id: str) -> bool:
        """Remove a session. Returns True if it existed."""
        return self._sessions.pop(session_id, None) is not None

    def active_sessions(self) -> int:
        """Count of non-expired sessions."""
        self._cleanup_expired()
        return len(self._sessions)

    def health(self) -> dict[str, object]:
        """Health check for pipeline monitoring."""
        return {
            "status": "healthy",
            "active_sessions": self.active_sessions(),
            "max_sessions": self._max_sessions,
            "ttl_seconds": self._ttl_seconds,
        }

    def _cleanup_expired(self) -> None:
        if not self._sessions:
            return
        expired = [sid for sid, sess in self._sessions.items() if self._is_expired(sess)]
        for sid in expired:
            _ = self._sessions.pop(sid, None)

    def _is_expired(self, session: Session) -> bool:
        if self._ttl_seconds <= 0:
            return False
        return (time.time() - session.last_accessed) > self._ttl_seconds

    def _evict_oldest(self) -> None:
        if not self._sessions:
            return
        oldest_id = min(self._sessions, key=lambda sid: self._sessions[sid].last_accessed)
        removed = self._sessions.pop(oldest_id, None)
        if removed:
            logger.debug("Evicted oldest session %s", oldest_id)
