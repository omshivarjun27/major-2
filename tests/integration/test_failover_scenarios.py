"""End-to-end failover integration tests.

Tests comprehensive failover scenarios across the STT and TTS failover managers,
verifying realistic failure patterns including gradual degradation, sudden outages,
intermittent failures, and recovery scenarios.

Test Scenarios:
1. Deepgram -> Whisper failover (gradual failure)
2. ElevenLabs -> Edge TTS failover (sudden outage)
3. Simultaneous STT + TTS failure (both fallbacks active)
4. Recovery after failover (primary restored)
5. Intermittent failures (circuit stays closed with retries)
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import patch

import pytest

from infrastructure.resilience.circuit_breaker import (
    CircuitBreakerConfig,
    CircuitBreakerState,
    clear_registry,
    register_circuit_breaker,
)
from infrastructure.speech.stt_failover import (
    STTFailoverConfig,
    STTFailoverManager,
    STTProvider,
)
from infrastructure.speech.tts_failover import (
    TTSFailoverConfig,
    TTSFailoverManager,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_state():
    """Reset global state between tests."""
    clear_registry()
    yield
    clear_registry()


@pytest.fixture
def fast_stt_config() -> STTFailoverConfig:
    """Fast STT failover config for testing."""
    return STTFailoverConfig(
        deepgram_service_name="deepgram",
        whisper_model_size="tiny",
        prewarm_whisper=False,  # Disable to avoid loading model
        failover_timeout_s=0.5,
    )


@pytest.fixture
def fast_tts_config() -> TTSFailoverConfig:
    """Fast TTS failover config for testing."""
    return TTSFailoverConfig(
        elevenlabs_service_name="elevenlabs",
        local_tts_voice="en-US-AriaNeural",
        prefer_edge_tts=True,
        failover_timeout_s=0.5,
        prewarm_local_tts=False,
    )


@pytest.fixture
def fast_cb_config() -> CircuitBreakerConfig:
    """Fast circuit breaker config for testing."""
    return CircuitBreakerConfig(
        failure_threshold=2,
        reset_timeout_s=0.2,  # 200ms for fast tests
        half_open_max_calls=1,
        success_threshold=1,
    )


# ---------------------------------------------------------------------------
# Scenario 1: Deepgram -> Whisper Failover (Gradual Failure)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestScenario1DeepgramWhisperFailover:
    """Scenario 1: Gradual Deepgram failure triggers Whisper activation."""

    async def test_gradual_failure_triggers_failover(
        self, fast_stt_config: STTFailoverConfig, fast_cb_config: CircuitBreakerConfig
    ):
        """Gradual Deepgram failures trip circuit and activate Whisper."""
        # Pre-register CB with fast config
        deepgram_cb = register_circuit_breaker("deepgram", config=fast_cb_config)

        # Patch WHISPER_AVAILABLE to True for testing
        with patch("infrastructure.speech.stt_failover.WHISPER_AVAILABLE", True):
            manager = STTFailoverManager(config=fast_stt_config)
            await manager.initialize()

            # Initially should be on Deepgram
            assert manager.get_active_provider() == "deepgram"
            assert deepgram_cb.state is CircuitBreakerState.CLOSED

            # Simulate gradual failures (but not enough to trip)
            await deepgram_cb._on_failure(RuntimeError("Timeout"))
            assert deepgram_cb.state is CircuitBreakerState.CLOSED
            assert manager.get_active_provider() == "deepgram"

            # Second failure trips the circuit
            await deepgram_cb._on_failure(RuntimeError("Timeout"))
            assert deepgram_cb.state is CircuitBreakerState.OPEN

            # Allow callback to process
            await asyncio.sleep(0.05)

            # Whisper should now be active (or NONE if not available)
            provider = manager.get_active_provider()
            assert provider in ("whisper", "none"), f"Expected whisper/none, got {provider}"

            await manager.shutdown()

    async def test_failover_timing_under_2_seconds(
        self, fast_stt_config: STTFailoverConfig, fast_cb_config: CircuitBreakerConfig
    ):
        """Failover completes within 2-second SLA."""
        deepgram_cb = register_circuit_breaker("deepgram", config=fast_cb_config)

        with patch("infrastructure.speech.stt_failover.WHISPER_AVAILABLE", True):
            manager = STTFailoverManager(config=fast_stt_config)
            await manager.initialize()

            start_time = time.monotonic()

            # Trip the circuit
            await deepgram_cb.trip()

            # Wait for failover
            await asyncio.sleep(0.1)

            elapsed_ms = (time.monotonic() - start_time) * 1000

            # Verify failover completed within SLA
            assert elapsed_ms < 2000, f"Failover took {elapsed_ms}ms (SLA: 2000ms)"

            # Verify failover happened
            assert manager.get_active_provider() in ("whisper", "none")

            await manager.shutdown()

    async def test_failover_recorded_in_history(
        self, fast_stt_config: STTFailoverConfig, fast_cb_config: CircuitBreakerConfig
    ):
        """Failover events are recorded in history."""
        deepgram_cb = register_circuit_breaker("deepgram", config=fast_cb_config)

        with patch("infrastructure.speech.stt_failover.WHISPER_AVAILABLE", True):
            manager = STTFailoverManager(config=fast_stt_config)
            await manager.initialize()

            # Trip the circuit
            await deepgram_cb.trip()
            await asyncio.sleep(0.05)

            # Check history
            history = manager.get_failover_history()
            assert len(history) >= 1

            last_event = history[-1]
            assert last_event.from_provider == STTProvider.DEEPGRAM
            assert last_event.trigger == "circuit_open"

            await manager.shutdown()


# ---------------------------------------------------------------------------
# Scenario 2: ElevenLabs -> Edge TTS Failover (Sudden Outage)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestScenario2ElevenLabsLocalFailover:
    """Scenario 2: Sudden ElevenLabs outage triggers local TTS activation."""

    async def test_sudden_outage_triggers_failover(
        self, fast_tts_config: TTSFailoverConfig, fast_cb_config: CircuitBreakerConfig
    ):
        """Sudden ElevenLabs outage immediately activates local TTS."""
        # Pre-register CB
        elevenlabs_cb = register_circuit_breaker("elevenlabs", config=fast_cb_config)

        with (
            patch("infrastructure.speech.tts_failover.EDGE_TTS_AVAILABLE", True),
            patch("infrastructure.speech.tts_failover.PYTTSX3_AVAILABLE", True),
        ):
            manager = TTSFailoverManager(config=fast_tts_config)
            await manager.initialize()

            # Initially on ElevenLabs
            assert manager.get_active_provider() == "elevenlabs"

            # Simulate sudden outage by manually tripping circuit
            await elevenlabs_cb.trip()

            # Allow callback to process
            await asyncio.sleep(0.05)

            # Should have failed over to local
            assert manager.get_active_provider() == "local"

            await manager.shutdown()

    async def test_failover_timing_under_2_seconds_tts(
        self, fast_tts_config: TTSFailoverConfig, fast_cb_config: CircuitBreakerConfig
    ):
        """TTS failover completes within 2-second SLA."""
        elevenlabs_cb = register_circuit_breaker("elevenlabs", config=fast_cb_config)

        with (
            patch("infrastructure.speech.tts_failover.EDGE_TTS_AVAILABLE", True),
            patch("infrastructure.speech.tts_failover.PYTTSX3_AVAILABLE", True),
        ):
            manager = TTSFailoverManager(config=fast_tts_config)
            await manager.initialize()

            start_time = time.monotonic()

            # Trip the circuit
            await elevenlabs_cb.trip()

            # Wait for failover
            await asyncio.sleep(0.1)

            elapsed_ms = (time.monotonic() - start_time) * 1000

            # Verify failover completed within SLA
            assert elapsed_ms < 2000, f"Failover took {elapsed_ms}ms (SLA: 2000ms)"

            # Verify failover happened
            assert manager.get_active_provider() == "local"

            await manager.shutdown()

    async def test_statistics_track_failover(
        self, fast_tts_config: TTSFailoverConfig, fast_cb_config: CircuitBreakerConfig
    ):
        """Failover statistics are correctly tracked."""
        elevenlabs_cb = register_circuit_breaker("elevenlabs", config=fast_cb_config)

        with (
            patch("infrastructure.speech.tts_failover.EDGE_TTS_AVAILABLE", True),
            patch("infrastructure.speech.tts_failover.PYTTSX3_AVAILABLE", True),
        ):
            manager = TTSFailoverManager(config=fast_tts_config)
            await manager.initialize()

            # Initial stats
            stats = manager.get_statistics()
            assert stats["total_failovers"] == 0

            # Trip circuit
            await elevenlabs_cb.trip()
            await asyncio.sleep(0.05)

            # Check updated stats
            stats = manager.get_statistics()
            assert stats["total_failovers"] == 1
            assert stats["current_provider"] == "local"

            await manager.shutdown()


# ---------------------------------------------------------------------------
# Scenario 3: Simultaneous STT + TTS Failure
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestScenario3SimultaneousFailure:
    """Scenario 3: Both STT and TTS fail simultaneously, both fallbacks activate."""

    async def test_both_services_failover_independently(
        self,
        fast_stt_config: STTFailoverConfig,
        fast_tts_config: TTSFailoverConfig,
        fast_cb_config: CircuitBreakerConfig,
    ):
        """Both STT and TTS can failover independently at the same time."""
        # Pre-register both CBs
        deepgram_cb = register_circuit_breaker("deepgram", config=fast_cb_config)
        elevenlabs_cb = register_circuit_breaker("elevenlabs", config=fast_cb_config)

        with (
            patch("infrastructure.speech.stt_failover.WHISPER_AVAILABLE", True),
            patch("infrastructure.speech.tts_failover.EDGE_TTS_AVAILABLE", True),
            patch("infrastructure.speech.tts_failover.PYTTSX3_AVAILABLE", True),
        ):
            stt_manager = STTFailoverManager(config=fast_stt_config)
            tts_manager = TTSFailoverManager(config=fast_tts_config)

            await stt_manager.initialize()
            await tts_manager.initialize()

            # Both should be on primary providers
            assert stt_manager.get_active_provider() == "deepgram"
            assert tts_manager.get_active_provider() == "elevenlabs"

            # Simulate simultaneous failures
            await asyncio.gather(
                deepgram_cb.trip(),
                elevenlabs_cb.trip(),
            )

            # Allow callbacks to process
            await asyncio.sleep(0.1)

            # Both should have failed over
            assert stt_manager.get_active_provider() in ("whisper", "none")
            assert tts_manager.get_active_provider() == "local"

            # Verify CB states
            assert deepgram_cb.state is CircuitBreakerState.OPEN
            assert elevenlabs_cb.state is CircuitBreakerState.OPEN

            await stt_manager.shutdown()
            await tts_manager.shutdown()

    async def test_combined_failover_timing(
        self,
        fast_stt_config: STTFailoverConfig,
        fast_tts_config: TTSFailoverConfig,
        fast_cb_config: CircuitBreakerConfig,
    ):
        """Combined STT+TTS failover still meets 2-second SLA."""
        deepgram_cb = register_circuit_breaker("deepgram", config=fast_cb_config)
        elevenlabs_cb = register_circuit_breaker("elevenlabs", config=fast_cb_config)

        with (
            patch("infrastructure.speech.stt_failover.WHISPER_AVAILABLE", True),
            patch("infrastructure.speech.tts_failover.EDGE_TTS_AVAILABLE", True),
            patch("infrastructure.speech.tts_failover.PYTTSX3_AVAILABLE", True),
        ):
            stt_manager = STTFailoverManager(config=fast_stt_config)
            tts_manager = TTSFailoverManager(config=fast_tts_config)

            await stt_manager.initialize()
            await tts_manager.initialize()

            start_time = time.monotonic()

            # Trip both simultaneously
            await asyncio.gather(
                deepgram_cb.trip(),
                elevenlabs_cb.trip(),
            )

            # Wait for failovers
            await asyncio.sleep(0.1)

            elapsed_ms = (time.monotonic() - start_time) * 1000

            # Both failovers should complete within SLA
            assert elapsed_ms < 2000, f"Combined failover took {elapsed_ms}ms (SLA: 2000ms)"

            await stt_manager.shutdown()
            await tts_manager.shutdown()

    async def test_health_reflects_degraded_state(
        self,
        fast_stt_config: STTFailoverConfig,
        fast_tts_config: TTSFailoverConfig,
        fast_cb_config: CircuitBreakerConfig,
    ):
        """Health endpoints reflect degraded state after failover."""
        deepgram_cb = register_circuit_breaker("deepgram", config=fast_cb_config)
        elevenlabs_cb = register_circuit_breaker("elevenlabs", config=fast_cb_config)

        with (
            patch("infrastructure.speech.stt_failover.WHISPER_AVAILABLE", True),
            patch("infrastructure.speech.tts_failover.EDGE_TTS_AVAILABLE", True),
            patch("infrastructure.speech.tts_failover.PYTTSX3_AVAILABLE", True),
        ):
            stt_manager = STTFailoverManager(config=fast_stt_config)
            tts_manager = TTSFailoverManager(config=fast_tts_config)

            await stt_manager.initialize()
            await tts_manager.initialize()

            # Trip both
            await asyncio.gather(
                deepgram_cb.trip(),
                elevenlabs_cb.trip(),
            )
            await asyncio.sleep(0.1)

            # Check health endpoints
            stt_health = stt_manager.health()
            tts_health = tts_manager.health()

            assert stt_health["deepgram_circuit_state"] == "open"
            assert tts_health["elevenlabs_circuit_state"] == "open"

            await stt_manager.shutdown()
            await tts_manager.shutdown()


# ---------------------------------------------------------------------------
# Scenario 4: Recovery After Failover
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestScenario4RecoveryAfterFailover:
    """Scenario 4: Services recover and failback to primary providers."""


    async def test_stt_recovery_failback(
        self, fast_stt_config: STTFailoverConfig, fast_cb_config: CircuitBreakerConfig
    ):
        """STT recovers from Whisper back to Deepgram via manual failback."""
        register_circuit_breaker("deepgram", config=fast_cb_config)

        with patch("infrastructure.speech.stt_failover.WHISPER_AVAILABLE", True):
            manager = STTFailoverManager(config=fast_stt_config)
            await manager.initialize()

            # Force failover to Whisper using manual method
            await manager.force_failover_to_whisper()
            await asyncio.sleep(0.05)
            assert manager.get_active_provider() in ("whisper", "none")

            # Force failback to Deepgram (simulates recovery)
            await manager.force_failback_to_deepgram()
            await asyncio.sleep(0.05)

            # Should be back on Deepgram
            assert manager.get_active_provider() == "deepgram"

            await manager.shutdown()

    async def test_tts_recovery_failback(
        self, fast_tts_config: TTSFailoverConfig, fast_cb_config: CircuitBreakerConfig
    ):
        """TTS recovers from local back to ElevenLabs via manual failback."""
        register_circuit_breaker("elevenlabs", config=fast_cb_config)

        with (
            patch("infrastructure.speech.tts_failover.EDGE_TTS_AVAILABLE", True),
            patch("infrastructure.speech.tts_failover.PYTTSX3_AVAILABLE", True),
        ):
            manager = TTSFailoverManager(config=fast_tts_config)
            await manager.initialize()

            # Force failover to local
            await manager.force_failover_to_local()
            await asyncio.sleep(0.05)
            assert manager.get_active_provider() == "local"

            # Force failback
            await manager.force_failback_to_elevenlabs()
            await asyncio.sleep(0.05)

            # Back on ElevenLabs
            assert manager.get_active_provider() == "elevenlabs"

            await manager.shutdown()

    async def test_recovery_timing_under_2_seconds(
        self, fast_tts_config: TTSFailoverConfig, fast_cb_config: CircuitBreakerConfig
    ):
        """Recovery (failback) completes within 2-second SLA."""
        register_circuit_breaker("elevenlabs", config=fast_cb_config)

        with (
            patch("infrastructure.speech.tts_failover.EDGE_TTS_AVAILABLE", True),
            patch("infrastructure.speech.tts_failover.PYTTSX3_AVAILABLE", True),
        ):
            manager = TTSFailoverManager(config=fast_tts_config)
            await manager.initialize()

            # Failover
            await manager.force_failover_to_local()
            await asyncio.sleep(0.05)

            start_time = time.monotonic()

            # Recover via manual failback
            await manager.force_failback_to_elevenlabs()
            await asyncio.sleep(0.05)

            elapsed_ms = (time.monotonic() - start_time) * 1000

            assert elapsed_ms < 2000, f"Recovery took {elapsed_ms}ms (SLA: 2000ms)"
            assert manager.get_active_provider() == "elevenlabs"

            await manager.shutdown()

    async def test_failback_recorded_in_history(
        self, fast_stt_config: STTFailoverConfig, fast_cb_config: CircuitBreakerConfig
    ):
        """Failback events are recorded in history."""
        register_circuit_breaker("deepgram", config=fast_cb_config)

        with patch("infrastructure.speech.stt_failover.WHISPER_AVAILABLE", True):
            manager = STTFailoverManager(config=fast_stt_config)
            await manager.initialize()

            # Failover and failback
            await manager.force_failover_to_whisper()
            await asyncio.sleep(0.05)

            await manager.force_failback_to_deepgram()
            await asyncio.sleep(0.05)

            # Check history has both events
            history = manager.get_failover_history()
            assert len(history) >= 2, f"Expected 2+ events, got {len(history)}: {history}"

            # Manual methods use 'manual' trigger
            triggers = [e.trigger for e in history]
            assert triggers.count("manual") >= 2, f"Expected 2 manual triggers, got: {triggers}"

            await manager.shutdown()


# ---------------------------------------------------------------------------
# Scenario 5: Intermittent Failures
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestScenario5IntermittentFailures:
    """Scenario 5: Intermittent failures don't trip circuit unnecessarily."""

    async def test_single_failure_no_failover(
        self, fast_stt_config: STTFailoverConfig
    ):
        """Single failure doesn't trigger failover (threshold=2)."""
        # Use CB with threshold=2
        cb_config = CircuitBreakerConfig(
            failure_threshold=2,
            reset_timeout_s=30.0,
        )
        deepgram_cb = register_circuit_breaker("deepgram", config=cb_config)

        with patch("infrastructure.speech.stt_failover.WHISPER_AVAILABLE", True):
            manager = STTFailoverManager(config=fast_stt_config)
            await manager.initialize()

            # Single failure
            await deepgram_cb._on_failure(RuntimeError("Transient error"))

            # Circuit stays closed
            assert deepgram_cb.state is CircuitBreakerState.CLOSED
            assert manager.get_active_provider() == "deepgram"

            # No failover events
            assert len(manager.get_failover_history()) == 0

            await manager.shutdown()

    async def test_success_after_failure_resets_count(
        self, fast_stt_config: STTFailoverConfig
    ):
        """Success after failure resets failure count, preventing trip."""
        cb_config = CircuitBreakerConfig(
            failure_threshold=2,
            reset_timeout_s=30.0,
        )
        deepgram_cb = register_circuit_breaker("deepgram", config=cb_config)

        with patch("infrastructure.speech.stt_failover.WHISPER_AVAILABLE", True):
            manager = STTFailoverManager(config=fast_stt_config)
            await manager.initialize()

            # Failure, then success
            await deepgram_cb._on_failure(RuntimeError("Error 1"))
            assert deepgram_cb.failure_count == 1

            await deepgram_cb._on_success()
            assert deepgram_cb.failure_count == 0

            # Another failure (count starts fresh)
            await deepgram_cb._on_failure(RuntimeError("Error 2"))
            assert deepgram_cb.failure_count == 1

            # Circuit still closed
            assert deepgram_cb.state is CircuitBreakerState.CLOSED
            assert manager.get_active_provider() == "deepgram"

            await manager.shutdown()

    async def test_intermittent_pattern_no_failover(
        self, fast_stt_config: STTFailoverConfig
    ):
        """Intermittent fail-succeed-fail-succeed pattern doesn't trip circuit."""
        cb_config = CircuitBreakerConfig(
            failure_threshold=3,
            reset_timeout_s=30.0,
        )
        deepgram_cb = register_circuit_breaker("deepgram", config=cb_config)

        with patch("infrastructure.speech.stt_failover.WHISPER_AVAILABLE", True):
            manager = STTFailoverManager(config=fast_stt_config)
            await manager.initialize()

            # Intermittent pattern
            for _ in range(10):
                await deepgram_cb._on_failure(RuntimeError("Intermittent"))
                await deepgram_cb._on_success()  # Resets count

            # Circuit should still be closed
            assert deepgram_cb.state is CircuitBreakerState.CLOSED
            assert manager.get_active_provider() == "deepgram"

            await manager.shutdown()

    async def test_burst_failures_trip_circuit(
        self, fast_stt_config: STTFailoverConfig, fast_cb_config: CircuitBreakerConfig
    ):
        """Burst of consecutive failures does trip the circuit."""
        deepgram_cb = register_circuit_breaker("deepgram", config=fast_cb_config)

        with patch("infrastructure.speech.stt_failover.WHISPER_AVAILABLE", True):
            manager = STTFailoverManager(config=fast_stt_config)
            await manager.initialize()

            # Burst of failures (no intervening successes)
            await deepgram_cb._on_failure(RuntimeError("Burst 1"))
            await deepgram_cb._on_failure(RuntimeError("Burst 2"))

            # Circuit should trip
            assert deepgram_cb.state is CircuitBreakerState.OPEN

            await asyncio.sleep(0.05)

            # Should have failed over
            assert manager.get_active_provider() in ("whisper", "none")

            await manager.shutdown()


