# Degradation Playbook

> Voice & Vision Assistant - Operational Playbook  
> Task: T-102 - Graceful Degradation Procedures

## Table of Contents

1. [Degradation Modes Overview](#degradation-modes-overview)
2. [Mode: FULL](#mode-full)
3. [Mode: PARTIAL](#mode-partial)
4. [Mode: MINIMAL](#mode-minimal)
5. [Mode: OFFLINE](#mode-offline)
6. [Detection and Monitoring](#detection-and-monitoring)
7. [Transition Procedures](#transition-procedures)
8. [Recovery Procedures](#recovery-procedures)
9. [User Communication Templates](#user-communication-templates)

---

## Degradation Modes Overview

The system operates in four degradation modes based on service health:

| Mode | Trigger Condition | Impact | Response |
|------|-------------------|--------|----------|
| **FULL** | All services healthy | None | Normal operation |
| **PARTIAL** | Non-critical services down | Avatar/optional features disabled | Auto-continue |
| **MINIMAL** | Critical services degraded | Local speech, core features only | Alert + monitor |
| **OFFLINE** | All cloud services unavailable | Voice-only, no vision/memory | Escalate |

### Service Classification

| Classification | Services | Impact if Down |
|----------------|----------|----------------|
| **Critical** | `deepgram`, `elevenlabs` | Triggers MINIMAL mode |
| **Important** | `ollama`, `livekit` | Triggers PARTIAL mode |
| **Non-Critical** | `tavus`, `duckduckgo` | Triggers PARTIAL mode |

---

## Mode: FULL

### Description
All services healthy, full functionality available.

### Detection
```bash
# Health endpoint returns:
curl -s .../health | jq '.status'
# "healthy"

# Degradation level:
curl -s .../metrics | grep degradation_level
# degradation_level{level="full"} 1
```

### Available Features
- ✅ Cloud STT (Deepgram)
- ✅ Cloud TTS (ElevenLabs)
- ✅ Vision processing (Ollama)
- ✅ Internet search (DuckDuckGo)
- ✅ Memory/RAG (FAISS + Ollama)
- ✅ Avatar (Tavus)
- ✅ Real-time WebRTC (LiveKit)

### Performance Expectations
| Metric | Target |
|--------|--------|
| STT latency | < 100ms |
| TTS latency | < 100ms |
| VQA latency | < 300ms |
| E2E hot path | < 500ms |

### Operator Actions
None required - normal operation.

---

## Mode: PARTIAL

### Description
Non-critical services unavailable. Core functionality intact.

### Trigger Conditions
- Tavus service unreachable
- DuckDuckGo search failing
- Important services (Ollama, LiveKit) degraded but not down

### Detection
```bash
# Degradation level:
curl -s .../metrics | grep degradation_level
# degradation_level{level="partial"} 1

# Check which services are degraded:
curl -s .../health | jq '.services[] | select(.status != "healthy")'
```

### Available Features
- ✅ Cloud STT (Deepgram)
- ✅ Cloud TTS (ElevenLabs)
- ✅ Vision processing (Ollama)
- ⚠️ Internet search (may be unavailable)
- ✅ Memory/RAG (FAISS + Ollama)
- ❌ Avatar (Tavus) - disabled
- ✅ Real-time WebRTC (LiveKit)

### Disabled Features
```python
disabled_features = {"tavus", "avatar"}
```

### User Announcement
> "Some features are temporarily unavailable. Core functionality continues."

### Performance Expectations
| Metric | Target |
|--------|--------|
| STT latency | < 100ms |
| TTS latency | < 100ms |
| VQA latency | < 300ms |
| E2E hot path | < 500ms |

### Operator Actions

1. **Monitor** (0-15 min)
   - Watch service health metrics
   - Review circuit breaker states
   - Check for auto-recovery

2. **Investigate** (if > 15 min)
   - Check external service status pages
   - Review recent deployments
   - Check network connectivity

3. **Escalate** (if > 30 min)
   - Create incident ticket
   - Notify engineering lead
   - Consider manual recovery steps

---

## Mode: MINIMAL

### Description
Critical services degraded. System falls back to local processing.

### Trigger Conditions
- Deepgram STT circuit breaker OPEN
- ElevenLabs TTS circuit breaker OPEN
- Any critical service DEGRADED for > 5 min

### Detection
```bash
# Degradation level:
curl -s .../metrics | grep degradation_level
# degradation_level{level="minimal"} 1

# Circuit breaker states:
curl -s .../metrics | grep circuit_breaker_state
# circuit_breaker_state{service="deepgram",state="open"} 1

# Alert firing:
# Alert: DegradedServiceCritical
```

### Available Features
- ⚠️ Local STT (Whisper fallback)
- ⚠️ Local TTS (Edge TTS fallback)
- ✅ Vision processing (if Ollama up)
- ❌ Internet search - disabled
- ❌ Memory/RAG - disabled
- ❌ Avatar (Tavus) - disabled
- ✅ Real-time WebRTC (LiveKit)

### Disabled Features
```python
disabled_features = {"tavus", "avatar", "search", "memory"}
use_local_stt = True
use_local_tts = True
allow_cloud_calls = False
```

### User Announcement
> "I'm experiencing connection issues. Switching to offline mode for voice."

### Performance Expectations
| Metric | Target | Notes |
|--------|--------|-------|
| STT latency | < 500ms | Local processing, slower |
| TTS latency | < 300ms | Edge TTS, adequate quality |
| VQA latency | < 500ms | If cloud available |
| E2E hot path | < 1000ms | Degraded but functional |

### Operator Actions

1. **Immediate** (0-5 min)
   - Acknowledge alert
   - Verify fallback systems are active
   - Check user impact

2. **Assess** (5-15 min)
   ```bash
   # Check cloud service status
   curl -s https://status.deepgram.com
   curl -s https://status.elevenlabs.io
   
   # Check local fallback health
   curl -s .../metrics | grep fallback_used
   ```

3. **Mitigate** (15-30 min)
   - If provider outage: Wait + monitor recovery
   - If API key issue: Rotate keys (see Security Incident runbook)
   - If rate limiting: Implement backoff

4. **Escalate** (if > 30 min)
   - Page engineering lead (P2 severity)
   - Consider switching providers
   - Update status page

### Escalation Criteria
| Duration | Action |
|----------|--------|
| 0-15 min | Monitor, auto-recovery expected |
| 15-30 min | Active investigation, notify team |
| 30-60 min | P2 incident, engineering lead involved |
| > 60 min | P1 escalation, CTO notification |

---

## Mode: OFFLINE

### Description
All cloud services unavailable. Minimal voice-only operation.

### Trigger Conditions
- All critical services (Deepgram + ElevenLabs) UNHEALTHY
- Network connectivity completely lost
- Cloud provider major outage

### Detection
```bash
# Degradation level:
curl -s .../metrics | grep degradation_level
# degradation_level{level="offline"} 1

# All critical services down:
curl -s .../health | jq '.services[] | select(.critical == true and .status == "unhealthy")'

# Alert firing:
# Alert: CloudServicesOffline (P1)
```

### Available Features
- ⚠️ Local STT (Whisper fallback)
- ⚠️ Local TTS (Edge TTS fallback)
- ❌ Vision processing - disabled
- ❌ Internet search - disabled
- ❌ Memory/RAG - disabled
- ❌ Avatar (Tavus) - disabled
- ⚠️ Real-time WebRTC (may be degraded)

### Disabled Features
```python
disabled_features = {"tavus", "avatar", "search", "memory", "vision"}
use_local_stt = True
use_local_tts = True
allow_cloud_calls = False
```

### User Announcement
> "I'm in offline mode. Only basic voice interaction is available."

### Performance Expectations
| Metric | Target | Notes |
|--------|--------|-------|
| STT latency | < 500ms | Local Whisper |
| TTS latency | < 300ms | Edge TTS |
| VQA | Unavailable | - |
| E2E hot path | < 800ms | Voice-only |

### Operator Actions

1. **Immediate** (0-5 min)
   - **P1 INCIDENT** - Page on-call immediately
   - Verify local fallbacks functioning
   - Check basic voice loop working

2. **Diagnose** (5-15 min)
   ```bash
   # Network check
   ping 8.8.8.8
   curl -s https://api.deepgram.com/health
   
   # Check for regional outage
   curl -s https://status.deepgram.com
   curl -s https://status.elevenlabs.io
   ```

3. **Communicate** (within 15 min)
   - Update status page
   - Notify stakeholders via Slack/email
   - Prepare user communication

4. **Recover** (ongoing)
   - Monitor for cloud service recovery
   - Be ready for immediate transition back
   - Document timeline

### Recovery Priority
1. Deepgram STT (enables cloud speech input)
2. ElevenLabs TTS (enables quality speech output)
3. Ollama VQA (enables vision features)
4. Other services (enhance functionality)

---

## Detection and Monitoring

### Automated Detection

The `DegradationCoordinator` automatically monitors service health:

```python
# Service health is checked via circuit breakers
from infrastructure.resilience.degradation_coordinator import (
    get_degradation_coordinator,
    DegradationLevel
)

coordinator = get_degradation_coordinator()
level = coordinator.get_degradation_level()  # FULL, PARTIAL, MINIMAL, OFFLINE
```

### Grafana Dashboard Panels

1. **Current Degradation Level** - Single stat with color coding
2. **Service Health Matrix** - Grid showing service status
3. **Degradation History** - Timeline of level changes
4. **Feature Availability** - List of enabled/disabled features

### Alert Rules

| Alert | Condition | Severity |
|-------|-----------|----------|
| `DegradedServiceNonCritical` | Non-critical service down > 5 min | Warning |
| `DegradedServiceCritical` | Critical service degraded > 2 min | High |
| `CloudServicesOffline` | All critical services down | Critical |
| `ProlongedDegradation` | MINIMAL/OFFLINE > 30 min | High |

---

## Transition Procedures

### Automatic Transitions

The system automatically transitions between modes:

```
FULL ←→ PARTIAL ←→ MINIMAL ←→ OFFLINE
```

Each transition:
1. Updates internal state
2. Adjusts feature availability
3. Sends user announcement (if callback configured)
4. Records event in history

### Manual Override

For testing or emergency intervention:

```bash
# Force specific degradation level
curl -X POST .../api/v1/degradation/force \
  -H "Content-Type: application/json" \
  -d '{"level": "minimal"}'

# Reset to auto-detection
curl -X POST .../api/v1/degradation/refresh
```

### Transition Checklist

When transitioning DOWN (more degraded):
- [ ] Verify fallback systems are active
- [ ] Confirm user announcement was sent
- [ ] Log transition in incident tracker
- [ ] Monitor error rates post-transition

When transitioning UP (less degraded):
- [ ] Verify cloud services are stable (not flapping)
- [ ] Confirm cloud processing resumes
- [ ] Send recovery announcement
- [ ] Close any related incidents

---

## Recovery Procedures

### From OFFLINE to MINIMAL

**Trigger**: At least one critical service recovers

1. Verify service health stable for > 2 min
2. Circuit breaker transitions to HALF-OPEN
3. Test requests succeed
4. Circuit breaker closes
5. DegradationCoordinator transitions to MINIMAL

### From MINIMAL to PARTIAL

**Trigger**: All critical services healthy

1. Verify both Deepgram and ElevenLabs healthy
2. Cloud calls re-enabled
3. Local fallbacks remain as backup
4. Transition to cloud processing

### From PARTIAL to FULL

**Trigger**: All services healthy

1. Verify all circuit breakers closed
2. All health checks passing
3. Optional features re-enabled
4. Normal operation resumes

### Verifying Recovery

```bash
# After recovery, verify:

# 1. Degradation level is correct
curl -s .../metrics | grep degradation_level

# 2. All features available
curl -s .../health | jq '.features'

# 3. No residual errors
curl -s .../metrics | grep error_rate

# 4. Latencies back to normal
curl -s .../metrics | grep latency_seconds
```

---

## User Communication Templates

### Entering Degraded Mode

**PARTIAL**:
> "Some optional features are temporarily unavailable, but I can still help you with most tasks. Core voice and vision capabilities continue to work normally."

**MINIMAL**:
> "I'm experiencing some connection issues and have switched to a backup system for voice. You might notice slightly slower responses, but I'm still here to help. Some features like internet search and memory recall are temporarily unavailable."

**OFFLINE**:
> "I'm currently in offline mode due to connection issues. I can still have a basic conversation with you, but vision features and some other capabilities are temporarily unavailable. I'll let you know when full service is restored."

### Recovery Announcements

**Returning to FULL**:
> "Good news - all services are back to normal. Full functionality has been restored."

**Returning to PARTIAL from MINIMAL**:
> "Connection issues have been resolved. Voice quality should be back to normal now."

### During Extended Outage (> 30 min)

> "I apologize for the continued service disruption. Our team is actively working to restore full functionality. In the meantime, I can help with basic voice interaction. Thank you for your patience."

---

## Quick Reference

### Mode Summary Table

| Mode | STT | TTS | Vision | Search | Memory | Avatar |
|------|-----|-----|--------|--------|--------|--------|
| FULL | Cloud | Cloud | ✅ | ✅ | ✅ | ✅ |
| PARTIAL | Cloud | Cloud | ✅ | ⚠️ | ✅ | ❌ |
| MINIMAL | Local | Local | ⚠️ | ❌ | ❌ | ❌ |
| OFFLINE | Local | Local | ❌ | ❌ | ❌ | ❌ |

### Escalation Quick Guide

| Mode | Duration | Action |
|------|----------|--------|
| PARTIAL | < 30 min | Monitor |
| PARTIAL | > 30 min | Investigate |
| MINIMAL | < 15 min | Monitor |
| MINIMAL | > 15 min | P2 Incident |
| OFFLINE | Any | P1 Incident |

### Key Commands

```bash
# Check current mode
curl -s .../health | jq '.degradation_level'

# Force refresh
curl -X POST .../api/v1/degradation/refresh

# View history
curl -s .../api/v1/degradation/history | jq

# Check feature availability
curl -s .../api/v1/degradation/features | jq
```

---

## Related Runbooks

- [Incident Response](./incident-response.md) - General incident procedures
- [Cloud Service Outage](./incident-response.md#1-cloud-service-outage) - Detailed outage response
- [Deployment Rollback](./incident-response.md#4-deployment-rollback) - If degradation caused by deployment
