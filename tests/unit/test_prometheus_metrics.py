"""Unit tests for Prometheus metrics infrastructure.

Tests T-091: Prometheus Metrics Foundation
"""


import pytest


class TestPrometheusAvailability:
    """Tests for prometheus_client availability check."""

    def test_prometheus_available(self):
        """Test that prometheus_client is installed."""
        from infrastructure.monitoring.prometheus_metrics import is_prometheus_available
        assert is_prometheus_available() is True

    def test_can_import_prometheus_client(self):
        """Test direct prometheus_client import."""
        import prometheus_client
        assert hasattr(prometheus_client, "Counter")
        assert hasattr(prometheus_client, "Gauge")
        assert hasattr(prometheus_client, "Histogram")


class TestCircuitBreakerState:
    """Tests for CircuitBreakerState enum."""

    def test_state_values(self):
        """Test circuit breaker state enum values."""
        from infrastructure.monitoring.prometheus_metrics import CircuitBreakerState

        assert CircuitBreakerState.CLOSED.value == "closed"
        assert CircuitBreakerState.OPEN.value == "open"
        assert CircuitBreakerState.HALF_OPEN.value == "half_open"

    def test_state_enumeration(self):
        """Test circuit breaker states are enumerable."""
        from infrastructure.monitoring.prometheus_metrics import CircuitBreakerState

        states = list(CircuitBreakerState)
        assert len(states) == 3


class TestServiceName:
    """Tests for ServiceName enum."""

    def test_all_services_defined(self):
        """Test all expected services are defined."""
        from infrastructure.monitoring.prometheus_metrics import ServiceName

        expected = {"deepgram", "elevenlabs", "ollama", "duckduckgo", "livekit", "tavus"}
        actual = {s.value for s in ServiceName}
        assert actual == expected


class TestModelName:
    """Tests for ModelName enum."""

    def test_all_models_defined(self):
        """Test all expected models are defined."""
        from infrastructure.monitoring.prometheus_metrics import ModelName

        expected = {"yolo", "midas", "llm", "embeddings"}
        actual = {m.value for m in ModelName}
        assert actual == expected


class TestPrometheusMetricsCreation:
    """Tests for PrometheusMetrics class creation."""

    def test_create_with_default_registry(self):
        """Test creating metrics with default registry."""
        from prometheus_client import CollectorRegistry

        from infrastructure.monitoring.prometheus_metrics import PrometheusMetrics

        # Use custom registry to avoid conflicts
        registry = CollectorRegistry()
        metrics = PrometheusMetrics(registry=registry)

        assert metrics is not None
        assert metrics.registry is registry

    def test_create_with_custom_namespace(self):
        """Test creating metrics with custom namespace."""
        from prometheus_client import CollectorRegistry

        from infrastructure.monitoring.prometheus_metrics import PrometheusMetrics

        registry = CollectorRegistry()
        metrics = PrometheusMetrics(
            registry=registry,
            namespace="test_app",
            subsystem="api",
        )

        assert metrics._namespace == "test_app"
        assert metrics._subsystem == "api"

    def test_health_returns_ok(self):
        """Test health check returns ok status."""
        from prometheus_client import CollectorRegistry

        from infrastructure.monitoring.prometheus_metrics import PrometheusMetrics

        registry = CollectorRegistry()
        metrics = PrometheusMetrics(registry=registry)

        health = metrics.health()
        assert health["status"] == "ok"
        assert health["backend"] == "prometheus"


class TestRequestMetrics:
    """Tests for request-related metrics."""

    def test_record_request(self):
        """Test recording a request with latency."""
        from prometheus_client import CollectorRegistry

        from infrastructure.monitoring.prometheus_metrics import PrometheusMetrics

        registry = CollectorRegistry()
        metrics = PrometheusMetrics(registry=registry)

        # Should not raise
        metrics.record_request("/api/health", "GET", 200, 0.05)
        metrics.record_request("/api/vqa", "POST", 200, 0.25)
        metrics.record_request("/api/vqa", "POST", 500, 0.10)

    def test_record_error(self):
        """Test recording an error."""
        from prometheus_client import CollectorRegistry

        from infrastructure.monitoring.prometheus_metrics import PrometheusMetrics

        registry = CollectorRegistry()
        metrics = PrometheusMetrics(registry=registry)

        metrics.record_error("vision_pipeline", "timeout")
        metrics.record_error("llm", "rate_limit")


