# Security Documentation

**Version**: 1.0.0 | **Date**: 2026-03-02

---

## 1. Threat Model

### Assets

| Asset | Sensitivity | Protection |
|-------|------------|------------|
| API keys (Deepgram, ElevenLabs, etc.) | HIGH | Env vars, never committed |
| Face embeddings | HIGH | Encrypted at rest (AES-256) |
| Memory/RAG data | MEDIUM | Local only, consent-gated |
| QR scan cache | LOW | Local file, TTL expiry |
| Audio/video frames | HIGH | Never stored, in-memory only |

### Threat Actors

- **External attacker**: network-level attacks on exposed ports
- **Compromised dependency**: supply chain attacks via third-party packages
- **Misconfigured deployment**: secrets leaked via env or logs

### Mitigations

| Threat | Mitigation |
|--------|-----------|
| Secret leakage via logs | PII scrubber strips API keys, face IDs, names from all log output |
| Secret in repo | `secrets-scan` CI step blocks commits with real credentials |
| Vulnerable dependency | Automated dependency scanning (`scripts/run_dep_scan.py`) on every PR |
| Code vulnerabilities | SAST via Bandit on every PR (`.github/workflows/security.yml`) |
| Container as root | Dockerfile runs as `appuser` (non-root) |
| API abuse | Rate limiting via FastAPI middleware (recommended for production) |

---

## 2. Secrets Management

**Never** commit secrets to the repository.

Required secrets are loaded from environment variables. For production:

1. Store secrets in a secrets manager (AWS Secrets Manager, Vault, etc.)
2. Inject as environment variables at container start
3. Validate presence with `python scripts/validate_env.py`

The `.gitignore` explicitly excludes `.env` files. The CI `secrets-scan` step
verifies no real API key patterns appear in committed files.

---

## 3. Data Privacy

### Principles

- **Minimal collection**: only data needed for the current request is processed
- **No persistence by default**: audio/video frames are never written to disk
- **Explicit consent**: face recognition and memory require explicit user consent
- **PII scrubbing**: all log output is scrubbed of names, API keys, and face IDs

### Face Data

- Stored encrypted at rest using AES-256 (via `shared/utils/encryption.py`)
- Requires explicit consent before any face is stored
- User can revoke consent — all embeddings are deleted immediately
- Consent audit trail is maintained

### Memory / RAG

- `MEMORY_ENABLED` defaults to `false` — user must opt in
- Memory data is stored locally (SQLite + FAISS)
- User can delete all memories with a single voice command
- No memory data is sent to external services

---

## 4. Security Scanning

### SAST (Bandit)

Runs on every PR via `.github/workflows/security.yml`:

```bash
bandit -r . -c .bandit --baseline .bandit-baseline.json
```

Zero HIGH or CRITICAL findings required to merge.

### Dependency Scanning

```bash
python scripts/run_dep_scan.py
```

Checks for known CVEs in installed packages. Zero critical CVEs required.

### DAST

```bash
python scripts/run_dast.py --target http://localhost:8000
```

OWASP ZAP scan against the running API. Reports saved to `reports/dast/`.

---

## 5. Container Security

The production Dockerfile (`deployments/docker/Dockerfile`) implements:

- **Non-root user**: container runs as `appuser` (UID unprivileged)
- **Multi-stage build**: no build tools (gcc, pip, etc.) in runtime image
- **Minimal base**: `python:3.11-slim` — no unnecessary packages
- **HEALTHCHECK**: Docker can detect and restart unhealthy containers
- **No secrets in image**: all secrets injected at runtime via env vars

---

## 6. Network Security

- Only ports 8000 (API) and 8081 (agent) are exposed
- LiveKit WebRTC traffic is encrypted (DTLS/SRTP)
- All HTTP API calls to external services use HTTPS

---

## 7. Incident Response

See `docs/runbooks/incident-response.md` for the full incident response playbook.

For a **security incident** specifically:

1. Rotate all API keys immediately
2. Review logs for the incident window (`docker logs vva`)
3. Check for any data exfiltration via network logs
4. Apply fix and redeploy
5. Notify affected users if personal data was involved
