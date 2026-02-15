"""
Tavus Adapter — Integration with Tavus real-time avatar API for visual persona.

Provides a thin, optional integration layer that streams scene narrations
to a Tavus replica for visual avatar feedback. Disabled by default.

Environment Variables:
    TAVUS_ENABLED: "true" to activate (default "false")
    TAVUS_API_KEY: API key for Tavus
    TAVUS_REPLICA_ID: Replica ID to use
    TAVUS_PERSONA_ID: Persona ID (optional)
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("tavus-adapter")


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
    timeout_s: float = 10.0

    @classmethod
    def from_env(cls) -> "TavusConfig":
        return cls(
            enabled=os.getenv("TAVUS_ENABLED", "false").lower() == "true",
            api_key=os.getenv("TAVUS_API_KEY", ""),
            replica_id=os.getenv("TAVUS_REPLICA_ID", ""),
            persona_id=os.getenv("TAVUS_PERSONA_ID", ""),
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

    @property
    def enabled(self) -> bool:
        return self.config.enabled and bool(self.config.api_key) and bool(self.config.replica_id)

    async def connect(self) -> bool:
        """Establish a Tavus conversation session."""
        if not self.enabled:
            logger.debug("Tavus integration disabled")
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
                        return True
                    else:
                        body = await resp.text()
                        logger.error("Tavus API error %d: %s", resp.status, body)
                        return False

        except ImportError:
            logger.warning("aiohttp not installed — Tavus integration unavailable")
            return False
        except Exception as exc:
            logger.error("Tavus connect failed: %s", exc)
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

        text = text[:self.config.max_text_length]
        msg = TavusMessage(role="user", text=text, timestamp_ms=time.time() * 1000)
        self._message_history.append(msg)

        if self._ws and not self._ws.closed:
            try:
                import json
                await self._ws.send_str(json.dumps({
                    "type": "conversation.respond",
                    "text": text,
                }))
                logger.debug("Sent to Tavus: %s", text[:50])
                return True
            except Exception as exc:
                logger.error("Tavus WS send failed: %s", exc)
                return False

        # Fallback: REST inject
        return await self._send_rest(text)

    async def _send_rest(self, text: str) -> bool:
        """Send narration via REST API fallback."""
        if not self._conversation_id:
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
                    return resp.status == 200
        except Exception as exc:
            logger.error("Tavus REST send failed: %s", exc)
            return False

    async def end_conversation(self) -> bool:
        """End the Tavus conversation session."""
        if not self.enabled or not self._conversation_id:
            return False

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
        return {
            "enabled": self.enabled,
            "connected": self._connected,
            "conversation_id": self._conversation_id,
            "messages_sent": len(self._message_history),
        }