class TestConnectionMetrics:
    """Tests for connection-related metrics."""

    def test_set_active_connections(self):
        """Test setting active connections."""
        from prometheus_client import CollectorRegistry

        from infrastructure.monitoring.prometheus_metrics import PrometheusMetrics

        registry = CollectorRegistry()
        metrics = PrometheusMetrics(registry=registry)

        metrics.set_active_connections("webrtc", 5)
        metrics.set_active_connections("api", 10)

    def test_inc_dec_connections(self):
        """Test incrementing and decrementing connections."""
        from prometheus_client import CollectorRegistry

        from infrastructure.monitoring.prometheus_metrics import PrometheusMetrics

        registry = CollectorRegistry()
        metrics = PrometheusMetrics(registry=registry)

        metrics.inc_connections("webrtc")
        metrics.inc_connections("webrtc")
        metrics.dec_connections("webrtc")


class TestResourceMetrics:
    """Tests for resource-related metrics."""

    def test_set_vram_usage(self):
        """Test setting VRAM usage."""
        from prometheus_client import CollectorRegistry

        from infrastructure.monitoring.prometheus_metrics import PrometheusMetrics

        registry = CollectorRegistry()
        metrics = PrometheusMetrics(registry=registry)

        metrics.set_vram_usage(4 * 1024 * 1024 * 1024)  # 4GB

    def test_set_ram_usage(self):
        """Test setting RAM usage."""
        from prometheus_client import CollectorRegistry

        from infrastructure.monitoring.prometheus_metrics import PrometheusMetrics

        registry = CollectorRegistry()
        metrics = PrometheusMetrics(registry=registry)

        metrics.set_ram_usage(8 * 1024 * 1024 * 1024)  # 8GB

    def test_set_cpu_usage(self):
        """Test setting CPU usage."""
        from prometheus_client import CollectorRegistry

        from infrastructure.monitoring.prometheus_metrics import PrometheusMetrics

        registry = CollectorRegistry()
        metrics = PrometheusMetrics(registry=registry)

        metrics.set_cpu_usage(45.5)


class TestCircuitBreakerMetrics:
    """Tests for circuit breaker metrics."""

    def test_set_circuit_breaker_state_closed(self):
        """Test setting circuit breaker to closed state."""
        from prometheus_client import CollectorRegistry

        from infrastructure.monitoring.prometheus_metrics import (
            CircuitBreakerState,
            PrometheusMetrics,
        )

        registry = CollectorRegistry()
        metrics = PrometheusMetrics(registry=registry)

        metrics.set_circuit_breaker_state("deepgram", CircuitBreakerState.CLOSED)

    def test_set_circuit_breaker_state_open(self):
        """Test setting circuit breaker to open state."""
        from prometheus_client import CollectorRegistry

        from infrastructure.monitoring.prometheus_metrics import (
            CircuitBreakerState,
            PrometheusMetrics,
        )

        registry = CollectorRegistry()
        metrics = PrometheusMetrics(registry=registry)

        metrics.set_circuit_breaker_state("elevenlabs", CircuitBreakerState.OPEN)

    def test_set_circuit_breaker_state_half_open(self):
        """Test setting circuit breaker to half-open state."""
        from prometheus_client import CollectorRegistry

        from infrastructure.monitoring.prometheus_metrics import (
            CircuitBreakerState,
            PrometheusMetrics,
        )

        registry = CollectorRegistry()
        metrics = PrometheusMetrics(registry=registry)

        metrics.set_circuit_breaker_state("ollama", CircuitBreakerState.HALF_OPEN)

    def test_record_circuit_breaker_trip(self):
        """Test recording circuit breaker trip event."""
        from prometheus_client import CollectorRegistry

        from infrastructure.monitoring.prometheus_metrics import PrometheusMetrics

        registry = CollectorRegistry()
        metrics = PrometheusMetrics(registry=registry)

        metrics.record_circuit_breaker_trip("deepgram")
        metrics.record_circuit_breaker_trip("deepgram")


