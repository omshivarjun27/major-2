---
id: ISSUE-019
title: .env File With Secrets Copied Into Docker Image
severity: critical
source_artifact: security_scan.json
architecture_layer: infrastructure
---

## Description
The root `Dockerfile` uses `COPY . .` which copies the entire working directory into the Docker image, including the `.env` file containing 7 real API keys. Anyone with access to the Docker image can extract the secrets.

## Root Cause
The `Dockerfile` uses a blanket `COPY . .` command without excluding sensitive files. The `.dockerignore` file does not exclude `.env`.

## Impact
Docker images published to any registry (Docker Hub, ECR, GCR) would contain production API keys. Any user who pulls the image can extract credentials by inspecting image layers.

## Reproducibility
always

## Remediation Plan
1. Add `.env` to `.dockerignore` immediately.
2. Use `--env-file` flag at runtime instead of baking secrets into the image.
3. For CI/CD, pass secrets via environment variables or a secrets manager.
4. Audit any previously published images for embedded secrets.

## Implementation Suggestion
```
# .dockerignore
.env
.env.*
*.pem
*.key
```

## GPU Impact
N/A

## Cloud Impact
All cloud API keys (Deepgram, ElevenLabs, LiveKit, Ollama, Tavus) would be exposed if the image is distributed.

## Acceptance Criteria
- [ ] `.env` added to `.dockerignore`
- [ ] Docker image built without `.env` present in any layer
- [ ] Secrets passed via `--env-file` or environment variables at runtime
- [ ] Previously published images audited and revoked if secrets found
