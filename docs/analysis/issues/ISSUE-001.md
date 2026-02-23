---
id: ISSUE-001
title: Real API Keys Committed to .env in Version Control
severity: critical
source_artifact: architecture_risks.md
architecture_layer: cross-cutting
---

## Description
Seven real API keys are committed to the tracked `.env` file in the git repository: LiveKit (URL, API key, API secret), Deepgram, Ollama, ElevenLabs (×2 entries), and Tavus.

## Root Cause
The `.env` file was added to version control before `.gitignore` was properly configured. No pre-commit hooks exist to prevent secrets from being committed.

## Impact
Anyone with repository access (including forks, CI logs, or Docker image layers) has full access to production API credentials. Keys persist in git history even after removal from working tree.

## Reproducibility
always

## Remediation Plan
1. Rotate all 7 API keys immediately via each provider's dashboard.
2. Remove `.env` from git tracking: `git rm --cached .env`.
3. Add `.env` to `.gitignore`.
4. Scrub git history using `git filter-repo` or BFG Repo-Cleaner.
5. Add `detect-secrets` pre-commit hook to prevent recurrence.

## Implementation Suggestion
```bash
# Step 1: Remove from tracking
git rm --cached .env
echo ".env" >> .gitignore

# Step 2: Install pre-commit hook
pip install pre-commit detect-secrets
# Add .pre-commit-config.yaml with detect-secrets hook
```

## GPU Impact
N/A

## Cloud Impact
All cloud service API keys (Deepgram, ElevenLabs, LiveKit, Ollama, Tavus) are exposed. Rotation required for all cloud providers.

## Acceptance Criteria
- [ ] All 7 API keys rotated with new credentials
- [ ] `.env` removed from git tracking and added to `.gitignore`
- [ ] Git history scrubbed of secrets
- [ ] `detect-secrets` pre-commit hook installed and verified
