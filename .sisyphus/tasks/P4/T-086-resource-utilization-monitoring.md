# T-086: resource-utilization-monitoring

> Phase: P4 | Cluster: CL-OPS | Risk: Low | State: completed | created_at: 2026-02-27T20:00:00Z

## Objective

Implement resource utilization monitoring to track CPU, memory, GPU, and VRAM usage during operation. Create dashboards and alerts for resource thresholds. Ensure the system operates within resource budgets under load.

## Implementation Plan

1. Implement resource monitoring utilities in `shared/utils/resource_monitor.py`.
2. Track key metrics:
   - CPU utilization (per core and total)
   - RAM usage and available memory
   - GPU utilization percentage
   - VRAM usage and available
   - Disk I/O for FAISS/SQLite
3. Create monitoring dashboard configuration (for Grafana in P5).
4. Implement resource alerts:
   - VRAM > 7GB warning
   - RAM > 80% warning
   - CPU sustained > 90%
5. Add resource stats to health endpoints.

## Files to Create

| File | Purpose |
|------|---------|
| `shared/utils/resource_monitor.py` | Resource monitoring utilities |
| `configs/monitoring/resource_alerts.yaml` | Alert threshold configuration |
| `tests/unit/test_resource_monitor.py` | Resource monitor tests |

## Acceptance Criteria

- [ ] CPU, RAM, GPU, VRAM monitoring implemented
- [ ] Metrics exposed via health API
- [ ] Alert thresholds configurable
- [ ] Dashboard configuration prepared for P5
- [ ] Resource usage logged during tests
- [ ] No significant overhead from monitoring (<1% CPU)

## Upstream Dependencies

T-077 (VRAM profiling)

## Downstream Unblocks

T-089 (SLA compliance), Phase 5 (monitoring)

## Estimated Scope

Small-Medium. Monitoring utilities, ~150-200 lines of code.
