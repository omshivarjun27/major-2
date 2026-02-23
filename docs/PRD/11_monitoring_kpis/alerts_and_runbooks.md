---
title: "Alerts & Runbooks"
version: 1.0.0
date: 2026-02-22T18:00:00Z
architecture_mode: hybrid_cloud_local_gpu
related_artifacts:
  - docs/PRD/11_monitoring_kpis/monitoring_plan.md
  - docs/analysis/hybrid_readiness.md
  - docs/analysis/component_inventory.json
---

# Alerts & Runbooks

This document defines alert thresholds, severity levels, and operational runbooks for the Voice & Vision Assistant. Each alert includes detection criteria, escalation rules, and step-by-step remediation procedures.

---

## Alert 1: GPU Memory Threshold

### Detection

| Parameter | Value |
|-----------|-------|
| **Metric** | `torch.cuda.memory_allocated()` on device cuda:0 |
| **WARNING threshold** | > 6,144 MB (6 GB — 75% of 8 GB RTX 4060) |
| **CRITICAL threshold** | > 7,680 MB (7.5 GB — 93.75% of 8 GB RTX 4060) |
| **Evaluation window** | Immediate (per-inference check) |
| **Source component** | PerceptionWorkerPool, PipelineMonitor |

### Severity Escalation

| Level | Condition | Action |
|-------|-----------|--------|
| **WARNING** | VRAM > 6 GB sustained for > 30s | Log warning, emit metric, notify operator |
| **CRITICAL** | VRAM > 7.5 GB at any point | Immediate intervention required |

### Runbook

**Goal**: Reduce GPU VRAM usage below the 6 GB warning threshold to prevent OOM crashes.

1. **Identify active models**
   - Check which GPU models are currently loaded:
     ```python
     import torch
     print(f"Allocated: {torch.cuda.memory_allocated() / 1e9:.2f} GB")
     print(f"Peak: {torch.cuda.max_memory_allocated() / 1e9:.2f} GB")
     ```
   - Review environment flags: `SPATIAL_USE_YOLO`, `SPATIAL_USE_MIDAS`, `ENABLE_FACE`, `EMBEDDING_MODEL`

2. **Identify VRAM leak**
   - Check if peak allocation grows monotonically over time (indicates leak)
   - Look for unreleased tensors: `torch.cuda.memory_summary()`
   - Check if models are being re-loaded without releasing previous instances

3. **Restart worker pool**
   - Restart PerceptionWorkerPool to release stale GPU allocations
   - Use `/debug/workers` endpoint to check pool state
   - If pool restart fails, restart the entire agent process

4. **Disable non-critical GPU models to free VRAM**
   - Priority order for disabling (least critical first):
     1. Face detection (`ENABLE_FACE=false`) — frees ~300 MB
     2. MiDaS depth estimation (`SPATIAL_USE_MIDAS=false`) — frees ~100 MB, falls back to SimpleDepthEstimator
     3. YOLO detection (`SPATIAL_USE_YOLO=false`) — frees ~200 MB, falls back to MockObjectDetector
     4. EasyOCR — falls back to Tesseract (CPU-only) — frees ~500 MB
   - Do NOT disable qwen3-embedding:4b (~2 GB) unless absolutely necessary — it disables the entire memory system

5. **Post-incident**
   - Reset peak memory tracker: `torch.cuda.reset_peak_memory_stats()`
   - Monitor VRAM for 10 minutes to confirm stability
   - File incident report if caused by a code change

---

## Alert 2: Cloud Timeout Threshold

### Detection

| Parameter | Value |
|-----------|-------|
| **Metric** | Cloud service response time (per-call) |
| **qwen3.5:cloud timeout** | > 5,000 ms |
| **Deepgram timeout** | > 3,000 ms |
| **ElevenLabs timeout** | > 3,000 ms |
| **WARNING condition** | Single timeout event |
| **CRITICAL condition** | 3 consecutive timeouts for the same service within 60 seconds |
| **Source component** | OllamaHandler, Deepgram plugin, ElevenLabs adapter |

### Severity Escalation

| Level | Condition | Action |
|-------|-----------|--------|
| **WARNING** | Single timeout | Log warning with service name, latency, and timestamp |
| **CRITICAL** | 3 consecutive timeouts within 60s | Activate fallback, alert operator |

### Runbook

**Goal**: Restore cloud service connectivity or activate fallback mechanisms.

1. **Check cloud service status**
   - Verify service is reachable from the local network:
     ```bash
     # qwen3.5:cloud (Ollama cloud runtime)
     curl -s -o /dev/null -w "%{http_code}" https://<ollama-cloud-endpoint>/health

     # Deepgram
     curl -s -o /dev/null -w "%{http_code}" https://api.deepgram.com/

     # ElevenLabs
     curl -s -o /dev/null -w "%{http_code}" https://api.elevenlabs.io/
     ```
   - Check provider status pages for known outages

2. **Verify network connectivity**
   - Test DNS resolution: `nslookup api.deepgram.com`
   - Test HTTPS connectivity: `curl -v https://api.deepgram.com/`
   - Check for firewall or proxy changes
   - Verify API keys are still valid (check for 401/403 responses)

