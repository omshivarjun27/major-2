# Phase 5: Operational Readiness

> **Phase Focus**: Prometheus monitoring, Grafana dashboards, alerting, structured logging, CD pipelines, backup/restore, incident runbooks, environment management.
> **Task Count**: 20 (T-091 through T-110)
> **Risk Classification**: HIGH for production CD pipeline and CD validation, MEDIUM for backup infrastructure and environment config, LOW for monitoring and documentation.
> **Priority Unlock**: T-091 Prometheus Metrics Foundation

---

## T-091: prometheus-metrics-foundation

- **Phase**: P5
- **Cluster**: CL-OPS
- **Objective**: Set up Prometheus metrics collection infrastructure. Create `infrastructure/monitoring/prometheus_metrics.py` with a metrics registry exposing: request_count (counter), request_latency_seconds (histogram), active_connections (gauge), circuit_breaker_state (enum gauge per service), vram_usage_bytes (gauge), model_inference_seconds (histogram per model). Configure Prometheus scrape endpoint at `/metrics` on port 9090. Use `prometheus_client` library. This is the monitoring priority unlock task.
- **Upstream Deps**: []
- **Downstream Impact**: [`T-092`, `T-093`, `T-094`, `T-095`, `T-108`]
- **Risk Tier**: Low
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`infrastructure/AGENTS.md`, `docs/architecture.md#monitoring`, `AGENTS.md#operational-risks`]
- **Versioning Impact**: minor
- **Governance Level**: standard
- **Regression Sensitivity**: low
- **Parallelization Eligible**: no, priority unlock task for Phase 5
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-092: grafana-dashboard-setup

- **Phase**: P5
- **Cluster**: CL-OPS
- **Objective**: Create Grafana dashboard configurations for operational monitoring. Design 4 dashboards: System Health (CPU, memory, VRAM, disk), Pipeline Performance (STT/VQA/TTS latencies, throughput), Service Resilience (circuit breaker states, fallback activations, error rates), User Activity (active sessions, query types, response times). Export dashboards as JSON provisioning files in `deployments/grafana/dashboards/`. Configure Grafana data source pointing to Prometheus.
- **Upstream Deps**: [`T-091`]
- **Downstream Impact**: [`T-108`]
- **Risk Tier**: Low
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`deployments/AGENTS.md`, `docs/operations.md#dashboards`]
- **Versioning Impact**: patch
- **Governance Level**: standard
- **Regression Sensitivity**: low
- **Parallelization Eligible**: no, needs Prometheus metrics
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-093: alert-rules-configuration

- **Phase**: P5
- **Cluster**: CL-OPS
- **Objective**: Configure alert rules for critical operational conditions. Create `deployments/prometheus/alert_rules.yml` with rules: hot_path_sla_violation (P95 > 500ms for 5 min), high_error_rate (5xx > 5% for 2 min), circuit_breaker_open (any service open > 5 min), high_vram (> 90% for 10 min), memory_leak_detected (RSS growth > 100MB/hour), disk_space_low (< 10% free). Configure Alertmanager routing to webhook and email channels.
- **Upstream Deps**: [`T-091`]
- **Downstream Impact**: [`T-108`]
- **Risk Tier**: Low
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`deployments/AGENTS.md`, `docs/operations.md#alerting`]
- **Versioning Impact**: patch
- **Governance Level**: standard
- **Regression Sensitivity**: low
- **Parallelization Eligible**: yes, independent from dashboards
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-094: structured-logging-enhancement

- **Phase**: P5
- **Cluster**: CL-OPS
- **Objective**: Enhance the structured logging system in `shared/logging/` to emit JSON-formatted logs with consistent fields: timestamp, level, module, function, correlation_id, session_id, latency_ms, service_name. Add log aggregation configuration for ELK stack or Loki. Ensure all modules use the structured logger consistently. Add request tracing via correlation IDs that propagate through the full pipeline from STT input to TTS output.
- **Upstream Deps**: [`T-091`]
- **Downstream Impact**: [`T-108`]
- **Risk Tier**: Low
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`shared/logging/AGENTS.md`, `shared/AGENTS.md`, `docs/operations.md#logging`]
- **Versioning Impact**: patch
- **Governance Level**: standard
- **Regression Sensitivity**: low
- **Parallelization Eligible**: yes, logging is independent
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-095: custom-metrics-instrumentation

