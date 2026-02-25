# T-008: pii-scrubber-verification

> Phase: P0 | Cluster: CL-SEC | Risk: Critical | State: not_started

## Objective

Verify that the PII scrubber catches all 7 API key patterns before they reach log output.
Add missing regex patterns. Write regression tests.

## Current State (Codebase Audit 2026-02-25)

### PIIScrubFilter Location
`shared/logging/logging_config.py`, lines 39-75

### Current Patterns (6 total)
```python
_PII_PATTERNS = [
    # Email addresses
    (re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"), "[EMAIL_REDACTED]"),
    # IP addresses (v4)
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[IP_REDACTED]"),
    # Face embedding IDs (fid_<hex>)
    (re.compile(r"\bfid_[a-f0-9]{8,}\b"), "[FACE_ID_REDACTED]"),
    # API key patterns (sk_, API prefix)
    (re.compile(r"\b(sk_[a-zA-Z0-9]{20,})\b"), "[API_KEY_REDACTED]"),
    (re.compile(r"\b(API[a-zA-Z0-9]{10,})\b"), "[API_KEY_REDACTED]"),
    # Bearer tokens
    (re.compile(r"Bearer\s+[a-zA-Z0-9._\-]+"), "Bearer [TOKEN_REDACTED]"),
]
```

### Coverage Gap Analysis

The 7 API keys and their typical formats:

| Key | Typical Format | Covered? |
|-----|---------------|----------|
| LIVEKIT_API_KEY | `API...` (short alphanumeric) | Partial (API prefix only if 10+ chars) |
| LIVEKIT_API_SECRET | Long alphanumeric string | NO |
| DEEPGRAM_API_KEY | `dg_...` or hex string | NO |
| OLLAMA_API_KEY | Various formats | NO |
| ELEVEN_API_KEY | Hex or alphanumeric 32+ chars | NO |
| OLLAMA_VL_API_KEY | Same as OLLAMA_API_KEY | NO |
| TAVUS_API_KEY | Alphanumeric string | NO |

Current patterns catch `sk_*` prefixed keys and `API*` prefixed keys.
Most real API keys from these providers don't match either pattern.

### Missing Pattern Categories
1. Generic long hex strings (32+ chars): `[a-f0-9]{32,}`
2. Generic long alphanumeric secrets (20+ chars after `=`): `(?<=KEY=)[a-zA-Z0-9]{20,}`
3. Deepgram-style: `dg_[a-zA-Z0-9]+`
4. Generic key=value secrets in log messages

## Implementation Plan

### Step 1: Add missing patterns

Extend `_PII_PATTERNS` in `shared/logging/logging_config.py`:

```python
_PII_PATTERNS = [
    # Existing patterns (keep as-is)
    (re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"), "[EMAIL_REDACTED]"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[IP_REDACTED]"),
    (re.compile(r"\bfid_[a-f0-9]{8,}\b"), "[FACE_ID_REDACTED]"),
    (re.compile(r"\b(sk_[a-zA-Z0-9]{20,})\b"), "[API_KEY_REDACTED]"),
    (re.compile(r"\b(API[a-zA-Z0-9]{10,})\b"), "[API_KEY_REDACTED]"),
    (re.compile(r"Bearer\s+[a-zA-Z0-9._\-]+"), "Bearer [TOKEN_REDACTED]"),

    # NEW: Deepgram-style keys (dg_ prefix)
    (re.compile(r"\bdg_[a-zA-Z0-9]{10,}\b"), "[API_KEY_REDACTED]"),

    # NEW: Generic long hex strings (likely API keys/secrets)
    (re.compile(r"\b[a-f0-9]{32,}\b"), "[HEX_SECRET_REDACTED]"),

    # NEW: Key=value patterns for named API keys in log messages
    (re.compile(
        r"(?i)((?:api[_-]?key|api[_-]?secret|token|password|secret)"
        r"\s*[=:]\s*)['\"]?([a-zA-Z0-9_\-./+]{8,})['\"]?"
    ), r"\1[REDACTED]"),

    # NEW: LiveKit secret format (ws:// URLs with credentials)
    (re.compile(r"(wss?://[^:]+:)[a-zA-Z0-9_\-]+(@)"), r"\1[REDACTED]\2"),
]
```

### Step 2: Create test data with realistic key formats

Generate test API keys matching each provider's format:

```python
TEST_KEYS = {
    "LIVEKIT_API_KEY": "APIabcdef1234567890",
    "LIVEKIT_API_SECRET": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
    "DEEPGRAM_API_KEY": "dg_abc123def456ghi789jkl012mno345",
    "OLLAMA_API_KEY": "ol-1234567890abcdef1234567890abcdef",
    "ELEVEN_API_KEY": "abcdef1234567890abcdef1234567890",
    "OLLAMA_VL_API_KEY": "ol-abcdef1234567890abcdef1234567890",
    "TAVUS_API_KEY": "tvs_abcdef1234567890abcdef",
}
```

### Step 3: Write regression tests

For each of the 7 keys, inject into a log message and verify redaction:

```python
class TestPIIScrubber:
    def test_each_api_key_redacted(self):
        """Inject each API key format and verify it's scrubbed."""
        scrubber = PIIScrubFilter(enabled=True)
        for key_name, test_value in TEST_KEYS.items():
            record = make_log_record(f"Connecting with {key_name}={test_value}")
            scrubber.filter(record)
            assert test_value not in record.msg, f"{key_name} leaked through PII scrubber"
```

### Step 4: Verify scrubber is enabled by default

Check that `configure_logging()` activates PIIScrubFilter. Verify it can be
disabled via `PII_SCRUB=false` for debug mode.

## Files to Modify

| File | Change |
|------|--------|
| `shared/logging/logging_config.py` | Add 3-4 new PII patterns to _PII_PATTERNS |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/unit/test_pii_scrubber.py` | (new file) |
| | Each of 7 API key formats redacted from log messages |
| | Email addresses redacted |
| | IP addresses redacted |
| | Face IDs redacted |
| | Bearer tokens redacted |
| | Scrubber disabled via flag — values pass through |
| | Combined message with multiple PII types — all redacted |
| | Key=value patterns redacted (e.g., "api_key=abc123") |
| | Non-PII content preserved (no false positives on short strings) |

## Acceptance Criteria

- [ ] All 7 API key formats redacted from log output
- [ ] No false positives on common short strings (ports, version numbers)
- [ ] Existing PII patterns (email, IP, face_id) still work
- [ ] Regression test for each key format
- [ ] PIIScrubFilter enabled by default in configure_logging()
- [ ] PII_SCRUB=false disables scrubber
- [ ] All existing tests pass
- [ ] ruff check clean, lint-imports clean

## Upstream Dependencies

T-001 (need to know final list of 7 API key names — already defined)

## Downstream Unblocks

T-011 (security smoke test verifies PII scrubbing end-to-end)

## Estimated Scope

- Modified: ~15 lines in logging_config.py (new patterns)
- Tests: ~120 LOC (new test file)
- Risk: Low (additive patterns, regex-only change)
