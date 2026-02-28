# T-050: p2-tech-debt-reassessment

> Phase: P2 | Cluster: CL-GOV | Risk: Low | State: completed | created_at: 2026-02-27T12:00:00Z | completed_at: 2026-02-27T14:00:00Z

## Objective

Reassess the technical debt register after all P2 changes are complete. Mark TD-001 (agent.py god file) as resolved if agent.py is under 500 LOC. Mark TD-003 (OllamaEmbedder sync blocking) as resolved if async conversion is verified. Mark TD-010 (shared/__init__.py re-exports) as resolved if cleanup is confirmed. Identify any new debt introduced during the refactoring and add it to the register with severity and fix-effort estimates. Update AGENTS.md Section 8 with the revised debt table.

## Current State (Codebase Audit 2026-02-27)

- T-042 is **complete**: `agent.py` is 288 LOC (well under the 500 LOC target). TD-001 is a candidate for resolution.
- T-044 is **complete**: OllamaEmbedder uses async aiohttp. TD-003 is a candidate for resolution.
- T-047 is **complete**: `shared/__init__.py` cleaned of unnecessary re-exports. TD-010 is a candidate for resolution.
- The remaining P2 tasks (T-043, T-045, T-046, T-048, T-049, T-051, T-052) must all complete before this reassessment can finalize.
- The current tech debt register lives in `AGENTS.md` and possibly `docs/tech-debt.md`.
- New debt may have been introduced during the agent split (e.g., duplicated utility functions across extracted modules, temporary compatibility shims).

## Implementation Plan

### Step 1: Verify TD-001 resolution (agent.py god file)

Confirm `apps/realtime/agent.py` is under 500 LOC. Verify no single file in `apps/realtime/` exceeds 500 LOC. If both conditions hold, mark TD-001 as resolved with the resolution date and final LOC count.

### Step 2: Verify TD-003 resolution (OllamaEmbedder sync)

Confirm OllamaEmbedder uses async patterns (aiohttp, `async def`, no blocking HTTP calls). Confirm T-045 and T-046 have eliminated remaining sync LLM calls. If verified, mark TD-003 as resolved.

### Step 3: Verify TD-010 resolution (shared/__init__.py)

Confirm `shared/__init__.py` exports only the intended public API. Verify downstream modules import directly from submodules. If verified, mark TD-010 as resolved.

### Step 4: Scan for new technical debt

Review all P2 changes for newly introduced debt:
- Duplicated code across extracted modules
- Temporary compatibility shims or adapters
- TODO/FIXME/HACK comments added during refactoring
- Overly broad exception handlers added for safety
- Missing type annotations on new interfaces
- Test coverage gaps in new modules

### Step 5: Update debt register

For each new debt item, record:
- Debt ID (TD-NNN)
- Description
- Severity (critical, high, medium, low)
- Fix effort estimate (hours)
- Affected files
- Recommended phase for resolution

### Step 6: Update AGENTS.md

Revise the technical debt section with:
- Resolved items marked with resolution date
- New items added with full metadata
- Updated risk assessment reflecting P2 outcomes

## Files to Create

None.

## Files to Modify

| File | Change |
|------|--------|
| `AGENTS.md` | Update technical debt section: resolve TD-001, TD-003, TD-010; add new debt items |
| `docs/tech-debt.md` | Full debt register update with P2 resolutions and new findings |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/unit/test_tech_debt_checks.py` | `test_agent_under_500_loc` - verify agent.py line count |
| | `test_no_file_exceeds_500_loc_in_realtime` - verify all apps/realtime/ files under 500 LOC |
| | `test_shared_init_minimal_exports` - verify shared/__init__.py has minimal re-exports |

## Acceptance Criteria

- [ ] TD-001 (agent.py god file) marked resolved with evidence (288 LOC)
- [ ] TD-003 (OllamaEmbedder sync) marked resolved with evidence (async aiohttp)
- [ ] TD-010 (shared/__init__.py) marked resolved with evidence (cleaned exports)
- [ ] All new debt items documented with severity and fix-effort estimates
- [ ] AGENTS.md technical debt section updated
- [ ] `docs/tech-debt.md` updated with full P2 reassessment
- [ ] No untracked debt items remain from P2 changes
- [ ] `ruff check .` clean
- [ ] `lint-imports` clean

## Upstream Dependencies

T-046 (async-audit-sweep), T-048 (import-boundary-enforcement), T-049 (agent-architecture-documentation). All P2 remediation and documentation must be complete before the final reassessment.

## Downstream Unblocks

None. This is a terminal governance task for Phase 2.

## Estimated Scope

- New code: ~30 LOC (debt check tests)
- Modified code: ~80 LOC (AGENTS.md and tech-debt.md updates)
- Tests: ~30 LOC (3 test functions)
- Risk: Low. Documentation and governance task with no code behavior changes.