- **Phase**: P5
- **Cluster**: CL-OPS
- **Objective**: Add custom Prometheus metrics instrumentation across all major components. Instrument: vision pipeline (per-stage timing), RAG pipeline (embed/search/reason timing), speech pipeline (STT/TTS timing), circuit breakers (state transitions, recovery time), FAISS index (query count, vector count), WebRTC agent (session count, reconnections). Use decorators and context managers for minimal code intrusion. Target: every SLA-relevant operation is measurable.
- **Upstream Deps**: [`T-091`]
- **Downstream Impact**: [`T-108`]
- **Risk Tier**: Low
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/AGENTS.md`, `infrastructure/AGENTS.md`, `application/AGENTS.md`]
- **Versioning Impact**: patch
- **Governance Level**: standard
- **Regression Sensitivity**: low
- **Parallelization Eligible**: yes, per-module instrumentation
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-096: cd-pipeline-staging

- **Phase**: P5
- **Cluster**: CL-OPS
- **Objective**: Implement a CD pipeline for automated deployment to staging. Extend `.github/workflows/` with a `deploy-staging.yml` workflow triggered on main branch pushes. Pipeline stages: build Docker image, push to registry, deploy to staging, run smoke tests, notify. Use GitHub Actions with environment-specific secrets. Implement blue-green deployment strategy with instant rollback capability. Staging environment mirrors production configuration.
- **Upstream Deps**: []
- **Downstream Impact**: [`T-097`, `T-109`]
- **Risk Tier**: Medium
- **Test Layers**: [Integration, System]
- **Doc Mutation Map**: [`.github/workflows/AGENTS.md`, `deployments/AGENTS.md`, `docs/operations.md#cd-pipeline`]
- **Versioning Impact**: minor
- **Governance Level**: elevated
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: yes, CD infrastructure independent of monitoring
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-097: cd-pipeline-production

- **Phase**: P5
- **Cluster**: CL-OPS
- **Objective**: Extend the CD pipeline for production deployment with approval gates. Create `deploy-production.yml` workflow with manual approval step. Implement canary deployment (10% traffic for 2 hours) with automated rollback if error rate > 1% or P95 > 600ms. Add deployment notifications to Slack/webhook. Implement deployment versioning with semantic tags. Include pre-deployment database migration step and post-deployment smoke test suite.
- **Upstream Deps**: [`T-096`]
- **Downstream Impact**: [`T-109`]
- **Risk Tier**: High
- **Test Layers**: [Integration, System]
- **Doc Mutation Map**: [`.github/workflows/AGENTS.md`, `deployments/AGENTS.md`, `docs/operations.md#production-deployment`]
- **Versioning Impact**: minor
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, depends on staging pipeline
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-098: faiss-backup-restore

- **Phase**: P5
- **Cluster**: CL-INF
- **Objective**: Implement automated backup and restore procedures for FAISS indices. Create `infrastructure/backup/faiss_backup.py` with scheduled backup (daily at 2 AM), incremental backup support (only changed indices), compression (gzip), and configurable retention (30 days). Create restore procedure with index validation after restore. Support local filesystem and S3-compatible storage backends. Add backup status metrics for Prometheus monitoring.
- **Upstream Deps**: []
- **Downstream Impact**: [`T-100`, `T-108`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`infrastructure/AGENTS.md`, `docs/operations.md#backup-restore`]
- **Versioning Impact**: minor
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: yes, infrastructure utility
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-099: sqlite-backup-restore

- **Phase**: P5
- **Cluster**: CL-INF
- **Objective**: Implement automated backup and restore for SQLite databases (consent store, memory metadata, cache). Create `infrastructure/backup/sqlite_backup.py` using SQLite online backup API for consistent snapshots. Schedule daily backups with 30-day retention. Implement point-in-time recovery using WAL (Write-Ahead Log) replay. Add backup integrity verification via `PRAGMA integrity_check`. Support same storage backends as FAISS backup.
- **Upstream Deps**: []
- **Downstream Impact**: [`T-100`, `T-108`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`infrastructure/AGENTS.md`, `docs/operations.md#backup-restore`]
- **Versioning Impact**: minor
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: yes, independent from FAISS backup
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-100: backup-scheduler-orchestrator

- **Phase**: P5
- **Cluster**: CL-INF
- **Objective**: Create a unified backup scheduler that orchestrates FAISS and SQLite backup jobs. Implement `infrastructure/backup/scheduler.py` using APScheduler with configurable cron expressions. Add backup health monitoring: track last successful backup time, backup size, duration. Alert if any backup is overdue by more than 24 hours. Implement backup verification by performing a test restore to a temporary location and validating data integrity.
- **Upstream Deps**: [`T-098`, `T-099`]
- **Downstream Impact**: [`T-108`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`infrastructure/AGENTS.md`, `docs/operations.md#backup-scheduler`]
- **Versioning Impact**: patch
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: no, needs both backup implementations
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-101: incident-response-runbook