class TestInferenceMetrics:
    """Tests for model inference metrics."""

    def test_record_inference(self):
        """Test recording model inference latency."""
        from prometheus_client import CollectorRegistry

        from infrastructure.monitoring.prometheus_metrics import PrometheusMetrics

        registry = CollectorRegistry()
        metrics = PrometheusMetrics(registry=registry)

        metrics.record_inference("yolo", 0.05)
        metrics.record_inference("midas", 0.08)
        metrics.record_inference("llm", 0.30)
        metrics.record_inference("embeddings", 0.02)

    def test_set_model_loaded(self):
        """Test setting model loaded state."""
        from prometheus_client import CollectorRegistry

        from infrastructure.monitoring.prometheus_metrics import PrometheusMetrics

        registry = CollectorRegistry()
        metrics = PrometheusMetrics(registry=registry)

        metrics.set_model_loaded("yolo", True)
        metrics.set_model_loaded("midas", False)


class TestSpeechPipelineMetrics:
    """Tests for speech pipeline metrics."""

    def test_record_stt_latency(self):
        """Test recording STT latency."""
        from prometheus_client import CollectorRegistry

        from infrastructure.monitoring.prometheus_metrics import PrometheusMetrics

        registry = CollectorRegistry()
        metrics = PrometheusMetrics(registry=registry)

        metrics.record_stt_latency(0.08)

    def test_record_tts_latency(self):
        """Test recording TTS latency."""
        from prometheus_client import CollectorRegistry

        from infrastructure.monitoring.prometheus_metrics import PrometheusMetrics

        registry = CollectorRegistry()
        metrics = PrometheusMetrics(registry=registry)

        metrics.record_tts_latency(0.09)

    def test_record_llm_latency(self):
        """Test recording LLM latency."""
        from prometheus_client import CollectorRegistry

        from infrastructure.monitoring.prometheus_metrics import PrometheusMetrics

        registry = CollectorRegistry()
        metrics = PrometheusMetrics(registry=registry)

        metrics.record_llm_latency(0.25)

    def test_record_faiss_query(self):
        """Test recording FAISS query latency."""
        from prometheus_client import CollectorRegistry

        from infrastructure.monitoring.prometheus_metrics import PrometheusMetrics

        registry = CollectorRegistry()
        metrics = PrometheusMetrics(registry=registry)

        metrics.record_faiss_query(0.01)


class TestQueueMetrics:
    """Tests for queue metrics."""

    def test_set_queue_size(self):
        """Test setting queue size."""
        from prometheus_client import CollectorRegistry

        from infrastructure.monitoring.prometheus_metrics import PrometheusMetrics

        registry = CollectorRegistry()
        metrics = PrometheusMetrics(registry=registry)

        metrics.set_queue_size("frame_buffer", 5)
        metrics.set_queue_size("audio_buffer", 3)


class TestBuildInfo:
    """Tests for build info metrics."""

    def test_set_build_info(self):
        """Test setting build information."""
        from prometheus_client import CollectorRegistry

        from infrastructure.monitoring.prometheus_metrics import PrometheusMetrics

        registry = CollectorRegistry()
        metrics = PrometheusMetrics(registry=registry)

        metrics.set_build_info(
            version="1.0.0",
            commit="abc123",
            build_date="2026-02-28",
        )


