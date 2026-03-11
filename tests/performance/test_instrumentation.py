"""P4: Pipeline Instrumentation Tests (T-088).

Tests for timing decorators, structured logging, and request tracing.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar

import pytest

# Project imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Instrumentation Models
# ---------------------------------------------------------------------------

@dataclass
class TimingRecord:
    """Record of a timed operation."""
    name: str
    start_time: float
    end_time: float
    duration_ms: float
    success: bool
    error: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": round(self.duration_ms, 3),
            "success": self.success,
            "error": self.error,
            "context": self.context,
        }


@dataclass
class Span:
    """A tracing span for request tracking."""
    span_id: str
    trace_id: str
    parent_id: Optional[str]
    name: str
    start_time: float
    end_time: float = 0.0
    tags: Dict[str, Any] = field(default_factory=dict)
    children: List["Span"] = field(default_factory=list)

    @property
    def duration_ms(self) -> float:
        if self.end_time == 0.0:
            return 0.0
        return (self.end_time - self.start_time) * 1000

    def finish(self):
        self.end_time = time.time()

    def add_child(self, name: str) -> "Span":
        child = Span(
            span_id=str(uuid.uuid4())[:8],
            trace_id=self.trace_id,
            parent_id=self.span_id,
            name=name,
            start_time=time.time(),
        )
        self.children.append(child)
        return child

    def to_dict(self) -> Dict[str, Any]:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "duration_ms": round(self.duration_ms, 3),
            "tags": self.tags,
            "children": [c.to_dict() for c in self.children],
        }


@dataclass
class TraceContext:
    """Context for distributed tracing."""
    trace_id: str
    current_span: Optional[Span] = None

    @classmethod
    def create(cls) -> "TraceContext":
        return cls(trace_id=str(uuid.uuid4())[:16])

    def start_span(self, name: str) -> Span:
        span = Span(
            span_id=str(uuid.uuid4())[:8],
            trace_id=self.trace_id,
            parent_id=self.current_span.span_id if self.current_span else None,
            name=name,
            start_time=time.time(),
        )
        if self.current_span:
            self.current_span.children.append(span)
        self.current_span = span
        return span


# ---------------------------------------------------------------------------
# Instrumentation Utilities
# ---------------------------------------------------------------------------

class InstrumentationCollector:
    """Collects instrumentation data."""

    def __init__(self):
        self._timings: List[TimingRecord] = []
        self._traces: Dict[str, Span] = {}

    def record_timing(self, record: TimingRecord):
        self._timings.append(record)

    def record_span(self, span: Span):
        self._traces[span.trace_id] = span

    def get_timings(self) -> List[TimingRecord]:
        return self._timings

    def get_traces(self) -> Dict[str, Span]:
        return self._traces

    def clear(self):
        self._timings = []
        self._traces = {}

    def get_summary(self) -> Dict[str, Any]:
        if not self._timings:
            return {"count": 0}

        durations = [t.duration_ms for t in self._timings]
        return {
            "count": len(self._timings),
            "total_ms": round(sum(durations), 3),
            "avg_ms": round(sum(durations) / len(durations), 3),
            "min_ms": round(min(durations), 3),
            "max_ms": round(max(durations), 3),
            "success_rate": sum(1 for t in self._timings if t.success) / len(self._timings),
        }


# Global collector for testing
_collector = InstrumentationCollector()


def get_collector() -> InstrumentationCollector:
    return _collector


# ---------------------------------------------------------------------------
# Timing Decorators
# ---------------------------------------------------------------------------

F = TypeVar("F", bound=Callable[..., Any])


def timed(stage_name: str, collector: Optional[InstrumentationCollector] = None) -> Callable[[F], F]:
    """Decorator for timing synchronous functions."""
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            coll = collector or get_collector()
            start = time.perf_counter()
            success = True
            error = None
            try:
                return func(*args, **kwargs)
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                end = time.perf_counter()
                record = TimingRecord(
                    name=stage_name,
                    start_time=start,
                    end_time=end,
                    duration_ms=(end - start) * 1000,
                    success=success,
                    error=error,
                )
                coll.record_timing(record)
        return wrapper  # type: ignore
    return decorator


def async_timed(stage_name: str, collector: Optional[InstrumentationCollector] = None) -> Callable[[F], F]:
    """Decorator for timing asynchronous functions."""
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            coll = collector or get_collector()
            start = time.perf_counter()
            success = True
            error = None
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                end = time.perf_counter()
                record = TimingRecord(
                    name=stage_name,
                    start_time=start,
                    end_time=end,
                    duration_ms=(end - start) * 1000,
                    success=success,
                    error=error,
                )
                coll.record_timing(record)
        return wrapper  # type: ignore
    return decorator


@contextmanager
def timed_block(name: str, collector: Optional[InstrumentationCollector] = None):
    """Context manager for timing code blocks."""
    coll = collector or get_collector()
    start = time.perf_counter()
    success = True
    error = None
    try:
        yield
    except Exception as e:
        success = False
        error = str(e)
        raise
    finally:
        end = time.perf_counter()
        record = TimingRecord(
            name=name,
            start_time=start,
            end_time=end,
            duration_ms=(end - start) * 1000,
            success=success,
            error=error,
        )
        coll.record_timing(record)


# ---------------------------------------------------------------------------
# Test Classes
# ---------------------------------------------------------------------------

class TestTimingRecord:
    """Tests for timing records."""

    def test_record_creation(self):
        """Test timing record creation."""
        record = TimingRecord(
            name="test_operation",
            start_time=1000.0,
            end_time=1000.05,
            duration_ms=50.0,
            success=True,
        )
        assert record.name == "test_operation"
        assert record.duration_ms == 50.0
        assert record.success is True

    def test_record_serialization(self):
        """Test timing record serialization."""
        record = TimingRecord(
            name="test",
            start_time=1000.0,
            end_time=1000.05,
            duration_ms=50.123,
            success=True,
            context={"frame_id": "abc123"},
        )
        d = record.to_dict()
        assert d["name"] == "test"
        assert d["duration_ms"] == 50.123
        assert d["context"]["frame_id"] == "abc123"


class TestSpan:
    """Tests for tracing spans."""

    def test_span_creation(self):
        """Test span creation."""
        span = Span(
            span_id="span1",
            trace_id="trace1",
            parent_id=None,
            name="root",
            start_time=time.time(),
        )
        assert span.span_id == "span1"
        assert span.parent_id is None

    def test_span_duration(self):
        """Test span duration calculation."""
        span = Span(
            span_id="span1",
            trace_id="trace1",
            parent_id=None,
            name="root",
            start_time=time.time(),
        )
        time.sleep(0.05)
        span.finish()
        assert span.duration_ms >= 40.0  # Allow some variance

    def test_child_span(self):
        """Test adding child spans."""
        parent = Span(
            span_id="parent",
            trace_id="trace1",
            parent_id=None,
            name="root",
            start_time=time.time(),
        )
        child = parent.add_child("child_operation")

        assert child.parent_id == "parent"
        assert child.trace_id == "trace1"
        assert len(parent.children) == 1

    def test_span_serialization(self):
        """Test span serialization."""
        span = Span(
            span_id="span1",
            trace_id="trace1",
            parent_id=None,
            name="root",
            start_time=time.time(),
            tags={"component": "vision"},
        )
        span.finish()
        d = span.to_dict()
        assert d["span_id"] == "span1"
        assert d["tags"]["component"] == "vision"
        assert "children" in d


class TestTraceContext:
    """Tests for trace context."""

    def test_context_creation(self):
        """Test trace context creation."""
        ctx = TraceContext.create()
        assert ctx.trace_id is not None
        assert len(ctx.trace_id) == 16

    def test_start_span(self):
        """Test starting spans in context."""
        ctx = TraceContext.create()
        span = ctx.start_span("operation1")

        assert span.trace_id == ctx.trace_id
        assert ctx.current_span == span

    def test_nested_spans(self):
        """Test nested span hierarchy."""
        ctx = TraceContext.create()
        parent = ctx.start_span("parent")
        child = ctx.start_span("child")

        assert child.parent_id == parent.span_id
        assert len(parent.children) == 1


class TestInstrumentationCollector:
    """Tests for instrumentation collector."""

    def test_record_timing(self):
        """Test recording timings."""
        collector = InstrumentationCollector()
        record = TimingRecord(
            name="test",
            start_time=1000.0,
            end_time=1000.05,
            duration_ms=50.0,
            success=True,
        )
        collector.record_timing(record)

        assert len(collector.get_timings()) == 1

    def test_summary_calculation(self):
        """Test summary calculation."""
        collector = InstrumentationCollector()
        for i in range(5):
            collector.record_timing(TimingRecord(
                name="test",
                start_time=0,
                end_time=0,
                duration_ms=10.0 * (i + 1),
                success=True,
            ))

        summary = collector.get_summary()
        assert summary["count"] == 5
        assert summary["avg_ms"] == 30.0  # (10+20+30+40+50)/5
        assert summary["min_ms"] == 10.0
        assert summary["max_ms"] == 50.0

    def test_clear(self):
        """Test clearing collector."""
        collector = InstrumentationCollector()
        collector.record_timing(TimingRecord("test", 0, 0, 10.0, True))
        collector.clear()

        assert len(collector.get_timings()) == 0


class TestTimedDecorator:
    """Tests for timing decorators."""

    def test_sync_timing(self):
        """Test synchronous function timing."""
        collector = InstrumentationCollector()

        @timed("sync_op", collector)
        def slow_function():
            time.sleep(0.05)
            return 42

        result = slow_function()

        assert result == 42
        timings = collector.get_timings()
        assert len(timings) == 1
        assert timings[0].name == "sync_op"
        assert timings[0].duration_ms >= 40.0
        assert timings[0].success is True

    async def test_async_timing(self):
        """Test asynchronous function timing."""
        collector = InstrumentationCollector()

        @async_timed("async_op", collector)
        async def async_function():
            await asyncio.sleep(0.05)
            return 42

        result = await async_function()

        assert result == 42
        timings = collector.get_timings()
        assert len(timings) == 1
        assert timings[0].name == "async_op"
        assert timings[0].duration_ms >= 40.0

    def test_timing_on_error(self):
        """Test timing records errors."""
        collector = InstrumentationCollector()

        @timed("error_op", collector)
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_function()

        timings = collector.get_timings()
        assert len(timings) == 1
        assert timings[0].success is False
        assert "Test error" in timings[0].error


class TestTimedBlock:
    """Tests for timed code blocks."""

    def test_timed_block_success(self):
        """Test timing a code block."""
        collector = InstrumentationCollector()

        with timed_block("block_op", collector):
            time.sleep(0.05)

        timings = collector.get_timings()
        assert len(timings) == 1
        assert timings[0].name == "block_op"
        assert timings[0].duration_ms >= 40.0

    def test_timed_block_error(self):
        """Test timed block with error."""
        collector = InstrumentationCollector()

        with pytest.raises(ValueError):
            with timed_block("error_block", collector):
                raise ValueError("Block error")

        timings = collector.get_timings()
        assert timings[0].success is False


class TestInstrumentationOverhead:
    """Tests for instrumentation overhead."""

    def test_decorator_overhead(self):
        """Test decorator adds minimal overhead."""
        collector = InstrumentationCollector()

        @timed("fast_op", collector)
        def fast_function():
            return 1 + 1

        # Warm up
        fast_function()
        collector.clear()

        # Measure
        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            fast_function()
        elapsed_ms = (time.perf_counter() - start) * 1000

        overhead_per_call = elapsed_ms / iterations
        # Should be < 1ms overhead per call
        assert overhead_per_call < 1.0

    async def test_async_decorator_overhead(self):
        """Test async decorator adds minimal overhead."""
        collector = InstrumentationCollector()

        @async_timed("fast_async", collector)
        async def fast_async():
            return 1 + 1

        # Warm up
        await fast_async()
        collector.clear()

        # Measure
        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            await fast_async()
        elapsed_ms = (time.perf_counter() - start) * 1000

        overhead_per_call = elapsed_ms / iterations
        assert overhead_per_call < 1.0


class TestStructuredLogging:
    """Tests for structured logging patterns."""

    def test_timing_record_as_json(self):
        """Test timing record produces valid JSON structure."""
        record = TimingRecord(
            name="test_op",
            start_time=1000.0,
            end_time=1000.05,
            duration_ms=50.0,
            success=True,
            context={"frame_id": "abc", "session_id": "xyz"},
        )
        d = record.to_dict()

        # Should be JSON-serializable
        import json
        json_str = json.dumps(d)
        assert '"name": "test_op"' in json_str
        assert '"frame_id": "abc"' in json_str

    def test_span_as_json(self):
        """Test span produces valid JSON structure."""
        span = Span(
            span_id="s1",
            trace_id="t1",
            parent_id=None,
            name="root",
            start_time=time.time(),
            tags={"component": "vision", "frame_id": "f1"},
        )
        span.finish()

        import json
        json_str = json.dumps(span.to_dict())
        assert '"span_id": "s1"' in json_str


class TestRequestTracing:
    """Tests for request tracing."""

    def test_unique_trace_ids(self):
        """Test trace IDs are unique."""
        traces = [TraceContext.create().trace_id for _ in range(100)]
        assert len(set(traces)) == 100

    def test_span_hierarchy(self):
        """Test span parent-child hierarchy."""
        ctx = TraceContext.create()

        root = ctx.start_span("request")
        stt = root.add_child("stt")
        stt.finish()

        llm = root.add_child("llm")
        llm.finish()

        tts = root.add_child("tts")
        tts.finish()

        root.finish()

        # Check hierarchy
        assert len(root.children) == 3
        assert all(c.parent_id == root.span_id for c in root.children)
        assert all(c.trace_id == ctx.trace_id for c in root.children)

    def test_trace_serialization(self):
        """Test full trace serialization."""
        ctx = TraceContext.create()
        root = ctx.start_span("request")
        child = root.add_child("process")
        child.finish()
        root.finish()

        d = root.to_dict()
        assert len(d["children"]) == 1
        assert d["children"][0]["parent_id"] == root.span_id