- **Phase**: P5
- **Cluster**: CL-GOV
- **Objective**: Create comprehensive incident response runbooks for the 6 most likely failure scenarios. Document step-by-step procedures for: (1) Complete cloud service outage, (2) VRAM exhaustion / CUDA OOM, (3) FAISS index corruption, (4) Deployment rollback procedure, (5) Memory leak escalation, (6) Security incident (API key compromise). Each runbook includes: detection criteria, severity classification, step-by-step response, escalation path, post-incident review template.
- **Upstream Deps**: []
- **Downstream Impact**: [`T-102`, `T-110`]
- **Risk Tier**: Low
- **Test Layers**: [Unit]
- **Doc Mutation Map**: [`docs/runbooks/`, `AGENTS.md#operational-risks`]
- **Versioning Impact**: none
- **Governance Level**: standard
- **Regression Sensitivity**: low
- **Parallelization Eligible**: yes, documentation task
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-102: degradation-playbook

- **Phase**: P5
- **Cluster**: CL-GOV
- **Objective**: Create a degradation playbook that documents the 4 system degradation modes from Phase 3 (FULL, DEGRADED-SPEECH, DEGRADED-VISION, MINIMAL) and provides operational procedures for each. Document: detection method (health endpoint + alerts), user communication templates, expected behavior per mode, recovery procedures, performance expectations per mode, and escalation criteria for moving between modes.
- **Upstream Deps**: [`T-101`]
- **Downstream Impact**: [`T-110`]
- **Risk Tier**: Low
- **Test Layers**: [Unit]
- **Doc Mutation Map**: [`docs/runbooks/`, `docs/operations.md#degradation-modes`]
- **Versioning Impact**: none
- **Governance Level**: standard
- **Regression Sensitivity**: low
- **Parallelization Eligible**: no, builds on incident runbook
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-103: health-dashboard-integration

- **Phase**: P5
- **Cluster**: CL-OPS
- **Objective**: Integrate the health check endpoints from Phase 3 (T-067) with the Grafana dashboards and alerting system. Create a dedicated health status panel showing real-time service status for all 6 cloud services. Add historical availability charts (uptime percentage over 24h, 7d, 30d). Wire health endpoint degradation events to Alertmanager. Add SLA compliance tracking: calculate and display actual vs target availability per service.
- **Upstream Deps**: [`T-092`, `T-093`]
- **Downstream Impact**: [`T-108`]
- **Risk Tier**: Low
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`deployments/AGENTS.md`, `docs/operations.md#health-monitoring`]
- **Versioning Impact**: patch
- **Governance Level**: standard
- **Regression Sensitivity**: low
- **Parallelization Eligible**: no, needs dashboards and alerts
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-104: log-rotation-retention

- **Phase**: P5
- **Cluster**: CL-OPS
- **Objective**: Implement log rotation and retention policies. Configure Python logging with TimedRotatingFileHandler: daily rotation, 30-day retention, gzip compression for archived logs. Set max log file size to 100MB with backup count of 5. Implement log shipping to centralized storage (configurable: local, S3, or Loki). Add log cleanup cron job for expired files. Ensure PII scrubber runs on logs before archival.
- **Upstream Deps**: [`T-094`]
- **Downstream Impact**: [`T-108`]
- **Risk Tier**: Low
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`shared/logging/AGENTS.md`, `docs/operations.md#log-management`]
- **Versioning Impact**: patch
- **Governance Level**: standard
- **Regression Sensitivity**: low
- **Parallelization Eligible**: no, depends on structured logging
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-105: environment-configuration-management

- **Phase**: P5
- **Cluster**: CL-OPS
- **Objective**: Implement environment-aware configuration management supporting dev, staging, and production profiles. Extend `shared/config/settings.py` with environment-specific overrides loaded from `configs/dev.yaml`, `configs/staging.yaml`, `configs/production.yaml`. Add configuration validation at startup that checks all required settings are present and within valid ranges. Add `config diff` CLI command to compare environments. Log active configuration (scrubbed of secrets) at startup.
- **Upstream Deps**: []
- **Downstream Impact**: [`T-108`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`shared/config/AGENTS.md`, `configs/AGENTS.md`, `docs/configuration.md`]
- **Versioning Impact**: minor
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: yes, independent configuration task
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-106: docker-compose-environments

- **Phase**: P5
- **Cluster**: CL-OPS
- **Objective**: Create Docker Compose configurations for dev, staging, and production environments. Create `docker-compose.dev.yml` with hot-reloading, debug logging, and mock services. Create `docker-compose.staging.yml` mirroring production with reduced resources. Enhance `docker-compose.test.yml` for integration test environment. Add Prometheus and Grafana services to compose files. Include environment variable templates and secrets management via Docker secrets.
- **Upstream Deps**: [`T-105`]
- **Downstream Impact**: [`T-109`]
- **Risk Tier**: Medium
- **Test Layers**: [Integration, System]
- **Doc Mutation Map**: [`deployments/AGENTS.md`, `docs/operations.md#docker-environments`]
- **Versioning Impact**: patch
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: no, needs config management
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-107: operational-documentation

