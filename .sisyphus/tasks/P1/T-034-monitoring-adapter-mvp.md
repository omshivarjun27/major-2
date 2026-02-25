# T-034: monitoring-adapter-mvp

> Phase: P1 | Cluster: CL-INF | Risk: Low | State: not_started

## Objective

Create a `MetricsCollector` ABC and `InMemoryMetrics` implementation in
`infrastructure/monitoring/`. Currently the directory contains only `__init__.py` (empty)
and `AGENTS.md` — a pure stub. This task delivers a minimal metrics collection layer
that supports counters, gauges, and histograms with in-memory storage.

The `InMemoryMetrics` implementation stores all metrics in thread-safe dictionaries,
suitable for development and testing. Production backends (Prometheus, StatsD) can be
added later by implementing the same ABC. The metrics collector is the observation
layer that the validation suite (T-035) will use to verify system behavior.

## Current State (Codebase Audit 2026-02-25)

- `infrastructure/monitoring/` contains only:
  - `__init__.py` (empty)
  - `AGENTS.md` (stub documentation)
- No metrics collection exists anywhere in the codebase.
- Latency tracking exists ad-hoc: `SpatialProcessor.process_frame()` records
  `latency_ms` in `NavigationOutput`, `VQAReasoner` tracks stats internally.
- No centralized counter/gauge/histogram abstraction.
- The infrastructure layer can import from `shared/` only.
- `threading.RLock` is used elsewhere (e.g., `FAISSIndexer`) for thread safety.

## Implementation Plan

### Step 1: Define MetricsCollector ABC

```python
from abc import ABC, abstractmethod
from typing import Optional

class MetricsCollector(ABC):
    @abstractmethod
    def increment(self, name: str, value: float = 1.0, tags: Optional[dict] = None) -> None: ...

    @abstractmethod
    def gauge(self, name: str, value: float, tags: Optional[dict] = None) -> None: ...

    @abstractmethod
    def histogram(self, name: str, value: float, tags: Optional[dict] = None) -> None: ...

    @abstractmethod
    def get_counter(self, name: str) -> float: ...

    @abstractmethod
    def get_gauge(self, name: str) -> Optional[float]: ...

    @abstractmethod
    def get_histogram(self, name: str) -> dict: ...

    @abstractmethod
    def get_all_metrics(self) -> dict: ...

    @abstractmethod
    def health(self) -> dict: ...

    @abstractmethod
    def reset(self) -> None: ...
```

### Step 2: Implement InMemoryMetrics

Store counters in a `dict[str, float]`, gauges in a `dict[str, float]`, histograms
in a `dict[str, list[float]]`. Use `threading.RLock` for thread safety. Histogram
`get_histogram()` returns min, max, mean, p50, p95, p99, count.

```python
class InMemoryMetrics(MetricsCollector):
    def __init__(self):
        self._lock = threading.RLock()
        self._counters: dict[str, float] = {}
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = {}
```

### Step 3: Add histogram percentile calculation

Compute percentiles from the stored value list using sorted indexing (no numpy needed).

### Step 4: Create factory function

```python
def create_metrics_collector(backend: str = "memory") -> MetricsCollector:
    if backend == "memory":
        return InMemoryMetrics()
    raise ValueError(f"Unknown metrics backend: {backend}")
```

### Step 5: Add NullMetrics implementation

A no-op implementation for when monitoring is disabled. All methods are no-ops, all
getters return 0 or empty dicts. Useful as a default fallback.

### Step 6: Write 8 unit tests

Cover counter increment, gauge set/get, histogram recording and percentiles, get_all,
health, reset, and NullMetrics no-op behavior.

## Files to Create

| File | Purpose |
|------|---------|
| `infrastructure/monitoring/collector.py` | MetricsCollector ABC + InMemoryMetrics + NullMetrics |
| `tests/unit/test_metrics_collector.py` | 8 unit tests for MetricsCollector |

## Files to Modify

| File | Change |
|------|--------|
| `infrastructure/monitoring/__init__.py` | Export MetricsCollector, InMemoryMetrics, NullMetrics, create_metrics_collector |
| `infrastructure/monitoring/AGENTS.md` | Document metrics abstraction, supported metric types, thread safety |
| `infrastructure/AGENTS.md` | Reference new monitoring module |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/unit/test_metrics_collector.py` | `test_increment_counter` - increment "requests" 3 times, verify get_counter returns 3.0 |
| | `test_gauge_set_and_get` - set gauge "cpu", verify get_gauge returns exact value |
| | `test_histogram_records_values` - record 10 values, verify get_histogram returns correct min/max/mean |
| | `test_histogram_percentiles` - record 100 values, verify p50 and p95 are in expected range |
| | `test_get_all_metrics` - add mixed metrics, verify get_all returns counters, gauges, histograms |
| | `test_health_reports_metric_count` - add metrics, verify health() reports correct counts |
| | `test_reset_clears_all` - add metrics, call reset(), verify all getters return zero/empty |
| | `test_null_metrics_no_ops` - NullMetrics increment/gauge/histogram do not raise, getters return defaults |

## Acceptance Criteria

- [ ] `MetricsCollector` ABC defined with increment, gauge, histogram, get, health, reset
- [ ] `InMemoryMetrics` stores all metrics in thread-safe dicts
- [ ] Histogram percentile calculation (p50, p95, p99) is correct
- [ ] `NullMetrics` is a no-op implementation that never raises
- [ ] `create_metrics_collector()` factory returns configured collector
- [ ] `get_all_metrics()` returns structured dict with all metric types
- [ ] All 8 tests pass: `pytest tests/unit/test_metrics_collector.py -v`
- [ ] `ruff check .` clean
- [ ] `lint-imports` clean (infrastructure/ imports only from shared/)
- [ ] `infrastructure/monitoring/AGENTS.md` updated

## Upstream Dependencies

T-033 (storage-adapter-mvp) — storage pattern established for infrastructure modules.

## Downstream Unblocks

None (leaf task in the Infrastructure cluster for this phase).

## Estimated Scope

- New code: ~200 LOC (ABC ~45, InMemoryMetrics ~100, NullMetrics ~30, factory ~15, percentiles ~10)
- Modified code: ~5 lines in __init__.py
- Tests: ~120 LOC
- Risk: Low. Self-contained infrastructure module. Thread safety via RLock is well-understood.
