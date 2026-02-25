"""Unit tests for application session management."""

from __future__ import annotations

import time

from application.session_management import SessionManager


def test_create_session() -> None:
    manager = SessionManager()
    session = manager.create_session({"user": "alice"})

    assert session.session_id
    assert session.created_at > 0
    assert session.last_accessed >= session.created_at
    assert session.metadata["user"] == "alice"


def test_get_session() -> None:
    manager = SessionManager()
    session = manager.create_session()
    original_accessed = session.last_accessed

    time.sleep(0.01)
    fetched = manager.get_session(session.session_id)

    assert fetched is not None
    assert fetched.session_id == session.session_id
    assert fetched.last_accessed >= original_accessed


def test_get_nonexistent() -> None:
    manager = SessionManager()
    assert manager.get_session("missing") is None


def test_destroy_session() -> None:
    manager = SessionManager()
    session = manager.create_session()

    assert manager.destroy_session(session.session_id) is True
    assert manager.get_session(session.session_id) is None


def test_destroy_nonexistent() -> None:
    manager = SessionManager()
    assert manager.destroy_session("missing") is False


def test_session_expiry() -> None:
    manager = SessionManager(ttl_seconds=0.01)
    session = manager.create_session()

    time.sleep(0.02)
    assert manager.get_session(session.session_id) is None


def test_max_sessions() -> None:
    manager = SessionManager(max_sessions=2, ttl_seconds=3600.0)
    s1 = manager.create_session({"idx": 1})
    time.sleep(0.01)
    s2 = manager.create_session({"idx": 2})
    time.sleep(0.01)
    s3 = manager.create_session({"idx": 3})

    assert manager.get_session(s1.session_id) is None
    assert manager.get_session(s2.session_id) is not None
    assert manager.get_session(s3.session_id) is not None
    assert manager.active_sessions() == 2


def test_health() -> None:
    manager = SessionManager(max_sessions=5, ttl_seconds=60.0)
    _ = manager.create_session()

    health = manager.health()
    assert health["status"] == "healthy"
    assert health["active_sessions"] == 1
    assert health["max_sessions"] == 5
    assert health["ttl_seconds"] == 60.0
