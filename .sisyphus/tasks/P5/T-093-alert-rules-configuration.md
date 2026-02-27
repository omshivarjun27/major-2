# T-093: Alert Rules Configuration

## Metadata
- **Phase**: P5
- **Cluster**: CL-OPS
- **Risk Tier**: Low
- **Upstream Deps**: [T-091]
- **Downstream Impact**: [T-108]
- **Current State**: completed

## Objective

Configure alert rules for critical operational conditions. Create `deployments/prometheus/alert_rules.yml` with rules:
- hot_path_sla_violation (P95 > 500ms for 5 min)
- high_error_rate (5xx > 5% for 2 min)
- circuit_breaker_open (any service open > 5 min)
- high_vram (> 90% for 10 min)
- memory_leak_detected (RSS growth > 100MB/hour)
- disk_space_low (< 10% free)

Configure Alertmanager routing to webhook and email channels.

## Acceptance Criteria

1. alert_rules.yml with 6+ alert rules
2. Alertmanager config with routing
3. Each alert has severity label
4. Unit test verifies YAML validity

## Test Requirements

- Unit: Verify YAML files are valid
