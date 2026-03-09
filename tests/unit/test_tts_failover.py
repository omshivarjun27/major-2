"""Unit tests for TTS Failover Manager.

Tests cover:
- TTSFailoverManager initialization
- Circuit breaker callback subscription
- Failover from ElevenLabs to local TTS on circuit OPEN
- Failback from local to ElevenLabs on circuit CLOSED
- Manual failover/failback
- Failover statistics tracking
- Failover event history
- Health reporting
- create_enhanced_local_fn helper
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
import pytest


class TestTTSFailoverConfig:
    """Tests for TTSFailoverConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        from infrastructure.speech.tts_failover import TTSFailoverConfig

        config = TTSFailoverConfig()
        assert config.elevenlabs_service_name == "elevenlabs"
        assert config.local_tts_voice == "en-US-AriaNeural"
        assert config.prefer_edge_tts is True
        assert config.failover_timeout_s == 2.0
        assert config.prewarm_local_tts is True

    def test_custom_config(self):
        """Test custom configuration values."""
        from infrastructure.speech.tts_failover import TTSFailoverConfig

        config = TTSFailoverConfig(
            elevenlabs_service_name="custom_elevenlabs",
            local_tts_voice="en-GB-SoniaNeural",
            prefer_edge_tts=False,
            failover_timeout_s=5.0,
        )
        assert config.elevenlabs_service_name == "custom_elevenlabs"
        assert config.local_tts_voice == "en-GB-SoniaNeural"
        assert config.prefer_edge_tts is False
        assert config.failover_timeout_s == 5.0


class TestTTSProvider:
    """Tests for TTSProvider enum."""

    def test_provider_values(self):
        """Test provider enum values."""
        from infrastructure.speech.tts_failover import TTSProvider

        assert TTSProvider.ELEVENLABS.value == "elevenlabs"
        assert TTSProvider.LOCAL.value == "local"
        assert TTSProvider.NONE.value == "none"


class TestFailoverEvent:
    """Tests for FailoverEvent dataclass."""

    def test_failover_event_creation(self):
        """Test creating a failover event."""
        from infrastructure.speech.tts_failover import FailoverEvent, TTSProvider

        event = FailoverEvent(
            timestamp=time.time(),
            from_provider=TTSProvider.ELEVENLABS,
            to_provider=TTSProvider.LOCAL,
            trigger="circuit_open",
            latency_ms=150.5,
        )
        assert event.from_provider == TTSProvider.ELEVENLABS
        assert event.to_provider == TTSProvider.LOCAL
        assert event.trigger == "circuit_open"
        assert event.latency_ms == 150.5

    def test_failover_event_str(self):
        """Test string representation of failover event."""
        from infrastructure.speech.tts_failover import FailoverEvent, TTSProvider

        event = FailoverEvent(
            timestamp=time.time(),
            from_provider=TTSProvider.ELEVENLABS,
            to_provider=TTSProvider.LOCAL,
            trigger="circuit_open",
            latency_ms=100.0,
        )
        event_str = str(event)
        assert "elevenlabs" in event_str
        assert "local" in event_str
        assert "circuit_open" in event_str


class TestFailoverStatistics:
    """Tests for FailoverStatistics dataclass."""

    def test_default_statistics(self):
        """Test default statistics values."""
        from infrastructure.speech.tts_failover import FailoverStatistics, TTSProvider

        stats = FailoverStatistics()
        assert stats.total_failovers == 0
        assert stats.total_failbacks == 0
        assert stats.total_time_in_fallback_ms == 0.0
        assert stats.current_provider == TTSProvider.ELEVENLABS

    def test_record_failover(self):
        """Test recording a failover."""
        from infrastructure.speech.tts_failover import FailoverStatistics, TTSProvider

        stats = FailoverStatistics()
        stats.record_failover()

        assert stats.total_failovers == 1
        assert stats.current_provider == TTSProvider.LOCAL
        assert stats.last_fallback_start is not None

    def test_record_failback(self):
        """Test recording a failback."""
        from infrastructure.speech.tts_failover import FailoverStatistics, TTSProvider

        stats = FailoverStatistics()
        stats.record_failover()
        time.sleep(0.1)  # Small delay to accumulate time
        stats.record_failback()

        assert stats.total_failovers == 1
        assert stats.total_failbacks == 1
        assert stats.current_provider == TTSProvider.ELEVENLABS
        assert stats.total_time_in_fallback_ms >= 50.0

    def test_to_dict(self):
        """Test converting statistics to dictionary."""
        from infrastructure.speech.tts_failover import FailoverStatistics

        stats = FailoverStatistics()
        stats.record_failover()

        result = stats.to_dict()
        assert "total_failovers" in result
        assert "total_failbacks" in result
        assert "total_time_in_fallback_ms" in result
        assert "currently_in_fallback" in result
        assert "current_provider" in result


