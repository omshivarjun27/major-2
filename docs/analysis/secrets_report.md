# Secrets Report

_Generated: 2026-02-22T12:33:49.409314+00:00_

## 🚨 CRITICAL: Real API Keys Committed to Repository

The `.env` file in the repository root contains **7 real API keys/secrets** that are committed to version control.

### Affected Secrets

| Line | Key | Redacted Value | Service |
|------|-----|----------------|---------|
| 3 | `LIVEKIT_API_KEY` | `APIv****d94p` | LiveKit WebRTC |
| 4 | `LIVEKIT_API_SECRET` | `8C76****RTvA` | LiveKit WebRTC |
| 7 | `DEEPGRAM_API_KEY` | `7877****2538` | Deepgram STT |
| 8 | `OLLAMA_API_KEY` | `6889****5Kyv` | Ollama LLM |
| 9 | `ELEVEN_API_KEY` | `sk_d****9c3f` | ElevenLabs TTS |
| 10 | `ELEVENLABS_API_KEY` | `sk_d****9c3f` | ElevenLabs TTS |
| 25 | `TAVUS_API_KEY` | `7fff****ad66` | Tavus Avatar |

### Risk Assessment

- **Severity**: CRITICAL
- **Exposure**: Anyone with repo access has these keys
- **Git History**: Even if removed now, keys exist in git history
- **CI Check**: The CI pipeline includes a secrets scan (`test_secrets_scan.py`) and a grep-based `.env` check, but clearly the `.env` was committed before these checks were in place.

### Recommended Actions

1. **IMMEDIATELY** rotate all 7 API keys with their respective providers
2. **Remove** `.env` from the repository: `git rm --cached .env`
3. **Add** `.env` to `.gitignore` (verify it's present)
4. **Scrub** git history: use `git filter-branch` or BFG Repo Cleaner
5. **Add** pre-commit hooks (e.g., `detect-secrets`) to prevent future leaks
6. **Verify** `.dockerignore` excludes `.env`

### Note on CI

The CI pipeline has a secrets scan job that checks for patterns like long alphanumeric strings in `.env`. This scan may have been added after the `.env` was already committed. The scan should block future commits but does not retroactively protect already-committed secrets.

---
_Actual secret values are intentionally redacted in this report._
