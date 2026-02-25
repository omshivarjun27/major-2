
## Phase 9C+9D — Deployment & CI/CD + Monitoring & KPIs (2026-02-22)

### Learnings
 Windows environment: Python only accessible via `.venv/Scripts/python.exe`, not on PATH
 YAML front matter format: `---` delimiters with title, version, date (ISO), architecture_mode fields match existing PRD convention from HLD/LLD
 CI/CD pipeline closely mirrors existing `.github/workflows/ci.yml` structure: secrets-scan → test → lint → docker, extended with security scan, OpenAPI validation, GPU tests, and artifact publish stages
 Deployment architecture is single-process, single-user — no horizontal scaling story needed; document scaling limitations honestly
 Cloud resilience is the biggest gap (CLOUD_EFFICIENCY=4/10) — all 5 cloud services lack retry/backoff/circuit breaker; document current state + planned improvements (BACKLOG-004)
 GPU VRAM budget: ~3.1GB peak / 8GB available (38.75%) — comfortable headroom but no active monitoring exists
 Existing observability: PipelineMonitor + Watchdog + structured logging + /health + /debug/* endpoints + SuccessEnvelope meta (gpu_used, cloud_calls, processing_time_ms)
 Alert thresholds derived from: 75% VRAM = 6GB warning, SceneGraphBuilder confidence ≥ 0.3, FAISS ~5K vector limit, frame freshness 500ms, debounce 7s
 Key security blockers for production: root containers (ISSUE-002), .env in image (ISSUE-019), committed API keys (ISSUE-001)

### File Inventory Created
 `docs/PRD/10_deployment_ci_cd/deployment_architecture.md` — 300 lines, 4 sections (local node, cloud, deployment models, network)
 `docs/PRD/10_deployment_ci_cd/ci_cd_pipeline.yaml` — 376 lines, 10 stages with GitHub Actions syntax
 `docs/PRD/10_deployment_ci_cd/metadata.json` — valid JSON
 `docs/PRD/11_monitoring_kpis/monitoring_plan.md` — 275 lines, 4 sections (local, cloud, KPIs, observability stack)
 `docs/PRD/11_monitoring_kpis/alerts_and_runbooks.md` — 352 lines, 6 alerts with full runbooks
 `docs/PRD/11_monitoring_kpis/metadata.json` — valid JSON

## Phase 9A+9B — Security & Privacy + Testing Strategy (2026-02-22)

### Learnings
 STRIDE analysis works well when applied per-layer; the 6-layer architecture (Interface, Application, Domain, Local GPU, Cloud, Storage) maps cleanly to 6 STRIDE matrices with 36 threat cells total
 Hybrid-specific risks are the most impactful: GPU OOM crash, cloud rate limit exhaustion, prompt injection via scene descriptions, and RAG memory poisoning are all unique to the hybrid architecture
 Risk scoring: multiply Likelihood (1-5) x Impact (1-5) for a 1-25 scale; CRITICAL ≥20, HIGH ≥12, MEDIUM ≥6, LOW <6
 Data flow privacy boundary is clear: frames never leave local machine, only text descriptions sent to cloud — this is a strong privacy-by-design pattern worth documenting explicitly
 The `get_encryption_manager()` in `shared/utils/` exists but is not wired to FAISS — a common pattern of 'infrastructure exists but isn't connected'
 7 committed API keys (ISSUE-001) is the single highest-risk finding; all remediation paths trace back to BACKLOG-001/019/020
 Test strategy aligns with existing 429+ tests, async auto mode, and CI pipeline structure; coverage targets of 80% unit minimum are achievable given 99.3% pass rate on non-broken tests
 CSV format works well for E2E test matrices; 7 columns (Test_ID, Scenario, Layer, Cloud_Involved, GPU_Involved, Expected_Result, Pass_Fail_Criteria) cover all dimensions needed
 Python not on PATH in this Windows environment — use `py` launcher for validation scripts

### File Inventory Created
 `docs/PRD/08_security_privacy/threat_model.md` — STRIDE analysis per layer, 6 hybrid-specific risks, 24-item severity matrix, 8 mitigation strategies, 5 known vulnerabilities
 `docs/PRD/08_security_privacy/data_flow_privacy.md` — 6 cloud data flows, 9 local-only data categories, cloud exposure boundaries table, audio/image/embedding privacy, memory retention and log sanitization policies
 `docs/PRD/08_security_privacy/encryption_and_keys.md` — API key storage, 2 known exposure issues, remediation plan, HTTPS enforcement table, TLS config per service, local disk encryption status, FAISS protection, log redaction policy
 `docs/PRD/08_security_privacy/metadata.json` — valid JSON
 `docs/PRD/09_testing/test_plan.md` — 10 testing strategy sections covering unit, integration, GPU stress, cloud timeout, retry, memory, vector similarity, OCR, QR, and performance benchmarks
 `docs/PRD/09_testing/e2e_test_matrix.csv` — 20 test rows (exceeds 15 minimum), 7 columns, covers all required scenarios E2E-001 through E2E-020
 `docs/PRD/09_testing/metadata.json` — valid JSON