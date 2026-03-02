# Operations Guide

**Version**: 1.0.0 | **Date**: 2026-03-02

This guide covers deployment, monitoring, scaling, and incident response for the
Voice & Vision Assistant in production.

---

## 1. Service Overview

| Service | Port | Purpose |
|---------|------|---------|
| API server | 8000 | FastAPI REST endpoints |
| Realtime agent | 8081 | LiveKit WebRTC agent |

Both services run inside a single Docker container by default.

---

## 2. Deployment

### Prerequisites

```bash
# Validate environment before deploying
python scripts/validate_env.py

# Required variables: LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET,
#                     DEEPGRAM_API_KEY, ELEVEN_API_KEY
```

### Docker Deployment

```bash
# Build the production image
docker build -f deployments/docker/Dockerfile -t voice-vision-assistant:1.0.0 .

# Run with environment file
docker run -d \
  --name vva \
  -p 8000:8000 \
  -p 8081:8081 \
  --env-file .env \
  --restart unless-stopped \
  voice-vision-assistant:1.0.0

# Verify health
curl http://localhost:8000/health
```

### Docker Compose (local testing)

```bash
docker compose -f docker-compose.test.yml up
```

### Canary Deployment

See `docs/canary-deployment.md` for the full canary workflow.

Quick start:
```bash
python scripts/canary_deploy.py start --image voice-vision-assistant:1.1.0
python scripts/canary_promote.py status
python scripts/canary_promote.py promote --weight 100
```

---

## 3. Health Checks

| Endpoint | Method | Expected Response |
|----------|--------|-------------------|
| `/health` | GET | `{"status": "ok"}` HTTP 200 |
| `/health/services` | GET | Service dependency status |

The Docker `HEALTHCHECK` probes `/health` every 30 seconds.

---

## 4. Monitoring

### Key Metrics

| Metric | Alert Threshold | Description |
|--------|----------------|-------------|
| P95 API latency | > 500 ms | Hot-path SLA |
| Error rate | > 0.5% | Request failures |
| CPU utilisation | > 85% | Sustained 5 min |
| Memory usage | > 90% | Container memory |

### Logs

Logs are emitted as structured JSON to stdout/stderr. Collect with your log aggregator.

Example log entry:
```json
{"ts": "2026-03-02T10:00:00Z", "level": "INFO", "module": "core.vqa", "msg": "VQA completed", "latency_ms": 280}
```

PII (faces, names, API keys) is scrubbed automatically. Debug mode logs more detail.

---

## 5. Scaling

The service is stateless (except optional local FAISS index). Scale horizontally:

```bash
docker run -d ... voice-vision-assistant:1.0.0   # Instance 1 (port 8000)
docker run -d -p 8001:8000 ... voice-vision-assistant:1.0.0  # Instance 2
```

Place a load balancer (nginx, Caddy, etc.) in front.

---

## 6. Backup & Recovery

### Data to back up

| Path | Contents | Frequency |
|------|----------|-----------|
| `data/` | Face embeddings, consent records | Daily |
| `qr_cache/` | QR scan cache | Weekly or on-demand |
| `.env` | Configuration (store in secrets manager) | On change |

### Recovery procedure

1. Stop the container: `docker stop vva`
2. Restore `data/` from backup
3. Restart the container: `docker start vva`
4. Verify health: `curl http://localhost:8000/health`

---

## 7. Common Operational Tasks

### Restart the service

```bash
docker restart vva
```

### View live logs

```bash
docker logs -f vva
```

### Update to new version

```bash
docker pull voice-vision-assistant:1.1.0
docker stop vva && docker rm vva
docker run -d --name vva -p 8000:8000 -p 8081:8081 \
  --env-file .env voice-vision-assistant:1.1.0
```

Or use the canary workflow for zero-downtime upgrade.

### Run smoke tests after deployment

```bash
python scripts/run_smoke.py --base-url http://localhost:8000
```

---

## 8. Incident Response

See `docs/runbooks/incident-response.md` for the full playbook.

Quick reference:

| Severity | Response Time | Escalation |
|----------|--------------|------------|
| P1 — Service down | 15 min | On-call → Lead |
| P2 — Degraded | 1 hour | On-call |
| P3 — Minor | Next business day | Team |

Rollback command (< 60 seconds):
```bash
python scripts/canary_promote.py rollback --reason "production incident P1"
```
