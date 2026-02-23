---
id: ISSUE-006
title: No Type Checker (mypy/pyright) Configured in CI or Locally
severity: high
source_artifact: architecture_risks.md
architecture_layer: cross-cutting
---

## Description
The project has no static type checker configured. Neither `mypy` nor `pyright` appears in `pyproject.toml`, CI configuration, or development dependencies. The codebase makes heavy use of `Optional[Any]`, `Any`, and untyped function signatures.

## Root Cause
Type checking was never integrated into the development workflow or CI pipeline. The focus was on runtime testing rather than static analysis.

## Impact
Type errors are only caught at runtime. Refactoring is high-risk without type safety guarantees. IDE support (autocomplete, error detection) is degraded. `FusedFrameResult` fields use `Any` for 7 of 13 fields, masking type mismatches.

## Reproducibility
always

## Remediation Plan
1. Add `mypy` to dev dependencies in `pyproject.toml`.
2. Create `mypy.ini` or `[tool.mypy]` section with initial permissive settings.
3. Add mypy to CI pipeline as a non-blocking check initially.
4. Gradually increase strictness: start with `--warn-return-any`, then `--disallow-untyped-defs`.
5. Replace `Any` types in critical data structures (`FusedFrameResult`, `UserData`).

## Implementation Suggestion
```toml
# pyproject.toml
[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
ignore_missing_imports = true
# Start permissive, then tighten per-module:
# [[tool.mypy.overrides]]
# module = "shared.*"
# disallow_untyped_defs = true
```

## GPU Impact
N/A

## Cloud Impact
N/A

## Acceptance Criteria
- [ ] mypy or pyright added to dev dependencies and CI pipeline
- [ ] Initial configuration passes on current codebase (permissive mode)
- [ ] `FusedFrameResult` `Any` fields replaced with concrete types
- [ ] CI runs type checker (warning-only initially, blocking within 2 sprints)
