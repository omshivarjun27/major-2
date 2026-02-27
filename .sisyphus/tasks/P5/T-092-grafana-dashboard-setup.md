# T-092: Grafana Dashboard Setup

## Metadata
- **Phase**: P5
- **Cluster**: CL-OPS
- **Risk Tier**: Low
- **Upstream Deps**: [T-091]
- **Downstream Impact**: [T-108]
- **Current State**: completed

## Objective

Create Grafana dashboard configurations for operational monitoring. Design 4 dashboards:
1. System Health (CPU, memory, VRAM, disk)
2. Pipeline Performance (STT/VQA/TTS latencies, throughput)
3. Service Resilience (circuit breaker states, fallback activations, error rates)
4. User Activity (active sessions, query types, response times)

Export dashboards as JSON provisioning files in `deployments/grafana/dashboards/`.
Configure Grafana data source pointing to Prometheus.

## Acceptance Criteria

1. 4 dashboard JSON files created in deployments/grafana/dashboards/
2. Prometheus data source configuration file
3. Dashboards reference metrics from T-091
4. Each dashboard has meaningful panels and thresholds
5. Unit test verifies JSON validity

## Test Requirements

- Unit: Verify JSON files are valid and contain expected panels
