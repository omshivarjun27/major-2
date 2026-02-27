# T-091: Prometheus Metrics Foundation

## Metadata
- **Phase**: P5
- **Cluster**: CL-OPS
- **Risk Tier**: Low
- **Upstream Deps**: []
- **Downstream Impact**: [T-092, T-093, T-094, T-095, T-108]
- **Current State**: completed

## Objective

Set up Prometheus metrics collection infrastructure. Create `infrastructure/monitoring/prometheus_metrics.py` with a metrics registry exposing:
- request_count (counter)
- request_latency_seconds (histogram)
- active_connections (gauge)
- circuit_breaker_state (enum gauge per service)
- vram_usage_bytes (gauge)
- model_inference_seconds (histogram per model)

Configure Prometheus scrape endpoint at `/metrics` on port 9090. Use `prometheus_client` library.

## Acceptance Criteria

1. PrometheusMetrics class implements MetricsCollector interface
2. All 6 metric types defined and accessible
3. /metrics endpoint returns valid Prometheus format
4. Unit tests verify metric registration and updates
5. Integration test verifies scrape endpoint works

## Implementation Notes

- Build on existing collector.py MetricsCollector interface
- Use prometheus_client library (already installed)
- Thread-safe implementation required
- Circuit breaker states: closed, open, half_open
- Model labels: yolo, midas, llm, embeddings

## Test Requirements

- Unit: test_prometheus_metrics.py with 15+ tests
- Integration: verify /metrics endpoint in API server
