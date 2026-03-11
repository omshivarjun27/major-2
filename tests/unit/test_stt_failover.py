"""Unit tests for STT Failover Manager.

Tests cover:
- STTFailoverManager initialization
- Circuit breaker callback subscription
- Failover from Deepgram to Whisper on circuit OPEN
- Failback from Whisper to Deepgram on circuit CLOSED
- Manual failover/failback
- Failover event history
- Health reporting
"""

import time
from unittest.mock import MagicMock


class TestSTTFailoverConfig:
    """Tests for STTFailoverConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        from infrastructure.speech.stt_failover import STTFailoverConfig

        config = STTFailoverConfig()
        assert config.deepgram_service_name == "deepgram"
        assert config.whisper_model_size == "base"
        assert config.prewarm_whisper is True
        assert config.failover_timeout_s == 2.0
        assert config.auto_initialize is False

    def test_custom_config(self):
        """Test custom configuration values."""
        from infrastructure.speech.stt_failover import STTFailoverConfig

        config = STTFailoverConfig(
            deepgram_service_name="custom_deepgram",
            whisper_model_size="tiny",
            prewarm_whisper=False,
            failover_timeout_s=5.0,
        )
        assert config.deepgram_service_name == "custom_deepgram"
        assert config.whisper_model_size == "tiny"
        assert config.prewarm_whisper is False
        assert config.failover_timeout_s == 5.0


class TestSTTProvider:
    """Tests for STTProvider enum."""

    def test_provider_values(self):
        """Test provider enum values."""
        from infrastructure.speech.stt_failover import STTProvider

        assert STTProvider.DEEPGRAM.value == "deepgram"
        assert STTProvider.WHISPER.value == "whisper"
        assert STTProvider.NONE.value == "none"


class TestFailoverEvent:
    """Tests for FailoverEvent dataclass."""

    def test_failover_event_creation(self):
        """Test creating a failover event."""
        from infrastructure.speech.stt_failover import FailoverEvent, STTProvider

        event = FailoverEvent(
            timestamp=time.time(),
            from_provider=STTProvider.DEEPGRAM,
            to_provider=STTProvider.WHISPER,
            trigger="circuit_open",
            latency_ms=150.5,
        )
        assert event.from_provider == STTProvider.DEEPGRAM
        assert event.to_provider == STTProvider.WHISPER
        assert event.trigger == "circuit_open"
        assert event.latency_ms == 150.5

    def test_failover_event_str(self):
        """Test string representation of failover event."""
        from infrastructure.speech.stt_failover import FailoverEvent, STTProvider

        event = FailoverEvent(
            timestamp=time.time(),
            from_provider=STTProvider.DEEPGRAM,
            to_provider=STTProvider.WHISPER,
            trigger="circuit_open",
            latency_ms=100.0,
        )
        event_str = str(event)
        assert "deepgram" in event_str
        assert "whisper" in event_str
        assert "circuit_open" in event_str


class TestSTTFailoverManagerInitialization:
    """Tests for STTFailoverManager initialization."""

    def test_init_with_default_config(self):
        """Test initialization with default configuration."""
        from infrastructure.speech.stt_failover import STTFailoverManager

        manager = STTFailoverManager()
        assert manager.config.deepgram_service_name == "deepgram"
        assert manager._initialized is False

    def test_init_with_custom_config(self):
        """Test initialization with custom configuration."""
        from infrastructure.speech.stt_failover import (
            STTFailoverConfig,
            STTFailoverManager,
        )

        config = STTFailoverConfig(whisper_model_size="tiny")
        manager = STTFailoverManager(config=config)
        assert manager.config.whisper_model_size == "tiny"

    async def test_initialize_registers_callback(self):
        """Test that initialize registers circuit breaker callback."""
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.speech.stt_failover import STTFailoverManager

        clear_registry()

        manager = STTFailoverManager()
        await manager.initialize()

        try:
            assert manager._initialized is True
            assert manager._callback_registered is True
            assert manager._deepgram_cb is not None
        finally:
            await manager.shutdown()
            clear_registry()

    async def test_initialize_is_idempotent(self):
        """Test that initialize can be called multiple times safely."""
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.speech.stt_failover import STTFailoverManager

        clear_registry()

        manager = STTFailoverManager()
        await manager.initialize()
        await manager.initialize()
        await manager.initialize()

        try:
            assert manager._initialized is True
        finally:
            await manager.shutdown()
            clear_registry()


class TestSTTFailoverManagerActiveProvider:
    """Tests for active provider management."""

    async def test_default_active_provider_is_deepgram(self):
        """Test that default active provider is Deepgram."""
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.speech.stt_failover import STTFailoverManager

        clear_registry()

        manager = STTFailoverManager()
        await manager.initialize()

        try:
            assert manager.get_active_provider() == "deepgram"
        finally:
            await manager.shutdown()
            clear_registry()

    async def test_get_active_provider_enum(self):
        """Test get_active_provider_enum returns enum."""
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.speech.stt_failover import STTFailoverManager, STTProvider

        clear_registry()

        manager = STTFailoverManager()
        await manager.initialize()

        try:
            provider = manager.get_active_provider_enum()
            assert provider == STTProvider.DEEPGRAM
        finally:
            await manager.shutdown()
            clear_registry()


class TestSTTFailoverManagerFailover:
    """Tests for failover functionality."""

    async def test_manual_failover_to_whisper(self):
        """Test manual failover to Whisper."""
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.speech import stt_failover
        from infrastructure.speech.local import whisper_stt
        from infrastructure.speech.stt_failover import STTFailoverManager

        clear_registry()
        original_available = whisper_stt.WHISPER_AVAILABLE
        original_stt_failover = stt_failover.WHISPER_AVAILABLE

        try:
            whisper_stt.WHISPER_AVAILABLE = True
            stt_failover.WHISPER_AVAILABLE = True

            manager = STTFailoverManager()
            await manager.initialize()

            assert manager.get_active_provider() == "deepgram"

            await manager.force_failover_to_whisper()

            assert manager.get_active_provider() == "whisper"
        finally:
            whisper_stt.WHISPER_AVAILABLE = original_available
            stt_failover.WHISPER_AVAILABLE = original_stt_failover
            await manager.shutdown()
            clear_registry()

    async def test_manual_failback_to_deepgram(self):
        """Test manual failback to Deepgram."""
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.speech import stt_failover
        from infrastructure.speech.local import whisper_stt
        from infrastructure.speech.stt_failover import STTFailoverManager

        clear_registry()
        original_available = whisper_stt.WHISPER_AVAILABLE
        original_stt_failover = stt_failover.WHISPER_AVAILABLE

        try:
            whisper_stt.WHISPER_AVAILABLE = True
            stt_failover.WHISPER_AVAILABLE = True

            manager = STTFailoverManager()
            await manager.initialize()

            await manager.force_failover_to_whisper()
            assert manager.get_active_provider() == "whisper"

            await manager.force_failback_to_deepgram()
            assert manager.get_active_provider() == "deepgram"
        finally:
            whisper_stt.WHISPER_AVAILABLE = original_available
            stt_failover.WHISPER_AVAILABLE = original_stt_failover
            await manager.shutdown()
            clear_registry()

    async def test_failover_when_whisper_not_available(self):
        """Test failover behavior when Whisper is not available."""
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.speech import stt_failover
        from infrastructure.speech.local import whisper_stt
        from infrastructure.speech.stt_failover import STTFailoverManager, STTProvider

        clear_registry()
        original_available = whisper_stt.WHISPER_AVAILABLE
        original_stt_failover = stt_failover.WHISPER_AVAILABLE

        try:
            whisper_stt.WHISPER_AVAILABLE = False
            stt_failover.WHISPER_AVAILABLE = False

            manager = STTFailoverManager()
            await manager.initialize()

            await manager.force_failover_to_whisper()

            # Should fall back to NONE when Whisper unavailable
            assert manager.get_active_provider_enum() == STTProvider.NONE
        finally:
            whisper_stt.WHISPER_AVAILABLE = original_available
            stt_failover.WHISPER_AVAILABLE = original_stt_failover
            await manager.shutdown()
            clear_registry()


class TestSTTFailoverManagerCircuitCallback:
    """Tests for circuit breaker callback handling."""

    async def test_circuit_open_triggers_failover(self):
        """Test that circuit OPEN state triggers failover to Whisper."""
        from infrastructure.resilience.circuit_breaker import (
            CircuitBreakerState,
            StateChangeEvent,
            clear_registry,
        )
        from infrastructure.speech import stt_failover
        from infrastructure.speech.local import whisper_stt
        from infrastructure.speech.stt_failover import STTFailoverManager

        clear_registry()
        original_available = whisper_stt.WHISPER_AVAILABLE
        original_stt_failover = stt_failover.WHISPER_AVAILABLE

        try:
            whisper_stt.WHISPER_AVAILABLE = True
            stt_failover.WHISPER_AVAILABLE = True

            manager = STTFailoverManager()
            await manager.initialize()

            assert manager.get_active_provider() == "deepgram"

            # Simulate circuit OPEN event
            event = StateChangeEvent(
                service_name="deepgram",
                previous_state=CircuitBreakerState.CLOSED,
                new_state=CircuitBreakerState.OPEN,
                failure_count=3,
            )
            await manager._on_circuit_state_change(event)

            assert manager.get_active_provider() == "whisper"
        finally:
            whisper_stt.WHISPER_AVAILABLE = original_available
            stt_failover.WHISPER_AVAILABLE = original_stt_failover
            await manager.shutdown()
            clear_registry()

    async def test_circuit_closed_triggers_failback(self):
        """Test that circuit CLOSED state triggers failback to Deepgram."""
        from infrastructure.resilience.circuit_breaker import (
            CircuitBreakerState,
            StateChangeEvent,
            clear_registry,
        )
        from infrastructure.speech import stt_failover
        from infrastructure.speech.local import whisper_stt
        from infrastructure.speech.stt_failover import STTFailoverManager

        clear_registry()
        original_available = whisper_stt.WHISPER_AVAILABLE
        original_stt_failover = stt_failover.WHISPER_AVAILABLE

        try:
            whisper_stt.WHISPER_AVAILABLE = True
            stt_failover.WHISPER_AVAILABLE = True

            manager = STTFailoverManager()
            await manager.initialize()

            # First, failover to Whisper
            await manager.force_failover_to_whisper()
            assert manager.get_active_provider() == "whisper"

            # Simulate circuit CLOSED event (after recovery)
            event = StateChangeEvent(
                service_name="deepgram",
                previous_state=CircuitBreakerState.HALF_OPEN,
                new_state=CircuitBreakerState.CLOSED,
                failure_count=0,
            )
            await manager._on_circuit_state_change(event)

            assert manager.get_active_provider() == "deepgram"
        finally:
            whisper_stt.WHISPER_AVAILABLE = original_available
            stt_failover.WHISPER_AVAILABLE = original_stt_failover
            await manager.shutdown()
            clear_registry()

    async def test_ignores_events_from_other_services(self):
        """Test that events from other services are ignored."""
        from infrastructure.resilience.circuit_breaker import (
            CircuitBreakerState,
            StateChangeEvent,
            clear_registry,
        )
        from infrastructure.speech.stt_failover import STTFailoverManager

        clear_registry()

        manager = STTFailoverManager()
        await manager.initialize()

        try:
            assert manager.get_active_provider() == "deepgram"

            # Simulate circuit OPEN event from different service
            event = StateChangeEvent(
                service_name="elevenlabs",  # Different service
                previous_state=CircuitBreakerState.CLOSED,
                new_state=CircuitBreakerState.OPEN,
                failure_count=3,
            )
            await manager._on_circuit_state_change(event)

            # Should still be on Deepgram
            assert manager.get_active_provider() == "deepgram"
        finally:
            await manager.shutdown()
            clear_registry()


class TestSTTFailoverManagerHistory:
    """Tests for failover history tracking."""

    async def test_failover_history_recorded(self):
        """Test that failover events are recorded in history."""
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.speech import stt_failover
        from infrastructure.speech.local import whisper_stt
        from infrastructure.speech.stt_failover import STTFailoverManager

        clear_registry()
        original_available = whisper_stt.WHISPER_AVAILABLE
        original_stt_failover = stt_failover.WHISPER_AVAILABLE

        try:
            whisper_stt.WHISPER_AVAILABLE = True
            stt_failover.WHISPER_AVAILABLE = True

            manager = STTFailoverManager()
            await manager.initialize()

            assert len(manager.get_failover_history()) == 0

            await manager.force_failover_to_whisper()

            history = manager.get_failover_history()
            assert len(history) == 1
            assert history[0].to_provider.value == "whisper"
            assert history[0].trigger == "manual"
        finally:
            whisper_stt.WHISPER_AVAILABLE = original_available
            stt_failover.WHISPER_AVAILABLE = original_stt_failover
            await manager.shutdown()
            clear_registry()

    async def test_history_trims_at_max(self):
        """Test that history is trimmed when exceeding max."""
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.speech import stt_failover
        from infrastructure.speech.local import whisper_stt
        from infrastructure.speech.stt_failover import STTFailoverManager

        clear_registry()
        original_available = whisper_stt.WHISPER_AVAILABLE
        original_stt_failover = stt_failover.WHISPER_AVAILABLE

        try:
            whisper_stt.WHISPER_AVAILABLE = True
            stt_failover.WHISPER_AVAILABLE = True

            manager = STTFailoverManager()
            manager._max_history = 5  # Set small limit for testing
            await manager.initialize()

            # Generate more events than max
            for _ in range(10):
                await manager.force_failover_to_whisper()
                await manager.force_failback_to_deepgram()

            history = manager.get_failover_history()
            assert len(history) <= 5
        finally:
            whisper_stt.WHISPER_AVAILABLE = original_available
            stt_failover.WHISPER_AVAILABLE = original_stt_failover
            await manager.shutdown()
            clear_registry()


class TestSTTFailoverManagerHealth:
    """Tests for health reporting."""

    async def test_health_snapshot(self):
        """Test health snapshot contains expected fields."""
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.speech.stt_failover import STTFailoverManager

        clear_registry()

        manager = STTFailoverManager()
        await manager.initialize()

        try:
            health = manager.health()

            assert "initialized" in health
            assert "active_provider" in health
            assert "deepgram_circuit_state" in health
            assert "whisper_available" in health
            assert "whisper_loaded" in health
            assert "failover_count" in health

            assert health["initialized"] is True
            assert health["active_provider"] == "deepgram"
        finally:
            await manager.shutdown()
            clear_registry()

    async def test_health_after_failover(self):
        """Test health snapshot after failover."""
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.speech import stt_failover
        from infrastructure.speech.local import whisper_stt
        from infrastructure.speech.stt_failover import STTFailoverManager

        clear_registry()
        original_available = whisper_stt.WHISPER_AVAILABLE
        original_stt_failover = stt_failover.WHISPER_AVAILABLE

        try:
            whisper_stt.WHISPER_AVAILABLE = True
            stt_failover.WHISPER_AVAILABLE = True

            manager = STTFailoverManager()
            await manager.initialize()

            await manager.force_failover_to_whisper()

            health = manager.health()
            assert health["active_provider"] == "whisper"
            assert health["failover_count"] == 1
            assert health["last_failover"] is not None
        finally:
            whisper_stt.WHISPER_AVAILABLE = original_available
            stt_failover.WHISPER_AVAILABLE = original_stt_failover
            await manager.shutdown()
            clear_registry()


class TestSTTFailoverManagerShutdown:
    """Tests for shutdown behavior."""

    async def test_shutdown_unregisters_callback(self):
        """Test that shutdown unregisters circuit breaker callback."""
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.speech.stt_failover import STTFailoverManager

        clear_registry()

        manager = STTFailoverManager()
        await manager.initialize()

        assert manager._callback_registered is True

        await manager.shutdown()

        assert manager._callback_registered is False
        assert manager._initialized is False

        clear_registry()

    async def test_shutdown_is_safe_without_init(self):
        """Test that shutdown is safe without prior initialization."""
        from infrastructure.speech.stt_failover import STTFailoverManager

        manager = STTFailoverManager()
        await manager.shutdown()  # Should not raise


class TestCreateSTTFailoverManager:
    """Tests for convenience creation function."""

    async def test_create_returns_initialized_manager(self):
        """Test that create function returns initialized manager."""
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.speech.stt_failover import create_stt_failover_manager

        clear_registry()

        manager = await create_stt_failover_manager()

        try:
            assert manager._initialized is True
            assert manager.get_active_provider() == "deepgram"
        finally:
            await manager.shutdown()
            clear_registry()

    async def test_create_with_custom_config(self):
        """Test create function with custom config."""
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.speech.stt_failover import (
            STTFailoverConfig,
            create_stt_failover_manager,
        )

        clear_registry()

        config = STTFailoverConfig(whisper_model_size="tiny")
        manager = await create_stt_failover_manager(config=config)

        try:
            assert manager.config.whisper_model_size == "tiny"
        finally:
            await manager.shutdown()
            clear_registry()


class TestSTTFailoverManagerTranscription:
    """Tests for transcription delegation."""

    async def test_transcribe_when_deepgram_active(self):
        """Test transcribe returns placeholder when Deepgram active."""
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.speech.stt_failover import STTFailoverManager

        clear_registry()

        manager = STTFailoverManager()
        await manager.initialize()

        try:
            result = await manager.transcribe(b"audio data")

            # Should indicate Deepgram is handled by LiveKit
            assert "LiveKit" in (result.error or "")
        finally:
            await manager.shutdown()
            clear_registry()

    async def test_transcribe_delegates_to_whisper(self):
        """Test transcribe delegates to Whisper when active."""
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.speech import stt_failover
        from infrastructure.speech.local import whisper_stt
        from infrastructure.speech.stt_failover import STTFailoverManager

        clear_registry()
        original_available = whisper_stt.WHISPER_AVAILABLE
        original_stt_failover = stt_failover.WHISPER_AVAILABLE
        original_fw = whisper_stt._faster_whisper

        try:
            whisper_stt.WHISPER_AVAILABLE = True
            stt_failover.WHISPER_AVAILABLE = True

            # Mock the Whisper model
            mock_segment = MagicMock()
            mock_segment.text = "Test transcription"
            mock_segment.avg_logprob = -0.5

            mock_info = MagicMock()
            mock_info.language = "en"

            mock_model = MagicMock()
            mock_model.transcribe.return_value = ([mock_segment], mock_info)

            mock_fw = MagicMock()
            mock_fw.WhisperModel.return_value = mock_model
            whisper_stt._faster_whisper = mock_fw

            manager = STTFailoverManager()
            await manager.initialize()

            await manager.force_failover_to_whisper()

            result = await manager.transcribe(b"audio data")

            assert result.text == "Test transcription"
        finally:
            whisper_stt.WHISPER_AVAILABLE = original_available
            stt_failover.WHISPER_AVAILABLE = original_stt_failover
            whisper_stt._faster_whisper = original_fw
            await manager.shutdown()
            clear_registry()