class TestTTSResult:
    """Tests for TTSResult dataclass."""

    def test_successful_result(self):
        """Test a successful synthesis result."""
        from infrastructure.speech.tts_failover import TTSResult

        result = TTSResult(
            audio_bytes=b"\x00\x01\x02",
            engine="elevenlabs",
            latency_ms=150.5,
            text="Hello",
        )
        assert len(result.audio_bytes) == 3
        assert result.engine == "elevenlabs"
        assert result.success is True

    def test_failed_result(self):
        """Test a failed synthesis result."""
        from infrastructure.speech.tts_failover import TTSResult

        result = TTSResult(
            audio_bytes=b"",
            engine="none",
            latency_ms=50.0,
            text="Hello",
            error="Synthesis failed",
        )
        assert result.success is False


class TestTTSFailoverManagerInitialization:
    """Tests for TTSFailoverManager initialization."""

    def test_init_with_default_config(self):
        """Test initialization with default configuration."""
        from infrastructure.speech.tts_failover import TTSFailoverManager

        manager = TTSFailoverManager()
        assert manager.config.elevenlabs_service_name == "elevenlabs"
        assert manager._initialized is False

    def test_init_with_custom_config(self):
        """Test initialization with custom configuration."""
        from infrastructure.speech.tts_failover import (
            TTSFailoverManager,
            TTSFailoverConfig,
        )

        config = TTSFailoverConfig(local_tts_voice="en-GB-SoniaNeural")
        manager = TTSFailoverManager(config=config)
        assert manager.config.local_tts_voice == "en-GB-SoniaNeural"

    async def test_initialize_registers_callback(self):
        """Test that initialize registers circuit breaker callback."""
        from infrastructure.speech.tts_failover import TTSFailoverManager
        from infrastructure.resilience.circuit_breaker import clear_registry

        clear_registry()

        manager = TTSFailoverManager()
        await manager.initialize()

        try:
            assert manager._initialized is True
            assert manager._callback_registered is True
            assert manager._elevenlabs_cb is not None
        finally:
            await manager.shutdown()
            clear_registry()

    async def test_initialize_is_idempotent(self):
        """Test that initialize can be called multiple times safely."""
        from infrastructure.speech.tts_failover import TTSFailoverManager
        from infrastructure.resilience.circuit_breaker import clear_registry

        clear_registry()

        manager = TTSFailoverManager()
        await manager.initialize()
        await manager.initialize()
        await manager.initialize()

        try:
            assert manager._initialized is True
        finally:
            await manager.shutdown()
            clear_registry()


class TestTTSFailoverManagerActiveProvider:
    """Tests for active provider management."""

    async def test_default_active_provider_is_elevenlabs(self):
        """Test that default active provider is ElevenLabs."""
        from infrastructure.speech.tts_failover import TTSFailoverManager
        from infrastructure.resilience.circuit_breaker import clear_registry

        clear_registry()

        manager = TTSFailoverManager()
        await manager.initialize()

        try:
            assert manager.get_active_provider() == "elevenlabs"
        finally:
            await manager.shutdown()
            clear_registry()

    async def test_get_active_provider_enum(self):
        """Test get_active_provider_enum returns enum."""
        from infrastructure.speech.tts_failover import TTSFailoverManager, TTSProvider
        from infrastructure.resilience.circuit_breaker import clear_registry

        clear_registry()

        manager = TTSFailoverManager()
        await manager.initialize()

        try:
            provider = manager.get_active_provider_enum()
            assert provider == TTSProvider.ELEVENLABS
        finally:
            await manager.shutdown()
            clear_registry()


