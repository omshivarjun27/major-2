"""Graceful degradation coordinator for orchestrating system behavior during service failures.

Monitors the service health registry and adjusts system behavior based on the current
degradation level. Provides TTS announcements to inform users about reduced capabilities.

Architecture constraint: imports from ``shared/`` and ``infrastructure/`` only.

Usage::

    from infrastructure.resilience.degradation_coordinator import DegradationCoordinator

    coordinator = DegradationCoordinator()
    await coordinator.initialize()

    # Check current degradation level
    level = coordinator.get_degradation_level()

    # Check if feature is available
    if coordinator.is_feature_available("search"):
        # Perform search
        ...
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from infrastructure.resilience.circuit_breaker import (
    StateChangeEvent,
    get_all_breakers,
)
from infrastructure.resilience.health_registry import (
    ServiceStatus,
    get_health_registry,
)

logger = logging.getLogger("resilience.degradation_coordinator")


class DegradationLevel(Enum):
    """System degradation levels."""

    FULL = "full"  # All services healthy
    PARTIAL = "partial"  # Some non-critical services degraded
    MINIMAL = "minimal"  # Critical services degraded, using fallbacks
    OFFLINE = "offline"  # All cloud services unavailable


@dataclass
class DegradationPolicy:
    """Policy for a specific degradation level."""

    level: DegradationLevel
    disabled_features: Set[str] = field(default_factory=set)
    use_local_stt: bool = False
    use_local_tts: bool = False
    announcement: str = ""
    allow_cloud_calls: bool = True


# Default policies per degradation level
DEFAULT_POLICIES: Dict[DegradationLevel, DegradationPolicy] = {
    DegradationLevel.FULL: DegradationPolicy(
        level=DegradationLevel.FULL,
        disabled_features=set(),
        use_local_stt=False,
        use_local_tts=False,
        announcement="",
        allow_cloud_calls=True,
    ),
    DegradationLevel.PARTIAL: DegradationPolicy(
        level=DegradationLevel.PARTIAL,
        disabled_features={"tavus", "avatar"},
        use_local_stt=False,
        use_local_tts=False,
        announcement="Some features are temporarily unavailable. Core functionality continues.",
        allow_cloud_calls=True,
    ),
    DegradationLevel.MINIMAL: DegradationPolicy(
        level=DegradationLevel.MINIMAL,
        disabled_features={"tavus", "avatar", "search", "memory"},
        use_local_stt=True,
        use_local_tts=True,
        announcement="I'm experiencing connection issues. Switching to offline mode for voice.",
        allow_cloud_calls=False,
    ),
    DegradationLevel.OFFLINE: DegradationPolicy(
        level=DegradationLevel.OFFLINE,
        disabled_features={"tavus", "avatar", "search", "memory", "vision"},
        use_local_stt=True,
        use_local_tts=True,
        announcement="I'm in offline mode. Only basic voice interaction is available.",
        allow_cloud_calls=False,
    ),
}


# Service criticality classification
CRITICAL_SERVICES = {"deepgram", "elevenlabs"}  # Core speech services
IMPORTANT_SERVICES = {"ollama", "livekit"}  # VQA and real-time
NON_CRITICAL_SERVICES = {"tavus", "duckduckgo"}  # Nice to have


@dataclass
class DegradationEvent:
    """Record of a degradation level change."""

    timestamp: float
    previous_level: DegradationLevel
    new_level: DegradationLevel
    trigger_service: Optional[str] = None
    announcement_sent: bool = False

    def __str__(self) -> str:
        return (
            f"[{time.strftime('%H:%M:%S', time.localtime(self.timestamp))}] "
            f"Degradation: {self.previous_level.value} → {self.new_level.value}"
            f"{f' (trigger: {self.trigger_service})' if self.trigger_service else ''}"
        )


# Type for announcement callback
AnnouncementCallback = Callable[[str], Any]


class DegradationCoordinator:
    """Coordinates system behavior during service degradation.

    Monitors service health and adjusts system capabilities based on which
    services are available. Provides announcements to inform users.
    """

    def __init__(
        self,
        policies: Optional[Dict[DegradationLevel, DegradationPolicy]] = None,
        announcement_callback: Optional[AnnouncementCallback] = None,
    ) -> None:
        """Initialize the degradation coordinator.

        Args:
            policies: Custom degradation policies. Defaults to DEFAULT_POLICIES.
            announcement_callback: Function to call for TTS announcements.
        """
        self._policies = policies or DEFAULT_POLICIES.copy()
        self._announcement_callback = announcement_callback

        # Current state
        self._current_level = DegradationLevel.FULL
        self._current_policy = self._policies[DegradationLevel.FULL]
        self._lock = asyncio.Lock()

        # Event tracking
        self._event_history: List[DegradationEvent] = []
        self._max_history = 100

        # Subscriptions
        self._subscribed_services: Set[str] = set()

        # Initialization state
        self._initialized = False

        logger.info("DegradationCoordinator created")

    async def initialize(self) -> None:
        """Initialize the coordinator and subscribe to circuit breaker events.

        Must be called before using the coordinator. Safe to call multiple times.
        """
        if self._initialized:
            return

        initial_level = None

        async with self._lock:
            if self._initialized:
                return

            # Subscribe to all known circuit breakers
            all_breakers = get_all_breakers()
            for service_name, cb in all_breakers.items():
                if service_name not in self._subscribed_services:
                    cb.add_callback(self._on_circuit_state_change)
                    self._subscribed_services.add(service_name)

            # Determine initial degradation level
            initial_level = self._compute_degradation_level()

            # Set initial level directly (no transition, no lock re-acquisition)
            if initial_level != self._current_level:
                self._current_level = initial_level
                self._current_policy = self._policies[initial_level]

            self._initialized = True
            logger.info(
                "DegradationCoordinator initialized (level=%s, subscribed=%d services)",
                self._current_level.value,
                len(self._subscribed_services),
            )

    async def shutdown(self) -> None:
        """Shutdown the coordinator and unsubscribe from events."""
        async with self._lock:
            # Unsubscribe from circuit breakers
            all_breakers = get_all_breakers()
            for service_name in self._subscribed_services:
                cb = all_breakers.get(service_name)
                if cb is not None:
                    cb.remove_callback(self._on_circuit_state_change)

            self._subscribed_services.clear()
            self._initialized = False
            logger.info("DegradationCoordinator shutdown complete")

    def get_degradation_level(self) -> DegradationLevel:
        """Get the current degradation level.

        Returns:
            Current DegradationLevel.
        """
        return self._current_level

    def get_current_policy(self) -> DegradationPolicy:
        """Get the current degradation policy.

        Returns:
            Current DegradationPolicy.
        """
        return self._current_policy

    def is_feature_available(self, feature: str) -> bool:
        """Check if a feature is available under current degradation.

        Args:
            feature: Feature name to check.

        Returns:
            True if feature is available.
        """
        return feature.lower() not in self._current_policy.disabled_features

    def should_use_local_stt(self) -> bool:
        """Check if local STT should be used.

        Returns:
            True if local STT should be used.
        """
        return self._current_policy.use_local_stt

    def should_use_local_tts(self) -> bool:
        """Check if local TTS should be used.

        Returns:
            True if local TTS should be used.
        """
        return self._current_policy.use_local_tts

    def can_make_cloud_calls(self) -> bool:
        """Check if cloud calls are allowed.

        Returns:
            True if cloud calls are allowed.
        """
        return self._current_policy.allow_cloud_calls

    def get_disabled_features(self) -> Set[str]:
        """Get set of currently disabled features.

        Returns:
            Set of disabled feature names.
        """
        return self._current_policy.disabled_features.copy()

    def get_event_history(self) -> List[DegradationEvent]:
        """Get degradation event history.

        Returns:
            List of DegradationEvent records.
        """
        return list(self._event_history)

    def set_announcement_callback(self, callback: AnnouncementCallback) -> None:
        """Set the announcement callback for TTS.

        Args:
            callback: Function to call with announcement text.
        """
        self._announcement_callback = callback

    async def _on_circuit_state_change(self, event: StateChangeEvent) -> None:
        """Handle circuit breaker state change callback."""
        logger.debug(
            "Circuit state change: %s %s → %s",
            event.service_name,
            event.previous_state.value,
            event.new_state.value,
        )

        # Recompute degradation level
        new_level = self._compute_degradation_level()

        if new_level != self._current_level:
            await self._transition_to(new_level, trigger_service=event.service_name)

    def _compute_degradation_level(self) -> DegradationLevel:
        """Compute degradation level based on current service health.

        Returns:
            Appropriate DegradationLevel.
        """
        registry = get_health_registry()

        # Get status of critical services
        critical_degraded = 0
        critical_unhealthy = 0
        for service in CRITICAL_SERVICES:
            health = registry.get_service_health(service)
            if health.status == ServiceStatus.UNHEALTHY:
                critical_unhealthy += 1
            elif health.status == ServiceStatus.DEGRADED:
                critical_degraded += 1

        # Get status of important services
        important_unhealthy = 0
        for service in IMPORTANT_SERVICES:
            health = registry.get_service_health(service)
            if health.status == ServiceStatus.UNHEALTHY:
                important_unhealthy += 1

        # Get status of non-critical services
        non_critical_unhealthy = 0
        for service in NON_CRITICAL_SERVICES:
            health = registry.get_service_health(service)
            if health.status == ServiceStatus.UNHEALTHY:
                non_critical_unhealthy += 1

        # Determine level based on service health
        total_critical = len(CRITICAL_SERVICES)

        # OFFLINE: All critical services down
        if critical_unhealthy >= total_critical:
            return DegradationLevel.OFFLINE

        # MINIMAL: Any critical service down
        if critical_unhealthy > 0 or critical_degraded > 0:
            return DegradationLevel.MINIMAL

        # PARTIAL: Important or non-critical services down
        if important_unhealthy > 0 or non_critical_unhealthy > 0:
            return DegradationLevel.PARTIAL

        # FULL: Everything healthy
        return DegradationLevel.FULL

    async def _transition_to(
        self,
        new_level: DegradationLevel,
        trigger_service: Optional[str] = None,
    ) -> None:
        """Transition to a new degradation level.

        Args:
            new_level: New degradation level.
            trigger_service: Service that triggered the transition.
        """
        async with self._lock:
            if new_level == self._current_level:
                return

            previous_level = self._current_level
            self._current_level = new_level
            self._current_policy = self._policies[new_level]

            # Record event
            event = DegradationEvent(
                timestamp=time.time(),
                previous_level=previous_level,
                new_level=new_level,
                trigger_service=trigger_service,
            )
            self._record_event(event)

            logger.warning(
                "Degradation transition: %s → %s (trigger=%s)",
                previous_level.value,
                new_level.value,
                trigger_service or "manual",
            )

            # Send announcement if callback is set
            announcement = self._current_policy.announcement
            if announcement and self._announcement_callback:
                try:
                    result = self._announcement_callback(announcement)
                    if asyncio.iscoroutine(result):
                        await result
                    event.announcement_sent = True
                    logger.info("Degradation announcement sent: %s", announcement[:50])
                except Exception as exc:
                    logger.error("Failed to send degradation announcement: %s", exc)

    def _record_event(self, event: DegradationEvent) -> None:
        """Record a degradation event in history."""
        self._event_history.append(event)

        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]

    async def force_degradation_level(self, level: DegradationLevel) -> None:
        """Force a specific degradation level (for testing/manual override).

        Args:
            level: Degradation level to force.
        """
        await self._transition_to(level, trigger_service="manual_override")

    async def refresh(self) -> None:
        """Refresh degradation level based on current service health."""
        new_level = self._compute_degradation_level()
        if new_level != self._current_level:
            await self._transition_to(new_level, trigger_service="refresh")

    def health(self) -> Dict[str, Any]:
        """Get health snapshot for the coordinator.

        Returns:
            Dictionary with coordinator health info.
        """
        return {
            "initialized": self._initialized,
            "current_level": self._current_level.value,
            "disabled_features": list(self._current_policy.disabled_features),
            "use_local_stt": self._current_policy.use_local_stt,
            "use_local_tts": self._current_policy.use_local_tts,
            "allow_cloud_calls": self._current_policy.allow_cloud_calls,
            "subscribed_services": list(self._subscribed_services),
            "event_count": len(self._event_history),
            "last_event": str(self._event_history[-1]) if self._event_history else None,
        }


# ---------------------------------------------------------------------------
# Singleton instance
# ---------------------------------------------------------------------------

_coordinator: Optional[DegradationCoordinator] = None


def get_degradation_coordinator() -> DegradationCoordinator:
    """Get or create the singleton degradation coordinator.

    Returns:
        The global DegradationCoordinator instance.
    """
    global _coordinator
    if _coordinator is None:
        _coordinator = DegradationCoordinator()
    return _coordinator


def reset_degradation_coordinator() -> None:
    """Reset the singleton coordinator (for testing)."""
    global _coordinator
    _coordinator = None


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------


async def create_degradation_coordinator(
    announcement_callback: Optional[AnnouncementCallback] = None,
) -> DegradationCoordinator:
    """Create and initialize a degradation coordinator.

    Args:
        announcement_callback: Optional callback for TTS announcements.

    Returns:
        Initialized DegradationCoordinator.
    """
    coordinator = DegradationCoordinator(announcement_callback=announcement_callback)
    await coordinator.initialize()
    return coordinator


def get_current_degradation_level() -> DegradationLevel:
    """Get the current system degradation level.

    Returns:
        Current DegradationLevel.
    """
    return get_degradation_coordinator().get_degradation_level()


def is_feature_enabled(feature: str) -> bool:
    """Check if a feature is enabled under current degradation.

    Args:
        feature: Feature name to check.

    Returns:
        True if feature is enabled.
    """
    return get_degradation_coordinator().is_feature_available(feature)


def should_use_local_speech() -> bool:
    """Check if local speech (STT/TTS) should be used.

    Returns:
        True if local speech should be used.
    """
    coordinator = get_degradation_coordinator()
    return coordinator.should_use_local_stt() or coordinator.should_use_local_tts()