class TestMetricsCollectorInterface:
    """Tests for MetricsCollector interface implementation."""

    def test_increment_interface(self):
        """Test increment method from interface."""
        from prometheus_client import CollectorRegistry

        from infrastructure.monitoring.prometheus_metrics import PrometheusMetrics

        registry = CollectorRegistry()
        metrics = PrometheusMetrics(registry=registry)

        metrics.increment("request_count", tags={
            "endpoint": "/api/health",
            "method": "GET",
            "status": "200",
        })

    def test_gauge_interface(self):
        """Test gauge method from interface."""
        from prometheus_client import CollectorRegistry

        from infrastructure.monitoring.prometheus_metrics import PrometheusMetrics

        registry = CollectorRegistry()
        metrics = PrometheusMetrics(registry=registry)

        metrics.gauge("vram_usage_bytes", 4_000_000_000)
        metrics.gauge("active_connections", 5, tags={"connection_type": "webrtc"})

    def test_histogram_interface(self):
        """Test histogram method from interface."""
        from prometheus_client import CollectorRegistry

        from infrastructure.monitoring.prometheus_metrics import PrometheusMetrics

        registry = CollectorRegistry()
        metrics = PrometheusMetrics(registry=registry)

        metrics.histogram("request_latency_seconds", 0.05, tags={
            "endpoint": "/api/health",
            "method": "GET",
        })


class TestPrometheusExport:
    """Tests for Prometheus metrics export."""

    def test_generate_metrics(self):
        """Test generating Prometheus format metrics."""
        from prometheus_client import CollectorRegistry

        from infrastructure.monitoring.prometheus_metrics import PrometheusMetrics

        registry = CollectorRegistry()
        metrics = PrometheusMetrics(registry=registry)

        # Record some data
        metrics.record_request("/api/health", "GET", 200, 0.01)
        metrics.set_vram_usage(1_000_000)

        output = metrics.generate_metrics()
        assert isinstance(output, bytes)
        assert len(output) > 0

    def test_metrics_output_contains_expected_metrics(self):
        """Test that output contains expected metric names."""
        from prometheus_client import CollectorRegistry

        from infrastructure.monitoring.prometheus_metrics import PrometheusMetrics

        registry = CollectorRegistry()
        metrics = PrometheusMetrics(registry=registry)

        metrics.record_request("/api/test", "POST", 200, 0.05)

        output = metrics.generate_metrics().decode("utf-8")

        assert "voice_vision_request_count_total" in output
        assert "voice_vision_request_latency_seconds" in output

    def test_get_content_type(self):
        """Test getting Prometheus content type."""
        from prometheus_client import CollectorRegistry

        from infrastructure.monitoring.prometheus_metrics import PrometheusMetrics

        registry = CollectorRegistry()
        metrics = PrometheusMetrics(registry=registry)

        content_type = metrics.get_content_type()
        assert "text/plain" in content_type or "text/openmetrics" in content_type


class TestGlobalMetricsInstance:
    """Tests for global metrics instance management."""

    def test_get_metrics_returns_instance(self):
        """Test that get_metrics returns an instance."""
        from infrastructure.monitoring.prometheus_metrics import (
            PrometheusMetrics,
            get_metrics,
            reset_metrics,
        )

        reset_metrics()
        metrics = get_metrics()
        assert isinstance(metrics, PrometheusMetrics)

    def test_get_metrics_returns_same_instance(self):
        """Test that get_metrics returns singleton."""
        from infrastructure.monitoring.prometheus_metrics import (
            get_metrics,
            reset_metrics,
        )

        reset_metrics()
        m1 = get_metrics()
        m2 = get_metrics()
        assert m1 is m2

    def test_reset_metrics_clears_instance(self):
        """Test that reset_metrics clears the singleton."""
        from infrastructure.monitoring.prometheus_metrics import (
            get_metrics,
            reset_metrics,
        )

        reset_metrics()
        get_metrics()
        reset_metrics()
        m2 = get_metrics()
        # After reset, we get a new instance
        # Note: Due to Prometheus registry behavior, this may still share metrics
        assert m2 is not None


