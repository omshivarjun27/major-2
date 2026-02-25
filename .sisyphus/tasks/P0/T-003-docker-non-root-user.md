# T-003: docker-non-root-user

> Phase: P0 | Cluster: CL-SEC | Risk: Critical | State: not_started

## Objective

Modify both Dockerfiles to run containers as a non-root user. Add a dedicated
application user, apply the USER directive, and fix file permissions on runtime directories.

## Current State (Codebase Audit 2026-02-25)

### Root Dockerfile (`Dockerfile`, 39 lines)
- Base: `python:3.11-slim`
- No USER directive — runs as root
- `COPY . .` (respects .dockerignore)
- WORKDIR: `/app`
- Ports: 8000, 8081

### Canonical Dockerfile (`deployments/docker/Dockerfile`, 49 lines)
- Same base: `python:3.11-slim`
- No USER directive — runs as root
- Selective COPY (core/, application/, infrastructure/, shared/, apps/, configs/, models/, data/)
- Creates `.runtime/logs` and `.runtime/cache` via `RUN mkdir -p`
- WORKDIR: `/app`
- Ports: 8000, 8081

### .dockerignore (75 lines)
- Already excludes `.env` (line 70), `venv/`, `__pycache__/`, `.git/`, test artifacts
- Well-configured — no changes needed

### Directories needing permission fixes
| Directory | Purpose | Needs write access |
|-----------|---------|-------------------|
| `/app/data/` | Persistent runtime data (consent, memory index) | Yes |
| `/app/.runtime/` | Logs, cache | Yes |
| `/app/models/` | ML model weights | No (read-only) |
| `/app/configs/` | Config files | No (read-only) |

## Implementation Plan

### Step 1: Add non-root user to Root Dockerfile

After system dependencies install, before COPY:

```dockerfile
# Create non-root application user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser
```

### Step 2: Fix permissions in Root Dockerfile

After `COPY . .`:

```dockerfile
# Ensure writable directories exist and are owned by appuser
RUN mkdir -p /app/data /app/.runtime/logs /app/.runtime/cache /app/qr_cache \
    && chown -R appuser:appuser /app/data /app/.runtime /app/qr_cache

# Switch to non-root user
USER appuser
```

### Step 3: Same changes to Canonical Dockerfile

After selective COPY and `RUN mkdir -p`:

```dockerfile
# Create non-root application user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

# Fix permissions for writable directories
RUN chown -R appuser:appuser /app/data /app/.runtime

# Switch to non-root user
USER appuser
```

### Step 4: Verify HEALTHCHECK still works

The healthcheck runs `python -c "import httpx; ..."` — this should work as appuser
since Python is installed system-wide. No change needed.

### Step 5: Verify CMD works as non-root

Both Dockerfiles use:
```dockerfile
CMD ["bash", "-c", "uvicorn apps.api.server:app --host 0.0.0.0 --port 8000 & python -m apps.realtime.entrypoint start"]
```
Ports 8000 and 8081 are above 1024 — no root needed for binding.

## Files to Modify

| File | Change |
|------|--------|
| `Dockerfile` | Add useradd, mkdir/chown, USER directive |
| `deployments/docker/Dockerfile` | Add useradd, chown, USER directive |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/performance/test_docker_hardening.py` | Verify Dockerfile has USER directive (parse file) |
| | Verify no `COPY .env` in either Dockerfile |
| | Verify .dockerignore excludes .env |

Note: Full Docker build/run verification is handled by existing CI docker job.
The pytest test validates Dockerfile content statically (no Docker daemon needed).

## Acceptance Criteria

- [ ] Root Dockerfile has `USER appuser` directive
- [ ] Canonical Dockerfile has `USER appuser` directive
- [ ] `/app/data/` and `/app/.runtime/` owned by appuser
- [ ] Ports 8000/8081 accessible (non-privileged ports)
- [ ] HEALTHCHECK still passes
- [ ] `docker build -t test .` succeeds locally (manual verification)
- [ ] Static Dockerfile analysis test passes
- [ ] ruff check clean, lint-imports clean

## Upstream Dependencies

None (independent entry point).

## Downstream Unblocks

T-004, T-011

## Estimated Scope

- Modified code: ~8 lines per Dockerfile (16 total)
- Tests: ~40 LOC (static Dockerfile analysis)
- Risk: Medium (permission issues may surface at runtime)
