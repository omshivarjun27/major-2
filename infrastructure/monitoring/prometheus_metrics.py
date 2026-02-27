"""Prometheus metrics collection infrastructure for Voice & Vision Assistant.

Provides standardized metrics collection compatible with Prometheus scraping.
Exposes metrics at /metrics endpoint for observability stack integration.

Task: T-091 - Prometheus Metrics Foundation
"""

from __future__ import annotations

import logging
import threading
from enum import Enum
from typing import Callable, Optional

try:
    from prometheus_client import (
        Counter,
        Gauge,
        Histogram,
        Info,
        CollectorRegistry,
        generate_latest,
        CONTENT_TYPE_LATEST,
        REGISTRY,
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

from infrastructure.monitoring.collector import MetricsCollector, MetricsSnapshot, HistogramStats

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker state values for metrics."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class ServiceName(Enum):
    """Service names for circuit breaker metrics."""
    DEEPGRAM = "deepgram"
    ELEVENLABS = "elevenlabs"
    OLLAMA = "ollama"
    DUCKDUCKGO = "duckduckgo"
    LIVEKIT = "livekit"
    TAVUS = "tavus"


class ModelName(Enum):
    """Model names for inference metrics."""
    YOLO = "yolo"
    MIDAS = "midas"
    LLM = "llm"
    EMBEDDINGS = "embeddings"


# Default histogram buckets for latency measurements
LATENCY_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
INFERENCE_BUCKETS = (0.01, 0.025, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0, 5.0, 10.0)


class PrometheusMetrics(MetricsCollector):
    """Prometheus-compatible metrics collector.
    
    Provides metrics in Prometheus format for scraping by Prometheus server.
    Thread-safe implementation using prometheus_client library.
    
    Metrics exposed:
    - request_count: Total requests by endpoint and status
    - request_latency_seconds: Request latency histogram
    - active_connections: Current active WebRTC/API connections
    - circuit_breaker_state: Circuit breaker state per service
    - vram_usage_bytes: Current VRAM usage
    - model_inference_seconds: Model inference latency per model
    """
    
    def __init__(
        self,
        registry: Optional[CollectorRegistry] = None,
        namespace: str = "voice_vision",
        subsystem: str = "",
    ) -> None:
        """Initialize Prometheus metrics.
        
        Args:
            registry: Custom registry or None to use default REGISTRY
            namespace: Metric namespace prefix (default: voice_vision)
            subsystem: Metric subsystem prefix (default: empty)
        """
        if not PROMETHEUS_AVAILABLE:
            raise RuntimeError("prometheus_client library not installed")
        
        self._registry = registry or REGISTRY
        self._namespace = namespace
        self._subsystem = subsystem
        self._lock = threading.RLock()
        
        # Initialize all metrics
        self._init_counters()
        self._init_gauges()
        self._init_histograms()
        self._init_info()
        
        logger.info("Prometheus metrics initialized with namespace=%s", namespace)
    
    def _init_counters(self) -> None:
        """Initialize counter metrics."""
        self._request_count = Counter(
            "request_count",
            "Total number of requests",
            ["endpoint", "method", "status"],
            namespace=self._namespace,
            subsystem=self._subsystem,
            registry=self._registry,
        )
        
        self._error_count = Counter(
            "error_count",
            "Total number of errors",
            ["component", "error_type"],
            namespace=self._namespace,
            subsystem=self._subsystem,
            registry=self._registry,
        )
        
        self._circuit_breaker_trips = Counter(
            "circuit_breaker_trips_total",
            "Total circuit breaker trip events",
            ["service"],
            namespace=self._namespace,
            subsystem=self._subsystem,
            registry=self._registry,
        )
    
    def _init_gauges(self) -> None:
        """Initialize gauge metrics."""
        self._active_connections = Gauge(
            "active_connections",
            "Current number of active connections",
            ["connection_type"],
            namespace=self._namespace,
            subsystem=self._subsystem,
            registry=self._registry,
        )
        
        self._vram_usage_bytes = Gauge(
            "vram_usage_bytes",
            "Current VRAM usage in bytes",
            namespace=self._namespace,
            subsystem=self._subsystem,
            registry=self._registry,
        )
        
        self._ram_usage_bytes = Gauge(
            "ram_usage_bytes",
            "Current RAM usage in bytes",
            namespace=self._namespace,
            subsystem=self._subsystem,
            registry=self._registry,
        )
        
        self._cpu_usage_percent = Gauge(
            "cpu_usage_percent",
            "Current CPU usage percentage",
            namespace=self._namespace,
            subsystem=self._subsystem,
            registry=self._registry,
        )
        
        # Circuit breaker state gauge (0=closed, 1=open, 2=half_open)
        self._circuit_breaker_state = Gauge(
            "circuit_breaker_state",
            "Circuit breaker state (0=closed, 1=open, 2=half_open)",
            ["service"],
            namespace=self._namespace,
            subsystem=self._subsystem,
            registry=self._registry,
        )
        
        self._model_loaded = Gauge(
            "model_loaded",
            "Whether a model is currently loaded (0=no, 1=yes)",
            ["model"],
            namespace=self._namespace,
            subsystem=self._subsystem,
            registry=self._registry,
        )
        
        self._queue_size = Gauge(
            "queue_size",
            "Current queue size",
            ["queue_name"],
            namespace=self._namespace,
            subsystem=self._subsystem,
            registry=self._registry,
        )

        # Health and degradation metrics (T-103)
        self._service_health = Gauge(
            "service_health",
            "Service health status (0=unhealthy, 1=healthy, 2=degraded)",
            ["service", "status"],
            namespace=self._namespace,
            subsystem=self._subsystem,
            registry=self._registry,
        )
        
        self._degradation_level = Gauge(
            "degradation_level",
            "Current degradation level (0=full, 1=partial, 2=minimal, 3=offline)",
            namespace=self._namespace,
            subsystem=self._subsystem,
            registry=self._registry,
        )
        
        self._degradation_transitions = Counter(
            "degradation_transitions_total",
            "Total degradation level transitions",
            namespace=self._namespace,
            subsystem=self._subsystem,
            registry=self._registry,
        )
        
        self._service_downtime = Counter(
            "service_downtime_seconds_total",
            "Total service downtime in seconds",
            ["service"],
            namespace=self._namespace,
            subsystem=self._subsystem,
            registry=self._registry,
        )
        
        self._feature_enabled = Gauge(
            "feature_enabled",
            "Whether a feature is currently enabled (0=disabled, 1=enabled)",
            ["feature"],
            namespace=self._namespace,
            subsystem=self._subsystem,
            registry=self._registry,
        )
        
        self._speech_mode = Gauge(
            "speech_mode",
            "Speech processing mode (0=local, 1=cloud)",
            ["type"],
            namespace=self._namespace,
            subsystem=self._subsystem,
            registry=self._registry,
        )
    
    def _init_histograms(self) -> None:
        """Initialize histogram metrics."""
        self._request_latency = Histogram(
            "request_latency_seconds",
            "Request latency in seconds",
            ["endpoint", "method"],
            namespace=self._namespace,
            subsystem=self._subsystem,
            registry=self._registry,
            buckets=LATENCY_BUCKETS,
        )
        
        self._model_inference_seconds = Histogram(
            "model_inference_seconds",
            "Model inference latency in seconds",
            ["model"],
            namespace=self._namespace,
            subsystem=self._subsystem,
            registry=self._registry,
            buckets=INFERENCE_BUCKETS,
        )
        
        self._stt_latency_seconds = Histogram(
            "stt_latency_seconds",
            "Speech-to-text latency in seconds",
            namespace=self._namespace,
            subsystem=self._subsystem,
            registry=self._registry,
            buckets=LATENCY_BUCKETS,
        )
        
        self._tts_latency_seconds = Histogram(
            "tts_latency_seconds",
            "Text-to-speech latency in seconds",
            namespace=self._namespace,
            subsystem=self._subsystem,
            registry=self._registry,
            buckets=LATENCY_BUCKETS,
        )
        
        self._llm_latency_seconds = Histogram(
            "llm_latency_seconds",
            "LLM inference latency in seconds",
            namespace=self._namespace,
            subsystem=self._subsystem,
            registry=self._registry,
            buckets=INFERENCE_BUCKETS,
        )
        
        self._faiss_query_seconds = Histogram(
            "faiss_query_seconds",
            "FAISS query latency in seconds",
            namespace=self._namespace,
            subsystem=self._subsystem,
            registry=self._registry,
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
        )
    
    def _init_info(self) -> None:
        """Initialize info metrics."""
        self._build_info = Info(
            "build",
            "Build information",
            namespace=self._namespace,
            subsystem=self._subsystem,
            registry=self._registry,
        )
    
    # ─────────────────────────────────────────────────────────────────
    # Request Metrics
    # ─────────────────────────────────────────────────────────────────
    
    def record_request(
        self,
        endpoint: str,
        method: str,
        status: int,
        latency_seconds: float,
    ) -> None:
        """Record a request with its latency and status.
        
        Args:
            endpoint: API endpoint path
            method: HTTP method (GET, POST, etc.)
            status: HTTP status code
            latency_seconds: Request latency in seconds
        """
        with self._lock:
            self._request_count.labels(
                endpoint=endpoint,
                method=method,
                status=str(status),
            ).inc()
            self._request_latency.labels(
                endpoint=endpoint,
                method=method,
            ).observe(latency_seconds)
    
    def record_error(self, component: str, error_type: str) -> None:
        """Record an error occurrence.
        
        Args:
            component: Component where error occurred
            error_type: Type/category of error
        """
        with self._lock:
            self._error_count.labels(
                component=component,
                error_type=error_type,
            ).inc()
    
    # ─────────────────────────────────────────────────────────────────
    # Connection Metrics
    # ─────────────────────────────────────────────────────────────────
    
    def set_active_connections(self, connection_type: str, count: int) -> None:
        """Set the current number of active connections.
        
        Args:
            connection_type: Type of connection (webrtc, api, websocket)
            count: Current connection count
        """
        with self._lock:
            self._active_connections.labels(connection_type=connection_type).set(count)
    
    def inc_connections(self, connection_type: str) -> None:
        """Increment active connection count."""
        with self._lock:
            self._active_connections.labels(connection_type=connection_type).inc()
    
    def dec_connections(self, connection_type: str) -> None:
        """Decrement active connection count."""
        with self._lock:
            self._active_connections.labels(connection_type=connection_type).dec()
    
    # ─────────────────────────────────────────────────────────────────
    # Resource Metrics
    # ─────────────────────────────────────────────────────────────────
    
    def set_vram_usage(self, bytes_used: int) -> None:
        """Set current VRAM usage.
        
        Args:
            bytes_used: VRAM usage in bytes
        """
        with self._lock:
            self._vram_usage_bytes.set(bytes_used)
    
    def set_ram_usage(self, bytes_used: int) -> None:
        """Set current RAM usage.
        
        Args:
            bytes_used: RAM usage in bytes
        """
        with self._lock:
            self._ram_usage_bytes.set(bytes_used)
    
    def set_cpu_usage(self, percent: float) -> None:
        """Set current CPU usage percentage.
        
        Args:
            percent: CPU usage as percentage (0-100)
        """
        with self._lock:
            self._cpu_usage_percent.set(percent)
    
    # ─────────────────────────────────────────────────────────────────
    # Circuit Breaker Metrics
    # ─────────────────────────────────────────────────────────────────
    
    def set_circuit_breaker_state(
        self,
        service: str,
        state: CircuitBreakerState,
    ) -> None:
        """Set circuit breaker state for a service.
        
        Args:
            service: Service name (e.g., deepgram, elevenlabs)
            state: Circuit breaker state
        """
        state_value = {
            CircuitBreakerState.CLOSED: 0,
            CircuitBreakerState.OPEN: 1,
            CircuitBreakerState.HALF_OPEN: 2,
        }.get(state, 0)
        
        with self._lock:
            self._circuit_breaker_state.labels(service=service).set(state_value)
    
    def record_circuit_breaker_trip(self, service: str) -> None:
        """Record a circuit breaker trip event.
        
        Args:
            service: Service name that tripped
        """
        with self._lock:
            self._circuit_breaker_trips.labels(service=service).inc()
    
    # ─────────────────────────────────────────────────────────────────
    # Model Inference Metrics
    # ─────────────────────────────────────────────────────────────────
    
    def record_inference(self, model: str, latency_seconds: float) -> None:
        """Record model inference latency.
        
        Args:
            model: Model name (yolo, midas, llm, embeddings)
            latency_seconds: Inference latency in seconds
        """
        with self._lock:
            self._model_inference_seconds.labels(model=model).observe(latency_seconds)
    
    def set_model_loaded(self, model: str, loaded: bool) -> None:
        """Set whether a model is currently loaded.
        
        Args:
            model: Model name
            loaded: True if loaded, False otherwise
        """
        with self._lock:
            self._model_loaded.labels(model=model).set(1 if loaded else 0)
    
    # ─────────────────────────────────────────────────────────────────
    # Speech Pipeline Metrics
    # ─────────────────────────────────────────────────────────────────
    
    def record_stt_latency(self, latency_seconds: float) -> None:
        """Record speech-to-text latency.
        
        Args:
            latency_seconds: STT latency in seconds
        """
        with self._lock:
            self._stt_latency_seconds.observe(latency_seconds)
    
    def record_tts_latency(self, latency_seconds: float) -> None:
        """Record text-to-speech latency.
        
        Args:
            latency_seconds: TTS latency in seconds
        """
        with self._lock:
            self._tts_latency_seconds.observe(latency_seconds)
    
    def record_llm_latency(self, latency_seconds: float) -> None:
        """Record LLM inference latency.
        
        Args:
            latency_seconds: LLM latency in seconds
        """
        with self._lock:
            self._llm_latency_seconds.observe(latency_seconds)
    
    def record_faiss_query(self, latency_seconds: float) -> None:
        """Record FAISS query latency.
        
        Args:
            latency_seconds: FAISS query latency in seconds
        """
        with self._lock:
            self._faiss_query_seconds.observe(latency_seconds)
    
    # ─────────────────────────────────────────────────────────────────
    # Queue Metrics
    # ─────────────────────────────────────────────────────────────────
    
    def set_queue_size(self, queue_name: str, size: int) -> None:
        """Set current queue size.
        
        Args:
            queue_name: Name of the queue
            size: Current queue size
        """
        with self._lock:
            self._queue_size.labels(queue_name=queue_name).set(size)
    
    # ─────────────────────────────────────────────────────────────────
    # Health & Degradation Metrics (T-103)
    # ─────────────────────────────────────────────────────────────────
    
    def set_service_health(self, service: str, status: str) -> None:
        """Set service health status.
        
        Args:
            service: Service name
            status: Health status (healthy, degraded, unhealthy)
        """
        status_value = {
            "unhealthy": 0,
            "healthy": 1,
            "degraded": 2,
        }.get(status.lower(), 0)
        
        with self._lock:
            self._service_health.labels(service=service, status=status.lower()).set(status_value)
    
    def set_degradation_level(self, level: str) -> None:
        """Set current degradation level.
        
        Args:
            level: Degradation level (full, partial, minimal, offline)
        """
        level_value = {
            "full": 0,
            "partial": 1,
            "minimal": 2,
            "offline": 3,
        }.get(level.lower(), 0)
        
        with self._lock:
            self._degradation_level.set(level_value)
    
    def record_degradation_transition(self) -> None:
        """Record a degradation level transition event."""
        with self._lock:
            self._degradation_transitions.inc()
    
    def record_service_downtime(self, service: str, seconds: float) -> None:
        """Record service downtime.
        
        Args:
            service: Service name
            seconds: Downtime duration in seconds
        """
        with self._lock:
            self._service_downtime.labels(service=service).inc(seconds)
    
    def set_feature_enabled(self, feature: str, enabled: bool) -> None:
        """Set whether a feature is enabled.
        
        Args:
            feature: Feature name (vision, memory, search, avatar)
            enabled: True if enabled, False otherwise
        """
        with self._lock:
            self._feature_enabled.labels(feature=feature).set(1 if enabled else 0)
    
    def set_speech_mode(self, speech_type: str, is_cloud: bool) -> None:
        """Set speech processing mode.
        
        Args:
            speech_type: Speech type (stt, tts)
            is_cloud: True if using cloud, False if local
        """
        with self._lock:
            self._speech_mode.labels(type=speech_type).set(1 if is_cloud else 0)
    # ─────────────────────────────────────────────────────────────────
    # Build Info
    # ─────────────────────────────────────────────────────────────────
    
    def set_build_info(
        self,
        version: str,
        commit: str = "",
        build_date: str = "",
    ) -> None:
        """Set build information.
        
        Args:
            version: Application version
            commit: Git commit hash
            build_date: Build date string
        """
        with self._lock:
            self._build_info.info({
                "version": version,
                "commit": commit,
                "build_date": build_date,
            })
    
    # ─────────────────────────────────────────────────────────────────
    # MetricsCollector Interface Implementation
    # ─────────────────────────────────────────────────────────────────
    
    def increment(
        self,
        name: str,
        value: float = 1.0,
        tags: dict[str, object] | None = None,
    ) -> None:
        """Increment a counter metric (MetricsCollector interface)."""
        # Route to appropriate counter based on name
        if name == "request_count":
            endpoint = tags.get("endpoint", "unknown") if tags else "unknown"
            method = tags.get("method", "GET") if tags else "GET"
            status = tags.get("status", "200") if tags else "200"
            self._request_count.labels(
                endpoint=str(endpoint),
                method=str(method),
                status=str(status),
            ).inc(value)
        elif name == "error_count":
            component = tags.get("component", "unknown") if tags else "unknown"
            error_type = tags.get("error_type", "unknown") if tags else "unknown"
            self._error_count.labels(
                component=str(component),
                error_type=str(error_type),
            ).inc(value)
    
    def gauge(
        self,
        name: str,
        value: float,
        tags: dict[str, object] | None = None,
    ) -> None:
        """Set a gauge metric (MetricsCollector interface)."""
        if name == "active_connections":
            conn_type = tags.get("connection_type", "unknown") if tags else "unknown"
            self._active_connections.labels(connection_type=str(conn_type)).set(value)
        elif name == "vram_usage_bytes":
            self._vram_usage_bytes.set(value)
        elif name == "ram_usage_bytes":
            self._ram_usage_bytes.set(value)
        elif name == "cpu_usage_percent":
            self._cpu_usage_percent.set(value)
        elif name == "circuit_breaker_state":
            service = tags.get("service", "unknown") if tags else "unknown"
            self._circuit_breaker_state.labels(service=str(service)).set(value)
    
    def histogram(
        self,
        name: str,
        value: float,
        tags: dict[str, object] | None = None,
    ) -> None:
        """Record a histogram value (MetricsCollector interface)."""
        if name == "request_latency_seconds":
            endpoint = tags.get("endpoint", "unknown") if tags else "unknown"
            method = tags.get("method", "GET") if tags else "GET"
            self._request_latency.labels(
                endpoint=str(endpoint),
                method=str(method),
            ).observe(value)
        elif name == "model_inference_seconds":
            model = tags.get("model", "unknown") if tags else "unknown"
            self._model_inference_seconds.labels(model=str(model)).observe(value)
        elif name == "stt_latency_seconds":
            self._stt_latency_seconds.observe(value)
        elif name == "tts_latency_seconds":
            self._tts_latency_seconds.observe(value)
        elif name == "llm_latency_seconds":
            self._llm_latency_seconds.observe(value)
        elif name == "faiss_query_seconds":
            self._faiss_query_seconds.observe(value)
    
    def get_counter(self, name: str) -> float:
        """Return counter value (MetricsCollector interface)."""
        # Prometheus counters don't directly expose values easily
        # This is mainly for interface compatibility
        return 0.0
    
    def get_gauge(self, name: str) -> float | None:
        """Return gauge value (MetricsCollector interface)."""
        return None
    
    def get_histogram(self, name: str) -> HistogramStats:
        """Return histogram stats (MetricsCollector interface)."""
        return {}
    
    def get_all_metrics(self) -> MetricsSnapshot:
        """Return all metrics (MetricsCollector interface)."""
        return {"counters": {}, "gauges": {}, "histograms": {}}
    
    def health(self) -> dict[str, int | str]:
        """Return health status."""
        return {
            "status": "ok",
            "backend": "prometheus",
            "namespace": self._namespace,
        }
    
    def reset(self) -> None:
        """Reset is not supported for Prometheus metrics."""
        logger.warning("Reset not supported for Prometheus metrics")
    
    # ─────────────────────────────────────────────────────────────────
    # Prometheus Export
    # ─────────────────────────────────────────────────────────────────
    
    def generate_metrics(self) -> bytes:
        """Generate Prometheus metrics output.
        
        Returns:
            Prometheus-formatted metrics as bytes
        """
        return generate_latest(self._registry)
    
    def get_content_type(self) -> str:
        """Get the content type for Prometheus metrics.
        
        Returns:
            Content-Type header value
        """
        return CONTENT_TYPE_LATEST
    
    @property
    def registry(self) -> CollectorRegistry:
        """Get the Prometheus registry."""
        return self._registry


# ─────────────────────────────────────────────────────────────────────────────
# Global Metrics Instance
# ─────────────────────────────────────────────────────────────────────────────

_metrics_instance: Optional[PrometheusMetrics] = None
_metrics_lock = threading.Lock()


def get_metrics() -> PrometheusMetrics:
    """Get or create the global Prometheus metrics instance.
    
    Returns:
        Global PrometheusMetrics instance
    
    Raises:
        RuntimeError: If prometheus_client is not available
    """
    global _metrics_instance
    
    if _metrics_instance is None:
        with _metrics_lock:
            if _metrics_instance is None:
                # Use a dedicated registry to avoid conflicts with tests
                from prometheus_client import CollectorRegistry
                registry = CollectorRegistry(auto_describe=True)
                _metrics_instance = PrometheusMetrics(registry=registry)
    
    return _metrics_instance


def reset_metrics() -> None:
    """Reset the global metrics instance (for testing)."""
    global _metrics_instance
    with _metrics_lock:
        if _metrics_instance is not None:
            # Unregister all collectors from the registry to allow re-creation
            try:
                from prometheus_client import REGISTRY
                # Clear our instance so next get_metrics creates fresh one with new registry
                pass
            except Exception:
                pass
        _metrics_instance = None


def is_prometheus_available() -> bool:
    """Check if Prometheus client is available.
    
    Returns:
        True if prometheus_client is installed
    """
    return PROMETHEUS_AVAILABLE


# ─────────────────────────────────────────────────────────────────────────────
# Metric Decorators
# ─────────────────────────────────────────────────────────────────────────────

def timed_request(endpoint: str, method: str = "GET") -> Callable:
    """Decorator to time and record request metrics.
    
    Args:
        endpoint: API endpoint path
        method: HTTP method
    
    Returns:
        Decorator function
    """
    import functools
    import time
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            status = 200
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = 500
                raise
            finally:
                latency = time.perf_counter() - start
                try:
                    get_metrics().record_request(endpoint, method, status, latency)
                except Exception:
                    pass  # Don't fail on metrics errors
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            status = 200
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = 500
                raise
            finally:
                latency = time.perf_counter() - start
                try:
                    get_metrics().record_request(endpoint, method, status, latency)
                except Exception:
                    pass
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    
    return decorator


def timed_inference(model: str) -> Callable:
    """Decorator to time and record model inference metrics.
    
    Args:
        model: Model name
    
    Returns:
        Decorator function
    """
    import functools
    import time
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                latency = time.perf_counter() - start
                try:
                    get_metrics().record_inference(model, latency)
                except Exception:
                    pass
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                latency = time.perf_counter() - start
                try:
                    get_metrics().record_inference(model, latency)
                except Exception:
                    pass
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    
    return decorator
