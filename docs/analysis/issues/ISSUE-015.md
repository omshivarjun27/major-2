---
id: ISSUE-015
title: 3,674 Ruff Lint Issues Across Codebase
severity: low
source_artifact: architecture_risks.md
architecture_layer: cross-cutting
---

## Description
The codebase has 3,674 lint issues detected by ruff: 2,929 whitespace warnings (W293), 366 unused imports (F401), 240 unsorted imports (I001), 34 unused variables (F841), 28 empty f-strings (F541), 6 bare except clauses (E722), and 3 undefined names (F821). 97.9% (3,596) are auto-fixable.

## Root Cause
No pre-commit hooks or CI lint enforcement blocked merges with lint issues. Developers did not run ruff locally before committing.

## Impact
Noisy diffs, developer friction, potential runtime bugs from 3 undefined names (F821). Pre-commit hooks are disabled or non-existent. Format compliance is only 23.3%.

## Reproducibility
always

## Remediation Plan
1. Run `ruff check . --fix` to auto-fix 97.9% of issues.
2. Run `ruff format .` to format all 155 non-compliant files.
3. Manually fix remaining ~78 issues (F841, F541, E722, F821).
4. Enable ruff as a pre-commit hook to prevent regression.

## Implementation Suggestion
```bash
# One-time fix
ruff check . --fix
ruff format .
# Then manually fix F821 (undefined names) — these are bugs
# Add pre-commit hook
```

## GPU Impact
N/A

## Cloud Impact
N/A

## Acceptance Criteria
- [ ] `ruff check .` reports 0 issues
- [ ] `ruff format --check .` reports 0 files to reformat
- [ ] Pre-commit hook configured to run ruff on staged files
- [ ] 3 F821 (undefined name) issues fixed (potential bugs)
