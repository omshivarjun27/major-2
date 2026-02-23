---
id: ISSUE-002
title: Both Dockerfiles Run Containers as Root
severity: critical
source_artifact: architecture_risks.md
architecture_layer: infrastructure
---

## Description
Neither `Dockerfile` (root) nor `deployments/docker/Dockerfile` contains a `USER` instruction. All containers run as the root user by default.

## Root Cause
Dockerfiles were written without security hardening. No non-root user was created during the build stage.

## Impact
Container escape vulnerability. A compromised process inside the container has full host-level access. This is a well-known Docker security anti-pattern flagged by CIS Benchmarks and most container scanning tools.

## Reproducibility
always

## Remediation Plan
1. Add a non-root user creation step after dependency installation in both Dockerfiles.
2. Set file ownership of application directory to the new user.
3. Switch to the non-root user before CMD/ENTRYPOINT.
4. Verify the application starts correctly as non-root.

## Implementation Suggestion
```dockerfile
# Add after dependency installation, before COPY application code
RUN adduser --disabled-password --gecos "" --uid 1001 appuser
COPY --chown=appuser:appuser . /app
USER appuser
```

## GPU Impact
N/A — Docker GPU pass-through (`--gpus all`) works with non-root users when NVIDIA Container Toolkit is configured.

## Cloud Impact
N/A

## Acceptance Criteria
- [ ] Both Dockerfiles contain `USER` instruction with non-root user
- [ ] Container starts and passes health check as non-root
- [ ] Docker image scan (e.g., Trivy) reports no root-user finding
