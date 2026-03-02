# Canary Deployment Guide

## Overview

This document describes the canary deployment strategy for Voice & Vision Assistant, implementing
a 10%/90% traffic split with automated analysis, auto-rollback on metric degradation, and manual
promotion CLI.

## Architecture

```
                    ┌──────────────────┐
    Incoming ───▶  │  Load Balancer   │
    Traffic         └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │ 90%          │              │ 10%
              ▼              │              ▼
       ┌─────────────┐       │      ┌─────────────┐
       │   Stable    │       │      │   Canary    │
       │  (current)  │       │      │   (new)     │
       └─────────────┘       │      └─────────────┘
                             │
                    ┌────────▼────────┐
                    │ Canary Analyser │
                    │ (2-hour window) │
                    └─────────────────┘
```

## Files

| File | Purpose |
|------|---------|
| `scripts/canary_deploy.py` | Deploy canary at configured split |
| `scripts/canary_analysis.py` | Automated metric analysis over 2-hour window |
| `scripts/canary_promote.py` | Manual promotion / rollback CLI |
| `deployments/canary/state.json` | Live canary state (generated at runtime) |
| `docker-compose.canary.yml` | Docker Compose for canary stack |

## Traffic Split Configuration

Default split: **10% canary / 90% stable**.

To change: set `CANARY_WEIGHT` environment variable (0–100) or pass `--weight` to the promotion CLI.

## Deployment Workflow

### 1. Start a canary deployment

```bash
python scripts/canary_deploy.py start --image voice-vision-assistant:v1.1.0
```

This will:
- Pull the new image
- Start the canary container at 10% traffic
- Write `deployments/canary/state.json`
- Begin the 2-hour analysis window

### 2. Monitor canary metrics

```bash
python scripts/canary_analysis.py --watch
```

The analyser compares canary vs stable on:
- **P95 latency** — must stay ≤ 500 ms (hot-path SLA)
- **Error rate** — must stay < 0.5%
- **CPU utilisation** — must stay < 85%

### 3. Auto-rollback conditions

Rollback is triggered automatically if any threshold is breached:

| Metric | Threshold | Window |
|--------|-----------|--------|
| P95 latency | > 500 ms sustained 5 min | 5-min rolling |
| Error rate | > 0.5% | 5-min rolling |
| CPU | > 85% | 5-min rolling |

Rollback completes within **60 seconds** of detection.

### 4. Manual promotion

After a successful 2-hour observation window:

```bash
# Promote canary to 100% traffic
python scripts/canary_promote.py promote --weight 100

# Or step-promote (e.g. 50% first)
python scripts/canary_promote.py promote --weight 50

# Check current state
python scripts/canary_promote.py status

# Roll back manually
python scripts/canary_promote.py rollback --reason "high latency observed"
```

## State File Schema

`deployments/canary/state.json`:

```json
{
  "phase": "canary | stable | promoted | rolled_back",
  "canary_weight": 10,
  "stable_weight": 90,
  "started_at": "2026-03-02T10:00:00Z",
  "promoted_at": null,
  "rolled_back_at": null,
  "rollback_reason": null,
  "history": [
    {"event": "weight_set", "canary_weight": 10, "ts": "..."},
    {"event": "promoted", "ts": "..."}
  ]
}
```

## CI/CD Integration

The GitHub Actions `deploy.yml` workflow:

1. Builds and pushes new Docker image
2. Calls `canary_deploy.py start` on the staging environment
3. Waits for 2-hour analysis window (`canary_analysis.py --wait`)
4. On success: calls `canary_promote.py promote --weight 100`
5. On failure: calls `canary_promote.py rollback --reason "CI threshold breach"`

## Rollback Runbook

If the canary needs emergency rollback:

```bash
# Immediate rollback to stable
python scripts/canary_promote.py rollback --reason "production incident"

# Verify rollback
python scripts/canary_promote.py status
# Expected: phase = "rolled_back", canary_weight = 0, stable_weight = 100

# Confirm service health
curl http://localhost:8000/health
```

Rollback SLA: **≤ 60 seconds** from detection to full stable traffic.
