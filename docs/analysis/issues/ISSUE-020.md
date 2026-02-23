---
id: ISSUE-020
title: No Pre-Commit Hooks for Secrets Detection or Linting
severity: medium
source_artifact: security_scan.json
architecture_layer: cross-cutting
---

## Description
No `.pre-commit-config.yaml` file exists in the repository. There are no automated checks preventing secrets, lint violations, or formatting issues from being committed.

## Root Cause
Pre-commit hooks were never configured as part of the development workflow. The CI pipeline has lint and secrets checks, but they only catch issues after commit/push.

## Impact
Secrets can be committed accidentally (as evidenced by the 7 API keys in `.env`). Lint issues accumulate (3,674 current issues). Formatting diverges (76.7% non-compliant).

## Reproducibility
always

## Remediation Plan
1. Create `.pre-commit-config.yaml` with hooks for: `detect-secrets`, `ruff` (lint + format), `trailing-whitespace`, `end-of-file-fixer`.
2. Install pre-commit in the project: `pip install pre-commit && pre-commit install`.
3. Document pre-commit setup in README/AGENTS.md.
4. Run `pre-commit run --all-files` once to establish baseline.

## Implementation Suggestion
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-added-large-files
```

## GPU Impact
N/A

## Cloud Impact
N/A

## Acceptance Criteria
- [ ] `.pre-commit-config.yaml` exists with detect-secrets and ruff hooks
- [ ] `pre-commit install` documented in setup instructions
- [ ] `pre-commit run --all-files` passes without critical findings
- [ ] New commits cannot introduce secrets without explicit override
