"""Unit tests for application event bus."""

from __future__ import annotations

import asyncio

from application.event_bus import EventBus


def test_subscribe_and_publish() -> None:
    bus = EventBus()
    received: list[object] = []

    def handler(data: object) -> None:
        received.append(data)

    bus.subscribe("hello", handler)
    count = asyncio.run(bus.publish("hello", {"ok": True}))

    assert count == 1
    assert received == [{"ok": True}]


def test_publish_no_subscribers() -> None:
    bus = EventBus()
    count = asyncio.run(bus.publish("missing", 123))
    assert count == 0


def test_multiple_subscribers() -> None:
    bus = EventBus()
    hits: list[tuple[str, object]] = []

    def handler_a(data: object) -> None:
        hits.append(("a", data))

    def handler_b(data: object) -> None:
        hits.append(("b", data))

    def handler_c(data: object) -> None:
        hits.append(("c", data))

    bus.subscribe("multi", handler_a)
    bus.subscribe("multi", handler_b)
    bus.subscribe("multi", handler_c)

    count = asyncio.run(bus.publish("multi", "payload"))

    assert count == 3
    assert ("a", "payload") in hits
    assert ("b", "payload") in hits
    assert ("c", "payload") in hits


def test_unsubscribe() -> None:
    bus = EventBus()
    called: list[object] = []

    def handler(data: object) -> None:
        called.append(data)

    bus.subscribe("bye", handler)
    removed = bus.unsubscribe("bye", handler)
    assert removed is True

    count = asyncio.run(bus.publish("bye", "ignored"))
    assert count == 0
    assert called == []


def test_unsubscribe_nonexistent() -> None:
    bus = EventBus()

    def handler(data: object) -> None:
        _ = data

    removed = bus.unsubscribe("nope", handler)
    assert removed is False


def test_async_callback() -> None:
    bus = EventBus()
    received: list[object] = []

    async def handler(data: object) -> None:
        await asyncio.sleep(0)
        received.append(data)

    bus.subscribe("async", handler)
    count = asyncio.run(bus.publish("async", "ok"))

    assert count == 1
    assert received == ["ok"]


def test_subscriber_count() -> None:
    bus = EventBus()

    def handler_a(data: object) -> None:
        _ = data

    def handler_b(data: object) -> None:
        _ = data

    bus.subscribe("a", handler_a)
    bus.subscribe("b", handler_b)
    bus.subscribe("b", handler_a)

    assert bus.subscriber_count() == 3
    assert bus.subscriber_count("a") == 1
    assert bus.subscriber_count("b") == 2
    assert bus.subscriber_count("missing") == 0


def test_health() -> None:
    bus = EventBus()

    def handler(data: object) -> None:
        _ = data

    bus.subscribe("evt", handler)
    _ = asyncio.run(bus.publish("evt", "payload"))

    health = bus.health()
    assert health["status"] == "healthy"
    assert health["events"] == 1
    assert health["subscribers"] == 1
    assert health["published_events"] == 1
