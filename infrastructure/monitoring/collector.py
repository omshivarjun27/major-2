"""Metrics collector primitives for infrastructure monitoring."""

# pyright: reportImplicitOverride=false

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from typing import TypedDict

HistogramStats = dict[str, float | int]


class MetricsSnapshot(TypedDict):
    """Snapshot of all metrics grouped by type."""

    counters: dict[str, float]
    gauges: dict[str, float]
    histograms: dict[str, HistogramStats]


class MetricsCollector(ABC):
    """Abstract metrics collector interface."""

    @abstractmethod
    def increment(self, name: str, value: float = 1.0, tags: dict[str, object] | None = None) -> None:
        """Increment a counter metric."""

    @abstractmethod
    def gauge(self, name: str, value: float, tags: dict[str, object] | None = None) -> None:
        """Set a gauge metric."""

    @abstractmethod
    def histogram(self, name: str, value: float, tags: dict[str, object] | None = None) -> None:
        """Record a histogram value."""

    @abstractmethod
    def get_counter(self, name: str) -> float:
        """Return the current counter value."""

    @abstractmethod
    def get_gauge(self, name: str) -> float | None:
        """Return the current gauge value, if set."""

    @abstractmethod
    def get_histogram(self, name: str) -> HistogramStats:
        """Return histogram summary statistics."""

    @abstractmethod
    def get_all_metrics(self) -> MetricsSnapshot:
        """Return all metrics grouped by type."""

    @abstractmethod
    def health(self) -> dict[str, int | str]:
        """Return metrics health metadata."""

    @abstractmethod
    def reset(self) -> None:
        """Reset all metrics."""


class InMemoryMetrics(MetricsCollector):
    """Thread-safe in-memory metrics collector."""

    def __init__(self) -> None:
        self._lock: threading.RLock = threading.RLock()
        self._counters: dict[str, float] = {}
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = {}

    def increment(self, name: str, value: float = 1.0, tags: dict[str, object] | None = None) -> None:
        with self._lock:
            self._counters[name] = self._counters.get(name, 0.0) + value

    def gauge(self, name: str, value: float, tags: dict[str, object] | None = None) -> None:
        with self._lock:
            self._gauges[name] = value

    def histogram(self, name: str, value: float, tags: dict[str, object] | None = None) -> None:
        with self._lock:
            if name not in self._histograms:
                self._histograms[name] = []
            self._histograms[name].append(value)

    def get_counter(self, name: str) -> float:
        with self._lock:
            return self._counters.get(name, 0.0)

    def get_gauge(self, name: str) -> float | None:
        with self._lock:
            return self._gauges.get(name)

    def get_histogram(self, name: str) -> HistogramStats:
        with self._lock:
            values = self._histograms.get(name)
            if not values:
                return {}
            return self._build_histogram(values)

    def get_all_metrics(self) -> MetricsSnapshot:
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {
                    name: self._build_histogram(values) for name, values in self._histograms.items()
                },
            }

    def health(self) -> dict[str, int | str]:
        with self._lock:
            return {
                "status": "ok",
                "counters": len(self._counters),
                "gauges": len(self._gauges),
                "histograms": len(self._histograms),
            }

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()

    def _build_histogram(self, values: list[float]) -> HistogramStats:
        if not values:
            return {}
        sorted_values = sorted(values)
        count = len(sorted_values)
        mean_value = sum(sorted_values) / count
        return {
            "min": sorted_values[0],
            "max": sorted_values[-1],
            "mean": mean_value,
            "p50": sorted_values[int(count * 0.50)],
            "p95": sorted_values[int(count * 0.95)],
            "p99": sorted_values[int(count * 0.99)],
            "count": count,
        }


class NullMetrics(MetricsCollector):
    """No-op metrics collector for disabled telemetry."""

    def increment(self, name: str, value: float = 1.0, tags: dict[str, object] | None = None) -> None:
        return None

    def gauge(self, name: str, value: float, tags: dict[str, object] | None = None) -> None:
        return None

    def histogram(self, name: str, value: float, tags: dict[str, object] | None = None) -> None:
        return None

    def get_counter(self, name: str) -> float:
        return 0.0

    def get_gauge(self, name: str) -> float | None:
        return None

    def get_histogram(self, name: str) -> HistogramStats:
        return {}

    def get_all_metrics(self) -> MetricsSnapshot:
        return {"counters": {}, "gauges": {}, "histograms": {}}

    def health(self) -> dict[str, int | str]:
        return {"status": "disabled"}

    def reset(self) -> None:
        return None


def create_metrics_collector(backend: str = "memory") -> MetricsCollector:
    """Factory for metrics collectors."""
    if backend == "memory":
        return InMemoryMetrics()
    if backend == "null":
        return NullMetrics()
    raise ValueError(f"Unknown metrics backend: {backend}")
