"""Event bus for decoupled intra-application communication."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Callable

logger = logging.getLogger("event-bus")

Callback = Callable[[object], object | None]


class EventBus:
    """In-memory publish/subscribe event bus for decoupled communication."""

    def __init__(self) -> None:
        self._subscribers: defaultdict[str, list[Callback]] = defaultdict(list)
        self._event_count: int = 0

    def subscribe(self, event_name: str, callback: Callback) -> None:
        """Register a callback for the given event name."""
        self._subscribers[event_name].append(callback)

    def unsubscribe(self, event_name: str, callback: Callback) -> bool:
        """Remove a callback. Returns True if found and removed."""
        subscribers = self._subscribers.get(event_name)
        if not subscribers:
            return False
        try:
            subscribers.remove(callback)
        except ValueError:
            return False
        if not subscribers:
            _ = self._subscribers.pop(event_name, None)
        return True

    async def publish(self, event_name: str, data: object | None = None) -> int:
        """Publish an event to all subscribers. Returns count of notified listeners."""
        subscribers = list(self._subscribers.get(event_name, []))
        if not subscribers:
            return 0
        self._event_count += 1
        notified = 0
        for callback in subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):  # pyright: ignore[reportDeprecated]
                    await callback(data)
                else:
                    _ = callback(data)
                notified += 1
            except Exception as exc:
                logger.error("EventBus callback error for '%s': %s", event_name, exc)
        return notified

    def subscriber_count(self, event_name: str | None = None) -> int:
        """Return number of subscribers, optionally filtered by event name."""
        if event_name is None:
            return sum(len(callbacks) for callbacks in self._subscribers.values())
        return len(self._subscribers.get(event_name, []))

    def health(self) -> dict[str, object]:
        """Health check for pipeline monitoring."""
        return {
            "status": "healthy",
            "events": len(self._subscribers),
            "subscribers": self.subscriber_count(),
            "published_events": self._event_count,
        }
