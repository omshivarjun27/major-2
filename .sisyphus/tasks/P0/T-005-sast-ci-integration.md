# T-005: sast-ci-integration

> Phase: P0 | Cluster: CL-SEC | Risk: Critical | State: not_started

## Objective

Integrate Bandit (Python SAST) into the GitHub Actions CI pipeline. Configure Bandit to scan
all Python source directories and fail the build on critical/high severity findings.

## Current State (Codebase Audit 2026-02-25)

### CI Pipeline (`.github/workflows/ci.yml`, 190 lines)
4 existing jobs:
1. `secrets-scan` — regex-based .env key detection
2. `test` — unit + integration + coverage on py3.10-3.12
3. `lint` — ruff check + lint-imports
4. `docker` — build image + smoke tests (main branch only)

No SAST, DAST, or dependency scanning exists.

### pyproject.toml tool configuration
Contains `[tool.ruff]`, `[tool.pytest.ini_options]`, `[tool.importlinter]`.
No `[tool.bandit]` section.

### Source directories to scan
- `shared/` — Cross-cutting utils (config, logging, encryption, schemas)
- `core/` — Domain engines (vqa, memory, face, audio, ocr, braille, qr, speech, vision)
- `application/` — Use-case orchestration (frame processing, pipelines)
- `infrastructure/` — External adapters (LLM, speech, Tavus)
- `apps/` — Entrypoints (API server, LiveKit agent, CLI)

### Known areas likely to flag
- `shared/utils/encryption.py` — Crypto operations (Fernet, SHA-256 KDF)
- `shared/config/settings.py` — os.environ access
- `apps/api/server.py` — FastAPI server with potential SSRF vectors

## Implementation Plan

### Step 1: Add Bandit to requirements-extras.txt

```
# Security scanning
bandit[toml]>=1.7.0
```

### Step 2: Configure Bandit in pyproject.toml

```toml
[tool.bandit]
exclude_dirs = ["tests", "research", "scripts", ".sisyphus"]
skips = []
targets = ["shared", "core", "application", "infrastructure", "apps"]
```

### Step 3: Establish baseline

Run Bandit locally to capture current findings:
```bash
bandit -r shared core application infrastructure apps -f json -o .sisyphus/baselines/bandit_baseline.json
```

Triage findings:
- **Critical/High**: Must be fixed before P0 completes
- **Medium/Low**: Documented as known, can be addressed in later phases
- **False positives**: Suppressed with `# nosec` + justification comment

### Step 4: Add SAST job to CI

Insert new job in `.github/workflows/ci.yml` after `lint` job:

```yaml
  sast:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install Bandit
        run: pip install "bandit[toml]>=1.7.0"

      - name: Run SAST scan
        run: |
          bandit -r shared core application infrastructure apps \
            -c pyproject.toml \
            -f json -o bandit_report.json \
            --severity-level high \
            --exit-zero

      - name: Check for critical findings
        run: |
          python -c "
          import json, sys
          with open('bandit_report.json') as f:
              report = json.load(f)
          critical = [r for r in report.get('results', [])
                      if r['issue_severity'] in ('HIGH', 'CRITICAL')]
          if critical:
              for r in critical:
                  print(f\"FAIL: {r['issue_severity']} - {r['issue_text']} in {r['filename']}:{r['line_number']}\")
              sys.exit(1)
          print(f\"SAST passed: {len(report.get('results', []))} findings, 0 critical/high\")
          "

      - name: Upload SAST report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: bandit-report
          path: bandit_report.json
```

### Step 5: Fix any critical/high findings

Based on codebase knowledge, likely findings:
- B303: SHA-256 usage in encryption.py (not a vulnerability — intentional key derivation)
- B105: Possible hardcoded password in settings.py defaults (false positive — placeholder strings)
- B113: Requests without timeout (check infrastructure/ adapters)

Suppress false positives with `# nosec B303 - intentional SHA-256 for key derivation`.

## Files to Create

| File | Purpose |
|------|---------|
| `.sisyphus/baselines/bandit_baseline.json` | Initial SAST scan results for regression tracking |

## Files to Modify

| File | Change |
|------|--------|
| `.github/workflows/ci.yml` | Add `sast` job with Bandit scan |
| `pyproject.toml` | Add `[tool.bandit]` configuration |
| `requirements-extras.txt` | Add `bandit[toml]>=1.7.0` |
| (various source files) | Add `# nosec` for justified false positives |

## Tests to Write

No new pytest tests — SAST is a CI-level check.
The Bandit scan itself serves as the "test."

## Acceptance Criteria

- [ ] Bandit configured in pyproject.toml with correct targets and exclusions
- [ ] CI has `sast` job that runs Bandit on every push/PR
- [ ] Build fails on HIGH/CRITICAL severity findings
- [ ] Baseline report generated and archived
- [ ] All existing critical/high findings resolved or justified with nosec
- [ ] bandit_report.json uploaded as CI artifact
- [ ] All existing tests pass
- [ ] ruff check clean

## Upstream Dependencies

None (independent entry point).

## Downstream Unblocks

T-010 (dependency vulnerability scanning builds on SAST presence)

## Estimated Scope

- CI config: ~35 lines in ci.yml
- pyproject.toml: ~5 lines
- Source fixes: ~5-10 nosec annotations
- Risk: Low (additive CI step, no code behavior change)