3. **Activate fallback mechanisms**
   - **qwen3.5:cloud timeout**: StubLLMClient automatically activates, returning "I don't have enough context to answer that" — no manual action needed
   - **Deepgram timeout**: No automated fallback exists — voice input will be lost. Consider implementing local Whisper STT (recommended but not yet available)
   - **ElevenLabs timeout**: LiveKit may automatically fall back to local TTS — monitor for degraded audio quality

4. **Escalate to service provider**
   - If service is confirmed down and no local fallback is available:
     - Check provider support channels
     - Monitor provider status page for resolution ETA
     - Log incident with timestamp, duration, and impact

5. **Post-recovery**
   - Verify cloud service is responding within normal latency bounds
   - Check that fallback mechanisms (if activated) have deactivated
   - Review logs for any data loss during the outage window

---

## Alert 3: Circuit Breaker Trigger

> **Note**: This alert applies when BACKLOG-004 (circuit breaker pattern) is implemented. Currently, no circuit breaker exists — cloud failures are unhandled.

### Detection

| Parameter | Value |
|-----------|-------|
| **Metric** | Circuit breaker state transition to OPEN |
| **Trigger condition** | 3 consecutive failures for a single cloud service |
| **Probe interval** | 30 seconds (HALF_OPEN state) |
| **Severity** | CRITICAL |
| **Source component** | Circuit breaker wrapper (per cloud service) |

### Severity Escalation

| Level | Condition | Action |
|-------|-----------|--------|
| **CRITICAL** | Circuit breaker opens for any cloud service | Immediate investigation required |

### Runbook

**Goal**: Identify the failing service, verify recovery, and restore normal operation.

1. **Log affected service**
   - Identify which circuit breaker opened: check logs for `circuit_breaker.state=OPEN` events
   - Record the service name, failure count, and timestamps of the 3 triggering failures
   - Check `/health` endpoint for service status (when health check enhancement is implemented)

2. **Verify service recovery**
   - Manually test the affected service endpoint (see Alert 2, Step 1)
   - Check if the issue is transient (network blip) or sustained (provider outage)
   - If transient: wait for the circuit breaker probe interval (30s) to automatically detect recovery

3. **Monitor probe interval**
   - The circuit breaker in HALF_OPEN state sends one probe request every 30 seconds
   - If the probe succeeds, the breaker transitions to CLOSED (normal operation resumes)
   - If the probe fails, the breaker remains OPEN
   - Monitor logs for `circuit_breaker.state=HALF_OPEN` and `circuit_breaker.state=CLOSED` transitions

4. **Manual reset if needed**
   - If the service has recovered but the circuit breaker is stuck OPEN:
     - Restart the agent process to reset all circuit breakers
     - Or invoke the circuit breaker reset API (when implemented)
   - Verify normal operation after reset

---

## Alert 4: Frame Processing Stall

### Detection

| Parameter | Value |
|-----------|-------|
| **Metric** | No frames processed for > 10 seconds |
| **Detection mechanism** | Watchdog background task (`application/pipelines/watchdog.py`) |
| **Severity** | CRITICAL |
| **Source component** | Watchdog, FrameOrchestrator |

### Severity Escalation

| Level | Condition | Action |
|-------|-----------|--------|
| **CRITICAL** | No frames processed for > 10s | Automatic pipeline restart + operator notification |

### Runbook

**Goal**: Restore frame processing pipeline to operational state.

1. **Check Watchdog logs**
   - Review logs for Watchdog stall detection events
   - Use `/debug/watchdog` endpoint to check Watchdog status
   - Verify the Watchdog itself is running (check asyncio task state)

2. **Verify camera feed**
   - Use `/debug/camera` endpoint to check camera frame availability
   - Use `/debug/frame-manager` endpoint to check LiveFrameManager state
   - Verify LiveKit WebRTC connection is active
   - Check if frames are being received but not processed (queue backup)

3. **Check worker pool health**
   - Use `/debug/workers` endpoint to inspect PerceptionWorkerPool state
   - Check for deadlocked threads in the ThreadPoolExecutor
   - Verify GPU is responsive: `nvidia-smi` should show GPU process
   - Check for CUDA errors in logs

4. **Trigger pipeline restart**
   - The Watchdog should automatically trigger a pipeline restart
   - If automatic restart fails:
     - Restart the LiveKit agent: `python -m apps.realtime.entrypoint dev`
     - If agent restart fails, restart the Docker container
   - Verify frame processing resumes via `/debug/frame-rate` endpoint

5. **Post-incident**
   - Review logs to identify root cause (GPU OOM, deadlock, network issue, camera disconnect)
   - Check if the stall correlates with a cloud service timeout (compounding failure)
   - File incident report with timeline and root cause

---

## Alert 5: FAISS Index Size

### Detection

