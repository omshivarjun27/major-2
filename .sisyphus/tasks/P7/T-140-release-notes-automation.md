# T-140: Release Notes Automation

**Status**: not_started
**Priority**: P7 — DevOps
**Created**: 2026-03-02

## Summary
Automate release notes generation by parsing conventional commits, grouping by category, extracting task summaries, generating changelog markdown, and integrating with GitHub Release workflow.

## Deliverables
- `scripts/generate_release_notes.py` — Conventional commit parser and changelog generator
- `CHANGELOG.md` template with auto-generated sections
- GitHub Actions workflow for automated release note generation
- Category grouping (features, fixes, docs, refactors, tests)

## Acceptance Criteria
- [ ] Parses conventional commit messages (feat, fix, docs, refactor, test, chore)
- [ ] Groups changes by category with task ID cross-references
- [ ] Generates well-formatted changelog markdown
- [ ] GitHub Release workflow creates release with generated notes on tag push
- [ ] Handles edge cases: merge commits, squashed commits, missing prefixes