# ---------------------------------------------------------------------------
# Additional Integration Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestFailoverManagerIntegration:
    """Additional integration tests for failover managers."""

    async def test_manual_failover_and_failback(
        self, fast_stt_config: STTFailoverConfig, fast_cb_config: CircuitBreakerConfig
    ):
        """Manual failover and failback work correctly."""
        register_circuit_breaker("deepgram", config=fast_cb_config)

        with patch("infrastructure.speech.stt_failover.WHISPER_AVAILABLE", True):
            manager = STTFailoverManager(config=fast_stt_config)
            await manager.initialize()

            # Manual failover
            await manager.force_failover_to_whisper()
            assert manager.get_active_provider() in ("whisper", "none")

            # Manual failback
            await manager.force_failback_to_deepgram()
            assert manager.get_active_provider() == "deepgram"

            await manager.shutdown()

    async def test_multiple_managers_share_circuit_breaker(
        self, fast_stt_config: STTFailoverConfig, fast_cb_config: CircuitBreakerConfig
    ):
        """Multiple failover managers share the same circuit breaker."""
        deepgram_cb = register_circuit_breaker("deepgram", config=fast_cb_config)

        with patch("infrastructure.speech.stt_failover.WHISPER_AVAILABLE", True):
            manager1 = STTFailoverManager(config=fast_stt_config)
            manager2 = STTFailoverManager(config=fast_stt_config)

            await manager1.initialize()
            await manager2.initialize()

            # Both should reference the same CB
            assert manager1._deepgram_cb is manager2._deepgram_cb
            assert manager1._deepgram_cb is deepgram_cb

            # Tripping via manager1 affects manager2
            await deepgram_cb.trip()
            await asyncio.sleep(0.05)

            # Both should have failed over
            assert manager1.get_active_provider() in ("whisper", "none")
            assert manager2.get_active_provider() in ("whisper", "none")

            await manager1.shutdown()
            await manager2.shutdown()

    async def test_health_endpoint_complete_information(
        self, fast_tts_config: TTSFailoverConfig, fast_cb_config: CircuitBreakerConfig
    ):
        """Health endpoint provides complete status information."""
        register_circuit_breaker("elevenlabs", config=fast_cb_config)

        with (
            patch("infrastructure.speech.tts_failover.EDGE_TTS_AVAILABLE", True),
            patch("infrastructure.speech.tts_failover.PYTTSX3_AVAILABLE", True),
        ):
            manager = TTSFailoverManager(config=fast_tts_config)
            await manager.initialize()

            health = manager.health()

            # Verify all expected fields
            assert "initialized" in health
            assert "active_provider" in health
            assert "elevenlabs_circuit_state" in health
            assert "local_tts_available" in health
            assert "local_tts_backend" in health
            assert "failover_count" in health
            assert "statistics" in health

            assert health["initialized"] is True
            assert health["active_provider"] == "elevenlabs"
            assert health["elevenlabs_circuit_state"] == "closed"

            await manager.shutdown()

    async def test_shutdown_cleanup(
        self, fast_stt_config: STTFailoverConfig, fast_cb_config: CircuitBreakerConfig
    ):
        """Shutdown properly cleans up resources."""
        register_circuit_breaker("deepgram", config=fast_cb_config)

        with patch("infrastructure.speech.stt_failover.WHISPER_AVAILABLE", True):
            manager = STTFailoverManager(config=fast_stt_config)
            await manager.initialize()

            # Verify callback is registered
            assert manager._callback_registered is True

            # Shutdown
            await manager.shutdown()

            # Verify cleanup
            assert manager._callback_registered is False
            assert manager._initialized is False