class TestTTSFailoverManagerFailover:
    """Tests for failover functionality."""

    async def test_manual_failover_to_local(self):
        """Test manual failover to local TTS."""
        from infrastructure.speech.tts_failover import TTSFailoverManager
        from infrastructure.speech import tts_failover
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.speech.local import edge_tts_fallback

        clear_registry()
        original_edge = edge_tts_fallback.EDGE_TTS_AVAILABLE
        original_tts_failover = tts_failover.EDGE_TTS_AVAILABLE

        try:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = True
            tts_failover.EDGE_TTS_AVAILABLE = True

            manager = TTSFailoverManager()
            await manager.initialize()

            assert manager.get_active_provider() == "elevenlabs"

            await manager.force_failover_to_local()

            assert manager.get_active_provider() == "local"
        finally:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = original_edge
            tts_failover.EDGE_TTS_AVAILABLE = original_tts_failover
            await manager.shutdown()
            clear_registry()

    async def test_manual_failback_to_elevenlabs(self):
        """Test manual failback to ElevenLabs."""
        from infrastructure.speech.tts_failover import TTSFailoverManager
        from infrastructure.speech import tts_failover
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.speech.local import edge_tts_fallback

        clear_registry()
        original_edge = edge_tts_fallback.EDGE_TTS_AVAILABLE
        original_tts_failover = tts_failover.EDGE_TTS_AVAILABLE

        try:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = True
            tts_failover.EDGE_TTS_AVAILABLE = True

            manager = TTSFailoverManager()
            await manager.initialize()

            await manager.force_failover_to_local()
            assert manager.get_active_provider() == "local"

            await manager.force_failback_to_elevenlabs()
            assert manager.get_active_provider() == "elevenlabs"
        finally:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = original_edge
            tts_failover.EDGE_TTS_AVAILABLE = original_tts_failover
            await manager.shutdown()
            clear_registry()

    async def test_failover_when_local_not_available(self):
        """Test failover behavior when local TTS is not available."""
        from infrastructure.speech.tts_failover import TTSFailoverManager, TTSProvider
        from infrastructure.speech import tts_failover
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.speech.local import edge_tts_fallback

        clear_registry()
        original_edge = edge_tts_fallback.EDGE_TTS_AVAILABLE
        original_pyttsx3 = edge_tts_fallback.PYTTSX3_AVAILABLE
        original_tts_edge = tts_failover.EDGE_TTS_AVAILABLE
        original_tts_pyttsx3 = tts_failover.PYTTSX3_AVAILABLE

        try:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = False
            edge_tts_fallback.PYTTSX3_AVAILABLE = False
            tts_failover.EDGE_TTS_AVAILABLE = False
            tts_failover.PYTTSX3_AVAILABLE = False

            manager = TTSFailoverManager()
            await manager.initialize()

            await manager.force_failover_to_local()

            assert manager.get_active_provider_enum() == TTSProvider.NONE
        finally:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = original_edge
            edge_tts_fallback.PYTTSX3_AVAILABLE = original_pyttsx3
            tts_failover.EDGE_TTS_AVAILABLE = original_tts_edge
            tts_failover.PYTTSX3_AVAILABLE = original_tts_pyttsx3
            await manager.shutdown()
            clear_registry()


class TestTTSFailoverManagerCircuitCallback:
    """Tests for circuit breaker callback handling."""

    async def test_circuit_open_triggers_failover(self):
        """Test that circuit OPEN state triggers failover to local."""
        from infrastructure.speech.tts_failover import TTSFailoverManager
        from infrastructure.speech import tts_failover
        from infrastructure.resilience.circuit_breaker import (
            CircuitBreakerState,
            StateChangeEvent,
            clear_registry,
        )
        from infrastructure.speech.local import edge_tts_fallback

        clear_registry()
        original_edge = edge_tts_fallback.EDGE_TTS_AVAILABLE
        original_tts_failover = tts_failover.EDGE_TTS_AVAILABLE

        try:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = True
            tts_failover.EDGE_TTS_AVAILABLE = True

            manager = TTSFailoverManager()
            await manager.initialize()

            assert manager.get_active_provider() == "elevenlabs"

            # Simulate circuit OPEN event
            event = StateChangeEvent(
                service_name="elevenlabs",
                previous_state=CircuitBreakerState.CLOSED,
                new_state=CircuitBreakerState.OPEN,
                failure_count=3,
            )
            await manager._on_circuit_state_change(event)

            assert manager.get_active_provider() == "local"
        finally:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = original_edge
            tts_failover.EDGE_TTS_AVAILABLE = original_tts_failover
            await manager.shutdown()
            clear_registry()

    async def test_circuit_closed_triggers_failback(self):
        """Test that circuit CLOSED state triggers failback to ElevenLabs."""
        from infrastructure.speech.tts_failover import TTSFailoverManager
        from infrastructure.speech import tts_failover
        from infrastructure.resilience.circuit_breaker import (
            CircuitBreakerState,
            StateChangeEvent,
            clear_registry,
        )
        from infrastructure.speech.local import edge_tts_fallback

        clear_registry()
        original_edge = edge_tts_fallback.EDGE_TTS_AVAILABLE
        original_tts_failover = tts_failover.EDGE_TTS_AVAILABLE

        try:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = True
            tts_failover.EDGE_TTS_AVAILABLE = True

            manager = TTSFailoverManager()
            await manager.initialize()

            await manager.force_failover_to_local()
            assert manager.get_active_provider() == "local"

            # Simulate circuit CLOSED event
            event = StateChangeEvent(
                service_name="elevenlabs",
                previous_state=CircuitBreakerState.HALF_OPEN,
                new_state=CircuitBreakerState.CLOSED,
                failure_count=0,
            )
            await manager._on_circuit_state_change(event)

            assert manager.get_active_provider() == "elevenlabs"
        finally:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = original_edge
            tts_failover.EDGE_TTS_AVAILABLE = original_tts_failover
            await manager.shutdown()
            clear_registry()

    async def test_ignores_events_from_other_services(self):
        """Test that events from other services are ignored."""
        from infrastructure.speech.tts_failover import TTSFailoverManager
        from infrastructure.resilience.circuit_breaker import (
            CircuitBreakerState,
            StateChangeEvent,
            clear_registry,
        )

        clear_registry()

        manager = TTSFailoverManager()
        await manager.initialize()

        try:
            assert manager.get_active_provider() == "elevenlabs"

            # Simulate circuit OPEN event from different service
            event = StateChangeEvent(
                service_name="deepgram",  # Different service
                previous_state=CircuitBreakerState.CLOSED,
                new_state=CircuitBreakerState.OPEN,
                failure_count=3,
            )
            await manager._on_circuit_state_change(event)

            # Should still be on ElevenLabs
            assert manager.get_active_provider() == "elevenlabs"
        finally:
            await manager.shutdown()
            clear_registry()


