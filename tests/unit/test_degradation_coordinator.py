"""Unit tests for Degradation Coordinator.

Tests cover:
- DegradationLevel enum
- DegradationPolicy dataclass
- DegradationCoordinator initialization
- Degradation level computation
- Feature availability checks
- Circuit breaker callback handling
- Event history tracking
- Health reporting
- Singleton access
"""

import asyncio
import time


class TestDegradationLevel:
    """Tests for DegradationLevel enum."""

    def test_level_values(self):
        """Test degradation level enum values."""
        from infrastructure.resilience.degradation_coordinator import DegradationLevel

        assert DegradationLevel.FULL.value == "full"
        assert DegradationLevel.PARTIAL.value == "partial"
        assert DegradationLevel.MINIMAL.value == "minimal"
        assert DegradationLevel.OFFLINE.value == "offline"


class TestDegradationPolicy:
    """Tests for DegradationPolicy dataclass."""

    def test_default_policy_creation(self):
        """Test creating a default policy."""
        from infrastructure.resilience.degradation_coordinator import (
            DegradationLevel,
            DegradationPolicy,
        )

        policy = DegradationPolicy(level=DegradationLevel.FULL)
        assert policy.level == DegradationLevel.FULL
        assert len(policy.disabled_features) == 0
        assert policy.use_local_stt is False
        assert policy.use_local_tts is False
        assert policy.allow_cloud_calls is True
        assert policy.announcement == ""

    def test_custom_policy_creation(self):
        """Test creating a custom policy."""
        from infrastructure.resilience.degradation_coordinator import (
            DegradationLevel,
            DegradationPolicy,
        )

        policy = DegradationPolicy(
            level=DegradationLevel.MINIMAL,
            disabled_features={"search", "memory"},
            use_local_stt=True,
            use_local_tts=True,
            announcement="Switching to offline mode",
            allow_cloud_calls=False,
        )
        assert policy.level == DegradationLevel.MINIMAL
        assert "search" in policy.disabled_features
        assert "memory" in policy.disabled_features
        assert policy.use_local_stt is True
        assert policy.use_local_tts is True


class TestDegradationEvent:
    """Tests for DegradationEvent dataclass."""

    def test_event_creation(self):
        """Test creating a degradation event."""
        from infrastructure.resilience.degradation_coordinator import (
            DegradationEvent,
            DegradationLevel,
        )

        event = DegradationEvent(
            timestamp=time.time(),
            previous_level=DegradationLevel.FULL,
            new_level=DegradationLevel.PARTIAL,
            trigger_service="duckduckgo",
        )
        assert event.previous_level == DegradationLevel.FULL
        assert event.new_level == DegradationLevel.PARTIAL
        assert event.trigger_service == "duckduckgo"
        assert event.announcement_sent is False

    def test_event_str(self):
        """Test string representation of event."""
        from infrastructure.resilience.degradation_coordinator import (
            DegradationEvent,
            DegradationLevel,
        )

        event = DegradationEvent(
            timestamp=time.time(),
            previous_level=DegradationLevel.FULL,
            new_level=DegradationLevel.MINIMAL,
            trigger_service="deepgram",
        )
        event_str = str(event)
        assert "full" in event_str
        assert "minimal" in event_str
        assert "deepgram" in event_str