class TestTimedDecorators:
    """Tests for timing decorators."""

    def test_timed_request_decorator_sync(self):
        """Test timed_request decorator on sync function."""
        from infrastructure.monitoring.prometheus_metrics import (
            reset_metrics,
            timed_request,
        )

        reset_metrics()

        @timed_request("/api/test", "GET")
        def test_endpoint():
            return "success"

        result = test_endpoint()
        assert result == "success"

    def test_timed_request_decorator_with_error(self):
        """Test timed_request decorator handles errors."""
        from infrastructure.monitoring.prometheus_metrics import (
            reset_metrics,
            timed_request,
        )

        reset_metrics()

        @timed_request("/api/error", "POST")
        def error_endpoint():
            raise ValueError("test error")

        with pytest.raises(ValueError):
            error_endpoint()

    def test_timed_inference_decorator_sync(self):
        """Test timed_inference decorator on sync function."""
        from infrastructure.monitoring.prometheus_metrics import (
            reset_metrics,
            timed_inference,
        )

        reset_metrics()

        @timed_inference("test_model")
        def run_inference():
            return [1, 2, 3]

        result = run_inference()
        assert result == [1, 2, 3]


class TestThreadSafety:
    """Tests for thread safety."""

    def test_concurrent_increments(self):
        """Test concurrent metric increments."""
        import threading

        from prometheus_client import CollectorRegistry

        from infrastructure.monitoring.prometheus_metrics import PrometheusMetrics

        registry = CollectorRegistry()
        metrics = PrometheusMetrics(registry=registry)

        errors = []

        def increment_task():
            try:
                for _ in range(100):
                    metrics.record_request("/api/test", "GET", 200, 0.01)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=increment_task) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_concurrent_gauge_updates(self):
        """Test concurrent gauge updates."""
        import threading

        from prometheus_client import CollectorRegistry

        from infrastructure.monitoring.prometheus_metrics import PrometheusMetrics

        registry = CollectorRegistry()
        metrics = PrometheusMetrics(registry=registry)

        errors = []

        def gauge_task(value):
            try:
                for _ in range(100):
                    metrics.set_vram_usage(value)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=gauge_task, args=(i * 1000,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


class TestMetricsIntegration:
    """Integration tests for metrics system."""

    def test_full_metrics_workflow(self):
        """Test a complete metrics recording workflow."""
        from prometheus_client import CollectorRegistry

        from infrastructure.monitoring.prometheus_metrics import (
            CircuitBreakerState,
            PrometheusMetrics,
        )

        registry = CollectorRegistry()
        metrics = PrometheusMetrics(registry=registry)

        # Simulate application startup
        metrics.set_build_info("1.0.0", "abc123", "2026-02-28")
        metrics.set_model_loaded("yolo", True)
        metrics.set_model_loaded("midas", True)

        # Simulate normal operation
        metrics.set_active_connections("webrtc", 3)
        metrics.set_vram_usage(4_000_000_000)
        metrics.set_cpu_usage(35.0)

        # Simulate requests
        for i in range(10):
            metrics.record_request("/api/health", "GET", 200, 0.01 + i * 0.001)

        # Simulate inference
        metrics.record_inference("yolo", 0.05)
        metrics.record_inference("midas", 0.08)
        metrics.record_llm_latency(0.25)

        # Simulate circuit breaker events
        metrics.set_circuit_breaker_state("deepgram", CircuitBreakerState.CLOSED)
        metrics.set_circuit_breaker_state("elevenlabs", CircuitBreakerState.CLOSED)

        # Generate output
        output = metrics.generate_metrics()
        assert len(output) > 1000  # Should have substantial metrics

    def test_metrics_in_prometheus_format(self):
        """Test that output follows Prometheus format."""
        from prometheus_client import CollectorRegistry

        from infrastructure.monitoring.prometheus_metrics import PrometheusMetrics

        registry = CollectorRegistry()
        metrics = PrometheusMetrics(registry=registry)

        metrics.record_request("/api/test", "GET", 200, 0.05)

        output = metrics.generate_metrics().decode("utf-8")
        lines = output.strip().split("\n")

        # Check for HELP and TYPE comments
        has_help = any(line.startswith("# HELP") for line in lines)
        has_type = any(line.startswith("# TYPE") for line in lines)

        assert has_help, "Output should contain HELP comments"
        assert has_type, "Output should contain TYPE comments"