| Parameter | Value |
|-----------|-------|
| **Metric** | `FAISSIndexer.index.ntotal` (vector count) |
| **WARNING threshold** | > 4,000 vectors (80% of 5,000 limit) |
| **CRITICAL threshold** | > 4,800 vectors (96% of 5,000 limit) |
| **Evaluation window** | Polled every 60 seconds |
| **Source component** | FAISSIndexer, PipelineMonitor |

### Severity Escalation

| Level | Condition | Action |
|-------|-----------|--------|
| **WARNING** | Index contains > 4,000 vectors | Schedule maintenance, plan eviction |
| **CRITICAL** | Index contains > 4,800 vectors | Immediate eviction required to prevent index failure |

### Runbook

**Goal**: Reduce FAISS index size below the warning threshold while preserving important memories.

1. **Run eviction policy**
   - Apply LRU eviction: remove vectors not accessed in the last 30 days
   - Apply time-based eviction: remove vectors older than the configured retention period
   - Use the `/memory/search` endpoint to identify low-value or duplicate memories
   - Target reducing index to ≤ 3,500 vectors (70% capacity) to provide headroom

2. **Consider index migration to IVFFlat (BACKLOG-005)**
   - The current IndexFlatL2 uses brute-force O(n) search and has practical limits around 5,000 vectors
   - IVFFlat would provide sub-linear search with support for 100K+ vectors
   - Migration requires reindexing all vectors — schedule during maintenance window
   - Estimated effort: Medium (2-4 hours)

3. **Archive old memories**
   - Export memories older than 90 days to cold storage (JSON file backup)
   - Remove exported memories from the active FAISS index
   - Verify index integrity after removal: run a test search against known vectors
   - Archive path: `data/memory_archive/` (create if needed)

4. **Post-eviction verification**
   - Confirm `index.ntotal` is below warning threshold
   - Run sample queries to verify search quality is not degraded
   - Monitor index growth rate to predict next eviction window

---

## Alert 6: Memory Consent Violation Attempt

### Detection

| Parameter | Value |
|-----------|-------|
| **Metric** | Memory store request received while `MEMORY_ENABLED=false` |
| **Severity** | INFO |
| **Source component** | Memory endpoints in FastAPI server (`/memory/store`, `/memory/search`, `/memory/query`) |

### Severity Escalation

| Level | Condition | Action |
|-------|-----------|--------|
| **INFO** | Memory operation attempted while memory is disabled | Log the denied request, no remediation needed |

### Runbook

**Goal**: Confirm that the system is correctly enforcing memory consent boundaries.

1. **Log denied request**
   - Record the denied operation type (store/search/query), timestamp, and source
   - Verify the response was a proper denial (not a silent failure or data leak)
   - Check that no data was persisted to the FAISS index or metadata store

2. **No action needed**
   - The system is behaving correctly by denying memory operations when consent is not granted
   - `MEMORY_ENABLED=false` is the default — this is expected behavior
   - If the user intends to enable memory, they must explicitly set `MEMORY_ENABLED=true` and grant consent via `/memory/consent`

3. **Investigate if persistent**
   - If this alert fires repeatedly from the same source, investigate whether a client is incorrectly configured
   - Check if the LiveKit agent or internal pipeline is attempting memory operations without checking the consent flag first
   - Review `core/memory/` code paths to ensure all entry points check `MEMORY_ENABLED` before proceeding

---

## Alert Summary Matrix

| # | Alert | WARNING | CRITICAL | Auto-Recovery | Manual Action |
|---|-------|---------|----------|---------------|---------------|
| 1 | GPU Memory Threshold | VRAM > 6 GB | VRAM > 7.5 GB | None | Disable non-critical GPU models |
| 2 | Cloud Timeout | Single timeout | 3 consecutive timeouts | StubLLMClient for LLM | Check service status, verify network |
| 3 | Circuit Breaker Trigger | — | Breaker opens | Auto-probe every 30s | Verify recovery, manual reset if stuck |
| 4 | Frame Processing Stall | — | No frames > 10s | Watchdog auto-restart | Check camera, workers, GPU |
| 5 | FAISS Index Size | > 4,000 vectors | > 4,800 vectors | None | Run eviction, archive old data |
| 6 | Memory Consent Violation | — | — (INFO only) | System correctly denies | None needed |

---

## Escalation Contacts

| Role | Responsibility | Contact Method |
|------|---------------|----------------|
| **On-Call Engineer** | First responder for WARNING and CRITICAL alerts | Internal alert channel |
| **Platform Lead** | Escalation for unresolved CRITICAL alerts (> 15 min) | Direct message |
| **Cloud Service Liaison** | Contact provider support for sustained cloud outages | Provider support portal |

---

## Alert Configuration Notes

- All alert thresholds are derived from the system's hardware specifications (RTX 4060, 8 GB VRAM) and operational requirements documented in the HLD and system prompt
- WARNING alerts are informational and should be investigated during business hours
- CRITICAL alerts require immediate investigation regardless of time
- Circuit breaker alerts (Alert 3) are pending implementation of BACKLOG-004
- GPU memory monitoring requires instrumentation (currently no active VRAM monitoring exists — this is a known gap)