class TestDegradationCoordinatorInitialization:
    """Tests for DegradationCoordinator initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default policies."""
        from infrastructure.resilience.degradation_coordinator import (
            DegradationCoordinator,
            DegradationLevel,
        )

        coordinator = DegradationCoordinator()
        assert coordinator._initialized is False
        assert coordinator._current_level == DegradationLevel.FULL

    def test_init_with_custom_policies(self):
        """Test initialization with custom policies."""
        from infrastructure.resilience.degradation_coordinator import (
            DegradationCoordinator,
            DegradationLevel,
            DegradationPolicy,
        )

        custom_policies = {
            DegradationLevel.FULL: DegradationPolicy(level=DegradationLevel.FULL),
            DegradationLevel.PARTIAL: DegradationPolicy(
                level=DegradationLevel.PARTIAL,
                disabled_features={"custom_feature"},
            ),
            DegradationLevel.MINIMAL: DegradationPolicy(level=DegradationLevel.MINIMAL),
            DegradationLevel.OFFLINE: DegradationPolicy(level=DegradationLevel.OFFLINE),
        }
        coordinator = DegradationCoordinator(policies=custom_policies)
        assert "custom_feature" in coordinator._policies[DegradationLevel.PARTIAL].disabled_features

    async def test_initialize(self):
        """Test coordinator initialization."""
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.resilience.degradation_coordinator import DegradationCoordinator

        clear_registry()

        coordinator = DegradationCoordinator()
        await coordinator.initialize()

        try:
            assert coordinator._initialized is True
        finally:
            await coordinator.shutdown()
            clear_registry()

    async def test_initialize_is_idempotent(self):
        """Test that initialize can be called multiple times safely."""
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.resilience.degradation_coordinator import DegradationCoordinator

        clear_registry()

        coordinator = DegradationCoordinator()
        await coordinator.initialize()
        await coordinator.initialize()
        await coordinator.initialize()

        try:
            assert coordinator._initialized is True
        finally:
            await coordinator.shutdown()
            clear_registry()


class TestDegradationCoordinatorLevel:
    """Tests for degradation level queries."""

    async def test_default_level_is_full(self):
        """Test that default level is FULL."""
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.resilience.degradation_coordinator import (
            DegradationCoordinator,
            DegradationLevel,
        )
        from infrastructure.resilience.health_registry import reset_health_registry

        clear_registry()
        reset_health_registry()

        coordinator = DegradationCoordinator()
        await coordinator.initialize()

        try:
            assert coordinator.get_degradation_level() == DegradationLevel.FULL
        finally:
            await coordinator.shutdown()
            clear_registry()
            reset_health_registry()

    async def test_get_current_policy(self):
        """Test getting current policy."""
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.resilience.degradation_coordinator import (
            DegradationCoordinator,
            DegradationLevel,
        )
        from infrastructure.resilience.health_registry import reset_health_registry

        clear_registry()
        reset_health_registry()

        coordinator = DegradationCoordinator()
        await coordinator.initialize()

        try:
            policy = coordinator.get_current_policy()
            assert policy.level == DegradationLevel.FULL
        finally:
            await coordinator.shutdown()
            clear_registry()
            reset_health_registry()


