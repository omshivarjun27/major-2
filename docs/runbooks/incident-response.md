# Incident Response Runbooks

> Voice & Vision Assistant - Operational Runbooks  
> Task: T-101 - Incident Response Runbook

## Table of Contents

1. [Cloud Service Outage](#1-cloud-service-outage)
2. [VRAM Exhaustion / CUDA OOM](#2-vram-exhaustion--cuda-oom)
3. [FAISS Index Corruption](#3-faiss-index-corruption)
4. [Deployment Rollback](#4-deployment-rollback)
5. [Memory Leak Escalation](#5-memory-leak-escalation)
6. [Security Incident](#6-security-incident-api-key-compromise)

---

## 1. Cloud Service Outage

### Detection Criteria
- Alert: `cloud_service_unavailable` firing
- Circuit breaker open for 5+ minutes on critical service
- Health endpoint returning degraded status
- User reports: "Assistant not responding" or "Connection errors"

### Severity Classification
| Affected Services | Severity | Response Time |
|-------------------|----------|---------------|
| All services | P1 - Critical | 15 min |
| STT or TTS only | P2 - High | 30 min |
| Search/optional services | P3 - Medium | 2 hours |

### Response Steps

1. **Assess Scope** (0-5 min)
   ```bash
   # Check health endpoint
   curl -s https://api.voice-vision.example.com/health | jq
   
   # Check circuit breaker states
   curl -s https://api.voice-vision.example.com/metrics | grep circuit_breaker
   ```

2. **Verify External Service Status** (5-10 min)
   - Deepgram: https://status.deepgram.com
   - ElevenLabs: https://status.elevenlabs.io
   - Ollama/SiliconFlow: Check internal monitoring

3. **Engage Fallback Mode** (10-15 min)
   ```bash
   # If STT down, system auto-switches to Whisper fallback
   # If TTS down, system auto-switches to Edge TTS
   
   # Verify fallback is active
   curl -s .../metrics | grep fallback_used
   ```

4. **Communicate Status** (15+ min)
   - Update status page
   - Notify affected users via in-app message
   - Escalate to provider support if prolonged

5. **Monitor Recovery**
   - Watch for circuit breaker transitions to half-open
   - Verify error rates returning to baseline
   - Confirm health endpoint shows "ok"

### Escalation Path
```
On-call Engineer → Engineering Lead → CTO (if > 2 hours)
```

### Post-Incident
- [ ] Create incident report within 24 hours
- [ ] Document root cause
- [ ] Update runbook if needed
- [ ] Schedule post-mortem if P1/P2

---

## 2. VRAM Exhaustion / CUDA OOM

### Detection Criteria
- Alert: `high_vram_usage` (> 90% for 10 min)
- Alert: `cuda_oom_error` (any occurrence)
- Model inference timeouts increasing
- Log pattern: `CUDA out of memory`

### Severity Classification
| Impact | Severity |
|--------|----------|
| Vision pipeline down | P1 - Critical |
| Degraded performance | P2 - High |
| Single model affected | P3 - Medium |

### Response Steps

1. **Immediate Triage** (0-5 min)
   ```bash
   # Check VRAM usage
   nvidia-smi --query-gpu=memory.used,memory.total --format=csv
   
   # Check running processes
   nvidia-smi pmon -s um
   ```

2. **Clear VRAM** (5-10 min)
   ```bash
   # Graceful model unload (preferred)
   curl -X POST .../api/v1/models/unload-unused
   
   # Force clear if needed (causes brief interruption)
   sudo systemctl restart voice-vision-api
   ```

3. **Identify Cause** (10-20 min)
   - Check for batch size increases
   - Look for memory leak indicators in logs
   - Review recent deployments

4. **Apply Fix**
   - If batch size: Reduce in config
   - If leak: Rollback to previous version
   - If growth: Enable periodic model unloading

### Prevention Checklist
- [ ] Set `PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512`
- [ ] Enable gradient checkpointing for large models
- [ ] Configure periodic VRAM cleanup cron

---

## 3. FAISS Index Corruption

### Detection Criteria
- Alert: `faiss_query_errors` spike
- Error logs: `Index read failed` or `Dimension mismatch`
- RAG pipeline returning no results
- Memory search returning garbage results

### Severity Classification
| Impact | Severity |
|--------|----------|
| All memory search broken | P1 - Critical |
| Single index corrupted | P2 - High |

### Response Steps

1. **Assess Damage** (0-5 min)
   ```bash
   # Test index integrity
   python -c "
   import faiss
   try:
       idx = faiss.read_index('data/faiss/memory.index')
       print(f'Index OK: {idx.ntotal} vectors')
   except Exception as e:
       print(f'Index CORRUPT: {e}')
   "
   ```

2. **Switch to Backup** (5-15 min)
   ```bash
   # List available backups
   ls -la data/backups/faiss/memory/
   
   # Restore from latest backup
   python -c "
   from infrastructure.backup import create_faiss_backup_manager
   mgr = create_faiss_backup_manager()
   backups = mgr.list_backups('memory')
   mgr.restore(backups[0].backup_id, 'memory', 'data/faiss/memory.index')
   "
   ```

3. **Verify Restoration**
   ```bash
   # Test query
   curl -X POST .../api/v1/memory/search \
     -d '{"query": "test query", "k": 5}'
   ```

4. **Investigate Root Cause**
   - Check for concurrent write access
   - Review recent ingestion jobs
   - Check disk health

### Recovery Notes
- If no backup available, index must be rebuilt from source data
- Rebuild time: ~10 min per 10k vectors
- Memory will be degraded until rebuild completes

---

## 4. Deployment Rollback

### Detection Criteria
- Post-deployment smoke tests failing
- Error rate spike > 5% after deployment
- User-reported regressions
- Alert: `deployment_health_check_failed`

### Severity Classification
| Impact | Severity |
|--------|----------|
| Production broken | P1 - Critical |
| Feature regression | P2 - High |
| Minor issues | P3 - Medium |

### Response Steps

1. **Confirm Need for Rollback** (0-5 min)
   - Check error rates in Grafana
   - Review recent alerts
   - Verify user reports

2. **Execute Rollback** (5-10 min)
   ```bash
   # Get previous version
   docker images | grep voice-vision | head -5
   
   # Rollback via GitHub Actions (recommended)
   gh workflow run deploy-production.yml \
     -f version=<previous-version>
   
   # Or manual rollback
   docker-compose pull voice-vision:previous-tag
   docker-compose up -d
   ```

3. **Verify Rollback** (10-15 min)
   ```bash
   # Check health
   curl -s .../health | jq
   
   # Run smoke tests
   pytest tests/integration/test_smoke.py -v
   ```

4. **Communicate**
   - Update deployment channel
   - Create issue for failed deployment
   - Schedule fix review

### Rollback Decision Matrix
| Error Rate | P95 Latency | Action |
|------------|-------------|--------|
| > 5% | > 600ms | Immediate rollback |
| > 2% | > 500ms | Rollback within 30 min |
| < 2% | < 500ms | Monitor, rollback if worsening |

---

## 5. Memory Leak Escalation

### Detection Criteria
- Alert: `memory_leak_detected` (RSS growth > 100MB/hour)
- Gradual increase in RAM usage over hours/days
- OOM kills in container logs
- Service restarts due to memory pressure

### Severity Classification
| Time to OOM | Severity |
|-------------|----------|
| < 1 hour | P1 - Critical |
| 1-4 hours | P2 - High |
| > 4 hours | P3 - Medium |

### Response Steps

1. **Assess Current State** (0-5 min)
   ```bash
   # Check memory usage trend
   curl -s .../metrics | grep ram_usage
   
   # Check container stats
   docker stats --no-stream voice-vision-api
   ```

2. **Collect Diagnostic Data** (5-15 min)
   ```bash
   # Generate memory profile
   curl -X POST .../api/v1/debug/memory-profile > mem_$(date +%s).json
   
   # Get heap dump if Python
   curl -X POST .../api/v1/debug/heap-dump
   ```

3. **Mitigate** (15-30 min)
   ```bash
   # Immediate: Increase memory limit if possible
   # Short-term: Schedule more frequent restarts
   
   # Add restart schedule
   echo "0 */4 * * * docker restart voice-vision-api" | crontab -
   ```

4. **Identify Root Cause**
   - Compare memory profiles before/after
   - Look for growing collections/caches
   - Check for circular references
   - Review recent code changes

### Common Leak Sources
- Unbounded caches (solution: add TTL/max size)
- Event listeners not cleaned up
- Circular references in closures
- Large objects in long-lived sessions

---

## 6. Security Incident (API Key Compromise)

### Detection Criteria
- Unusual API usage patterns
- Authentication from unknown IPs
- Alert: `api_key_usage_anomaly`
- External report of key exposure

### Severity Classification
**ALWAYS P1 - CRITICAL**

### Response Steps

1. **Immediate Actions** (0-10 min)
   ```bash
   # Revoke compromised key IMMEDIATELY
   # Deepgram
   curl -X DELETE https://api.deepgram.com/v1/keys/{key_id}
   
   # ElevenLabs
   curl -X DELETE https://api.elevenlabs.io/v1/user/subscription/keys/{key_id}
   ```

2. **Rotate All Keys** (10-30 min)
   - Generate new keys for all services
   - Update secrets in deployment:
     ```bash
     # Update GitHub secrets
     gh secret set DEEPGRAM_API_KEY
     gh secret set ELEVEN_API_KEY
     
     # Trigger deployment with new keys
     ```

3. **Assess Impact** (30-60 min)
   - Review API usage logs for compromised period
   - Check for unauthorized data access
   - Estimate financial impact

4. **Notify Stakeholders**
   - Security team
   - Legal/compliance (if data breach)
   - Affected users (if their data accessed)

5. **Post-Incident**
   - [ ] Document timeline of compromise
   - [ ] Identify how key was exposed
   - [ ] Implement additional controls
   - [ ] Security review within 48 hours

### Prevention Checklist
- [ ] Never commit keys to git
- [ ] Use secret scanning in CI
- [ ] Rotate keys quarterly
- [ ] Use least-privilege API keys
- [ ] Enable usage alerts on all services

---

## Post-Incident Review Template

```markdown
## Incident Summary
- **Date**: YYYY-MM-DD
- **Duration**: X hours Y minutes
- **Severity**: P1/P2/P3
- **Category**: [Outage/Security/Data/Performance]

## Timeline
- HH:MM - Detection
- HH:MM - Response started
- HH:MM - Mitigation applied
- HH:MM - Resolution confirmed

## Root Cause
[Description of underlying issue]

## Impact
- Users affected: X
- Revenue impact: $X
- Data loss: Yes/No

## Actions Taken
1. [Action 1]
2. [Action 2]

## Follow-up Items
- [ ] Item 1 - Owner - Due date
- [ ] Item 2 - Owner - Due date

## Lessons Learned
- What went well:
- What could improve:
```

---

## Quick Reference

### Emergency Contacts
| Role | Contact | Escalation |
|------|---------|------------|
| On-call Engineer | PagerDuty | Auto |
| Engineering Lead | Slack @eng-lead | Manual |
| Security Lead | security@company.com | Immediate |

### Key URLs
- Status Page: https://status.voice-vision.example.com
- Grafana: https://grafana.internal/dashboards
- PagerDuty: https://company.pagerduty.com
- Runbooks: This document

### Critical Commands
```bash
# Health check
curl -s .../health | jq

# Restart service
docker-compose restart voice-vision-api

# View logs
docker-compose logs -f --tail=100 voice-vision-api

# Force garbage collection
curl -X POST .../api/v1/debug/gc
```
