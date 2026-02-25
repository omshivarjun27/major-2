"""Unit tests for infrastructure monitoring metrics collector."""

# pyright: reportUnknownMemberType=false

from __future__ import annotations

import pytest

from infrastructure.monitoring import InMemoryMetrics, NullMetrics


def test_increment_counter() -> None:
    metrics = InMemoryMetrics()
    metrics.increment("requests")
    metrics.increment("requests")
    metrics.increment("requests")

    assert metrics.get_counter("requests") == 3.0


def test_gauge_set_and_get() -> None:
    metrics = InMemoryMetrics()
    metrics.gauge("cpu", 75.5)

    assert metrics.get_gauge("cpu") == 75.5


def test_histogram_records_values() -> None:
    metrics = InMemoryMetrics()
    values = list(range(1, 11))
    for value in values:
        metrics.histogram("latency", float(value))

    stats = metrics.get_histogram("latency")

    assert stats["min"] == 1.0
    assert stats["max"] == 10.0
    assert stats["mean"] == pytest.approx(5.5)


def test_histogram_percentiles() -> None:
    metrics = InMemoryMetrics()
    for value in range(100):
        metrics.histogram("latency", float(value))

    stats = metrics.get_histogram("latency")

    assert 49 <= stats["p50"] <= 50
    assert 94 <= stats["p95"] <= 95


def test_get_all_metrics() -> None:
    metrics = InMemoryMetrics()
    metrics.increment("requests", 2.0)
    metrics.gauge("cpu", 80.0)
    metrics.histogram("latency", 123.0)

    all_metrics = metrics.get_all_metrics()

    assert set(all_metrics.keys()) == {"counters", "gauges", "histograms"}
    assert all_metrics["counters"]["requests"] == 2.0
    assert all_metrics["gauges"]["cpu"] == 80.0
    assert "latency" in all_metrics["histograms"]


def test_health_reports_metric_count() -> None:
    metrics = InMemoryMetrics()
    metrics.increment("requests")
    metrics.increment("errors")
    metrics.gauge("cpu", 70.0)
    metrics.histogram("latency", 1.0)
    metrics.histogram("latency", 2.0)

    health = metrics.health()

    assert health["status"] == "ok"
    assert health["counters"] == 2
    assert health["gauges"] == 1
    assert health["histograms"] == 1


def test_reset_clears_all() -> None:
    metrics = InMemoryMetrics()
    metrics.increment("requests")
    metrics.gauge("cpu", 70.0)
    metrics.histogram("latency", 1.0)

    metrics.reset()

    assert metrics.get_counter("requests") == 0.0
    assert metrics.get_gauge("cpu") is None
    assert metrics.get_histogram("latency") == {}
    assert metrics.get_all_metrics() == {"counters": {}, "gauges": {}, "histograms": {}}


def test_null_metrics_no_ops() -> None:
    metrics = NullMetrics()
    metrics.increment("requests")
    metrics.gauge("cpu", 1.0)
    metrics.histogram("latency", 10.0)

    assert metrics.get_counter("requests") == 0.0
    assert metrics.get_gauge("cpu") is None
    assert metrics.get_histogram("latency") == {}
    assert metrics.get_all_metrics() == {"counters": {}, "gauges": {}, "histograms": {}}
    assert metrics.health() == {"status": "disabled"}
