
### SECTION 6: Auto-Documentation Templates

Provide 7 reusable documentation templates as markdown code blocks:

**Template 1: Module AGENTS.md**
```markdown
# {module}/AGENTS.md
## Module: {name}
**Layer**: {shared|core|application|infrastructure|apps}
**Purpose**: {one-line description}
## Ownership
- Maintainer: {team/person}
- Last reviewed: {date}
## Public API
| Function/Class | Purpose | Signature |
|...
## Dependencies
- Imports from: {list}
- Imported by: {list}
## Anti-patterns
- NEVER {pattern}
## Test Commands
- `pytest tests/unit/test_{module}.py -v`
```

**Template 2: API Endpoint**
```markdown
## {METHOD} {path}
**Auth**: {required|optional|none}
**Rate Limit**: {value}
### Request
{schema}
### Response
{schema with status codes}
### Errors
| Code | Meaning |
### Example
```bash
curl -X {METHOD} http://localhost:8000{path}
```
```

**Template 3: Service Integration**
```markdown
## {Provider Name} Integration
**Purpose**: {what it does}
**Auth**: {method, API key, OAuth, etc.}
**Base URL**: {url}
### Retry Policy
- Max retries: {N}
- Backoff: {strategy}
### Fallback
{what happens when service is down}
### SLA
- Latency: {target}
- Uptime: {target}
### Config
| Env Var | Purpose | Default |
```

**Template 4: LiveKit Agent**
```markdown
## Agent: {name}
**Trigger**: {what activates it}
**Port**: 8081
### Input
{what the agent receives}
### Output
{what the agent produces}
### Latency SLA
- Target: {ms}
- Max: {ms}
### Dependencies
{list of core modules used}
### Error Handling
{degradation strategy}
```

**Template 5: Data Model**
```markdown
## {ClassName}
**Type**: {dataclass|Pydantic|Enum}
**Module**: {module path}
### Fields
| Field | Type | Required | Default | Description |
### Validation
{rules}
### Usage
```python
{example code}
```
```

**Template 6: Pipeline Workflow**
```markdown
## Pipeline: {name}
**Module**: application/pipelines/{file}
### Input
{what it receives}
### Output
{what it produces}
### Steps
1. {step}, {duration}ms
2. {step}, {duration}ms
### Timeout
- Max: {ms}
### Error Handling
{strategy}
### Performance Target
- Latency: {ms}
- Throughput: {ops/sec}
```

**Template 7: Deployment Checklist**
```markdown
## Deployment: {name}
**Image**: {docker image}
**Ports**: {list}
### Environment Variables
| Var | Required | Purpose |
### Health Check
- Endpoint: {url}
- Interval: {seconds}
### Rollback
{procedure}
### Smoke Tests
```bash
{commands}
```
```

---

### SECTION 7: Change Detection & Auto-Update Policy

| # | Trigger (WHEN) | Action (THEN) | Owner | Automation |
|---|----------------|---------------|-------|------------|
| 1 | New Python file added to `core/` | Update parent module `AGENTS.md` with new file reference | Module maintainer | CI lint check |
| 2 | New REST endpoint added to `apps/api/` | Update API documentation and OpenAPI spec | API team | OpenAPI auto-gen |
| 3 | Dependency added/removed in `requirements.txt` | Update deployment docs and Docker build instructions | DevOps | `pip freeze` diff |
| 4 | Schema modified in `shared/schemas/` | Update data model documentation and dependent module docs | Schema owner | import-linter |
| 5 | Config key added to `shared/config/settings.py` | Update settings documentation and `.env.example` | Config owner | Manual review |
| 6 | Test file added to `tests/` | Update test documentation and coverage matrix | QA | Coverage report |
| 7 | Dockerfile or Compose file changed | Update deployment documentation and CI pipeline docs | DevOps | Docker build CI |
| 8 | CI pipeline (`ci.yml`) modified | Update CI documentation section | DevOps | Manual review |
| 9 | Any `AGENTS.md` modified | Update Section 5 coverage matrix in this index | Doc maintainer | Manual review |
| 10 | Performance SLA threshold changed | Update benchmark docs and Section 4 research layer | Performance team | Benchmark CI |
| 11 | New external service integrated | Update service integration docs and risk map | Integration owner | Manual review |
| 12 | Security vulnerability identified | Update risk map (Section 9) and create remediation ticket | Security team | SAST scan |

---

### SECTION 8: Documentation Governance Rules

**8.1 Naming Conventions**