class TestTTSFailoverManagerStatistics:
    """Tests for failover statistics tracking."""

    async def test_statistics_track_failover(self):
        """Test that statistics track failover events."""
        from infrastructure.speech.tts_failover import TTSFailoverManager
        from infrastructure.speech import tts_failover
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.speech.local import edge_tts_fallback

        clear_registry()
        original_edge = edge_tts_fallback.EDGE_TTS_AVAILABLE
        original_tts_failover = tts_failover.EDGE_TTS_AVAILABLE

        try:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = True
            tts_failover.EDGE_TTS_AVAILABLE = True

            manager = TTSFailoverManager()
            await manager.initialize()

            stats = manager.get_statistics()
            assert stats["total_failovers"] == 0

            await manager.force_failover_to_local()

            stats = manager.get_statistics()
            assert stats["total_failovers"] == 1
            assert stats["currently_in_fallback"] is True
        finally:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = original_edge
            tts_failover.EDGE_TTS_AVAILABLE = original_tts_failover
            await manager.shutdown()
            clear_registry()

    async def test_statistics_track_failback(self):
        """Test that statistics track failback events."""
        from infrastructure.speech.tts_failover import TTSFailoverManager
        from infrastructure.speech import tts_failover
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.speech.local import edge_tts_fallback

        clear_registry()
        original_edge = edge_tts_fallback.EDGE_TTS_AVAILABLE
        original_tts_failover = tts_failover.EDGE_TTS_AVAILABLE

        try:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = True
            tts_failover.EDGE_TTS_AVAILABLE = True

            manager = TTSFailoverManager()
            await manager.initialize()

            await manager.force_failover_to_local()
            await manager.force_failback_to_elevenlabs()

            stats = manager.get_statistics()
            assert stats["total_failovers"] == 1
            assert stats["total_failbacks"] == 1
            assert stats["currently_in_fallback"] is False
        finally:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = original_edge
            tts_failover.EDGE_TTS_AVAILABLE = original_tts_failover
            await manager.shutdown()
            clear_registry()


class TestTTSFailoverManagerHistory:
    """Tests for failover history tracking."""

    async def test_failover_history_recorded(self):
        """Test that failover events are recorded in history."""
        from infrastructure.speech.tts_failover import TTSFailoverManager
        from infrastructure.speech import tts_failover
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.speech.local import edge_tts_fallback

        clear_registry()
        original_edge = edge_tts_fallback.EDGE_TTS_AVAILABLE
        original_tts_failover = tts_failover.EDGE_TTS_AVAILABLE

        try:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = True
            tts_failover.EDGE_TTS_AVAILABLE = True

            manager = TTSFailoverManager()
            await manager.initialize()

            assert len(manager.get_failover_history()) == 0

            await manager.force_failover_to_local()

            history = manager.get_failover_history()
            assert len(history) == 1
            assert history[0].to_provider.value == "local"
            assert history[0].trigger == "manual"
        finally:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = original_edge
            tts_failover.EDGE_TTS_AVAILABLE = original_tts_failover
            await manager.shutdown()
            clear_registry()


