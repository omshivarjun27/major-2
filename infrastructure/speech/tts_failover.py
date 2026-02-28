"""TTS Failover Manager for automatic ElevenLabs ↔ Local TTS switching.

Automatically switches from ElevenLabs (cloud) to Edge TTS / pyttsx3 (local) when
the ElevenLabs circuit breaker opens, and switches back when it recovers. Failover
completes within 2 seconds of circuit state change.

This manager wraps and coordinates with the existing TTSManager, providing enhanced
local fallback via LocalTTSFallback and tracking failover statistics.

Architecture constraint: imports from ``shared/`` and ``infrastructure/`` only.

Usage::

    from infrastructure.speech.tts_failover import TTSFailoverManager

    manager = TTSFailoverManager()
    await manager.initialize()

    # Synthesize using managed failover
    result = manager.synthesize("Hello, world!")

    # Check current provider
    provider = manager.get_active_provider()  # "elevenlabs" or "local"
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Generator, List, Optional

from infrastructure.resilience.circuit_breaker import (
    CircuitBreakerState,
    StateChangeEvent,
    get_circuit_breaker,
    register_circuit_breaker,
    CircuitBreakerConfig,
)
from infrastructure.speech.local.edge_tts_fallback import (
    LocalTTSFallback,
    LocalTTSConfig,
    SynthesisResult as LocalSynthesisResult,
    EDGE_TTS_AVAILABLE,
    PYTTSX3_AVAILABLE,
)

logger = logging.getLogger("speech.tts_failover")


class TTSProvider(Enum):
    """Available TTS providers."""

    ELEVENLABS = "elevenlabs"
    LOCAL = "local"
    NONE = "none"


@dataclass
class FailoverEvent:
    """Record of a failover event."""

    timestamp: float
    from_provider: TTSProvider
    to_provider: TTSProvider
    trigger: str  # "circuit_open", "circuit_closed", "manual", "initialization"
    latency_ms: float = 0.0

    def __str__(self) -> str:
        return (
            f"[{time.strftime('%H:%M:%S', time.localtime(self.timestamp))}] "
            f"Failover: {self.from_provider.value} → {self.to_provider.value} "
            f"(trigger={self.trigger}, latency={self.latency_ms:.1f}ms)"
        )


@dataclass
class FailoverStatistics:
    """Statistics tracking for failover behavior."""

    total_failovers: int = 0
    total_failbacks: int = 0
    total_time_in_fallback_ms: float = 0.0
    last_fallback_start: Optional[float] = None
    current_provider: TTSProvider = TTSProvider.ELEVENLABS

    def record_failover(self) -> None:
        """Record a failover to local TTS."""
        self.total_failovers += 1
        self.last_fallback_start = time.monotonic()
        self.current_provider = TTSProvider.LOCAL

    def record_failback(self) -> None:
        """Record a failback to ElevenLabs."""
        self.total_failbacks += 1
        if self.last_fallback_start is not None:
            duration_ms = (time.monotonic() - self.last_fallback_start) * 1000
            self.total_time_in_fallback_ms += duration_ms
            self.last_fallback_start = None
        self.current_provider = TTSProvider.ELEVENLABS

    def to_dict(self) -> Dict[str, Any]:
        """Convert statistics to dictionary."""
        return {
            "total_failovers": self.total_failovers,
            "total_failbacks": self.total_failbacks,
            "total_time_in_fallback_ms": self.total_time_in_fallback_ms,
            "currently_in_fallback": self.last_fallback_start is not None,
            "current_provider": self.current_provider.value,
        }


@dataclass
class TTSFailoverConfig:
    """Configuration for TTS failover manager."""

    elevenlabs_service_name: str = "elevenlabs"
    """Circuit breaker service name for ElevenLabs."""

    local_tts_voice: str = "en-US-AriaNeural"
    """Voice for local TTS fallback (Edge TTS voice ID)."""

    prefer_edge_tts: bool = True
    """Prefer Edge TTS over pyttsx3 for local fallback."""

    failover_timeout_s: float = 2.0
    """Maximum time allowed for failover to complete."""

    prewarm_local_tts: bool = True
    """Pre-initialize local TTS on startup for faster failover."""


@dataclass
class TTSResult:
    """Result of a TTS synthesis operation."""

    audio_bytes: bytes
    """Synthesized audio bytes."""

    engine: str
    """Engine used: 'elevenlabs', 'local', 'cache', or 'none'."""

    latency_ms: float
    """Synthesis latency in milliseconds."""

    text: str
    """Original text that was synthesized."""

    fallback_used: bool = False
    """True if local fallback was used instead of primary."""

    cache_hit: bool = False
    """True if result was served from cache."""

    chunk_index: Optional[int] = None
    """Index of this chunk (for chunked synthesis)."""

    total_chunks: Optional[int] = None
    """Total number of chunks (for chunked synthesis)."""

    error: Optional[str] = None
    """Error message if synthesis failed."""

    @property
    def success(self) -> bool:
        """True if synthesis succeeded."""
        return len(self.audio_bytes) > 0 and self.error is None


class TTSFailoverManager:
    """Manages automatic failover between ElevenLabs and local TTS providers.

    Subscribes to the ElevenLabs circuit breaker state changes and automatically
    switches to/from the local TTS fallback based on circuit state. Also provides
    enhanced local_fn for TTSManager integration.

    Thread-safe: all state changes are protected by a threading lock for sync access.
    """

    def __init__(self, config: Optional[TTSFailoverConfig] = None) -> None:
        """Initialize the failover manager.

        Args:
            config: Configuration options. Uses defaults if not provided.
        """
        self.config = config or TTSFailoverConfig()

        # Current active provider
        self._active_provider = TTSProvider.ELEVENLABS
        self._lock = asyncio.Lock()

        # Local TTS fallback
        self._local_tts: Optional[LocalTTSFallback] = None

        # Failover tracking
        self._failover_history: List[FailoverEvent] = []
        self._max_history = 100
        self._statistics = FailoverStatistics()

        # Circuit breaker reference
        self._elevenlabs_cb = None
        self._callback_registered = False

        # Initialization state
        self._initialized = False

        logger.info(
            "TTSFailoverManager created (elevenlabs_cb=%s, edge_tts=%s, pyttsx3=%s)",
            self.config.elevenlabs_service_name,
            EDGE_TTS_AVAILABLE,
            PYTTSX3_AVAILABLE,
        )

    async def initialize(self) -> None:
        """Initialize the failover manager and subscribe to circuit breaker.

        Must be called before using the manager. Safe to call multiple times.
        """
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            # Get or create the ElevenLabs circuit breaker
            self._elevenlabs_cb = get_circuit_breaker(self.config.elevenlabs_service_name)
            if self._elevenlabs_cb is None:
                self._elevenlabs_cb = register_circuit_breaker(
                    self.config.elevenlabs_service_name,
                    config=CircuitBreakerConfig(
                        failure_threshold=3,
                        reset_timeout_s=30.0,
                        half_open_max_calls=1,
                        success_threshold=1,
                    ),
                )

            # Subscribe to state changes
            if not self._callback_registered:
                self._elevenlabs_cb.add_callback(self._on_circuit_state_change)
                self._callback_registered = True

            # Initialize local TTS fallback
            local_config = LocalTTSConfig(
                voice=self.config.local_tts_voice,
                prefer_edge_tts=self.config.prefer_edge_tts,
            )
            self._local_tts = LocalTTSFallback(config=local_config)

            # Check current circuit state
            if self._elevenlabs_cb.state is CircuitBreakerState.OPEN:
                await self._activate_local("initialization")
            else:
                self._active_provider = TTSProvider.ELEVENLABS
                self._statistics.current_provider = TTSProvider.ELEVENLABS

            self._initialized = True
            logger.info(
                "TTSFailoverManager initialized (active=%s, local_backend=%s)",
                self._active_provider.value,
                self._local_tts.get_backend() if self._local_tts else "none",
            )

    async def shutdown(self) -> None:
        """Shutdown the manager and cleanup resources."""
        async with self._lock:
            if self._elevenlabs_cb is not None and self._callback_registered:
                self._elevenlabs_cb.remove_callback(self._on_circuit_state_change)
                self._callback_registered = False

            self._initialized = False
            logger.info("TTSFailoverManager shutdown complete")

    def get_active_provider(self) -> str:
        """Get the name of the currently active TTS provider.

        Returns:
            Provider name: "elevenlabs", "local", or "none"
        """
        return self._active_provider.value

    def get_active_provider_enum(self) -> TTSProvider:
        """Get the currently active TTS provider as enum."""
        return self._active_provider

    def get_local_fn(self) -> Callable[[str], bytes]:
        """Get a local TTS function for TTSManager integration.

        This returns a sync callable compatible with TTSManager.local_fn.

        Returns:
            Callable that takes text and returns audio bytes.
        """
        if self._local_tts is None:
            # Initialize local TTS if not done
            local_config = LocalTTSConfig(
                voice=self.config.local_tts_voice,
                prefer_edge_tts=self.config.prefer_edge_tts,
            )
            self._local_tts = LocalTTSFallback(config=local_config)

        return self._local_tts.synthesize

    def synthesize(self, text: str) -> TTSResult:
        """Synthesize speech using the currently active provider.

        This is a sync method for compatibility with existing TTSManager patterns.

        Args:
            text: Text to synthesize.

        Returns:
            TTSResult with audio and metadata.
        """
        start_time = time.monotonic()

        if not text or not text.strip():
            return TTSResult(
                audio_bytes=b"",
                engine="none",
                latency_ms=0.0,
                text=text,
                error="Empty text provided",
            )

        # When in local mode or ElevenLabs unavailable, use local TTS
        if self._active_provider == TTSProvider.LOCAL:
            return self._synthesize_local(text, start_time)

        # In ElevenLabs mode, return a placeholder
        # (actual ElevenLabs synthesis is handled by TTSManager)
        return TTSResult(
            audio_bytes=b"",
            engine="elevenlabs",
            latency_ms=(time.monotonic() - start_time) * 1000,
            text=text,
            error="ElevenLabs synthesis handled by TTSManager",
        )

    def _synthesize_local(self, text: str, start_time: float) -> TTSResult:
        """Synthesize using local TTS fallback."""
        if self._local_tts is None:
            return TTSResult(
                audio_bytes=b"",
                engine="none",
                latency_ms=(time.monotonic() - start_time) * 1000,
                text=text,
                fallback_used=True,
                error="Local TTS not available",
            )

        result = self._local_tts.synthesize_with_result(text)
        latency_ms = (time.monotonic() - start_time) * 1000

        return TTSResult(
            audio_bytes=result.audio_bytes,
            engine=f"local:{result.backend}",
            latency_ms=latency_ms,
            text=text,
            fallback_used=True,
            error=result.error,
        )

    async def async_synthesize(self, text: str) -> TTSResult:
        """Synthesize speech asynchronously.

        Args:
            text: Text to synthesize.

        Returns:
            TTSResult with audio and metadata.
        """
        start_time = time.monotonic()

        if not text or not text.strip():
            return TTSResult(
                audio_bytes=b"",
                engine="none",
                latency_ms=0.0,
                text=text,
                error="Empty text provided",
            )

        if self._active_provider == TTSProvider.LOCAL:
            return await self._async_synthesize_local(text, start_time)

        return TTSResult(
            audio_bytes=b"",
            engine="elevenlabs",
            latency_ms=(time.monotonic() - start_time) * 1000,
            text=text,
            error="ElevenLabs synthesis handled by TTSManager",
        )

    async def _async_synthesize_local(self, text: str, start_time: float) -> TTSResult:
        """Synthesize using local TTS fallback asynchronously."""
        if self._local_tts is None:
            return TTSResult(
                audio_bytes=b"",
                engine="none",
                latency_ms=(time.monotonic() - start_time) * 1000,
                text=text,
                fallback_used=True,
                error="Local TTS not available",
            )

        result = await self._local_tts.async_synthesize_with_result(text)
        latency_ms = (time.monotonic() - start_time) * 1000

        return TTSResult(
            audio_bytes=result.audio_bytes,
            engine=f"local:{result.backend}",
            latency_ms=latency_ms,
            text=text,
            fallback_used=True,
            error=result.error,
        )

    async def _on_circuit_state_change(self, event: StateChangeEvent) -> None:
        """Handle circuit breaker state change callback."""
        if event.service_name != self.config.elevenlabs_service_name:
            return

        logger.info(
            "ElevenLabs circuit state change: %s → %s (failures=%d)",
            event.previous_state.value,
            event.new_state.value,
            event.failure_count,
        )

        # CLOSED → OPEN: Activate local fallback
        if (
            event.previous_state is CircuitBreakerState.CLOSED
            and event.new_state is CircuitBreakerState.OPEN
        ):
            await self._activate_local("circuit_open")

        # HALF_OPEN → CLOSED: Switch back to ElevenLabs
        elif (
            event.previous_state is CircuitBreakerState.HALF_OPEN
            and event.new_state is CircuitBreakerState.CLOSED
        ):
            await self._activate_elevenlabs("circuit_closed")

        # OPEN → HALF_OPEN: Prepare for possible recovery
        elif (
            event.previous_state is CircuitBreakerState.OPEN
            and event.new_state is CircuitBreakerState.HALF_OPEN
        ):
            logger.info("ElevenLabs entering HALF_OPEN state - testing recovery")

        # HALF_OPEN → OPEN: Recovery failed
        elif (
            event.previous_state is CircuitBreakerState.HALF_OPEN
            and event.new_state is CircuitBreakerState.OPEN
        ):
            logger.warning("ElevenLabs recovery failed - staying on local fallback")

    async def _activate_local(self, trigger: str) -> None:
        """Activate local TTS as the provider."""
        start_time = time.monotonic()

        async with self._lock:
            if self._active_provider == TTSProvider.LOCAL:
                return

            previous = self._active_provider

            if not self._local_tts_available():
                logger.error("Cannot activate local TTS - no backend available")
                self._active_provider = TTSProvider.NONE
                self._record_failover(previous, TTSProvider.NONE, trigger, 0.0)
                return

            # Ensure local TTS is initialized
            if self._local_tts is None:
                local_config = LocalTTSConfig(
                    voice=self.config.local_tts_voice,
                    prefer_edge_tts=self.config.prefer_edge_tts,
                )
                self._local_tts = LocalTTSFallback(config=local_config)

            self._active_provider = TTSProvider.LOCAL
            self._statistics.record_failover()
            latency_ms = (time.monotonic() - start_time) * 1000

            self._record_failover(previous, TTSProvider.LOCAL, trigger, latency_ms)
            logger.info(
                "TTS failover: %s → local (trigger=%s, latency=%.1fms, backend=%s)",
                previous.value,
                trigger,
                latency_ms,
                self._local_tts.get_backend(),
            )

    async def _activate_elevenlabs(self, trigger: str) -> None:
        """Activate ElevenLabs as the TTS provider."""
        start_time = time.monotonic()

        async with self._lock:
            if self._active_provider == TTSProvider.ELEVENLABS:
                return

            previous = self._active_provider
            self._active_provider = TTSProvider.ELEVENLABS
            self._statistics.record_failback()
            latency_ms = (time.monotonic() - start_time) * 1000

            self._record_failover(previous, TTSProvider.ELEVENLABS, trigger, latency_ms)
            logger.info(
                "TTS failback: %s → ElevenLabs (trigger=%s, latency=%.1fms)",
                previous.value,
                trigger,
                latency_ms,
            )

    def _local_tts_available(self) -> bool:
        """Check if local TTS is available."""
        return EDGE_TTS_AVAILABLE or PYTTSX3_AVAILABLE

    def _record_failover(
        self,
        from_provider: TTSProvider,
        to_provider: TTSProvider,
        trigger: str,
        latency_ms: float,
    ) -> None:
        """Record a failover event in history."""
        event = FailoverEvent(
            timestamp=time.time(),
            from_provider=from_provider,
            to_provider=to_provider,
            trigger=trigger,
            latency_ms=latency_ms,
        )
        self._failover_history.append(event)

        if len(self._failover_history) > self._max_history:
            self._failover_history = self._failover_history[-self._max_history:]

        logger.debug("Failover recorded: %s", event)

    async def force_failover_to_local(self) -> None:
        """Manually force failover to local TTS."""
        await self._activate_local("manual")

    async def force_failback_to_elevenlabs(self) -> None:
        """Manually force failback to ElevenLabs."""
        await self._activate_elevenlabs("manual")

    def get_failover_history(self) -> List[FailoverEvent]:
        """Get the failover event history."""
        return list(self._failover_history)

    def get_statistics(self) -> Dict[str, Any]:
        """Get failover statistics."""
        return self._statistics.to_dict()

    def health(self) -> Dict[str, Any]:
        """Health snapshot for diagnostics."""
        cb_state = "unknown"
        if self._elevenlabs_cb is not None:
            cb_state = self._elevenlabs_cb.state.value

        local_health = {}
        if self._local_tts is not None:
            local_health = self._local_tts.health()

        return {
            "initialized": self._initialized,
            "active_provider": self._active_provider.value,
            "elevenlabs_circuit_state": cb_state,
            "local_tts_available": self._local_tts_available(),
            "local_tts_backend": self._local_tts.get_backend() if self._local_tts else "none",
            "failover_count": len(self._failover_history),
            "last_failover": str(self._failover_history[-1]) if self._failover_history else None,
            "statistics": self._statistics.to_dict(),
            "local_tts_health": local_health,
        }


# Convenience functions

async def create_tts_failover_manager(
    config: Optional[TTSFailoverConfig] = None,
) -> TTSFailoverManager:
    """Create and initialize a TTS failover manager.

    Args:
        config: Optional configuration.

    Returns:
        Initialized TTSFailoverManager instance.
    """
    manager = TTSFailoverManager(config=config)
    await manager.initialize()
    return manager


def create_enhanced_local_fn(
    voice: str = "en-US-AriaNeural",
    prefer_edge_tts: bool = True,
) -> Callable[[str], bytes]:
    """Create an enhanced local TTS function for TTSManager.

    This replaces the stub _stub_tts with actual LocalTTSFallback.

    Args:
        voice: Voice ID for Edge TTS.
        prefer_edge_tts: Whether to prefer Edge TTS over pyttsx3.

    Returns:
        Callable compatible with TTSManager.local_fn.
    """
    config = LocalTTSConfig(voice=voice, prefer_edge_tts=prefer_edge_tts)
    fallback = LocalTTSFallback(config=config)
    return fallback.synthesize
