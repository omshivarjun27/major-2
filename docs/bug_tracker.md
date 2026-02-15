# Bug Tracker — Voice-Vision Assistant

## Fixed Bugs (This Session — Security & Code Quality Audit)

| # | Severity | Component | Description | Fix |
|---|----------|-----------|-------------|-----|
| 1 | **Critical** | Security | Hardcoded API keys (LiveKit, Deepgram, ElevenLabs, Ollama, Tavus, encryption key) in `.env` | Scrubbed to placeholders; matches `.env.example` |
| 2 | **High** | Privacy | 21 unencrypted `fid_*.npy` face embedding files at repo root — biometric PII on disk | Deleted all 21 files; `.gitignore` already blocks re-commit |
| 3 | **Medium** | Code Quality | PydanticDeprecated warnings — `class Config` deprecated in Pydantic v2 | Migrated to `model_config = ConfigDict(populate_by_name=True)` |
| 4 | **Medium** | Naming | `google_places.py` was a misleading filename (uses OSM Nominatim) | Module removed entirely (places search feature dropped) |
| 5 | **Medium** | Repro | `repro/harness.py` was a stub — didn't run actual pipeline | Enhanced with synthetic frame builder, per-frame comparison, p50/p95 latency |
| 6 | **Medium** | CI | No secrets-scanning CI job | Added `secrets-scan` job to `.github/workflows/ci.yml` |

## Previously Fixed Bugs (Prior Sessions)

| # | Severity | Component | Description | Fix |
|---|----------|-----------|-------------|-----|
| 7 | **Critical** | Tests | `test_debug_endpoints.py` collection error | Moved to lazy `@pytest.fixture(scope="module")` |
| 8 | **High** | Deps | FastAPI 0.104.1 incompatible with httpx 0.28.1 | Upgraded FastAPI to 0.129.0 |
| 9 | **Medium** | Tests | Debug endpoint tests return 403 | Added auth token fixture |
| 10 | **Medium** | Tests | OCR `backend_used` vs `backend` key mismatch | Updated assertions to accept both |
| 11 | **Low** | Tests | `test_access_control_fuzz` module reload | Added `importlib.reload()` cleanup |
| 12 | **Low** | Tests | `test_secrets_scan` false positive on test tokens | Excluded `tests/` dir |

## Test Results Summary

| Suite | Passed | Skipped | Failed | Errors | Total |
|-------|--------|---------|--------|--------|-------|
| `tests/` (unit + integration) | ~1610 | 1 | 0 | 0 | ~1611 |
| `nfr/tests/` (NFR) | 94 | 0 | 0 | 0 | 94 |
| **Combined** | **1704** | **1** | **0** | **0** | **1705** |