class TestDegradationCoordinatorFeatures:
    """Tests for feature availability checks."""

    async def test_all_features_available_at_full(self):
        """Test that all features are available at FULL level."""
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.resilience.degradation_coordinator import DegradationCoordinator
        from infrastructure.resilience.health_registry import reset_health_registry

        clear_registry()
        reset_health_registry()

        coordinator = DegradationCoordinator()
        await coordinator.initialize()

        try:
            assert coordinator.is_feature_available("search") is True
            assert coordinator.is_feature_available("memory") is True
            assert coordinator.is_feature_available("tavus") is True
        finally:
            await coordinator.shutdown()
            clear_registry()
            reset_health_registry()

    async def test_features_disabled_at_partial(self):
        """Test that some features are disabled at PARTIAL level."""
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.resilience.degradation_coordinator import (
            DegradationCoordinator,
            DegradationLevel,
        )
        from infrastructure.resilience.health_registry import reset_health_registry

        clear_registry()
        reset_health_registry()

        coordinator = DegradationCoordinator()
        await coordinator.initialize()
        await coordinator.force_degradation_level(DegradationLevel.PARTIAL)

        try:
            # Default PARTIAL policy disables tavus
            assert coordinator.is_feature_available("tavus") is False
            assert coordinator.is_feature_available("search") is True
        finally:
            await coordinator.shutdown()
            clear_registry()
            reset_health_registry()

    async def test_features_disabled_at_minimal(self):
        """Test that more features are disabled at MINIMAL level."""
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.resilience.degradation_coordinator import (
            DegradationCoordinator,
            DegradationLevel,
        )
        from infrastructure.resilience.health_registry import reset_health_registry

        clear_registry()
        reset_health_registry()

        coordinator = DegradationCoordinator()
        await coordinator.initialize()
        await coordinator.force_degradation_level(DegradationLevel.MINIMAL)

        try:
            assert coordinator.is_feature_available("tavus") is False
            assert coordinator.is_feature_available("search") is False
            assert coordinator.is_feature_available("memory") is False
        finally:
            await coordinator.shutdown()
            clear_registry()
            reset_health_registry()

    async def test_get_disabled_features(self):
        """Test getting disabled features."""
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.resilience.degradation_coordinator import (
            DegradationCoordinator,
            DegradationLevel,
        )
        from infrastructure.resilience.health_registry import reset_health_registry

        clear_registry()
        reset_health_registry()

        coordinator = DegradationCoordinator()
        await coordinator.initialize()
        await coordinator.force_degradation_level(DegradationLevel.MINIMAL)

        try:
            disabled = coordinator.get_disabled_features()
            assert isinstance(disabled, set)
            assert len(disabled) > 0
        finally:
            await coordinator.shutdown()
            clear_registry()
            reset_health_registry()


class TestDegradationCoordinatorSpeech:
    """Tests for speech mode queries."""

    async def test_cloud_speech_at_full(self):
        """Test cloud speech used at FULL level."""
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.resilience.degradation_coordinator import DegradationCoordinator
        from infrastructure.resilience.health_registry import reset_health_registry

        clear_registry()
        reset_health_registry()

        coordinator = DegradationCoordinator()
        await coordinator.initialize()

        try:
            assert coordinator.should_use_local_stt() is False
            assert coordinator.should_use_local_tts() is False
            assert coordinator.can_make_cloud_calls() is True
        finally:
            await coordinator.shutdown()
            clear_registry()
            reset_health_registry()

    async def test_local_speech_at_minimal(self):
        """Test local speech used at MINIMAL level."""
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.resilience.degradation_coordinator import (
            DegradationCoordinator,
            DegradationLevel,
        )
        from infrastructure.resilience.health_registry import reset_health_registry

        clear_registry()
        reset_health_registry()

        coordinator = DegradationCoordinator()
        await coordinator.initialize()
        await coordinator.force_degradation_level(DegradationLevel.MINIMAL)

        try:
            assert coordinator.should_use_local_stt() is True
            assert coordinator.should_use_local_tts() is True
            assert coordinator.can_make_cloud_calls() is False
        finally:
            await coordinator.shutdown()
            clear_registry()
            reset_health_registry()


