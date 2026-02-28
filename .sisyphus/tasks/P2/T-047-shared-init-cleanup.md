# T-047: shared-init-cleanup

> Phase: P2 | Cluster: CL-APP | Risk: Medium | State: completed | created_at: 2026-02-25T10:00:00Z | completed_at: 2026-02-25T11:00:00Z

## Objective

Clean up `shared/__init__.py` to remove unnecessary re-exports and reduce coupling between the shared layer and its consumers. Audit every symbol exported from `shared/__init__.py`, identify which ones are actually imported by other modules, and remove dead exports. Organize remaining imports by functional group (config, logging, schemas, utils). Update all downstream import sites that relied on the convenience re-exports to import directly from submodules. This addresses TD-010 and makes the shared module's public API explicit rather than a grab bag of transitive imports.

## Current State (Codebase Audit 2026-02-27)

- **COMPLETED** during the P2 architecture remediation work (prior to this session).
- `shared/__init__.py` has been cleaned up — dead re-exports removed.
- Remaining imports organized by functional group.
- Downstream import sites updated to import directly from submodules.
- TD-010 (shared/__init__.py re-exports) marked as resolved in tech-debt.md.

## Implemented Files

| File | Purpose |
|------|---------|
| `shared/__init__.py` | Cleaned up — dead exports removed, organized by group |

## Evidence of Completion

- `shared/__init__.py` no longer re-exports unnecessary symbols.
- All downstream consumers import directly from `shared.config`, `shared.schemas`, etc.
- TD-010 resolved in `docs/tech-debt.md`.
- `lint-imports` passes with zero violations.

## Acceptance Criteria

- [x] Dead re-exports removed from `shared/__init__.py`
- [x] Remaining imports organized by functional group (config, logging, schemas, utils)
- [x] All downstream import sites updated to import from submodules directly
- [x] TD-010 (shared/__init__.py re-exports) resolved
- [x] `ruff check .` clean
- [x] `lint-imports` clean (zero violations)
- [x] No regressions in existing test suite

## Upstream Dependencies

BASE-001 (base infrastructure).

## Downstream Unblocks

T-048 (import boundary enforcement).

## Estimated Scope

- Modified code: ~50 LOC in shared/__init__.py + scattered import updates
- Risk: Medium (import changes can cause cascading failures if missed)
