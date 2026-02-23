---
title: "Encryption & Key Management"
version: 1.0.0
date: 2026-02-22T18:00:00Z
architecture_mode: hybrid_cloud_local_gpu
---

# Encryption & Key Management

This document covers the current state of encryption, key management, and secret handling in the Voice & Vision Assistant for Blind. It identifies known exposure issues, documents transport encryption for all cloud services, and provides remediation paths aligned with the prioritized backlog.

---

## 1. Cloud API Key Storage

### 1.1 Current Mechanism

All cloud API keys are stored as environment variables in a `.env` file at the project root. The application loads these values at startup using `os.environ.get("KEY", "default")`. There are 7 API keys managed this way:

| Key | Service | Purpose |
|-----|---------|---------|
| `LIVEKIT_API_KEY` | LiveKit | WebRTC session authentication |
| `LIVEKIT_API_SECRET` | LiveKit | WebRTC token signing |
| `DEEPGRAM_API_KEY` | Deepgram | Speech-to-text API access |
| `OLLAMA_API_KEY` | Ollama Cloud | LLM inference (qwen3.5:cloud) |
| `ELEVEN_API_KEY` | ElevenLabs | Text-to-speech API access |
| `ELEVENLABS_API_KEY` | ElevenLabs | Text-to-speech API access (duplicate) |
| `TAVUS_API_KEY` | Tavus | Virtual avatar API access (optional) |

### 1.2 Design Intent

The `.env` file approach follows the 12-factor app methodology — configuration is externalized from code. A `.env.example` file provides a template with placeholder values. The intent is that `.env` is never committed to version control.

---

## 2. Known Secret Exposure

### 2.1 ISSUE-001: 7 API Keys Committed to .env (CRITICAL)

**Status**: Unresolved. Tracked as BACKLOG-001 (P0).

All 7 API keys contain real credentials that have been committed to the git repository:

| Key | Line in .env | Value Pattern |
|-----|:---:|---------------|
| `LIVEKIT_API_KEY` | 3 | APIv****d94p |
| `LIVEKIT_API_SECRET` | 4 | 8C76****RTvA |
| `DEEPGRAM_API_KEY` | 7 | 7877****2538 |
| `OLLAMA_API_KEY` | 8 | 6889****5Kyv |
| `ELEVEN_API_KEY` | 9 | sk_d****9c3f |
| `ELEVENLABS_API_KEY` | 10 | sk_d****9c3f |
| `TAVUS_API_KEY` | 25 | 7fff****ad66 |

**Risk**: Anyone with read access to the repository can extract these keys and use them to:
- Make API calls charged to the project's accounts.
- Access or manipulate Deepgram transcription services.
- Access ElevenLabs voice synthesis.
- Join LiveKit sessions.
- Access Tavus avatar services.

### 2.2 ISSUE-019: .env Copied Into Docker Image (HIGH)

**Status**: Unresolved. Tracked as BACKLOG-019 (P0).

The root `Dockerfile` uses `COPY . .` which includes the `.env` file in the Docker image layers. Even if `.env` is deleted in a subsequent layer, it remains extractable from the image's build history.

**Risk**: Any Docker image published or shared exposes all 7 API keys to anyone who can pull the image.

---

## 3. Remediation Plan

### 3.1 Immediate Key Rotation (BACKLOG-001)

**Priority**: P0 | **Effort**: S (1-2 hours)

1. **Rotate all 7 API keys** by generating new credentials from each provider dashboard (LiveKit, Deepgram, Ollama, ElevenLabs, Tavus).
2. **Remove `.env` from git tracking**: `git rm --cached .env`
3. **Add `.env` to `.gitignore`** to prevent future commits.
4. **Scrub git history** of the committed `.env` file using `git filter-branch` or `BFG Repo-Cleaner`.
5. **Install `detect-secrets` pre-commit hook** to prevent future secret commits.

### 3.2 Docker Secret Isolation (BACKLOG-019)

**Priority**: P0 | **Effort**: S (1-2 hours)