class TestDegradationCoordinatorTransitions:
    """Tests for degradation level transitions."""

    async def test_force_degradation_level(self):
        """Test forcing degradation level."""
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.resilience.degradation_coordinator import (
            DegradationCoordinator,
            DegradationLevel,
        )
        from infrastructure.resilience.health_registry import reset_health_registry

        clear_registry()
        reset_health_registry()

        coordinator = DegradationCoordinator()
        await coordinator.initialize()

        try:
            assert coordinator.get_degradation_level() == DegradationLevel.FULL

            await coordinator.force_degradation_level(DegradationLevel.OFFLINE)

            assert coordinator.get_degradation_level() == DegradationLevel.OFFLINE
        finally:
            await coordinator.shutdown()
            clear_registry()
            reset_health_registry()

    async def test_transition_records_event(self):
        """Test that transitions record events."""
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.resilience.degradation_coordinator import (
            DegradationCoordinator,
            DegradationLevel,
        )
        from infrastructure.resilience.health_registry import reset_health_registry

        clear_registry()
        reset_health_registry()

        coordinator = DegradationCoordinator()
        await coordinator.initialize()

        try:
            assert len(coordinator.get_event_history()) == 0

            await coordinator.force_degradation_level(DegradationLevel.PARTIAL)

            history = coordinator.get_event_history()
            assert len(history) == 1
            assert history[0].previous_level == DegradationLevel.FULL
            assert history[0].new_level == DegradationLevel.PARTIAL
        finally:
            await coordinator.shutdown()
            clear_registry()
            reset_health_registry()

    async def test_no_event_for_same_level(self):
        """Test that no event is recorded when level doesn't change."""
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.resilience.degradation_coordinator import (
            DegradationCoordinator,
            DegradationLevel,
        )
        from infrastructure.resilience.health_registry import reset_health_registry

        clear_registry()
        reset_health_registry()

        coordinator = DegradationCoordinator()
        await coordinator.initialize()

        try:
            # Try to transition to same level
            await coordinator.force_degradation_level(DegradationLevel.FULL)

            assert len(coordinator.get_event_history()) == 0
        finally:
            await coordinator.shutdown()
            clear_registry()
            reset_health_registry()


class TestDegradationCoordinatorAnnouncements:
    """Tests for TTS announcements."""

    async def test_announcement_callback_called(self):
        """Test that announcement callback is called on transition."""
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.resilience.degradation_coordinator import (
            DegradationCoordinator,
            DegradationLevel,
        )
        from infrastructure.resilience.health_registry import reset_health_registry

        clear_registry()
        reset_health_registry()

        announcements = []

        def capture_announcement(text: str) -> None:
            announcements.append(text)

        coordinator = DegradationCoordinator(announcement_callback=capture_announcement)
        await coordinator.initialize()

        try:
            await coordinator.force_degradation_level(DegradationLevel.PARTIAL)

            assert len(announcements) == 1
            assert "unavailable" in announcements[0].lower() or "features" in announcements[0].lower()
        finally:
            await coordinator.shutdown()
            clear_registry()
            reset_health_registry()

    async def test_async_announcement_callback(self):
        """Test async announcement callback."""
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.resilience.degradation_coordinator import (
            DegradationCoordinator,
            DegradationLevel,
        )
        from infrastructure.resilience.health_registry import reset_health_registry

        clear_registry()
        reset_health_registry()

        announcements = []

        async def async_capture(text: str) -> None:
            await asyncio.sleep(0.01)
            announcements.append(text)

        coordinator = DegradationCoordinator(announcement_callback=async_capture)
        await coordinator.initialize()

        try:
            await coordinator.force_degradation_level(DegradationLevel.MINIMAL)

            assert len(announcements) == 1
        finally:
            await coordinator.shutdown()
            clear_registry()
            reset_health_registry()

    async def test_set_announcement_callback(self):
        """Test setting announcement callback after initialization."""
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.resilience.degradation_coordinator import (
            DegradationCoordinator,
            DegradationLevel,
        )
        from infrastructure.resilience.health_registry import reset_health_registry

        clear_registry()
        reset_health_registry()

        announcements = []

        coordinator = DegradationCoordinator()
        await coordinator.initialize()
        coordinator.set_announcement_callback(lambda t: announcements.append(t))

        try:
            await coordinator.force_degradation_level(DegradationLevel.OFFLINE)

            assert len(announcements) == 1
        finally:
            await coordinator.shutdown()
            clear_registry()
            reset_health_registry()


class TestDegradationCoordinatorHealth:
    """Tests for health reporting."""

    async def test_health_snapshot(self):
        """Test health snapshot."""
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.resilience.degradation_coordinator import DegradationCoordinator
        from infrastructure.resilience.health_registry import reset_health_registry

        clear_registry()
        reset_health_registry()

        coordinator = DegradationCoordinator()
        await coordinator.initialize()

        try:
            health = coordinator.health()

            assert "initialized" in health
            assert "current_level" in health
            assert "disabled_features" in health
            assert "use_local_stt" in health
            assert "use_local_tts" in health
            assert "allow_cloud_calls" in health
            assert health["initialized"] is True
            assert health["current_level"] == "full"
        finally:
            await coordinator.shutdown()
            clear_registry()
            reset_health_registry()