| Item | Convention | Example |
|------|-----------|---------|
| Documentation files | kebab-case `.md` | `test-strategy.md`, `data-flow.md` |
| Knowledge base files | UPPER_SNAKE `.md` | `AGENTS.md`, `README.md` |
| PRD documents | `{NN}_{name}.md` numbered | `01_prd_cover.md`, `05_hld_system.md` |
| Analysis artifacts | descriptive kebab-case | `architecture-map.md`, `data-flows.md` |
| Config files | lowercase with extension | `config.yaml`, `.env.example` |
| Directories | lowercase, no hyphens in code dirs | `core/vqa/`, `shared/schemas/` |

**8.2 Quality Standards**

- All `.md` documentation files in `docs/PRD/` MUST include YAML front matter with `title`, `version`, `date`, `status`
- Mermaid diagrams MUST use `flowchart TB` or `flowchart LR` with named subgraphs, no pie charts, no sequence diagrams without justification
- Tables MUST have headers and alignment markers
- Code examples MUST specify language in fenced blocks (python, bash, etc.)
- All public-facing numbers (LOC, test count, file count) MUST be derived from automated scans, not manual estimates
- Maximum line length in documentation: 120 characters (matching code style)

**8.3 Review Workflow**

| Doc Type | Required Reviewer | Approval Needed | Auto-checks |
|----------|------------------|-----------------|-------------|
| AGENTS.md | Module maintainer | 1 approval | import-linter, prohibited terms scan |
| PRD documents | Tech lead + PM | 2 approvals | YAML front matter validation |
| API documentation | API team lead | 1 approval | Schema validation against code |
| Deployment docs | DevOps lead | 1 approval | Docker build smoke test |
| Risk/Security docs | Security team | 1 approval | SAST scan results attached |
| This index | Tech lead | 1 approval | Full prohibited terms scan |

**8.4 Prohibited Content**

- **NO** marketing language, promotional tone, or superlatives ("best-in-class", "revolutionary", "cutting-edge")
- **NO** prohibited terms: "Claude", "Anthropic", "OpenAI"
- **NO** hardcoded credentials, API keys, tokens, or secrets in any documentation
- **NO** placeholder text ("TBD", "TODO", "to be determined", "coming soon") in committed documentation
- **NO** duplicate content across `AGENTS.md` files, each file must be unique to its module scope
- **NO** `print()` statements in code examples, use `logging` module
- **NO** relative imports in code examples that cross module boundaries

---

### SECTION 9: Risk Map

| Risk ID | Category | Description | Severity | Likelihood | Affected Modules | Mitigation | Status |
|---------|----------|-------------|----------|------------|------------------|------------|--------|
| RISK-001 | Coupling | `apps/realtime/agent.py` is 2087 LOC with imports from ALL layers, god file | High | Confirmed | `apps/realtime`, all layers | Refactor into handler classes, extract perception, speech, and navigation into sub-modules | Open |
| RISK-002 | SPOF | Deepgram is the sole STT provider, no fallback if service is unavailable | High | Medium | `infrastructure/speech`, `apps/realtime` | Implement Whisper (local) as fallback STT provider | Open |
| RISK-003 | SPOF | ElevenLabs is the sole TTS provider, no fallback if service is unavailable | High | Medium | `infrastructure/speech`, `apps/realtime` | Implement Edge TTS or Coqui TTS as local fallback | Open |
| RISK-004 | Security | 7 API keys stored in `.env` with no secrets management (Vault, KMS) | Critical | Confirmed | All modules using external services | Migrate to HashiCorp Vault or cloud KMS, rotate all keys | Open |
| RISK-005 | Security | Docker containers run as root, no non-root user configured | High | Confirmed | `deployments/docker` | Add `USER nonroot` to Dockerfile, test with restricted permissions | Open |
| RISK-006 | Async | `OllamaEmbedder.embed_text()` is synchronous, blocks the event loop in async context | Medium | Confirmed | `core/memory/embeddings.py` | Wrap in `asyncio.to_thread()` or `run_in_executor()` | Open |
| RISK-007 | Resilience | No circuit breakers or retry/backoff for any cloud service (Ollama, Deepgram, ElevenLabs, LiveKit) | High | High | `infrastructure/*` | Implement `tenacity` retry with exponential backoff and circuit breaker pattern | Open |
| RISK-008 | Data | FAISS indices are not backed up, data loss on disk failure | Medium | Low | `core/memory`, `data/` | Implement scheduled FAISS index snapshots to cloud storage | Open |
| RISK-009 | Data | SQLite single-writer lock, concurrent write requests will queue or fail | Medium | Medium | `core/memory` | Use WAL mode for SQLite, consider PostgreSQL for multi-writer scenarios | Open |
| RISK-010 | Performance | Hot path SLA (500ms) may be violated under concurrent load, no load testing performed | High | Medium | `application/pipelines`, `apps/api` | Run load tests with Locust/k6, profile and optimize bottlenecks | Open |
| RISK-011 | GPU | ~3.1GB peak VRAM usage on 8GB RTX 4060, limited headroom for model upgrades | Medium | Medium | `core/vision`, `core/memory` | Profile per-model VRAM, implement model unloading between tasks | Open |
| RISK-012 | Privacy | Face recognition requires explicit consent gating, consent state persistence must be validated | High | Low | `core/face`, `apps/api` | Audit consent flow end-to-end, add integration tests for consent denial | Open |
| RISK-013 | Doc Gap | 3 modules lack AGENTS.md: `configs/`, `deployments/`, `scripts/` | Low | Confirmed | Documentation suite | Create AGENTS.md for remaining 3 modules | Open |
| RISK-014 | Architecture | `core/reasoning/` is a placeholder module with no implementation | Low | Confirmed | `core/reasoning` | Either implement or remove from architecture docs | Open |
| RISK-015 | External | 6 cloud provider dependencies, any provider outage degrades or disables functionality | High | Medium | All `infrastructure/` modules | Document degradation matrix, implement health checks per provider | Open |

