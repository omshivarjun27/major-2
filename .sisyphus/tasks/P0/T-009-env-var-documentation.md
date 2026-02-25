# T-009: env-var-documentation

> Phase: P0 | Cluster: CL-SEC | Risk: Critical | State: not_started

## Objective

Document all environment variables in settings.py with descriptions, defaults,
types, and security classifications. Group by functional area.

## Current State (Codebase Audit 2026-02-25)

### settings.py Facts
- 372 lines, 82 `os.environ.get()` calls
- Flat CONFIG dict with no type validation (manual casts: int(), float(), .lower() == "true")
- No Pydantic BaseSettings (despite AGENTS.md suggesting it)
- Variables grouped by comment blocks but no formal documentation
- 7 secret keys mixed in with non-secret config vars

### Functional Groups (from reading settings.py)
1. **Vision Provider** (2 vars): VISION_PROVIDER, OLLAMA_VL_MODEL_ID
2. **API Keys / Secrets** (7 vars): LIVEKIT_API_KEY, etc.
3. **Tavus Avatar** (5 vars): ENABLE_AVATAR, TAVUS_*
4. **Spatial Perception** (12 vars): SPATIAL_*, YOLO_*, MIDAS_*, ENABLE_SEGMENTATION, etc.
5. **QR / AR Scanning** (5 vars): ENABLE_QR_SCANNING, QR_*
6. **Latency Targets** (4 vars): TARGET_*_LATENCY_MS
7. **Live Frame / Capture** (5 vars): LIVE_FRAME_*, CAPTURE_*, FRAME_BUFFER_*
8. **Worker Pool** (6 vars): NUM_*_WORKERS
9. **Debounce** (3 vars): DEBOUNCE_*, DISTANCE_DELTA_M, CONFIDENCE_DELTA
10. **Watchdog** (2 vars): CAMERA_STALL_*, WORKER_STALL_*
11. **Continuous Processing** (5 vars): ALWAYS_ON, CONTINUOUS_*, PROACTIVE_*
12. **Privacy / Consent** (2 vars): MEMORY_TELEMETRY, MEMORY_REQUIRE_CONSENT
13. **Face Engine** (8 vars): FACE_*
14. **Audio Engine** (6 vars): AUDIO_*
15. **Action Recognition** (5 vars): ACTION_*
16. **Cloud Sync** (4 vars): CLOUD_SYNC_*, MEMORY_EVENT_*, MEMORY_AUTO_*
17. **Tavus Integration** (1 var): TAVUS_ENABLED
18. **Raw Media** (1 var): RAW_MEDIA_SAVE
19. **Speech/VQA Features** (3 vars): ENABLE_SPEECH_VQA, ENABLE_PRIORITY_SCENE, etc.
20. **Hardcoded Constants** (2): MAX_TOKENS, TEMPERATURE

**Total documented: ~82 env vars + 2 constants**

### Additional env vars used outside settings.py
- `MEMORY_ENCRYPTION_KEY` (shared/utils/encryption.py)
- `FACE_ENCRYPTION_KEY` (core/face/face_embeddings.py)
- `MEMORY_ENABLED` (core/memory/config.py)
- `MEMORY_RETENTION_DAYS`, `MEMORY_MAX_VECTORS`, etc. (core/memory/config.py)
- `ANTHROPIC_API_KEY` (core/memory/llm_client.py)

These bring the total closer to 90-95 env vars.

## Implementation Plan

### Step 1: Create env var documentation file

Create `docs/configuration.md` with structured documentation:

```markdown
# Environment Variable Reference

## Security Classification
- SECRET: Must use SecretProvider. Never log. Never commit.
- INTERNAL: Not sensitive but not for end users.
- PUBLIC: Safe to expose, documented defaults.

## API Keys & Secrets (SECRET)
| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| LIVEKIT_API_KEY | str | "" | LiveKit WebRTC API key |
| ... | ... | ... | ... |

## Spatial Perception (PUBLIC)
| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| SPATIAL_PERCEPTION_ENABLED | bool | true | Enable obstacle detection pipeline |
| ... | ... | ... | ... |
```

### Step 2: Add inline documentation to settings.py

Above each group in CONFIG dict, add a comment block explaining the group:

```python
# ===== API KEYS & SECRETS =====
# Classification: SECRET — sourced via SecretProvider
# These MUST be set for production. Default empty strings disable the service.
"OLLAMA_VL_API_KEY": _secret_provider.get_secret("OLLAMA_VL_API_KEY") or "",
```

### Step 3: Mark secret vs non-secret classification

In documentation, clearly tag which variables are SECRET:

```python
# In-code: Add a SECRETS set for programmatic identification
SECRETS = frozenset({
    "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "DEEPGRAM_API_KEY",
    "OLLAMA_API_KEY", "ELEVEN_API_KEY", "OLLAMA_VL_API_KEY",
    "TAVUS_API_KEY", "MEMORY_ENCRYPTION_KEY", "FACE_ENCRYPTION_KEY",
    "ANTHROPIC_API_KEY",
})
```

### Step 4: Add configuration validation helper

```python
def validate_config() -> list[str]:
    """Return list of configuration warnings."""
    warnings = []
    for key in SECRETS:
        val = CONFIG.get(key, "") or ""
        if not val:
            warnings.append(f"SECRET {key} is not set")
    return warnings
```

## Files to Create

| File | Purpose |
|------|---------|
| `docs/configuration.md` | Complete env var reference with types, defaults, classifications |

## Files to Modify

| File | Change |
|------|--------|
| `shared/config/settings.py` | SECRETS frozenset, validate_config(), inline comments |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/unit/test_config_docs.py` | |
| | Every os.environ.get key in settings.py is documented in configuration.md |
| | SECRETS set contains exactly the expected keys |
| | validate_config() returns warnings for unset secrets |
| | No SECRET values in CONFIG defaults (all default to empty string) |

## Acceptance Criteria

- [ ] docs/configuration.md created with all 90+ env vars documented
- [ ] Each var has: name, type, default, description, security classification
- [ ] Vars grouped by functional area
- [ ] SECRET classification on all API keys and encryption keys
- [ ] SECRETS frozenset in settings.py for programmatic access
- [ ] validate_config() helper function
- [ ] Sync test verifying docs match actual settings.py
- [ ] ruff check clean, lint-imports clean

## Upstream Dependencies

T-002 (SecretProvider wired into settings.py — need final list of vars routed through it)

## Downstream Unblocks

T-012 (baseline metrics references config variable count)

## Estimated Scope

- docs/configuration.md: ~200 lines
- settings.py: ~30 lines (SECRETS set, validate_config, comments)
- Tests: ~50 LOC
- Risk: Low (documentation + light code additions)
