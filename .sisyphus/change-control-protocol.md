# Change Control Protocol — Version Management and Release Governance

**Voice & Vision Assistant for Blind — 150-Task Change Tracking**

---

## 1. Changelog Maintenance

### Root Changelog Structure
The root `changelog.md` file serves as the single source of truth for all project changes across releases. This file is created in Phase 0 (currently MISSING) and follows the Keep a Changelog format (keepachangelog.com).

### Changelog Categories
All changes are organized into six distinct categories:
- **Added**: New features, capabilities, or components introduced in this release
- **Changed**: Modifications to existing functionality, performance improvements, or behavior adjustments
- **Deprecated**: Features or APIs marked for removal; backward compatible but discouraged
- **Removed**: Features, APIs, or endpoints deleted; breaking changes that eliminate functionality
- **Fixed**: Bug fixes, corrected behavior, and resolved issues
- **Security**: Security patches, vulnerability fixes, and hardening measures

### Fragment-Driven Workflow
Each task produces a `changelog-fragment.md` file stored in its task folder (`tasks/task-{ID}/changelog-fragment.md`). Fragments contain:
- Category (one of six above)
- Change description (1-2 sentences)
- Task ID reference
- Related API/data contract changes (if applicable)

Fragments are merged into the root changelog during Phase transitions (approximately every 20 tasks) using the fragment merging model (Section 2).

---

## 2. Fragment Merging Model

### Fragment Location and Naming
Each task generates a `changelog-fragment.md` file at:
```
tasks/task-{ID}/changelog-fragment.md
```

Fragment format:
```markdown
## Category: [Added|Changed|Deprecated|Removed|Fixed|Security]

**Task ID**: {ID}
**Description**: {1-2 sentence summary of the change}
**Contracts Changed**: {List of affected API/data contracts}
```

### Merge Process at Phase Boundaries
At the completion of each Phase (roughly every 20 tasks), fragments are merged into the root changelog following this strict order:
1. **Security** fragments (highest priority)
2. **Fixed** fragments (bug corrections)
3. **Changed** fragments (behavior/performance modifications)
4. **Added** fragments (new features)
5. **Deprecated** fragments (sunset notices)
6. **Removed** fragments (breaking changes)

### Fragment Preservation
After merging into the root changelog, all fragment files are **retained** in their original task folders. Fragments are never deleted; they serve as audit trail and historical record. The root changelog aggregates but does not replace task-level documentation.

### Merge Validation
Before merging, validate:
- No duplicate task IDs across fragments
- All referenced contracts exist in project
- Category alignment with task type
- No conflicting changes within same release

---

## 3. Semantic Versioning Rule

### Current Version
- **Current**: 1.0.0 (tagged 2025-05-19)
- **Format**: MAJOR.MINOR.PATCH

### Version Bump Criteria
- **MAJOR** (e.g., 1.0.0 → 2.0.0): Breaking API changes, architecture restructuring, incompatible data model changes, removal of critical endpoints or config variables
- **MINOR** (e.g., 1.0.0 → 1.1.0): New features, significant enhancements, non-breaking behavioral changes, new endpoints with backward-compatible schema
- **PATCH** (e.g., 1.0.0 → 1.0.1): Bug fixes, security patches, documentation updates, performance improvements without API changes

### Phase-Based Versioning Strategy
- **Phase 0–1**: PATCH version bumps (1.0.x series) for security hardening and architecture completion
- **Phase 2–3**: MINOR version bump to 1.1.0 at Phase 2 completion; MINOR bump to 1.2.0 at Phase 3 completion (resilience + performance)
- **Phase 4–5**: MINOR bump to 1.3.0 at Phase 4 completion (operations and monitoring)
- **Phase 6–7**: Eligible for MAJOR bump to 2.0.0 at Phase 6 completion if breaking changes warranted; otherwise MINOR bump to 1.4.0

---

## 4. Task-to-Version Mapping

### Release Grouping Strategy
Tasks are grouped into numbered releases at Phase boundaries. Each Phase generates one release across 8 phases:

