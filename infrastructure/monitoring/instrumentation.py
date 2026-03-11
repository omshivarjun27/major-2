"""Metrics instrumentation for Voice & Vision Assistant components.

Provides decorators, context managers, and helper functions for adding
Prometheus metrics to existing components with minimal code intrusion.

Task: T-095 - Custom Metrics Instrumentation
"""

from __future__ import annotations

import asyncio
import functools
import logging
import time
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar

from infrastructure.monitoring.prometheus_metrics import (
    CircuitBreakerState,
    get_metrics,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline Stage Enum
# ─────────────────────────────────────────────────────────────────────────────

class VisionStage(Enum):
    """Vision pipeline stages for instrumentation."""
    OBJECT_DETECTION = "object_detection"
    SEGMENTATION = "segmentation"
    DEPTH_ESTIMATION = "depth_estimation"
    SPATIAL_FUSION = "spatial_fusion"
    NAVIGATION_FORMAT = "navigation_format"
    SCENE_DESCRIPTION = "scene_description"


class RAGStage(Enum):
    """RAG pipeline stages for instrumentation."""
    EMBEDDING = "embedding"
    SEARCH = "search"
    RETRIEVAL = "retrieval"
    REASONING = "reasoning"
    GENERATION = "generation"


class SpeechStage(Enum):
    """Speech pipeline stages for instrumentation."""
    STT = "stt"
    TTS = "tts"
    VOICE_ACTIVITY = "voice_activity"
    AUDIO_PROCESSING = "audio_processing"


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline Metrics Context Manager
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PipelineStageMetrics:
    """Metrics collected for a pipeline stage execution."""
    stage: str
    pipeline: str
    start_time: float = field(default_factory=time.perf_counter)
    end_time: Optional[float] = None
    success: bool = True
    error_type: Optional[str] = None

    @property
    def duration_seconds(self) -> float:
        """Get duration in seconds."""
        if self.end_time is None:
            return time.perf_counter() - self.start_time
        return self.end_time - self.start_time

    def complete(self, success: bool = True, error_type: Optional[str] = None) -> None:
        """Mark stage as complete."""
        self.end_time = time.perf_counter()
        self.success = success
        self.error_type = error_type


@contextmanager
def timed_stage(pipeline: str, stage: str, record_errors: bool = True):
    """Context manager for timing pipeline stages.

    Automatically records latency and errors to Prometheus metrics.

    Args:
        pipeline: Pipeline name (vision, rag, speech)
        stage: Stage name within the pipeline
        record_errors: Whether to record errors on exception

    Yields:
        PipelineStageMetrics for additional metadata

    Example:
        with timed_stage("vision", "object_detection") as metrics:
            detections = detector.detect(frame)
        # Latency automatically recorded
    """
    metrics_obj = PipelineStageMetrics(stage=stage, pipeline=pipeline)

    try:
        yield metrics_obj
        metrics_obj.complete(success=True)
    except Exception as e:
        metrics_obj.complete(success=False, error_type=type(e).__name__)
        if record_errors:
            try:
                get_metrics().record_error(f"{pipeline}_{stage}", type(e).__name__)
            except Exception:
                pass  # Don't fail on metrics errors
        raise
    finally:
        try:
            prom = get_metrics()
            # Record to model inference histogram with pipeline_stage label
            prom.record_inference(f"{pipeline}_{stage}", metrics_obj.duration_seconds)
        except Exception:
            pass


@asynccontextmanager
async def async_timed_stage(pipeline: str, stage: str, record_errors: bool = True):
    """Async context manager for timing pipeline stages.

    Same as timed_stage but for async code.
    """
    metrics_obj = PipelineStageMetrics(stage=stage, pipeline=pipeline)

    try:
        yield metrics_obj
        metrics_obj.complete(success=True)
    except Exception as e:
        metrics_obj.complete(success=False, error_type=type(e).__name__)
        if record_errors:
            try:
                get_metrics().record_error(f"{pipeline}_{stage}", type(e).__name__)
            except Exception:
                pass
        raise
    finally:
        try:
            prom = get_metrics()
            prom.record_inference(f"{pipeline}_{stage}", metrics_obj.duration_seconds)
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# Stage Timing Decorators
# ─────────────────────────────────────────────────────────────────────────────

def instrument_stage(pipeline: str, stage: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to instrument a function as a pipeline stage.

    Args:
        pipeline: Pipeline name
        stage: Stage name

    Returns:
        Decorated function

    Example:
        @instrument_stage("vision", "object_detection")
        async def detect_objects(frame):
            return detector.detect(frame)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            with timed_stage(pipeline, stage):
                return func(*args, **kwargs)

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            async with async_timed_stage(pipeline, stage):
                return await func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper

    return decorator


def instrument_vision(stage: VisionStage) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for vision pipeline stages.

    Example:
        @instrument_vision(VisionStage.OBJECT_DETECTION)
        async def detect(self, frame):
            ...
    """
    return instrument_stage("vision", stage.value)


def instrument_rag(stage: RAGStage) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for RAG pipeline stages.

    Example:
        @instrument_rag(RAGStage.EMBEDDING)
        async def embed(self, text):
            ...
    """
    return instrument_stage("rag", stage.value)


def instrument_speech(stage: SpeechStage) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for speech pipeline stages.

    Example:
        @instrument_speech(SpeechStage.STT)
        async def transcribe(self, audio):
            ...
    """
    return instrument_stage("speech", stage.value)


# ─────────────────────────────────────────────────────────────────────────────
# FAISS Index Metrics
# ─────────────────────────────────────────────────────────────────────────────

class FAISSMetricsTracker:
    """Tracker for FAISS index metrics.

    Provides methods to record FAISS operations:
    - Query count and latency
    - Index vector count
    - Index operations (add, remove)
    """

    def __init__(self, index_name: str = "default"):
        """Initialize FAISS metrics tracker.

        Args:
            index_name: Name to identify the index in metrics
        """
        self._index_name = index_name
        self._query_count = 0
        self._vector_count = 0

    def record_query(self, latency_seconds: float, result_count: int = 0) -> None:
        """Record a FAISS query operation.

        Args:
            latency_seconds: Query latency in seconds
            result_count: Number of results returned
        """
        self._query_count += 1
        try:
            prom = get_metrics()
            prom.record_faiss_query(latency_seconds)
        except Exception:
            pass

    def set_vector_count(self, count: int) -> None:
        """Set the current vector count in the index.

        Args:
            count: Number of vectors in the index
        """
        self._vector_count = count
        try:
            prom = get_metrics()
            prom.set_queue_size(f"faiss_{self._index_name}_vectors", count)
        except Exception:
            pass

    @contextmanager
    def timed_query(self):
        """Context manager for timing FAISS queries.

        Yields:
            dict to store query metadata

        Example:
            with tracker.timed_query() as query:
                results = index.search(vectors, k=10)
                query['result_count'] = len(results)
        """
        query_data: Dict[str, Any] = {"result_count": 0}
        start = time.perf_counter()

        try:
            yield query_data
        finally:
            latency = time.perf_counter() - start
            self.record_query(latency, query_data.get("result_count", 0))


# ─────────────────────────────────────────────────────────────────────────────
# Circuit Breaker Metrics
# ─────────────────────────────────────────────────────────────────────────────

class CircuitBreakerMetricsTracker:
    """Tracker for circuit breaker metrics.

    Records state transitions, trips, and recovery times.
    """

    def __init__(self, service_name: str):
        """Initialize circuit breaker tracker.

        Args:
            service_name: Name of the service being protected
        """
        self._service_name = service_name
        self._current_state = CircuitBreakerState.CLOSED
        self._last_state_change = time.perf_counter()
        self._trip_count = 0

    def record_state_change(self, new_state: CircuitBreakerState) -> None:
        """Record a state transition.

        Args:
            new_state: New circuit breaker state
        """
        old_state = self._current_state
        self._current_state = new_state

        # Record time in previous state
        state_duration = time.perf_counter() - self._last_state_change
        self._last_state_change = time.perf_counter()

        try:
            prom = get_metrics()
            prom.set_circuit_breaker_state(self._service_name, new_state)

            # Record trip event if transitioning to OPEN
            if new_state == CircuitBreakerState.OPEN and old_state != CircuitBreakerState.OPEN:
                self._trip_count += 1
                prom.record_circuit_breaker_trip(self._service_name)

            logger.debug(
                "Circuit breaker %s: %s -> %s (was in %s for %.2fs)",
                self._service_name,
                old_state.value,
                new_state.value,
                old_state.value,
                state_duration,
            )
        except Exception:
            pass

    def open(self) -> None:
        """Transition to OPEN state."""
        self.record_state_change(CircuitBreakerState.OPEN)

    def half_open(self) -> None:
        """Transition to HALF_OPEN state."""
        self.record_state_change(CircuitBreakerState.HALF_OPEN)

    def close(self) -> None:
        """Transition to CLOSED state."""
        self.record_state_change(CircuitBreakerState.CLOSED)

    @property
    def state(self) -> CircuitBreakerState:
        """Get current state."""
        return self._current_state

    @property
    def trip_count(self) -> int:
        """Get total trip count."""
        return self._trip_count


# ─────────────────────────────────────────────────────────────────────────────
# WebRTC Session Metrics
# ─────────────────────────────────────────────────────────────────────────────

class WebRTCMetricsTracker:
    """Tracker for WebRTC agent metrics.

    Records session count, reconnections, and connection states.
    """

    def __init__(self):
        """Initialize WebRTC metrics tracker."""
        self._active_sessions = 0
        self._total_sessions = 0
        self._reconnection_count = 0

    def session_started(self, session_id: Optional[str] = None) -> None:
        """Record a new session starting.

        Args:
            session_id: Optional session identifier for logging
        """
        self._active_sessions += 1
        self._total_sessions += 1

        try:
            prom = get_metrics()
            prom.inc_connections("webrtc")
            logger.debug("WebRTC session started: %s (active: %d)", session_id, self._active_sessions)
        except Exception:
            pass

    def session_ended(self, session_id: Optional[str] = None) -> None:
        """Record a session ending.

        Args:
            session_id: Optional session identifier for logging
        """
        self._active_sessions = max(0, self._active_sessions - 1)

        try:
            prom = get_metrics()
            prom.dec_connections("webrtc")
            logger.debug("WebRTC session ended: %s (active: %d)", session_id, self._active_sessions)
        except Exception:
            pass

    def record_reconnection(self, session_id: Optional[str] = None) -> None:
        """Record a reconnection event.

        Args:
            session_id: Optional session identifier for logging
        """
        self._reconnection_count += 1

        try:
            prom = get_metrics()
            prom.record_error("webrtc", "reconnection")
            logger.info("WebRTC reconnection: %s (total: %d)", session_id, self._reconnection_count)
        except Exception:
            pass

    @property
    def active_sessions(self) -> int:
        """Get current active session count."""
        return self._active_sessions

    @property
    def total_sessions(self) -> int:
        """Get total session count since startup."""
        return self._total_sessions

    @property
    def reconnection_count(self) -> int:
        """Get total reconnection count."""
        return self._reconnection_count


# ─────────────────────────────────────────────────────────────────────────────
# Speech Pipeline Instrumentation
# ─────────────────────────────────────────────────────────────────────────────

def record_stt_latency(latency_seconds: float) -> None:
    """Record speech-to-text latency.

    Args:
        latency_seconds: STT processing time in seconds
    """
    try:
        get_metrics().record_stt_latency(latency_seconds)
    except Exception:
        pass


def record_tts_latency(latency_seconds: float) -> None:
    """Record text-to-speech latency.

    Args:
        latency_seconds: TTS processing time in seconds
    """
    try:
        get_metrics().record_tts_latency(latency_seconds)
    except Exception:
        pass


def record_llm_latency(latency_seconds: float) -> None:
    """Record LLM inference latency.

    Args:
        latency_seconds: LLM processing time in seconds
    """
    try:
        get_metrics().record_llm_latency(latency_seconds)
    except Exception:
        pass


@contextmanager
def timed_stt():
    """Context manager for timing STT operations.

    Example:
        with timed_stt():
            transcript = await stt.transcribe(audio)
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        record_stt_latency(time.perf_counter() - start)


@contextmanager
def timed_tts():
    """Context manager for timing TTS operations.

    Example:
        with timed_tts():
            audio = await tts.synthesize(text)
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        record_tts_latency(time.perf_counter() - start)


@contextmanager
def timed_llm():
    """Context manager for timing LLM operations.

    Example:
        with timed_llm():
            response = await llm.generate(prompt)
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        record_llm_latency(time.perf_counter() - start)


@asynccontextmanager
async def async_timed_stt():
    """Async context manager for timing STT operations."""
    start = time.perf_counter()
    try:
        yield
    finally:
        record_stt_latency(time.perf_counter() - start)


@asynccontextmanager
async def async_timed_tts():
    """Async context manager for timing TTS operations."""
    start = time.perf_counter()
    try:
        yield
    finally:
        record_tts_latency(time.perf_counter() - start)


@asynccontextmanager
async def async_timed_llm():
    """Async context manager for timing LLM operations."""
    start = time.perf_counter()
    try:
        yield
    finally:
        record_llm_latency(time.perf_counter() - start)


# ─────────────────────────────────────────────────────────────────────────────
# Resource Tracking
# ─────────────────────────────────────────────────────────────────────────────

def update_resource_metrics() -> None:
    """Update resource usage metrics (CPU, RAM, VRAM).

    Call periodically (e.g., every 10 seconds) to update resource gauges.
    Safe to call - handles import errors gracefully.
    """
    try:
        import psutil
        prom = get_metrics()

        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=None)
        prom.set_cpu_usage(cpu_percent)

        # RAM usage
        memory = psutil.virtual_memory()
        prom.set_ram_usage(memory.used)

    except ImportError:
        logger.debug("psutil not available for resource metrics")
    except Exception as e:
        logger.debug("Failed to update resource metrics: %s", e)

    # VRAM usage (NVIDIA GPUs)
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,nounits,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            vram_mb = int(result.stdout.strip().split("\n")[0])
            get_metrics().set_vram_usage(vram_mb * 1024 * 1024)  # Convert to bytes
    except Exception:
        pass  # VRAM metrics are optional


# ─────────────────────────────────────────────────────────────────────────────
# Global Trackers (Singleton Pattern)
# ─────────────────────────────────────────────────────────────────────────────

_webrtc_tracker: Optional[WebRTCMetricsTracker] = None
_faiss_trackers: Dict[str, FAISSMetricsTracker] = {}
_circuit_breaker_trackers: Dict[str, CircuitBreakerMetricsTracker] = {}


def get_webrtc_tracker() -> WebRTCMetricsTracker:
    """Get the global WebRTC metrics tracker."""
    global _webrtc_tracker
    if _webrtc_tracker is None:
        _webrtc_tracker = WebRTCMetricsTracker()
    return _webrtc_tracker


def get_faiss_tracker(index_name: str = "default") -> FAISSMetricsTracker:
    """Get a FAISS metrics tracker for the specified index.

    Args:
        index_name: Name of the FAISS index

    Returns:
        FAISSMetricsTracker for the index
    """
    if index_name not in _faiss_trackers:
        _faiss_trackers[index_name] = FAISSMetricsTracker(index_name)
    return _faiss_trackers[index_name]


def get_circuit_breaker_tracker(service_name: str) -> CircuitBreakerMetricsTracker:
    """Get a circuit breaker tracker for the specified service.

    Args:
        service_name: Name of the service

    Returns:
        CircuitBreakerMetricsTracker for the service
    """
    if service_name not in _circuit_breaker_trackers:
        _circuit_breaker_trackers[service_name] = CircuitBreakerMetricsTracker(service_name)
    return _circuit_breaker_trackers[service_name]


def reset_trackers() -> None:
    """Reset all global trackers (for testing)."""
    global _webrtc_tracker, _faiss_trackers, _circuit_breaker_trackers
    _webrtc_tracker = None
    _faiss_trackers = {}
    _circuit_breaker_trackers = {}