class TestTTSFailoverManagerHealth:
    """Tests for health reporting."""

    async def test_health_snapshot(self):
        """Test health snapshot contains expected fields."""
        from infrastructure.speech.tts_failover import TTSFailoverManager
        from infrastructure.resilience.circuit_breaker import clear_registry

        clear_registry()

        manager = TTSFailoverManager()
        await manager.initialize()

        try:
            health = manager.health()

            assert "initialized" in health
            assert "active_provider" in health
            assert "elevenlabs_circuit_state" in health
            assert "local_tts_available" in health
            assert "statistics" in health

            assert health["initialized"] is True
            assert health["active_provider"] == "elevenlabs"
        finally:
            await manager.shutdown()
            clear_registry()


class TestTTSFailoverManagerShutdown:
    """Tests for shutdown behavior."""

    async def test_shutdown_unregisters_callback(self):
        """Test that shutdown unregisters circuit breaker callback."""
        from infrastructure.speech.tts_failover import TTSFailoverManager
        from infrastructure.resilience.circuit_breaker import clear_registry

        clear_registry()

        manager = TTSFailoverManager()
        await manager.initialize()

        assert manager._callback_registered is True

        await manager.shutdown()

        assert manager._callback_registered is False
        assert manager._initialized is False

        clear_registry()

    async def test_shutdown_is_safe_without_init(self):
        """Test that shutdown is safe without prior initialization."""
        from infrastructure.speech.tts_failover import TTSFailoverManager

        manager = TTSFailoverManager()
        await manager.shutdown()  # Should not raise


class TestCreateTTSFailoverManager:
    """Tests for convenience creation function."""

    async def test_create_returns_initialized_manager(self):
        """Test that create function returns initialized manager."""
        from infrastructure.speech.tts_failover import create_tts_failover_manager
        from infrastructure.resilience.circuit_breaker import clear_registry

        clear_registry()

        manager = await create_tts_failover_manager()

        try:
            assert manager._initialized is True
            assert manager.get_active_provider() == "elevenlabs"
        finally:
            await manager.shutdown()
            clear_registry()


class TestCreateEnhancedLocalFn:
    """Tests for create_enhanced_local_fn helper."""

    def test_create_returns_callable(self):
        """Test that create_enhanced_local_fn returns a callable."""
        from infrastructure.speech.tts_failover import create_enhanced_local_fn

        fn = create_enhanced_local_fn()
        assert callable(fn)

    def test_create_with_custom_voice(self):
        """Test create_enhanced_local_fn with custom voice."""
        from infrastructure.speech.tts_failover import create_enhanced_local_fn

        fn = create_enhanced_local_fn(voice="en-GB-SoniaNeural")
        assert callable(fn)


class TestTTSFailoverManagerGetLocalFn:
    """Tests for get_local_fn method."""

    async def test_get_local_fn_returns_callable(self):
        """Test that get_local_fn returns a callable."""
        from infrastructure.speech.tts_failover import TTSFailoverManager
        from infrastructure.resilience.circuit_breaker import clear_registry

        clear_registry()

        manager = TTSFailoverManager()
        await manager.initialize()

        try:
            local_fn = manager.get_local_fn()
            assert callable(local_fn)
        finally:
            await manager.shutdown()
            clear_registry()

    def test_get_local_fn_works_without_initialize(self):
        """Test that get_local_fn works even without initialize."""
        from infrastructure.speech.tts_failover import TTSFailoverManager

        manager = TTSFailoverManager()
        local_fn = manager.get_local_fn()
        assert callable(local_fn)


class TestTTSFailoverManagerSynthesis:
    """Tests for synthesis methods."""

    def test_synthesize_empty_text_returns_error(self):
        """Test that empty text returns error result."""
        from infrastructure.speech.tts_failover import TTSFailoverManager

        manager = TTSFailoverManager()
        result = manager.synthesize("")

        assert result.success is False
        assert result.error == "Empty text provided"

    async def test_async_synthesize_empty_text_returns_error(self):
        """Test that async with empty text returns error result."""
        from infrastructure.speech.tts_failover import TTSFailoverManager

        manager = TTSFailoverManager()
        result = await manager.async_synthesize("")

        assert result.success is False
        assert result.error == "Empty text provided"