| Phase | Completion | Release | Version | Focus |
|-------|-----------|---------|---------|-------|
| 0 | Tasks T-001 to T-012 (12) | Release 1.0.1–1.0.3 | 1.0.x | Security hardening, secrets management |
| 1 | Tasks T-013 to T-037 (25) | Release 1.1.0 | 1.1.0 | Core feature completion, stub elimination |
| 2 | Tasks T-038 to T-052 (15) | Release 1.2.0 | 1.2.0 | Architecture remediation, god file split |
| 3 | Tasks T-053 to T-072 (20) | Release 1.3.0 | 1.3.0 | Resilience patterns, circuit breakers |
| 4 | Tasks T-073 to T-090 (18) | Release 1.4.0 | 1.4.0 | Performance optimization, VRAM reduction |
| 5 | Tasks T-091 to T-110 (20) | Release 1.5.0 | 1.5.0 | Operational readiness, monitoring, backups |
| 6 | Tasks T-111 to T-132 (22) | Release 1.6.0 or 2.0.0 | 1.6.0/2.0.0 | Feature evolution, cloud sync, reasoning |
| 7 | Tasks T-133 to T-150 (18) | Release 2.0.0 or 2.1.0 | 2.0.0/2.1.0 | Hardening, regression suite, release |

### Version Tag Naming
Tags follow Git convention: `v{VERSION}` (e.g., `v1.0.1`, `v1.1.0`, `v2.0.0`). Each Phase boundary produces a release tag after all fragment merges complete.

### Backporting Policy
Security patches (Category: Security) may be backported to prior MINOR versions (e.g., patch applied to both 1.0.x and 1.1.0 if vulnerability discovered). All other changes must go to the next planned release.

---

## 5. Breaking Change Detection

### Breaking Change Definition
A change is **breaking** if it violates backward compatibility. Breaking changes include:
- Removal of REST API endpoints or modification of HTTP methods
- Removal or required renaming of request/response JSON fields
- Removal or default value change of configuration variables (env vars)
- Modification of data model schema (Pydantic) causing incompatibility
- Change in method signature (adding required parameters without defaults)
- Modification of authentication or authorization scheme
- Change in error response format or HTTP status codes

### Detection Method
Before and after each task, compare two contract files:
1. **api-contracts.json**: OpenAPI-like specification of all REST endpoints, methods, paths, request/response schemas
2. **data-contracts.json**: JSON Schema representation of all Pydantic models in codebase

Breaking changes detected via structured diff:
- Endpoint removal: breaking
- New endpoint: not breaking
- Request field removal: breaking
- Response field addition: not breaking
- Response field removal: breaking
- Type narrowing (e.g., string → int): breaking
- Type widening (e.g., int → string): not breaking
- Enum value removal: breaking
- Default value addition: not breaking

### Impact Assessment
When breaking change detected:
1. Requires explicit task flag: `breaking_change: true`
2. MAJOR version bump required
3. Must document migration path in changelog fragment
4. One-release deprecation period required (old API coexists with new)
5. Explicit sign-off required from architect

---

## 6. API Contract Change Enforcement

### Contract Documentation
Every task modifying API surface must document changes in `tasks/task-{ID}/api-contracts.json`:

```json
{
  "task_id": "task-{ID}",
  "endpoints": [
    {
      "path": "/api/v1/example",
      "method": "GET",
      "change_type": "added|modified|removed|deprecated",
      "backward_compatible": true|false,
      "request_schema": {...},
      "response_schema": {...},
      "breaking_fields": []
    }
  ]
}
```

### Backward Compatibility Requirement
All Phase 0–5 changes must maintain backward compatibility:
- New endpoints: additive only (do not remove old endpoints)
- Modified endpoints: old fields retained, new fields optional with defaults
- Deprecated endpoints: respond with HTTP 200 but include `Deprecated` header
- Request schema: do not make previously optional fields required
- Response schema: new fields optional; existing fields immutable in type