1. **Add `.env` to `.dockerignore`** so `COPY . .` excludes it.
2. **Pass secrets at runtime** via `docker run --env-file .env` or `docker compose` environment configuration.
3. **Audit previously published images** for embedded secrets. Revoke any images that contain real keys.

### 3.3 Pre-Commit Hooks (BACKLOG-020)

**Priority**: P2 | **Effort**: M (2-4 hours)

1. **Create `.pre-commit-config.yaml`** with `detect-secrets` and `ruff` hooks.
2. **Document `pre-commit install`** in setup instructions.
3. **Verify**: `pre-commit run --all-files` passes without critical findings.
4. **Enforce**: New commits cannot introduce secrets without explicit `--no-verify` override.

---

## 4. HTTPS Enforcement

All cloud API calls use encrypted transport. The system does not make any unencrypted HTTP calls to external services.

| Service | Protocol | Encryption | Library |
|---------|----------|------------|---------|
| qwen3.5:cloud (LLM) | HTTPS | TLS 1.2+ | `httpx.AsyncClient` |
| Deepgram (STT) | WSS | TLS 1.2+ | LiveKit Deepgram plugin |
| ElevenLabs (TTS) | HTTPS/WSS | TLS 1.2+ | LiveKit ElevenLabs plugin |
| LiveKit (WebRTC) | WSS + DTLS/SRTP | TLS 1.2+ (signaling), DTLS (media) | LiveKit SDK |
| Tavus (Avatar) | HTTPS | TLS 1.2+ | `httpx` / `requests` |
| DuckDuckGo (Search) | HTTPS | TLS 1.2+ | `duckduckgo_search` library |
| Ollama local (Embedding) | HTTP | None (localhost only) | `requests` |

**Note**: The local Ollama embedding service (`qwen3-embedding:4b`) communicates over HTTP on localhost. This is acceptable because the traffic never leaves the machine. No sensitive data traverses the network — the embedding model and FAISS index operate entirely within the local process boundary.

---

## 5. TLS Configuration per Service

### 5.1 Deepgram (WSS)

- **Protocol**: WebSocket Secure (WSS) with TLS encryption.
- **Certificate Validation**: Handled by the LiveKit Deepgram plugin's underlying WebSocket library.
- **Connection**: Persistent WebSocket for streaming audio.
- **Reconnection**: Plugin-internal reconnect on connection drop. No application-level retry/backoff (BACKLOG-004).

### 5.2 ElevenLabs (HTTPS/WSS)

- **Protocol**: HTTPS for REST API, WSS for streaming audio.
- **Certificate Validation**: Standard TLS certificate chain validation via the LiveKit ElevenLabs plugin.
- **Connection**: Per-request HTTPS or persistent WebSocket for streaming.
- **Reconnection**: Plugin-internal behavior. No application-level retry/backoff (BACKLOG-004).

### 5.3 Ollama Cloud — qwen3.5:cloud (HTTPS)

- **Protocol**: HTTPS for LLM inference requests.
- **Certificate Validation**: Standard TLS certificate chain validation via `httpx.AsyncClient`.
- **Connection**: Per-request HTTPS with `asyncio.wait_for()` timeout enforcement.
- **Reconnection**: No retry/backoff. `StubLLMClient` provides static fallback on failure.

### 5.4 LiveKit (WSS + DTLS/SRTP)

- **Protocol**: WSS for signaling, DTLS for key exchange, SRTP for media encryption.
- **Certificate Validation**: LiveKit SDK handles DTLS certificate exchange and SRTP key derivation.
- **Connection**: Persistent WebRTC session with built-in reconnect.
- **Security**: End-to-end media encryption via SRTP. Signaling encrypted via WSS.

### 5.5 DuckDuckGo (HTTPS)

- **Protocol**: HTTPS for search queries.
- **Certificate Validation**: Standard TLS via `duckduckgo_search` library.
- **Connection**: Per-request HTTPS.
- **Error Handling**: No documented error handling for search failures.

---

## 6. Local Disk Encryption

### 6.1 FAISS Index — Not Encrypted at Rest (ISSUE-012)

**Status**: Unresolved. Tracked as BACKLOG-012 (P2).

