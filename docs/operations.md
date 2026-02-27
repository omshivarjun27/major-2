# Voice & Vision Assistant — Operations Guide

> Comprehensive operational documentation for SRE/DevOps engineers  
> Task: T-107 - Operational Documentation

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Monitoring Stack](#2-monitoring-stack)
3. [Backup Procedures](#3-backup-procedures)
4. [CD Pipeline](#4-cd-pipeline)
5. [Environment Management](#5-environment-management)
6. [Log Management](#6-log-management)
7. [Health Endpoints](#7-health-endpoints)
8. [Troubleshooting](#8-troubleshooting)
9. [Quick Start for Operators](#9-quick-start-for-operators)

---

## 1. Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    Voice & Vision Assistant                      │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────────┐│
│  │ REST API│  │ WebRTC  │  │  VQA    │  │  Spatial Perception ││
│  │  :8000  │  │  Agent  │  │ Pipeline│  │      Pipeline       ││
│  │         │  │  :8081  │  │         │  │                     ││
│  └────┬────┘  └────┬────┘  └────┬────┘  └──────────┬──────────┘│
│       │            │            │                   │           │
│  ┌────┴────────────┴────────────┴───────────────────┴──────┐   │
│  │               Infrastructure Layer                       │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │   │
│  │  │ Deepgram │ │ElevenLabs│ │  Ollama  │ │ LiveKit  │   │   │
│  │  │   (STT)  │ │   (TTS)  │ │  (VQA)   │ │ (WebRTC) │   │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │   │
│  └──────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                     Data Layer                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐    │
│  │  FAISS   │  │  SQLite  │  │   QR     │  │    Logs      │    │
│  │  Index   │  │  Memory  │  │  Cache   │  │   (.json)    │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Service Dependencies

| Service | Type | Critical | Fallback |
|---------|------|----------|----------|
| Deepgram | STT | Yes | Whisper local |
| ElevenLabs | TTS | Yes | Edge TTS |
| Ollama | VQA | Yes | None |
| LiveKit | WebRTC | Yes | None |
| DuckDuckGo | Search | No | Disabled |
| Tavus | Avatar | No | Disabled |

### Latency SLAs

| Component | Target | Hot Path |
|-----------|--------|----------|
| STT | < 100ms | Yes |
| VQA | < 300ms | Yes |
| TTS | < 100ms | Yes |
| Total E2E | < 500ms | - |

---

## 2. Monitoring Stack

### Components

```
┌───────────────────────────────────────────────────────┐
│                   Monitoring Stack                     │
│                                                        │
│  ┌──────────────┐    ┌──────────────┐                │
│  │  Prometheus  │───▶│  Grafana     │                │
│  │    :9090     │    │    :3000     │                │
│  └──────┬───────┘    └──────────────┘                │
│         │                                             │
│  ┌──────┴───────┐    ┌──────────────┐                │
│  │ Alertmanager │    │    Loki      │                │
│  │    :9093     │    │    :3100     │                │
│  └──────────────┘    └──────────────┘                │
└───────────────────────────────────────────────────────┘
```

### Prometheus Configuration

**Scrape targets:**
- Application metrics: `http://assistant:8000/metrics`
- Node metrics: `http://node-exporter:9100/metrics`

**Key metrics:**
```promql
# Request rate
rate(voice_vision_request_count_total[5m])

# Error rate
sum(rate(voice_vision_request_count_total{status=~"5.."}[5m])) 
  / sum(rate(voice_vision_request_count_total[5m]))

# P95 latency
histogram_quantile(0.95, rate(voice_vision_request_latency_seconds_bucket[5m]))

# VRAM usage
voice_vision_vram_usage_bytes / 8589934592 * 100
```

### Grafana Dashboards

| Dashboard | UID | Purpose |
|-----------|-----|---------|
| System Health | voice-vision-system-health | CPU, RAM, VRAM, queues |
| Pipeline Performance | voice-vision-pipeline | STT/VQA/TTS latencies |
| Service Resilience | voice-vision-resilience | Circuit breakers, errors |
| Health Status & SLA | voice-vision-health-status | Service health, uptime |

### Alert Rules

| Alert | Condition | Severity |
|-------|-----------|----------|
| HotPathSLAViolation | P95 > 500ms for 5m | Critical |
| HighErrorRate | 5xx > 5% for 2m | Warning |
| CircuitBreakerOpen | Any service > 5m | Warning |
| HighVRAM | > 90% for 10m | Warning |
| MemoryLeakDetected | RSS growth > 100MB/hr | Warning |
| DiskSpaceLow | < 10% free | Warning |

---

## 3. Backup Procedures

### Backup Schedule

| Component | Schedule | Retention | Type |
|-----------|----------|-----------|------|
| FAISS Index | Daily 2:00 AM | 30 days | Incremental |
| SQLite Databases | Daily 2:30 AM | 30 days | Full |
| Configurations | On change | 90 days | Full |

### Manual Backup Commands

```bash
# Trigger FAISS backup
curl -X POST http://localhost:8000/api/v1/backup/faiss

# Trigger SQLite backup
curl -X POST http://localhost:8000/api/v1/backup/sqlite

# List backups
curl http://localhost:8000/api/v1/backup/list

# Verify backup integrity
curl -X POST http://localhost:8000/api/v1/backup/verify
```

### Restore Procedure

```bash
# 1. Stop the application
docker compose stop assistant

# 2. Restore FAISS index
python -c "
from infrastructure.backup import create_faiss_backup_manager
mgr = create_faiss_backup_manager()
backups = mgr.list_backups('memory')
mgr.restore(backups[0].backup_id, 'memory', 'data/faiss/memory.index')
"

# 3. Restore SQLite
python -c "
from infrastructure.backup import create_sqlite_backup_manager
mgr = create_sqlite_backup_manager()
backups = mgr.list_backups('memory.db')
mgr.restore(backups[0].backup_id, 'memory.db', 'data/memory.db')
"

# 4. Restart application
docker compose start assistant

# 5. Verify health
curl http://localhost:8000/health
```

### Backup Monitoring

Prometheus metric: `voice_vision_backup_last_success_timestamp`

Alert if no successful backup in 48 hours.

---

## 4. CD Pipeline

### Pipeline Overview

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  Push   │───▶│  Build  │───▶│ Staging │───▶│  Prod   │
│         │    │ & Test  │    │ Deploy  │    │ Deploy  │
└─────────┘    └─────────┘    └────┬────┘    └────┬────┘
                                   │              │
                              Automated      Manual Approval
                                   │              │
                              Smoke Tests    Canary 10%
                                             2hr monitor
```

### Deployment Targets

| Environment | Trigger | Strategy | Approval |
|-------------|---------|----------|----------|
| Staging | Push to main | Blue-green | Automatic |
| Production | Manual | Canary 10% | Required |

### Deployment Commands

```bash
# Deploy to staging (automatic on main push)
gh workflow run deploy-staging.yml

# Deploy to production
gh workflow run deploy-production.yml \
  -f version=v1.2.3 \
  -f skip_canary=false

# Rollback production
gh workflow run deploy-production.yml \
  -f version=v1.2.2 \
  -f rollback=true
```

### Canary Deployment

1. Deploy to 10% of traffic
2. Monitor for 2 hours
3. Check metrics:
   - Error rate < 1%
   - P95 latency < 600ms
4. Auto-rollback if thresholds exceeded
5. Full rollout if healthy

### Rollback Procedure

```bash
# Get previous version
docker images | grep voice-vision | head -5

# Rollback via GitHub Actions
gh workflow run deploy-production.yml \
  -f version=<previous-version> \
  -f rollback=true

# Or manual rollback
docker-compose pull voice-vision:<previous-tag>
docker-compose up -d

# Verify
curl http://localhost:8000/health
```

---

## 5. Environment Management

### Configuration Files

| Environment | Config File | Settings |
|-------------|-------------|----------|
| Development | `configs/development.yaml` | Debug, relaxed thresholds |
| Staging | `configs/staging.yaml` | Prod-like, more metrics |
| Production | `configs/production.yaml` | Strict SLAs |

### Environment Variables

Core variables (all environments):
```bash
ENVIRONMENT=production|staging|development
LOG_LEVEL=DEBUG|INFO|WARNING|ERROR
LOG_FORMAT=json|text
PII_SCRUB=true|false
```

Feature flags:
```bash
SPATIAL_PERCEPTION_ENABLED=true
ENABLE_QR_SCANNING=true
FACE_ENGINE_ENABLED=true
AUDIO_ENGINE_ENABLED=true
MEMORY_ENABLED=false  # Requires consent
```

### Secrets Management

**Production secrets (Docker Secrets):**
- `deepgram_api_key`
- `elevenlabs_api_key`
- `ollama_api_key`
- `livekit_api_key`
- `livekit_api_secret`

```bash
# Create Docker secret
echo "your-api-key" | docker secret create deepgram_api_key -

# List secrets
docker secret ls

# Rotate secret
docker secret rm deepgram_api_key
echo "new-api-key" | docker secret create deepgram_api_key -
docker service update --secret-rm deepgram_api_key --secret-add deepgram_api_key assistant
```

### Configuration Diff

```bash
# Compare staging vs production
python -c "
from shared.config.environment import config_diff
diff = config_diff('staging', 'production')
print(diff)
"
```

---

## 6. Log Management

### Log Locations

| Type | Location | Format |
|------|----------|--------|
| Application | `/app/.runtime/logs/voice-vision.log` | JSON |
| Access logs | `/app/.runtime/logs/access.log` | JSON |
| Error logs | `/app/.runtime/logs/error.log` | JSON |

### Log Rotation

- **Daily rotation** at midnight
- **Size-based rotation** at 100MB
- **Compression** using gzip
- **Retention**: 30 days (production), 14 days (staging)

### Log Queries (Loki)

```logql
# Errors in last hour
{job="voice-vision"} |= "ERROR" | json

# Slow requests (> 500ms)
{job="voice-vision"} | json | latency_ms > 500

# Specific session
{job="voice-vision"} | json | session_id = "ses_abc123"

# Circuit breaker events
{job="voice-vision"} |= "circuit_breaker"
```

### Log Cleanup

```bash
# Manual cleanup (dry run)
python -c "
from shared.logging import cleanup_old_logs
deleted = cleanup_old_logs(retention_days=30, dry_run=True)
print(f'Would delete {len(deleted)} files')
"

# Execute cleanup
python -c "
from shared.logging import cleanup_old_logs
deleted = cleanup_old_logs(retention_days=30, dry_run=False)
print(f'Deleted {len(deleted)} files')
"
```

---

## 7. Health Endpoints

### Endpoints

| Endpoint | Purpose | Response |
|----------|---------|----------|
| `GET /health` | Liveness check | 200 OK |
| `GET /health/ready` | Readiness check | 200/503 |
| `GET /health/detailed` | Component status | JSON |
| `GET /metrics` | Prometheus metrics | Text |

### Health Response Format

```json
{
  "status": "healthy",
  "degradation_level": "full",
  "services": {
    "deepgram": {"status": "healthy", "latency_ms": 45},
    "elevenlabs": {"status": "healthy", "latency_ms": 32},
    "ollama": {"status": "healthy", "latency_ms": 120},
    "livekit": {"status": "healthy", "latency_ms": 15}
  },
  "features": {
    "vision": true,
    "memory": true,
    "search": true,
    "avatar": false
  },
  "uptime_seconds": 86400,
  "version": "1.2.3"
}
```

### Degradation Levels

| Level | Meaning | Impact |
|-------|---------|--------|
| FULL | All healthy | Normal operation |
| PARTIAL | Non-critical down | Avatar/search disabled |
| MINIMAL | Critical degraded | Local STT/TTS |
| OFFLINE | All cloud down | Voice-only mode |

---

## 8. Troubleshooting

### Decision Tree

```
Problem Detected
       │
       ▼
┌──────────────────┐
│ Check /health    │
└────────┬─────────┘
         │
    ┌────┴────┐
    │         │
  Healthy   Unhealthy
    │         │
    ▼         ▼
Check logs  Check circuit
             breakers
    │         │
    ▼         ▼
Performance  Service
issue        outage
    │         │
    ▼         ▼
Profile     Check external
metrics     status pages
```

### Common Issues

#### High Latency

1. Check Grafana latency dashboard
2. Identify slow component (STT/VQA/TTS)
3. Check VRAM usage
4. Check queue sizes
5. Consider scaling workers

```bash
# Check queue sizes
curl -s localhost:8000/metrics | grep queue_size

# Check worker utilization
curl -s localhost:8000/metrics | grep worker
```

#### Circuit Breaker Open

1. Identify affected service
2. Check external service status
3. Review recent logs for errors
4. Wait for half-open transition
5. If persistent, check API keys

```bash
# Check circuit breaker states
curl -s localhost:8000/metrics | grep circuit_breaker_state

# Force refresh (testing only)
curl -X POST localhost:8000/api/v1/circuit-breaker/reset
```

#### Memory Leak

1. Check RAM growth trend
2. Generate memory profile
3. Compare before/after snapshots
4. Identify growing objects
5. Restart as temporary fix

```bash
# Generate profile
curl -X POST localhost:8000/api/v1/debug/memory-profile > profile.json

# Force GC
curl -X POST localhost:8000/api/v1/debug/gc
```

#### VRAM Exhaustion

1. Check VRAM metrics
2. Unload unused models
3. Reduce batch sizes
4. Restart service

```bash
# Check VRAM
nvidia-smi --query-gpu=memory.used,memory.total --format=csv

# Unload models
curl -X POST localhost:8000/api/v1/models/unload-unused
```

---

## 9. Quick Start for Operators

### Daily Checks

1. **Health Status**
   ```bash
   curl -s http://localhost:8000/health | jq '.status'
   ```

2. **Error Rate** (Grafana or Prometheus)
   ```bash
   curl -s 'http://prometheus:9090/api/v1/query?query=rate(voice_vision_error_count_total[1h])'
   ```

3. **Backup Status**
   ```bash
   curl -s http://localhost:8000/api/v1/backup/status
   ```

### Emergency Commands

```bash
# Restart service
docker compose restart assistant

# View recent logs
docker compose logs -f --tail=100 assistant

# Force health refresh
curl -X POST http://localhost:8000/api/v1/health/refresh

# Trigger immediate backup
curl -X POST http://localhost:8000/api/v1/backup/now

# Enable debug logging temporarily
curl -X POST http://localhost:8000/api/v1/config/log-level -d '{"level": "DEBUG"}'
```

### Key URLs

| Resource | URL |
|----------|-----|
| API Health | `http://localhost:8000/health` |
| Prometheus | `http://localhost:9090` |
| Grafana | `http://localhost:3000` |
| Alertmanager | `http://localhost:9093` |
| Loki | `http://localhost:3100` |

### On-Call Checklist

- [ ] Check Grafana dashboards
- [ ] Review recent alerts
- [ ] Verify backup status
- [ ] Check disk space
- [ ] Review error logs
- [ ] Verify circuit breaker states
- [ ] Check VRAM/RAM usage

---

## Related Documentation

- [Incident Response Runbook](runbooks/incident-response.md)
- [Degradation Playbook](runbooks/degradation-playbook.md)
- [AGENTS.md](../AGENTS.md) - System overview
