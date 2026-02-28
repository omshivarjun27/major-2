"""
Tavus Adapter — Integration with Tavus real-time avatar API for visual persona.

Provides a thin, optional integration layer that streams scene narrations
to a Tavus replica for visual avatar feedback. Disabled by default.

Circuit breaker integration: when Tavus API fails repeatedly, the adapter
silently degrades (returns False) rather than blocking or erroring.

Environment Variables:
    TAVUS_ENABLED: "true" to activate (default "false")
    TAVUS_API_KEY: API key for Tavus
    TAVUS_REPLICA_ID: Replica ID to use
    TAVUS_PERSONA_ID: Persona ID (optional)
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from infrastructure.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerState,
    register_circuit_breaker,
)
from infrastructure.resilience.retry_policy import RetryPolicy, get_retry_policy
from infrastructure.resilience.timeout_config import get_timeout

logger = logging.getLogger("tavus-adapter")

# Circuit breaker config for Tavus: conservative thresholds since Tavus is non-critical
_TAVUS_CB_CONFIG = CircuitBreakerConfig(
    failure_threshold=2,  # Trip after 2 failures (non-critical service)
    reset_timeout_s=60.0,  # Wait 60s before probing
    half_open_max_calls=1,
    success_threshold=1,
)


def _log_tavus_state_change(event: Any) -> None:
    """Log circuit breaker state transitions for Tavus."""
    logger.warning(
        "Tavus circuit breaker: %s -> %s (failures: %d)",
        event.previous_state.value,
        event.new_state.value,
        event.failure_count,
    )


@dataclass
class TavusConfig:
    """Tavus integration configuration."""

    enabled: bool = False
    api_key: str = ""
    replica_id: str = ""
    persona_id: str = ""
    base_url: str = "https://api.tavus.io/v2"
    conversation_url: str = "wss://tavus.io"
    max_text_length: int = 500
    timeout_s: float = 0.0  # 0 means use centralized config

    @classmethod
    def from_env(cls) -> "TavusConfig":
        return cls(
            enabled=os.getenv("TAVUS_ENABLED", "false").lower() == "true",
            api_key=os.getenv("TAVUS_API_KEY", ""),
            replica_id=os.getenv("TAVUS_REPLICA_ID", ""),
            persona_id=os.getenv("TAVUS_PERSONA_ID", ""),
            timeout_s=get_timeout("avatar"),  # Use centralized timeout config
        )


@dataclass
class TavusMessage:
    """A message to/from Tavus."""

    role: str  # "user" or "assistant"
    text: str
    timestamp_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"role": self.role, "text": self.text, "timestamp_ms": self.timestamp_ms}


class TavusAdapter:
    """Thin wrapper around Tavus conversational video API.

    When enabled, streams text narrations to a Tavus replica that
    renders a speaking avatar. The avatar can be shown on a paired
    display device (e.g., smart glasses companion screen).

    All operations are no-ops when disabled.

    Circuit breaker behavior:
    - When circuit is OPEN, all API calls return False immediately (silent degradation)
    - Circuit trips after 2 consecutive failures
    - Circuit resets after 60 seconds of rest

    Usage::

        adapter = TavusAdapter()  # reads env
        await adapter.connect()
        await adapter.send_narration("There is a car approaching on your left.")
        await adapter.disconnect()
    """

    def __init__(self, config: Optional[TavusConfig] = None):
        self.config = config or TavusConfig.from_env()
        self._conversation_id: Optional[str] = None
        self._ws = None
        self._connected = False
        self._message_history: List[TavusMessage] = []

        # Register circuit breaker ONLY when Tavus is enabled (no overhead otherwise)
        self._cb: Optional[CircuitBreaker] = None
        self._retry_policy: Optional[RetryPolicy] = None
        if self.enabled:
            self._cb = register_circuit_breaker(
                "tavus",
                config=_TAVUS_CB_CONFIG,
                on_state_change=[_log_tavus_state_change],
            )
            self._retry_policy = get_retry_policy("tavus")
            logger.info("Tavus adapter initialized with circuit breaker and retry policy")

    @property
    def enabled(self) -> bool:
        return self.config.enabled and bool(self.config.api_key) and bool(self.config.replica_id)

    def _is_circuit_open(self) -> bool:
        """Check if circuit breaker is open (Tavus unavailable)."""
        if self._cb is None:
            return False
        return self._cb.state is CircuitBreakerState.OPEN

    async def _record_success(self) -> None:
        """Record a successful API call to the circuit breaker."""
        if self._cb is not None:
            # Reset failure count on success
            if self._cb.state is CircuitBreakerState.HALF_OPEN:
                await self._cb.reset()
            elif self._cb._failure_count > 0:
                self._cb._failure_count = 0

    async def _record_failure(self, error: Optional[Exception] = None) -> None:
        """Record a failed API call to the circuit breaker."""
        if self._cb is None:
            return

        current_state = self._cb.state
        if current_state is CircuitBreakerState.CLOSED:
            self._cb._failure_count += 1
            if self._cb._failure_count >= _TAVUS_CB_CONFIG.failure_threshold:
                await self._cb.trip()
                logger.warning("Tavus circuit tripped after %d failures", self._cb._failure_count)
        elif current_state is CircuitBreakerState.HALF_OPEN:
            await self._cb.trip()
            logger.warning("Tavus circuit re-tripped from half-open state")

    async def connect(self) -> bool:
        """Establish a Tavus conversation session."""
        if not self.enabled:
            logger.debug("Tavus integration disabled")
            return False

        # Circuit breaker: fast-fail if circuit is open
        if self._is_circuit_open():
            logger.debug("Tavus circuit is OPEN — skipping connect")
            return False

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                headers = {"x-api-key": self.config.api_key, "Content-Type": "application/json"}
                payload = {
                    "replica_id": self.config.replica_id,
                }
                if self.config.persona_id:
                    payload["persona_id"] = self.config.persona_id

                async with session.post(
                    f"{self.config.base_url}/conversations",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_s),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self._conversation_id = data.get("conversation_id")
                        conversation_url = data.get("conversation_url", "")
                        logger.info("Tavus conversation created: %s", self._conversation_id)

                        if conversation_url:
                            self._ws = await session.ws_connect(conversation_url)
                            self._connected = True

                        await self._record_success()
                        return True
                    else:
                        body = await resp.text()
                        logger.error("Tavus API error %d: %s", resp.status, body)
                        await self._record_failure()
                        return False

        except ImportError:
            logger.warning("aiohttp not installed — Tavus integration unavailable")
            return False
        except Exception as exc:
            logger.error("Tavus connect failed: %s", exc)
            await self._record_failure(exc)
            return False

    async def send_narration(self, text: str) -> bool:
        """Send a narration text to the Tavus avatar to speak.

        Args:
            text: Scene narration or alert text (max 500 chars)

        Returns:
            True if sent successfully.
        """
        if not self.enabled:
            return False

        # Circuit breaker: fast-fail if circuit is open
        if self._is_circuit_open():
            logger.debug("Tavus circuit is OPEN — skipping send_narration")
            return False

        text = text[: self.config.max_text_length]
        msg = TavusMessage(role="user", text=text, timestamp_ms=time.time() * 1000)
        self._message_history.append(msg)

        if self._ws and not self._ws.closed:
            try:
                import json

                await self._ws.send_str(
                    json.dumps(
                        {
                            "type": "conversation.respond",
                            "text": text,
                        }
                    )
                )
                logger.debug("Sent to Tavus: %s", text[:50])
                await self._record_success()
                return True
            except Exception as exc:
                logger.error("Tavus WS send failed: %s", exc)
                await self._record_failure(exc)
                return False

        # Fallback: REST inject
        return await self._send_rest(text)

    async def _send_rest(self, text: str) -> bool:
        """Send narration via REST API fallback."""
        if not self._conversation_id:
            return False

        # Circuit breaker: fast-fail if circuit is open
        if self._is_circuit_open():
            logger.debug("Tavus circuit is OPEN — skipping REST send")
            return False

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                headers = {"x-api-key": self.config.api_key, "Content-Type": "application/json"}
                async with session.post(
                    f"{self.config.base_url}/conversations/{self._conversation_id}/inject",
                    headers=headers,
                    json={"text": text, "role": "user"},
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_s),
                ) as resp:
                    if resp.status == 200:
                        await self._record_success()
                        return True
                    else:
                        await self._record_failure()
                        return False
        except Exception as exc:
            logger.error("Tavus REST send failed: %s", exc)
            await self._record_failure(exc)
            return False

    async def end_conversation(self) -> bool:
        """End the Tavus conversation session."""
        if not self.enabled or not self._conversation_id:
            return False

        # Don't check circuit breaker for cleanup operations
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                headers = {"x-api-key": self.config.api_key}
                async with session.delete(
                    f"{self.config.base_url}/conversations/{self._conversation_id}",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_s),
                ) as resp:
                    ok = resp.status in (200, 204)
                    if ok:
                        logger.info("Tavus conversation ended: %s", self._conversation_id)
                    return ok
        except Exception as exc:
            logger.error("Tavus end conversation failed: %s", exc)
            return False

    async def disconnect(self) -> None:
        """Close WebSocket and end conversation."""
        if self._ws and not self._ws.closed:
            await self._ws.close()
        await self.end_conversation()
        self._connected = False
        self._conversation_id = None

    def get_history(self) -> List[dict]:
        return [m.to_dict() for m in self._message_history]

    def health(self) -> dict:
        """Health snapshot including circuit breaker state."""
        result = {
            "enabled": self.enabled,
            "connected": self._connected,
            "conversation_id": self._conversation_id,
            "messages_sent": len(self._message_history),
            "circuit_breaker": None,
        }
        if self._cb is not None:
            result["circuit_breaker"] = self._cb.snapshot()
        return result
