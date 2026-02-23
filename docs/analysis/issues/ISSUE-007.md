---
id: ISSUE-007
title: In-Memory State Lost on Process Restart
severity: high
source_artifact: architecture_risks.md
architecture_layer: apps
---

## Description
All session state is stored in-memory with no persistence mechanism. This includes `UserData` (per-session state with ~30 fields), tracked objects in `SpatialFuser`, debounce history, conversation context, and session logs.

## Root Cause
The application was designed as a single-process, single-user assistive device. No session persistence layer was implemented because the initial deployment model assumed continuous operation.

## Impact
A process restart (crash, deploy, OOM kill) loses all user context: spatial tracking continuity, conversation history, debounce state, and session data. The user must re-establish context from scratch, which is particularly disruptive for a blind user relying on environmental continuity.

## Reproducibility
always

## Remediation Plan
1. Identify critical state that must survive restarts (tracked objects, conversation history, consent state).
2. Implement a persistence layer using Redis or file-backed store.
3. Add session recovery logic on startup that restores last-known state.
4. Implement periodic state checkpointing (every N seconds or on significant state changes).
5. Add session expiry to prevent unbounded state growth.

## Implementation Suggestion
```python
import json
import redis

class SessionPersistence:
    def __init__(self, redis_url="redis://localhost:6379"):
        self.client = redis.Redis.from_url(redis_url)

    def save_state(self, session_id: str, state: dict) -> None:
        self.client.setex(f"session:{session_id}", 3600, json.dumps(state))

    def load_state(self, session_id: str) -> Optional[dict]:
        data = self.client.get(f"session:{session_id}")
        return json.loads(data) if data else None
```

## GPU Impact
N/A — state persistence is CPU/IO bound.

## Cloud Impact
Redis could be cloud-hosted (e.g., Redis Cloud) for multi-instance deployments. Currently single-instance only.

## Acceptance Criteria
- [ ] Critical session state (tracked objects, conversation history) persisted to durable store
- [ ] Session recovery on startup restores last-known state within 1 second
- [ ] State checkpoint interval configurable (default: 30 seconds)
- [ ] Session expiry prevents unbounded storage growth
