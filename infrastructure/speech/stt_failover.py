"""STT Failover Manager for automatic Deepgram ↔ Whisper switching.

Automatically switches from Deepgram (cloud) to Whisper (local) when the Deepgram
circuit breaker opens, and switches back when it recovers. Failover completes
within 2 seconds of circuit state change.

Architecture constraint: imports from ``shared/`` and ``infrastructure/`` only.

Usage::

    from infrastructure.speech.stt_failover import STTFailoverManager

    manager = STTFailoverManager()
    await manager.initialize()

    # Transcribe using the active provider
    result = await manager.transcribe(audio_bytes)

    # Check current provider
    provider = manager.get_active_provider()  # "deepgram" or "whisper"
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from infrastructure.resilience.circuit_breaker import (
    CircuitBreakerConfig,
    CircuitBreakerState,
    StateChangeEvent,
    get_circuit_breaker,
    register_circuit_breaker,
)
from infrastructure.speech.local.whisper_stt import (
    WHISPER_AVAILABLE,
    TranscriptionResult,
    WhisperConfig,
    WhisperSTT,
)

logger = logging.getLogger("speech.stt_failover")


class STTProvider(Enum):
    """Available STT providers."""

    DEEPGRAM = "deepgram"
    WHISPER = "whisper"
    NONE = "none"


@dataclass
class FailoverEvent:
    """Record of a failover event."""

    timestamp: float
    from_provider: STTProvider
    to_provider: STTProvider
    trigger: str  # "circuit_open", "circuit_closed", "manual", "initialization"
    latency_ms: float = 0.0

    def __str__(self) -> str:
        return (
            f"[{time.strftime('%H:%M:%S', time.localtime(self.timestamp))}] "
            f"Failover: {self.from_provider.value} → {self.to_provider.value} "
            f"(trigger={self.trigger}, latency={self.latency_ms:.1f}ms)"
        )


@dataclass
class STTFailoverConfig:
    """Configuration for STT failover manager."""

    deepgram_service_name: str = "deepgram"
    """Circuit breaker service name for Deepgram."""

    whisper_model_size: str = "base"
    """Whisper model size for fallback (tiny/base/small)."""

    prewarm_whisper: bool = True
    """Pre-load Whisper model after first fallback for faster subsequent failovers."""

    failover_timeout_s: float = 2.0
    """Maximum time allowed for failover to complete."""

    auto_initialize: bool = False
    """Automatically initialize on construction (requires running event loop)."""


class STTFailoverManager:
    """Manages automatic failover between Deepgram and Whisper STT providers.

    Subscribes to the Deepgram circuit breaker state changes and automatically
    switches to/from the Whisper local fallback based on circuit state.

    Thread-safe: all state changes are protected by an asyncio lock.
    """

    def __init__(self, config: Optional[STTFailoverConfig] = None) -> None:
        """Initialize the failover manager.

        Args:
            config: Configuration options. Uses defaults if not provided.
        """
        self.config = config or STTFailoverConfig()

        # Current active provider
        self._active_provider = STTProvider.DEEPGRAM
        self._lock = asyncio.Lock()

        # Whisper fallback (lazy-initialized)
        self._whisper: Optional[WhisperSTT] = None
        self._whisper_prewarmed = False

        # Failover event history
        self._failover_history: List[FailoverEvent] = []
        self._max_history = 100

        # Circuit breaker reference (set during initialize)
        self._deepgram_cb = None
        self._callback_registered = False

        # Initialization state
        self._initialized = False

        logger.info(
            "STTFailoverManager created (deepgram_cb=%s, whisper_available=%s)",
            self.config.deepgram_service_name,
            WHISPER_AVAILABLE,
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

            # Get or create the Deepgram circuit breaker
            self._deepgram_cb = get_circuit_breaker(self.config.deepgram_service_name)
            if self._deepgram_cb is None:
                # Register with default config if not already registered
                self._deepgram_cb = register_circuit_breaker(
                    self.config.deepgram_service_name,
                    config=CircuitBreakerConfig(
                        failure_threshold=3,
                        reset_timeout_s=15.0,
                        half_open_max_calls=1,
                        success_threshold=1,
                    ),
                )

            # Subscribe to state changes
            if not self._callback_registered:
                self._deepgram_cb.add_callback(self._on_circuit_state_change)
                self._callback_registered = True

            # Check current circuit state and set initial provider
            if self._deepgram_cb.state is CircuitBreakerState.OPEN:
                await self._activate_whisper("initialization")
            else:
                self._active_provider = STTProvider.DEEPGRAM

            # Initialize Whisper if available
            if WHISPER_AVAILABLE:
                whisper_config = WhisperConfig(model_size=self.config.whisper_model_size)
                self._whisper = WhisperSTT(config=whisper_config)

            self._initialized = True
            logger.info(
                "STTFailoverManager initialized (active=%s)",
                self._active_provider.value,
            )

    async def shutdown(self) -> None:
        """Shutdown the manager and cleanup resources."""
        async with self._lock:
            # Unsubscribe from circuit breaker
            if self._deepgram_cb is not None and self._callback_registered:
                self._deepgram_cb.remove_callback(self._on_circuit_state_change)
                self._callback_registered = False

            # Unload Whisper model if loaded
            if self._whisper is not None and self._whisper.is_loaded():
                await self._whisper.unload()

            self._initialized = False
            logger.info("STTFailoverManager shutdown complete")

    def get_active_provider(self) -> str:
        """Get the name of the currently active STT provider.

        Returns:
            Provider name: "deepgram", "whisper", or "none"
        """
        return self._active_provider.value

    def get_active_provider_enum(self) -> STTProvider:
        """Get the currently active STT provider as enum."""
        return self._active_provider

    async def transcribe(
        self,
        audio_data: Union[bytes, str],
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcribe audio using the currently active provider.

        Args:
            audio_data: Audio bytes (PCM/WAV) or path to audio file.
            language: Override language code (e.g., "en", "es").

        Returns:
            TranscriptionResult with text and metadata.

        Note:
            When active provider is Deepgram, this method is a passthrough
            since Deepgram is accessed via LiveKit plugins. The actual
            Deepgram transcription happens in the agent layer.
        """
        if not self._initialized:
            await self.initialize()

        if self._active_provider == STTProvider.WHISPER:
            return await self._transcribe_whisper(audio_data, language)
        elif self._active_provider == STTProvider.DEEPGRAM:
            # Deepgram is handled by LiveKit; return placeholder
            return TranscriptionResult(
                text="",
                language=language or "en",
                latency_ms=0.0,
                confidence=0.0,
                model_size="cloud",
                segments=0,
                error="Deepgram transcription handled by LiveKit agent",
            )
        else:
            return TranscriptionResult(
                text="",
                language=language or "en",
                latency_ms=0.0,
                confidence=0.0,
                model_size="none",
                segments=0,
                error="No STT provider available",
            )

    async def _transcribe_whisper(
        self,
        audio_data: Union[bytes, str],
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcribe using Whisper local fallback."""
        if self._whisper is None:
            return TranscriptionResult(
                text="",
                language=language or "en",
                latency_ms=0.0,
                confidence=0.0,
                model_size="none",
                segments=0,
                error="Whisper not available",
            )

        result = await self._whisper.transcribe(audio_data, language=language)

        # Pre-warm the model after first successful use
        if result.success and self.config.prewarm_whisper:
            self._whisper_prewarmed = True

        return result

    async def _on_circuit_state_change(self, event: StateChangeEvent) -> None:
        """Handle circuit breaker state change callback.

        This is the main failover trigger. Called by the circuit breaker
        whenever the state changes.
        """
        if event.service_name != self.config.deepgram_service_name:
            return

        logger.info(
            "Circuit state change: %s → %s (failures=%d)",
            event.previous_state.value,
            event.new_state.value,
            event.failure_count,
        )

        # CLOSED → OPEN: Activate Whisper fallback
        if (
            event.previous_state is CircuitBreakerState.CLOSED
            and event.new_state is CircuitBreakerState.OPEN
        ):
            await self._activate_whisper("circuit_open")

        # HALF_OPEN → CLOSED: Switch back to Deepgram
        elif (
            event.previous_state is CircuitBreakerState.HALF_OPEN
            and event.new_state is CircuitBreakerState.CLOSED
        ):
            await self._activate_deepgram("circuit_closed")

        # OPEN → HALF_OPEN: Prepare for possible recovery
        elif (
            event.previous_state is CircuitBreakerState.OPEN
            and event.new_state is CircuitBreakerState.HALF_OPEN
        ):
            logger.info("Deepgram entering HALF_OPEN state - testing recovery")

        # HALF_OPEN → OPEN: Recovery failed, stay on Whisper
        elif (
            event.previous_state is CircuitBreakerState.HALF_OPEN
            and event.new_state is CircuitBreakerState.OPEN
        ):
            logger.warning("Deepgram recovery failed - staying on Whisper fallback")

    async def _activate_whisper(self, trigger: str) -> None:
        """Activate Whisper as the STT provider."""
        start_time = time.monotonic()

        async with self._lock:
            if self._active_provider == STTProvider.WHISPER:
                return

            previous = self._active_provider

            if not WHISPER_AVAILABLE:
                logger.error(
                    "Cannot activate Whisper fallback - faster-whisper not installed"
                )
                self._active_provider = STTProvider.NONE
                self._record_failover(previous, STTProvider.NONE, trigger, 0.0)
                return

            # Ensure Whisper is ready
            if self._whisper is None:
                whisper_config = WhisperConfig(model_size=self.config.whisper_model_size)
                self._whisper = WhisperSTT(config=whisper_config)

            # Pre-load model if configured and not already loaded
            if self.config.prewarm_whisper and not self._whisper.is_loaded():
                logger.info("Pre-loading Whisper model for failover...")
                try:
                    async with asyncio.timeout(self.config.failover_timeout_s):
                        await self._whisper._ensure_model_loaded()
                except asyncio.TimeoutError:
                    logger.warning(
                        "Whisper model pre-load timed out after %.1fs",
                        self.config.failover_timeout_s,
                    )

            self._active_provider = STTProvider.WHISPER
            latency_ms = (time.monotonic() - start_time) * 1000

            self._record_failover(previous, STTProvider.WHISPER, trigger, latency_ms)
            logger.info(
                "STT failover: %s → Whisper (trigger=%s, latency=%.1fms)",
                previous.value,
                trigger,
                latency_ms,
            )

    async def _activate_deepgram(self, trigger: str) -> None:
        """Activate Deepgram as the STT provider."""
        start_time = time.monotonic()

        async with self._lock:
            if self._active_provider == STTProvider.DEEPGRAM:
                return

            previous = self._active_provider
            self._active_provider = STTProvider.DEEPGRAM
            latency_ms = (time.monotonic() - start_time) * 1000

            self._record_failover(previous, STTProvider.DEEPGRAM, trigger, latency_ms)
            logger.info(
                "STT failback: %s → Deepgram (trigger=%s, latency=%.1fms)",
                previous.value,
                trigger,
                latency_ms,
            )

    def _record_failover(
        self,
        from_provider: STTProvider,
        to_provider: STTProvider,
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

        # Trim history
        if len(self._failover_history) > self._max_history:
            self._failover_history = self._failover_history[-self._max_history :]

        logger.debug("Failover recorded: %s", event)

    async def force_failover_to_whisper(self) -> None:
        """Manually force failover to Whisper (for testing/debugging)."""
        await self._activate_whisper("manual")

    async def force_failback_to_deepgram(self) -> None:
        """Manually force failback to Deepgram (for testing/debugging)."""
        await self._activate_deepgram("manual")

    def get_failover_history(self) -> List[FailoverEvent]:
        """Get the failover event history."""
        return list(self._failover_history)

    def health(self) -> Dict[str, Any]:
        """Health snapshot for diagnostics."""
        cb_state = "unknown"
        if self._deepgram_cb is not None:
            cb_state = self._deepgram_cb.state.value

        whisper_health = {}
        if self._whisper is not None:
            whisper_health = self._whisper.health()

        return {
            "initialized": self._initialized,
            "active_provider": self._active_provider.value,
            "deepgram_circuit_state": cb_state,
            "whisper_available": WHISPER_AVAILABLE,
            "whisper_loaded": self._whisper.is_loaded() if self._whisper else False,
            "whisper_prewarmed": self._whisper_prewarmed,
            "failover_count": len(self._failover_history),
            "last_failover": str(self._failover_history[-1]) if self._failover_history else None,
            "whisper_health": whisper_health,
        }


# Convenience function to create and initialize the manager
async def create_stt_failover_manager(
    config: Optional[STTFailoverConfig] = None,
) -> STTFailoverManager:
    """Create and initialize an STT failover manager.

    Args:
        config: Optional configuration.

    Returns:
        Initialized STTFailoverManager instance.
    """
    manager = STTFailoverManager(config=config)
    await manager.initialize()
    return manager