The FAISS vector index at `data/memory_index/` stores 384-dimensional embeddings as unencrypted binary data. The associated `metadata.json` stores memory metadata (timestamps, summaries, session IDs) as plaintext JSON.

**Risk**: An attacker with filesystem access can:
- Read the FAISS index and perform nearest-neighbor queries to recover approximate memory content.
- Read `metadata.json` to access memory summaries, timestamps, and session associations.

**Available Infrastructure**: The `get_encryption_manager()` utility exists in `shared/utils/` and provides encryption capabilities. However, it is not currently wired to FAISS index persistence.

**Remediation** (BACKLOG-012, P2, effort M):
1. Encrypt the FAISS index binary file at rest using `get_encryption_manager()`.
2. Encrypt `metadata.json` at rest.
3. Implement auto-migration: on first load, detect unencrypted indexes and encrypt them.
4. Verify decryption on application restart.

### 6.2 QR Cache — Not Encrypted

QR cache files in `qr_cache/` are stored as plaintext JSON. They contain decoded QR payloads (URLs, contact info, location data). No encryption is applied.

**Risk**: Low to Medium. QR cache data is transient (subject to TTL expiry) and does not contain user-generated content. However, cached URLs and contact information could be sensitive.

### 6.3 Face Consent — Not Encrypted

Face consent state in `data/face_consent.json` is stored as plaintext JSON. It contains consent boolean, timestamp, and optional reason.

**Risk**: Low. The consent file does not contain biometric data (face embeddings are not persisted by default). The consent state itself is not highly sensitive.

### 6.4 Session Logs — Not Encrypted

Session logs in `.runtime/logs/` are stored as plaintext. They may contain processing metadata and component status information.

**Risk**: Low. Logs should not contain PII per the log sanitization policy. However, if bare `except` clauses capture and log user data, sensitive information could appear in log files.

---

## 7. FAISS Index Protection

### 7.1 Current State

- **Storage Format**: Binary FAISS index file + JSON metadata.
- **Location**: `data/memory_index/` directory.
- **Access Control**: OS-level file permissions only. No application-level authentication or authorization on index files.
- **Integrity**: No checksum or signature verification on index files. Corruption or tampering is not detected.
- **Encryption**: Not encrypted at rest (ISSUE-012).
- **Backup**: No automated backup mechanism.

### 7.2 Recommendations

1. **Encrypt at rest** using `get_encryption_manager()` (BACKLOG-012).
2. **Add checksum verification** to detect corruption or tampering on load.
3. **Implement file-level locking** to prevent concurrent access issues (partially addressed by `threading.RLock` in FAISSIndexer).
4. **Set restrictive file permissions** (e.g., `chmod 600`) on index files.
5. **In Docker**: Run as non-root user (BACKLOG-002) to limit filesystem access scope.

---

## 8. Log Redaction Policy

### 8.1 Requirements

API keys and secrets must never appear in log output at any logging level. The following rules apply:

1. **Environment variables**: Never log the value of environment variables containing keys or secrets. Use `os.environ.get()` for access; never log the return value.
2. **HTTP headers**: Authentication headers (`Authorization`, `x-api-key`) must be redacted or omitted from request/response logging.
3. **Request bodies**: API request bodies containing credentials (e.g., Ollama API key in headers) must not be logged.
4. **Error messages**: Exception messages from cloud API calls may contain request URLs with embedded tokens. These must be scrubbed before logging.

### 8.2 Current Implementation

- **Structured logging**: The system uses `shared.logging.logging_config.configure_logging()` which provides structured log output. Field-based logging naturally separates metadata from content.
- **Named loggers**: Each component uses a dedicated logger (e.g., `logging.getLogger("vqa-perception")`), enabling per-component log level control.
- **`log_event()`**: Structured telemetry events use predefined fields, reducing the risk of accidental PII inclusion.

### 8.3 Gaps

- No automated redaction filter in the logging pipeline.
- 6 bare `except` clauses may log full exception details including request/response content.
- No unit tests verifying that API keys are excluded from log output.
- No log audit process to detect accidental secret exposure.