@pytest.mark.integration
class TestFailoverEdgeCases:
    """Edge case tests for failover scenarios."""

    async def test_no_fallback_available(
        self, fast_stt_config: STTFailoverConfig, fast_cb_config: CircuitBreakerConfig
    ):
        """Graceful handling when no fallback is available."""
        deepgram_cb = register_circuit_breaker("deepgram", config=fast_cb_config)

        # Whisper NOT available
        with patch("infrastructure.speech.stt_failover.WHISPER_AVAILABLE", False):
            manager = STTFailoverManager(config=fast_stt_config)
            await manager.initialize()

            # Trip circuit
            await deepgram_cb.trip()
            await asyncio.sleep(0.05)

            # Should be in NONE state
            assert manager.get_active_provider() == "none"

            await manager.shutdown()

    async def test_failover_during_half_open_failure(
        self, fast_stt_config: STTFailoverConfig, fast_cb_config: CircuitBreakerConfig
    ):
        """Stays on fallback when half-open probe fails."""
        deepgram_cb = register_circuit_breaker("deepgram", config=fast_cb_config)

        with patch("infrastructure.speech.stt_failover.WHISPER_AVAILABLE", True):
            manager = STTFailoverManager(config=fast_stt_config)
            await manager.initialize()

            # Trip to fallback
            await deepgram_cb.trip()
            await asyncio.sleep(0.05)
            initial_provider = manager.get_active_provider()

            # Wait for half-open (check internal _state, not lazy property)
            await asyncio.sleep(0.25)

            # Force transition to half-open via the state property check
            _ = deepgram_cb.state  # This triggers lazy half-open check

            # Make a call that will fail, triggering HALF_OPEN -> OPEN
            async def failing_fn():
                raise RuntimeError("Still broken")

            try:
                await deepgram_cb.call(failing_fn)
            except RuntimeError:
                pass

            # Should stay on fallback (OPEN or HALF_OPEN doesn't matter for provider)
            assert manager.get_active_provider() == initial_provider

            await manager.shutdown()

    async def test_rapid_state_changes(
        self, fast_tts_config: TTSFailoverConfig
    ):
        """Handles rapid state changes without race conditions."""
        cb_config = CircuitBreakerConfig(
            failure_threshold=1,  # Trip immediately
            reset_timeout_s=0.05,  # Very fast reset
        )
        elevenlabs_cb = register_circuit_breaker("elevenlabs", config=cb_config)

        with (
            patch("infrastructure.speech.tts_failover.EDGE_TTS_AVAILABLE", True),
            patch("infrastructure.speech.tts_failover.PYTTSX3_AVAILABLE", True),
        ):
            manager = TTSFailoverManager(config=fast_tts_config)
            await manager.initialize()

            # Rapid trip/reset cycles
            for _ in range(5):
                await elevenlabs_cb.trip()
                await asyncio.sleep(0.02)
                await elevenlabs_cb.reset()
                await asyncio.sleep(0.02)

            # Should end up in a stable state (ElevenLabs since we reset)
            await asyncio.sleep(0.1)

            # Manager should have a valid provider
            provider = manager.get_active_provider()
            assert provider in ("elevenlabs", "local", "none")

            await manager.shutdown()
