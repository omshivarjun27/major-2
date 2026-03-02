# T-133: SAST Scanning Setup

**Status**: completed
**Priority**: P7 — Security
**Created**: 2026-03-02
**Completed**: 2026-03-02

## Summary
Set up Bandit-based SAST scanning with `.bandit` config, `scripts/run_sast.py` runner script, baseline file, and GitHub Actions integration.

## Deliverables
- `.bandit` — Bandit configuration excluding tests/research/scripts
- `.bandit-baseline.json` — Empty baseline for known false positives
- `scripts/run_sast.py` — CLI script to run Bandit, parse JSON output, report pass/fail
- `.github/workflows/security.yml` — SAST job in CI

## Acceptance Criteria
- [x] Bandit config excludes test files and known false positives
- [x] Script blocks on HIGH/CRITICAL severity findings
- [x] Exit code 0 if no HIGH/CRITICAL, 1 otherwise
- [x] Graceful handling when Bandit is not installed
- [x] Tests cover arg parsing, baseline loading, classification, blocking logic