---

### SECTION 10: Documentation Health Score

**Overall Score: 68/100**

| Metric | Raw Score | Max | Pct | Weight | Weighted Score | Details |
|--------|-----------|-----|-----|--------|----------------|---------|
| AGENTS.md Coverage | 14 | 25 | 56% | 25% | 14.0 | 14 of 25 modules have AGENTS.md files |
| Test Coverage | 21 | 25 | 84% | 25% | 21.0 | 21 of 25 modules have associated tests |
| README Coverage | 5 | 25 | 20% | 15% | 3.0 | ~5 modules have README files |
| PRD Completeness | 41 | 50 | 82% | 15% | 12.3 | 41 PRD files across 10 subdirectories |
| Doc Freshness | 9 | 10 | 90% | 10% | 9.0 | Last major update: 2026-02-23 |
| Risk Documentation | 8 | 10 | 80% | 10% | 8.0 | 15-entry risk map with mitigations |
| **Total** | | | | **100%** | **67.3 → 68** | |

**Improvement Recommendations**

| # | Action | Impact | Effort | Priority | Score Gain |
|---|--------|--------|--------|----------|------------|
| 1 | Create AGENTS.md for `configs/`, `deployments/`, `scripts/` | +3 AGENTS.md coverage | Low (1-2 hours) | High | +3.0 |
| 2 | Create README.md for all `core/` submodules (10 modules) | +10 README coverage | Medium (4-6 hours) | High | +6.0 |
| 3 | Add AGENTS.md to `core/reasoning/` or remove placeholder | +1 AGENTS.md + reduces doc confusion | Low (30 min) | Medium | +1.0 |
| 4 | Implement circuit breaker documentation for all cloud services | Completes resilience docs | Medium (2-3 hours) | High | +1.5 |
| 5 | Create load testing report and add to performance docs | Fills performance gap | High (8-12 hours) | Medium | +1.0 |
| 6 | Add README.md to `application/`, `infrastructure/`, `apps/` | +3 README coverage | Low (2 hours) | Medium | +1.8 |
| 7 | Document consent flow for face recognition end-to-end | Closes privacy risk gap | Medium (2-3 hours) | High | +0.5 |
| 8 | Create runbook for incident response and service degradation | Operational readiness | High (6-8 hours) | Medium | +1.0 |

**Target Score**: Implementing recommendations 1-4 would raise the score from **68 → 81/100**.

---

### Change Log

| Date | Section | Change | Author |
|------|---------|--------|--------|
| 2026-02-23 | All | Initial enterprise-grade documentation index creation | OpenCode Architect |
| 2026-02-23 | Sections 1-5 | Repository overview, directory map, architecture, research layer, coverage matrix | OpenCode Architect |
| 2026-02-23 | Sections 6-10 | Templates, change detection policy, governance, risk map, health score | OpenCode Architect |
| 2026-02-23 | Change Log | Initialized change tracking | OpenCode Architect |

---

*End of Document*