class TestDegradationCoordinatorShutdown:
    """Tests for shutdown behavior."""

    async def test_shutdown(self):
        """Test coordinator shutdown."""
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.resilience.degradation_coordinator import DegradationCoordinator
        from infrastructure.resilience.health_registry import reset_health_registry

        clear_registry()
        reset_health_registry()

        coordinator = DegradationCoordinator()
        await coordinator.initialize()

        assert coordinator._initialized is True

        await coordinator.shutdown()

        assert coordinator._initialized is False
        assert len(coordinator._subscribed_services) == 0

        clear_registry()
        reset_health_registry()

    async def test_shutdown_without_init(self):
        """Test shutdown without prior initialization."""
        from infrastructure.resilience.degradation_coordinator import DegradationCoordinator

        coordinator = DegradationCoordinator()
        await coordinator.shutdown()  # Should not raise


class TestSingletonFunctions:
    """Tests for singleton access functions."""

    def test_get_degradation_coordinator_singleton(self):
        """Test singleton returns same instance."""
        from infrastructure.resilience.degradation_coordinator import (
            get_degradation_coordinator,
            reset_degradation_coordinator,
        )

        reset_degradation_coordinator()

        coord1 = get_degradation_coordinator()
        coord2 = get_degradation_coordinator()

        assert coord1 is coord2

        reset_degradation_coordinator()

    def test_reset_degradation_coordinator(self):
        """Test resetting creates new instance."""
        from infrastructure.resilience.degradation_coordinator import (
            get_degradation_coordinator,
            reset_degradation_coordinator,
        )

        reset_degradation_coordinator()

        coord1 = get_degradation_coordinator()
        reset_degradation_coordinator()
        coord2 = get_degradation_coordinator()

        assert coord1 is not coord2

        reset_degradation_coordinator()


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_get_current_degradation_level(self):
        """Test get_current_degradation_level function."""
        from infrastructure.resilience.degradation_coordinator import (
            DegradationLevel,
            get_current_degradation_level,
            reset_degradation_coordinator,
        )

        reset_degradation_coordinator()

        level = get_current_degradation_level()

        assert level == DegradationLevel.FULL

        reset_degradation_coordinator()

    def test_is_feature_enabled(self):
        """Test is_feature_enabled function."""
        from infrastructure.resilience.degradation_coordinator import (
            is_feature_enabled,
            reset_degradation_coordinator,
        )

        reset_degradation_coordinator()

        # At FULL level, all features should be enabled
        assert is_feature_enabled("search") is True
        assert is_feature_enabled("memory") is True

        reset_degradation_coordinator()

    def test_should_use_local_speech(self):
        """Test should_use_local_speech function."""
        from infrastructure.resilience.degradation_coordinator import (
            reset_degradation_coordinator,
            should_use_local_speech,
        )

        reset_degradation_coordinator()

        # At FULL level, should not use local speech
        assert should_use_local_speech() is False

        reset_degradation_coordinator()

    async def test_create_degradation_coordinator(self):
        """Test create_degradation_coordinator function."""
        from infrastructure.resilience.circuit_breaker import clear_registry
        from infrastructure.resilience.degradation_coordinator import (
            create_degradation_coordinator,
        )
        from infrastructure.resilience.health_registry import reset_health_registry

        clear_registry()
        reset_health_registry()

        coordinator = await create_degradation_coordinator()

        try:
            assert coordinator._initialized is True
        finally:
            await coordinator.shutdown()
            clear_registry()
            reset_health_registry()


