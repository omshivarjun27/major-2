# T-004: docker-secrets-injection

> Phase: P0 | Cluster: CL-SEC | Risk: Critical | State: not_started

## Objective

Configure Docker and Docker Compose to inject secrets via `env_file:` directive or
`docker run --env-file` instead of baking values into images. Remove hardcoded test
secrets from compose files. Add `.env.example` template.

## Current State (Codebase Audit 2026-02-25)

### docker-compose.test.yml (root, 24 lines)
```yaml
environment:
  - LIVEKIT_URL=ws://localhost:7880
  - LIVEKIT_API_KEY=devkey
  - LIVEKIT_API_SECRET=devsecret
  - DEEPGRAM_API_KEY=test
  - ELEVEN_API_KEY=test
  - LLM_BASE_URL=http://localhost:11434/v1
  - LLM_API_KEY=test
```
Secrets hardcoded as test values directly in compose spec.

### deployments/compose/docker-compose.test.yml (26 lines)
Identical environment block with same hardcoded test values.

### .dockerignore
Line 70-71: `.env` and `.env.example` already excluded from build context.

### Dockerfiles
- Root: `COPY . .` but .dockerignore blocks .env
- Canonical: Selective COPY — never touches .env
- Neither Dockerfile bakes secrets into image (confirmed clean)

### .env file
EXISTS in repo root — contains actual key placeholders (`your_livekit_url`, etc.)
CI secrets-scan job validates no real keys are committed.

## Implementation Plan

### Step 1: Create .env.example template

Create `.env.example` with all expected variables and placeholder values:

```env
# ===== REQUIRED SECRETS (must be set for production) =====
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
DEEPGRAM_API_KEY=your_deepgram_api_key
OLLAMA_API_KEY=your_ollama_api_key
ELEVEN_API_KEY=your_elevenlabs_api_key
OLLAMA_VL_API_KEY=your_ollama_vl_api_key
TAVUS_API_KEY=your_tavus_api_key

# ===== OPTIONAL CONFIG (safe defaults) =====
VISION_PROVIDER=ollama
SPATIAL_PERCEPTION_ENABLED=true
ENABLE_QR_SCANNING=true
# ... (non-secret config vars with defaults)
```

### Step 2: Update root docker-compose.test.yml

Replace hardcoded environment block with env_file:

```yaml
version: "3.8"
services:
  voice-vision-assistant:
    build: .
    ports:
      - "8000:8000"
      - "8081:8081"
    env_file:
      - .env
    environment:
      # Test overrides (non-secret only)
      - SPATIAL_PERCEPTION_ENABLED=true
      - SPATIAL_USE_YOLO=false
      - ENABLE_QR_SCANNING=true
    healthcheck:
      test: ["CMD", "python", "-c", "import httpx; r=httpx.get('http://localhost:8000/health'); assert r.status_code==200"]
      interval: 30s
      timeout: 5s
      retries: 3
```

### Step 3: Update deployments/compose/docker-compose.test.yml

Same pattern — use env_file, keep only non-secret overrides in environment block.

### Step 4: Verify .dockerignore blocks .env

Already confirmed (line 70). Add a comment:
```
# Secrets — NEVER include in build context
.env
.env.*
!.env.example
```

Wait — .env.example is also excluded on line 71. For T-004, we WANT .env.example
in the build context (it's not a secret). Update .dockerignore to allow it.

### Step 5: Update CI docker job

The CI docker job (`ci.yml` lines 143-189) currently hardcodes test env vars
in `docker run` commands. These are test values, not real secrets — keep them
but add a comment explaining the pattern:

```yaml
- name: Smoke test – API health endpoint
  run: |
    # Test secrets — NOT real API keys, safe for CI
    docker run -d --name smoke-test -p 8000:8000 \
      -e LIVEKIT_URL=ws://localhost:7880 \
      -e LIVEKIT_API_KEY=devkey \
      ...
```

No functional change to CI — just documentation.

## Files to Create

| File | Purpose |
|------|---------|
| `.env.example` | Template with all expected env vars and placeholder values |

## Files to Modify

| File | Change |
|------|--------|
| `docker-compose.test.yml` | Replace hardcoded secrets with `env_file: .env` |
| `deployments/compose/docker-compose.test.yml` | Same as above |
| `.dockerignore` | Allow .env.example through (change line 71) |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/performance/test_docker_hardening.py` | (extends T-003 tests) |
| | Verify .env.example exists and contains all 7 secret key names |
| | Verify .dockerignore excludes .env but allows .env.example |
| | Verify compose files use env_file directive |
| | Verify no hardcoded real API key patterns in compose files |

## Acceptance Criteria

- [ ] .env.example committed with all 7 secret keys as placeholders
- [ ] docker-compose.test.yml uses env_file: .env
- [ ] deployments/compose/docker-compose.test.yml uses env_file: .env
- [ ] .dockerignore allows .env.example, blocks .env
- [ ] No COPY .env in either Dockerfile (already clean — verify)
- [ ] CI docker job still passes with test values
- [ ] All existing tests pass
- [ ] ruff check clean

## Upstream Dependencies

T-001 (SecretProvider must exist for integration), T-003 (non-root user for full Docker hardening)

## Downstream Unblocks

T-011

## Estimated Scope

- New files: .env.example (~30 lines)
- Modified: 2 compose files (~10 lines each), .dockerignore (1 line)
- Tests: ~50 LOC
- Risk: Low (compose config change, no code logic)