- **Phase**: P5
- **Cluster**: CL-GOV
- **Objective**: Create comprehensive operational documentation covering all Phase 5 deliverables. Document: monitoring architecture (Prometheus + Grafana + Alertmanager), backup procedures and schedules, CD pipeline workflows, environment management, log management, and health check endpoints. Create a quick-start operations guide for new operators. Include architecture diagrams and troubleshooting decision trees. Target audience: SRE/DevOps engineers.
- **Upstream Deps**: [`T-102`, `T-103`]
- **Downstream Impact**: [`T-110`]
- **Risk Tier**: Low
- **Test Layers**: [Unit]
- **Doc Mutation Map**: [`docs/operations.md`, `docs/architecture.md#operations`, `AGENTS.md#documentation-coverage`]
- **Versioning Impact**: none
- **Governance Level**: standard
- **Regression Sensitivity**: low
- **Parallelization Eligible**: no, needs monitoring + runbooks complete
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-108: p5-monitoring-stack-integration

- **Phase**: P5
- **Cluster**: CL-OPS
- **Objective**: Integration closeout. Verify the complete monitoring stack works end-to-end. Start all services, generate synthetic load, verify: Prometheus scrapes all metrics, Grafana dashboards populate correctly, alert rules fire on simulated failures, logs flow to aggregation, backup metrics are tracked. Produce a monitoring readiness report documenting each component's status and any gaps.
- **Upstream Deps**: [`T-095`, `T-100`, `T-103`, `T-104`, `T-105`]
- **Downstream Impact**: [`T-110`]
- **Risk Tier**: Medium
- **Test Layers**: [Integration, System, Regression]
- **Doc Mutation Map**: [`tests/integration/AGENTS.md`, `AGENTS.md#documentation-coverage`]
- **Versioning Impact**: none
- **Governance Level**: elevated
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: no, final monitoring validation
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-109: p5-cd-pipeline-validation

- **Phase**: P5
- **Cluster**: CL-OPS
- **Objective**: Integration closeout. Execute a full CD pipeline dry run: build Docker image, push to test registry, deploy to staging environment, run smoke tests, verify rollback procedure works. Measure deployment time (target: < 10 minutes from commit to staging). Test the production deployment flow with approval gate simulation. Verify canary deployment metrics collection works.
- **Upstream Deps**: [`T-097`, `T-106`]
- **Downstream Impact**: [`T-110`]
- **Risk Tier**: High
- **Test Layers**: [Integration, System]
- **Doc Mutation Map**: [`tests/integration/AGENTS.md`, `.github/workflows/AGENTS.md`, `AGENTS.md#documentation-coverage`]
- **Versioning Impact**: none
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, needs CD pipeline complete
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-110: p5-runbook-execution-test

- **Phase**: P5
- **Cluster**: CL-GOV
- **Objective**: Integration closeout. Execute each incident response runbook against a simulated scenario. Test all 6 runbook procedures from T-101 and the degradation playbook from T-102. Record pass/fail for each step. Measure response time from incident detection to resolution. Document gaps or unclear steps discovered during execution. Update runbooks with lessons learned. Produce a final operational readiness assessment.
- **Upstream Deps**: [`T-107`, `T-108`, `T-109`]
- **Downstream Impact**: []
- **Risk Tier**: Medium
- **Test Layers**: [Integration, System, Regression]
- **Doc Mutation Map**: [`docs/runbooks/`, `AGENTS.md#documentation-coverage`]
- **Versioning Impact**: none
- **Governance Level**: elevated
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: no, final phase validation
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## Phase Exit Criteria

1. All tasks in this phase have `current_state: completed`
2. Prometheus monitoring live and collecting metrics from all instrumented components
3. Grafana dashboards displaying real-time data for all 4 dashboard categories
4. Alert rules configured and tested (at least 6 alert rules firing on simulated failures)
5. CD pipeline functional for both staging (automated) and production (with approval gate)
6. Backup/restore procedures tested and automated (FAISS + SQLite, daily schedule)
7. Incident response runbooks documented and validated via simulation
8. Structured logging with correlation IDs propagating through full pipeline
9. All environments (dev, staging, production) have Docker Compose configurations
10. Deployment time from commit to staging < 10 minutes

## Downstream Notes

- P6 feature additions will use the monitoring infrastructure to track new feature metrics
- P7 release gate requires the CD pipeline, monitoring, and runbooks to be fully operational
- P7 canary deployment relies on P5's production CD pipeline with canary strategy
- Alert thresholds established here become the baseline for P7 production readiness
