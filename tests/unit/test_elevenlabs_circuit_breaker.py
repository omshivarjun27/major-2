"""Tests for ElevenLabs TTS circuit breaker integration.

Validates that TTSManager correctly integrates with the circuit breaker
pattern: recording successes/failures and skipping remote calls when
the circuit is OPEN.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from infrastructure.resilience.circuit_breaker import (
    CircuitBreakerState,
    clear_registry,
    get_circuit_breaker,
)
from infrastructure.speech.elevenlabs.tts_manager import TTSManager


@pytest.fixture(autouse=True)
def clean_registry():
    """Ensure each test gets a fresh circuit breaker registry."""
    clear_registry()
    yield
    clear_registry()


class TestElevenLabsCircuitBreaker:
    """Circuit breaker integration with TTSManager."""

    async def test_cb_registered_on_init(self):
        """TTSManager registers an 'elevenlabs' circuit breaker on construction."""
        mgr = TTSManager(cache_enabled=False)
        cb = get_circuit_breaker("elevenlabs")
        assert cb is not None, "Circuit breaker should be registered"
        assert cb.state is CircuitBreakerState.CLOSED
        assert mgr._cb is cb

    async def test_remote_success_records_cb_success(self):
        """Successful remote call schedules _on_success, keeping CB closed."""
        remote_fn = MagicMock(return_value=b"audio-data")
        mgr = TTSManager(remote_fn=remote_fn, cache_enabled=False)

        result = mgr.synthesise("hello")
        await asyncio.sleep(0.05)  # Let async CB update process

        assert result.engine == "remote"
        assert result.fallback_used is False
        assert mgr._cb.state is CircuitBreakerState.CLOSED
        assert mgr._cb.failure_count == 0

    async def test_remote_failure_records_cb_failure(self):
        """A single remote failure increments the CB failure counter."""

        def failing_remote(text: str) -> bytes:
            raise ConnectionError("Service unavailable")

        local_fn = MagicMock(return_value=b"local-audio")
        mgr = TTSManager(
            local_fn=local_fn, remote_fn=failing_remote, cache_enabled=False
        )

        result = mgr.synthesise("test")
        await asyncio.sleep(0.05)

        assert result.engine == "local"
        assert result.fallback_used is True
        assert mgr.remote_failures == 1
        assert mgr._cb.failure_count == 1

    async def test_three_failures_trip_circuit(self):
        """Three consecutive remote failures trip the circuit to OPEN."""

        def failing_remote(text: str) -> bytes:
            raise ConnectionError("fail")

        local_fn = MagicMock(return_value=b"local")
        mgr = TTSManager(
            local_fn=local_fn, remote_fn=failing_remote, cache_enabled=False
        )

        for _ in range(3):
            mgr.synthesise("test")
            await asyncio.sleep(0.05)

        assert mgr._cb.state is CircuitBreakerState.OPEN
        assert mgr.remote_failures == 3

    async def test_open_circuit_skips_remote(self):
        """When circuit is OPEN, remote_fn is never called — local fallback used."""
        remote_fn = MagicMock(return_value=b"remote")
        local_fn = MagicMock(return_value=b"local")
        mgr = TTSManager(
            remote_fn=remote_fn, local_fn=local_fn, cache_enabled=False
        )

        # Force-trip the circuit
        await mgr._cb.trip()

        result = mgr.synthesise("test")
        assert result.engine == "local"
        assert result.fallback_used is True
        remote_fn.assert_not_called()

    async def test_open_circuit_result_metadata(self):
        """TTSResult from an open-circuit call has correct metadata."""
        local_fn = MagicMock(return_value=b"fallback-audio")
        mgr = TTSManager(
            remote_fn=MagicMock(), local_fn=local_fn, cache_enabled=False
        )

        await mgr._cb.trip()

        result = mgr.synthesise("hello world")
        assert result.audio_bytes == b"fallback-audio"
        assert result.engine == "local"
        assert result.fallback_used is True
        assert result.text == "hello world"

    async def test_health_includes_circuit_breaker(self):
        """health() returns a dict with circuit_breaker snapshot."""
        mgr = TTSManager(cache_enabled=False)
        h = mgr.health()

        assert "circuit_breaker" in h
        assert h["circuit_breaker"]["service"] == "elevenlabs"
        assert h["circuit_breaker"]["state"] == "closed"
        assert "total_calls" in h
        assert "remote_failures" in h
        assert "cache_hits" in h

    async def test_health_reflects_counters(self):
        """health() counters update after synthesise calls."""
        remote_fn = MagicMock(return_value=b"audio")
        mgr = TTSManager(remote_fn=remote_fn, cache_enabled=False)

        mgr.synthesise("one")
        mgr.synthesise("two")
        h = mgr.health()

        assert h["total_calls"] == 2
        assert h["remote_failures"] == 0

    async def test_cache_still_works_with_cb(self):
        """Cache hits bypass remote AND circuit breaker entirely."""
        remote_fn = MagicMock(return_value=b"remote-audio")
        mgr = TTSManager(
            remote_fn=remote_fn, cache_enabled=True, cache_max_entries=10
        )

        # First call — remote, populates cache
        r1 = mgr.synthesise("cached text")
        assert r1.engine == "remote"

        # Second call — cache hit, remote not called again
        r2 = mgr.synthesise("cached text")
        assert r2.cache_hit is True
        assert r2.engine == "cache"
        assert remote_fn.call_count == 1

    async def test_schedule_cb_async_no_event_loop(self):
        """_schedule_cb_async silently does nothing when no event loop is running."""
        mgr = TTSManager(cache_enabled=False)

        # Create a coroutine and pass it — should not raise
        async def dummy_coro():
            pass

        # When called outside an async context (simulated by wrapping in executor),
        # it should gracefully no-op. Here we just verify no exception is raised.
        # Since we ARE in an async context, create a separate thread to test.

        def call_from_thread():
            mgr._schedule_cb_async(dummy_coro)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, call_from_thread)
        # No exception means success

    async def test_no_remote_fn_no_cb_interaction(self):
        """When remote_fn is None, CB is not checked at all — pure local."""
        local_fn = MagicMock(return_value=b"local-only")
        mgr = TTSManager(local_fn=local_fn, remote_fn=None, cache_enabled=False)

        result = mgr.synthesise("test")
        assert result.engine == "local"
        assert result.fallback_used is False
        # CB should still be closed and untouched
        assert mgr._cb.state is CircuitBreakerState.CLOSED
        assert mgr._cb.failure_count == 0

    async def test_multiple_managers_share_cb(self):
        """Multiple TTSManager instances share the same CB (same service name)."""
        mgr1 = TTSManager(cache_enabled=False)
        mgr2 = TTSManager(cache_enabled=False)
        assert mgr1._cb is mgr2._cb

    async def test_circuit_recovery_after_reset(self):
        """After manual reset, circuit returns to CLOSED and remote is attempted again."""
        call_count = 0

        def counting_remote(text: str) -> bytes:
            nonlocal call_count
            call_count += 1
            return b"remote-audio"

        mgr = TTSManager(
            remote_fn=counting_remote, cache_enabled=False
        )

        # Trip the circuit
        await mgr._cb.trip()
        assert mgr._cb.state is CircuitBreakerState.OPEN

        # Remote is skipped while open
        mgr.synthesise("test1")
        assert call_count == 0

        # Reset the circuit
        await mgr._cb.reset()
        assert mgr._cb.state is CircuitBreakerState.CLOSED

        # Remote is called again
        result = mgr.synthesise("test2")
        assert call_count == 1
        assert result.engine == "remote"
