---
id: ISSUE-011
title: No API Rate Limiting on FastAPI Endpoints
severity: medium
source_artifact: architecture_risks.md
architecture_layer: apps
---

## Description
The FastAPI server (`apps/api/server.py`) exposes endpoints for perception frame processing, VQA, memory operations, and debug functionality without any rate limiting middleware. Endpoints like `/perception/frame` and `/vqa/ask` trigger expensive image processing and LLM inference.

## Root Cause
Rate limiting was not implemented during initial development. The system was designed as a single-user assistive device, but the REST API is network-accessible.

## Impact
Vulnerable to denial-of-service attacks. Heavy image processing + LLM cloud calls are expensive both computationally and financially. A flood of requests could exhaust GPU resources, cloud API quotas, and VRAM.

## Reproducibility
always

## Remediation Plan
1. Add `slowapi` (rate limiting middleware for FastAPI) to dependencies.
2. Configure per-IP and per-endpoint rate limits.
3. Apply stricter limits to expensive endpoints (`/perception/frame`, `/vqa/ask`, `/memory/store`).
4. Return HTTP 429 with `Retry-After` header when limits exceeded.

## Implementation Suggestion
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/perception/frame")
@limiter.limit("10/minute")
async def perception_frame(request: Request, ...):
    ...
```

## GPU Impact
Rate limiting protects GPU resources from being overwhelmed by concurrent inference requests.

## Cloud Impact
Rate limiting protects cloud API quotas (Ollama cloud, Deepgram, ElevenLabs) from exhaustion due to abuse.

## Acceptance Criteria
- [ ] `slowapi` or equivalent rate limiting middleware installed and configured
- [ ] Expensive endpoints limited to ≤10 requests/minute per IP
- [ ] HTTP 429 returned with appropriate `Retry-After` header
- [ ] Rate limit configuration is externalized (environment variable or config file)
