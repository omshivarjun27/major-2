---
id: ISSUE-013
title: No Graceful Shutdown for Agent or API Server
severity: medium
source_artifact: architecture_risks.md
architecture_layer: apps
---

## Description
Neither `apps/realtime/agent.py` nor `apps/api/server.py` implements signal handlers for SIGTERM/SIGINT. There is no cleanup logic for the FAISS index, Tavus session, tracked objects, or session logs on shutdown.

## Root Cause
Lifecycle management was not implemented. The application assumes it will either run indefinitely or be killed without cleanup requirements.

## Impact
- Abrupt termination may corrupt the FAISS index if a write is in progress
- Tavus avatar conversations left dangling (orphaned WebSocket connections)
- Final telemetry and session logs lost
- In-memory state not flushed to disk

## Reproducibility
likely

## Remediation Plan
1. Add `atexit` or signal handlers to both `agent.py` and `server.py`.
2. Implement cleanup logic: flush FAISS index, disconnect Tavus, log final telemetry.
3. Use `asyncio.Event` for coordinated shutdown in async contexts.
4. Add a shutdown timeout to prevent hanging on cleanup.

## Implementation Suggestion
```python
import atexit
import signal

def _cleanup():
    logger.info("Graceful shutdown initiated")
    if faiss_indexer:
        faiss_indexer._save()
    if tavus_adapter:
        tavus_adapter.disconnect()
    logger.info("Shutdown complete")

atexit.register(_cleanup)
signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
```

## GPU Impact
N/A

## Cloud Impact
Dangling Tavus and LiveKit sessions may consume cloud resources until timeout.

## Acceptance Criteria
- [ ] Signal handlers registered for SIGTERM and SIGINT
- [ ] FAISS index flushed to disk on shutdown
- [ ] Tavus sessions cleanly disconnected
- [ ] Graceful shutdown completes within 10-second timeout