### Deprecation Period
API removal follows this timeline:
1. **Release N**: Endpoint/field marked `deprecated` with `Sunset` header and `until` date
2. **Release N+1**: Endpoint/field returns HTTP 410 Gone; client must migrate
3. **Release N+2**: Endpoint/field removed entirely

### Version Headers
All responses include API version headers:
```
X-API-Version: 1.0.0
X-API-Deprecated: false|true
X-API-Sunset: {RFC 7231 date if deprecated}
```

---

## 7. JSON Schema Diff Detection

### Data Contract File Structure
Every task affecting Pydantic models must maintain `tasks/task-{ID}/data-contracts.json`:

```json
{
  "task_id": "task-{ID}",
  "models": [
    {
      "model_name": "ExampleModel",
      "change_type": "added|modified|unchanged",
      "fields": [
        {
          "name": "field_name",
          "type": "string|int|bool|array|object",
          "required": true|false,
          "change": "added|modified|removed|unchanged"
        }
      ]
    }
  ]
}
```

### Safe vs. Breaking Changes

| Change | Type | Impact | Version |
|--------|------|--------|---------|
| Field addition with default | Safe | PATCH | 1.0.x |
| Field removal | Breaking | MAJOR | 2.0.0 |
| Required field addition (no default) | Breaking | MAJOR | 2.0.0 |
| Type narrowing (string → int) | Breaking | MAJOR | 2.0.0 |
| Type widening (int → string) | Safe | MINOR | 1.1.0 |
| Default value change | Safe | PATCH | 1.0.x |
| Enum value removal | Breaking | MAJOR | 2.0.0 |
| Enum value addition | Safe | MINOR | 1.1.0 |

### Automated Diff Tool
Use `json-schema-diff` tool to detect changes:
```bash
json-schema-diff before.json after.json --strict
```

Output indicates breaking/safe status automatically. Any breaking detection triggers approval workflow.

---

## 8. Approval Workflow

### Phase-Based Approval Tiers

#### Phase 0 (Security Hardening)
- **Approval**: None required; immediate execution
- **Review**: Post-hoc review by architect within 48 hours
- **Rollback**: Auto-rollback if any test fails
- **Rationale**: Security issues require rapid patching

#### Phases 1–4 (Core & Operational)
- **Approval**: Architect sign-off required before merge
- **Review**: Architect reviews task, contracts, and tests
- **Breaking Changes**: Explicit sign-off + migration plan required
- **Rollback**: Team member may trigger rollback for test failures
- **Timeline**: 24-hour approval SLA

#### Phases 5–7 (Production & Evolution)
- **Approval**: Architect + DevOps sign-off required
- **Review**: Both parties verify contracts, deployment impact, monitoring
- **Breaking Changes**: Require explicit sign-off + deprecation plan + migration guide
- **Rollback**: Architect or DevOps may trigger; requires post-incident review
- **Timeline**: 48-hour approval SLA

### Breaking Change Approval
When `breaking_change: true` detected:
1. Changelog fragment includes migration plan
2. Data contracts diff clearly marked "BREAKING"
3. API contracts include sunset dates
4. Approval requires: one architect signature + one DevOps signature
5. One-release deprecation period enforced in Phase 1+

### Rollback Authority
**Any team member** may trigger rollback if:
- Test suite fails after merge
- Critical path performance degrades > 10%
- Security scanner detects new vulnerabilities
- Integration tests fail in staging

**Only Architect or DevOps** may trigger rollback if:
- Breaking change causes data loss (Phase 2+)
- Configuration migration fails
- Production monitoring detects critical issues (Phase 5+)

### Approval Sign-Off Format
All approvals recorded in `tasks/task-{ID}/approvals.md`:
```markdown
## Task {ID} Approvals

- [ ] Architect: {Name} — {Date}
- [ ] DevOps: {Name} — {Date (Phase 5+ only)}

### Notes
{Comments, concerns, caveats}
```

---

**Document Version**: 1.0.0  
**Last Updated**: 2026-02-24  
**Scope**: All 150 tasks across Phases 0–7  
**Authority**: Architect + DevOps Team