class TestDegradationLevelComputation:
    """Tests for degradation level computation."""

    async def test_partial_when_non_critical_down(self):
        """Test PARTIAL level when non-critical service is down."""
        from infrastructure.resilience.circuit_breaker import (
            clear_registry,
            register_circuit_breaker,
        )
        from infrastructure.resilience.degradation_coordinator import (
            DegradationCoordinator,
            DegradationLevel,
        )
        from infrastructure.resilience.health_registry import reset_health_registry

        clear_registry()
        reset_health_registry()

        # Register all services
        register_circuit_breaker("deepgram")
        register_circuit_breaker("elevenlabs")
        register_circuit_breaker("ollama")
        register_circuit_breaker("livekit")
        cb_duck = register_circuit_breaker("duckduckgo")

        # Trip non-critical service
        await cb_duck.trip()

        coordinator = DegradationCoordinator()
        await coordinator.initialize()

        try:
            assert coordinator.get_degradation_level() == DegradationLevel.PARTIAL
        finally:
            await coordinator.shutdown()
            clear_registry()
            reset_health_registry()

    async def test_minimal_when_critical_down(self):
        """Test MINIMAL level when critical service is down."""
        from infrastructure.resilience.circuit_breaker import (
            clear_registry,
            register_circuit_breaker,
        )
        from infrastructure.resilience.degradation_coordinator import (
            DegradationCoordinator,
            DegradationLevel,
        )
        from infrastructure.resilience.health_registry import reset_health_registry

        clear_registry()
        reset_health_registry()

        # Register services
        cb_deepgram = register_circuit_breaker("deepgram")
        register_circuit_breaker("elevenlabs")

        # Trip critical service
        await cb_deepgram.trip()

        coordinator = DegradationCoordinator()
        await coordinator.initialize()

        try:
            assert coordinator.get_degradation_level() == DegradationLevel.MINIMAL
        finally:
            await coordinator.shutdown()
            clear_registry()
            reset_health_registry()

    async def test_offline_when_all_critical_down(self):
        """Test OFFLINE level when all critical services are down."""
        from infrastructure.resilience.circuit_breaker import (
            clear_registry,
            register_circuit_breaker,
        )
        from infrastructure.resilience.degradation_coordinator import (
            DegradationCoordinator,
            DegradationLevel,
        )
        from infrastructure.resilience.health_registry import reset_health_registry

        clear_registry()
        reset_health_registry()

        # Register critical services
        cb_deepgram = register_circuit_breaker("deepgram")
        cb_elevenlabs = register_circuit_breaker("elevenlabs")

        # Trip both critical services
        await cb_deepgram.trip()
        await cb_elevenlabs.trip()

        coordinator = DegradationCoordinator()
        await coordinator.initialize()

        try:
            assert coordinator.get_degradation_level() == DegradationLevel.OFFLINE
        finally:
            await coordinator.shutdown()
            clear_registry()
            reset_health_registry()


class TestDegradationCoordinatorRefresh:
    """Tests for refresh functionality."""

    async def test_refresh_updates_level(self):
        """Test that refresh updates degradation level."""
        from infrastructure.resilience.circuit_breaker import (
            clear_registry,
            register_circuit_breaker,
        )
        from infrastructure.resilience.degradation_coordinator import (
            DegradationCoordinator,
            DegradationLevel,
        )
        from infrastructure.resilience.health_registry import reset_health_registry

        clear_registry()
        reset_health_registry()

        cb_deepgram = register_circuit_breaker("deepgram")
        register_circuit_breaker("elevenlabs")

        coordinator = DegradationCoordinator()
        await coordinator.initialize()

        try:
            assert coordinator.get_degradation_level() == DegradationLevel.FULL

            # Trip service
            await cb_deepgram.trip()

            # Refresh
            await coordinator.refresh()

            assert coordinator.get_degradation_level() == DegradationLevel.MINIMAL
        finally:
            await coordinator.shutdown()
            clear_registry()
            reset_health_registry()
