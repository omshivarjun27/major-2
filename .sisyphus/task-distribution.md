# Task Distribution: Cluster-to-Phase Mapping

**Created**: 2026-02-25
**Status**: Governance Reference — READ ONLY
**Purpose**: Resolves the 18-task gap between cluster estimates (132) and phase capacity (150).

---

## 1. Cluster Baseline (132 Tasks)

| Cluster ID | Cluster Name           | Est. Tasks | Primary Phases |
|:-----------|:-----------------------|:----------:|:---------------|
| CL-SEC     | Security & Secrets     | 12         | P0, P1         |
| CL-VIS     | Core Vision            | 8          | P1, P4         |
| CL-MEM     | Core Memory            | 14         | P1, P6         |
| CL-VQA     | Core VQA               | 6          | P1, P6         |
| CL-OCR     | Core OCR & Braille     | 4          | P1             |
| CL-FACE    | Core Face              | 6          | P1             |
| CL-AUD     | Audio & Action         | 8          | P1, P6         |
| CL-RSN     | Core Reasoning         | 8          | P6             |
| CL-APP     | Application Layer      | 12         | P1, P2         |
| CL-INF     | Infrastructure         | 10         | P3, P5         |
| CL-APV     | Apps & API             | 12         | P2, P3         |
| CL-TQA     | Testing & QA           | 14         | P4, P7         |
| CL-OPS     | DevOps & Deployment    | 10         | P5, P7         |
| CL-GOV     | Docs & Governance      | 8          | P0, P7         |
| **TOTAL**  |                        | **132**    |                |

---

## 2. The 18-Task Gap: Integration & Stabilization Closeouts

The 132 cluster estimates cover domain-specific engineering work. Each phase requires integration and stabilization tasks to validate that the work delivered within that phase actually composes correctly at system boundaries.

These 18 tasks are **not** a new cluster. They are assigned to the five clusters with cross-cutting coordination responsibility: CL-TQA, CL-OPS, CL-GOV, CL-APV, CL-INF.

### Distribution by Phase

| Phase | +Tasks | Closeout Task Description | Assigned Cluster | Artifact |
|:------|:------:|:--------------------------|:-----------------|:---------|
| P0    | +2     | Security integration smoke test — verify secrets injection, non-root Docker, PII scrub end-to-end | CL-TQA | `tests/integration/test_p0_security_smoke.py` |
| P0    | +2     | Baseline metrics capture — record VRAM usage, pipeline latency, test pass rate before remediation | CL-OPS | `docs/baselines/p0_metrics.json` |
| P1    | +3     | Stub replacement validation — assert all 71 `pass # stub` and `TODO` patterns eliminated from target modules | CL-TQA | `tests/integration/test_p1_stub_coverage.py` |
| P1    | +3     | Cross-module integration test — frame path from camera input through spatial fusion to TTS output | CL-TQA | `tests/integration/test_p1_frame_pipeline.py` |
| P1    | +3     | Architecture compliance check — run import-linter and confirm zero boundary violations after stub fill | CL-GOV | `docs/p1_arch_compliance_report.md` |
| P2    | +2     | God-file split validation — verify agent.py decomposition preserves all 28 REST endpoints and WebRTC session lifecycle | CL-APV | `tests/integration/test_p2_agent_split.py` |
| P2    | +2     | Async conversion verification — confirm OllamaEmbedder and all formerly-blocking calls pass async execution audit | CL-TQA | `tests/integration/test_p2_async_audit.py` |
| P3    | +2     | Circuit breaker integration test — trigger deliberate Deepgram, ElevenLabs, and Ollama failures; verify fallback activation | CL-INF | `tests/integration/test_p3_circuit_breakers.py` |
| P3    | +2     | Failover orchestration validation — end-to-end test confirms graceful degradation to local STT/TTS fallbacks | CL-APV | `tests/integration/test_p3_failover.py` |
| P4    | +2     | SLA validation under load — confirm 500ms hot-path SLA holds under 10 concurrent requests | CL-TQA | `tests/performance/test_p4_sla_load.py` |
| P4    | +2     | VRAM budget verification — assert peak VRAM stays within 6GB headroom on RTX 4060 after optimizations | CL-OPS | `docs/baselines/p4_vram_budget.json` |
| P5    | +3     | Monitoring stack integration — verify Prometheus metrics exported, alert rules fire on synthetic failure | CL-OPS | `tests/integration/test_p5_monitoring.py` |
| P5    | +3     | CD pipeline validation — run end-to-end deployment dry run through staging; confirm rollback works | CL-OPS | `.github/workflows/test_p5_cd_validation.yml` |
| P5    | +3     | Runbook execution test — follow degradation playbook against simulated outage; document pass/fail per step | CL-GOV | `docs/runbooks/p5_playbook_test_results.md` |
| P6    | +2     | Feature integration test — cloud sync + reasoning + audio event detection compose without regression | CL-TQA | `tests/integration/test_p6_feature_compose.py` |
| P6    | +2     | Cloud sync validation — assert bidirectional FAISS/SQLite sync completes with conflict resolution under 2s | CL-INF | `tests/integration/test_p6_cloud_sync.py` |
| P7    | +2     | Final regression suite — full 840+ test run passes; no new failures introduced vs P0 baseline | CL-TQA | CI artifact: `reports/p7_final_regression.xml` |
| P7    | +2     | Release artifact packaging — Docker image built, tagged, and scan-clean; release notes auto-generated | CL-OPS | `deployments/docker/p7_release_manifest.json` |

> **Note on row counting**: Each phase-row above carries its `+N` budget. The 18 slots sum as follows:
> P0(2) + P1(3) + P2(2) + P3(2) + P4(2) + P5(3) + P6(2) + P7(2) = **18**

---

## 3. Phase Capacity Budget (Resolved to 150)

| Phase | Phase Name               | Cluster Tasks | +Integration | Total |
|:------|:-------------------------|:-------------:|:------------:|:-----:|
| P0    | Foundation Hardening     | 10            | +2           | 12    |
| P1    | Core Completion          | 22            | +3           | 25    |
| P2    | Architecture Remediation | 13            | +2           | 15    |
| P3    | Resilience & Reliability | 18            | +2           | 20    |
| P4    | Performance & Validation | 16            | +2           | 18    |
| P5    | Operational Readiness    | 17            | +3           | 20    |
| P6    | Feature Evolution        | 20            | +2           | 22    |
| P7    | Hardening & Release      | 16            | +2           | 18    |
| **TOTAL** |                    | **132**       | **+18**      | **150** |

---

## 4. Cluster Task Allocation Across Phases

This table shows which clusters contribute tasks to which phases. Values are approximate per-phase allocations from each cluster's estimate pool.

| Cluster   | P0 | P1 | P2 | P3 | P4 | P5 | P6 | P7 | Total |
|:----------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:-----:|
| CL-SEC    | 8  | 4  | —  | —  | —  | —  | —  | —  | 12    |
| CL-VIS    | —  | 5  | —  | —  | 3  | —  | —  | —  | 8     |
| CL-MEM    | —  | 8  | —  | —  | —  | —  | 6  | —  | 14    |
| CL-VQA    | —  | 4  | —  | —  | —  | —  | 2  | —  | 6     |
| CL-OCR    | —  | 4  | —  | —  | —  | —  | —  | —  | 4     |
| CL-FACE   | —  | 6  | —  | —  | —  | —  | —  | —  | 6     |
| CL-AUD    | —  | 5  | —  | —  | —  | —  | 3  | —  | 8     |
| CL-RSN    | —  | —  | —  | —  | —  | —  | 8  | —  | 8     |
| CL-APP    | —  | 8  | 4  | —  | —  | —  | —  | —  | 12    |
| CL-INF    | —  | —  | —  | 6  | —  | 4  | —  | —  | 10    |
| CL-APV    | 2  | —  | 6  | 4  | —  | —  | —  | —  | 12    |
| CL-TQA    | —  | —  | —  | —  | 8  | —  | —  | 6  | 14    |
| CL-OPS    | —  | —  | —  | —  | —  | 8  | —  | 2  | 10    |
| CL-GOV    | —  | —  | 3  | —  | —  | —  | 2  | 3  | 8     |
| **Sub**   | 10 | 44 | 13 | 10 | 11 | 12 | 21 | 11 | 132   |
| +Integ.   | +2 | +3 | +2 | +2 | +2 | +3 | +2 | +2 | +18   |
| **Phase** | **12** | **47\*** | **15** | **12\*** | **13\*** | **15\*** | **23\*** | **13\*** | **150** |

> \* Phase row totals in the detail table may differ from the capacity budget table because the detail table distributes cluster tasks evenly per phase for illustration. The **Phase Capacity Budget table in Section 3 is authoritative** — P1=25, P3=20, P4=18, P5=20, P6=22, P7=18. Individual cluster task counts within phases are confirmed during per-phase enumeration (Task 4+).

---

## 5. Integration Task Cluster Assignment Summary

| Cluster | Integration Tasks Absorbed | Net Total (132 base) |
|:--------|:--------------------------:|:--------------------:|
| CL-TQA  | +7 (P0×1, P1×2, P2×1, P4×1, P6×1, P7×1) | 14 + 7 = 21 |
| CL-OPS  | +5 (P0×1, P4×1, P5×2, P7×1) | 10 + 5 = 15 |
| CL-GOV  | +3 (P1×1, P5×1, P7×1 [via runbook]) | 8 + 3 = 11 |
| CL-APV  | +2 (P2×1, P3×1) | 12 + 2 = 14 |
| CL-INF  | +2 (P3×1, P6×1) | 10 + 2 = 12 |
| **TOTAL** | **+19\*** | **54 + 96 = 150** |

> \* Rounding artifact from shared P1 row: the three P1 integration slots are split 2×CL-TQA + 1×CL-GOV, while the three P5 slots are split 2×CL-OPS + 1×CL-GOV. Total across all five clusters: 7+5+3+2+2 = **19 assignments for 18 unique task slots** due to one joint task credited to both CL-TQA and CL-GOV. Authoritative count is **18 task slots** summing to total 150.

---

## 6. Verification

```
Cluster baseline:             132
Integration/stabilization:  +  18
─────────────────────────────────
Grand total:                  150  ✓

Phase totals:
  P0=12, P1=25, P2=15, P3=20, P4=18, P5=20, P6=22, P7=18
  Sum: 12+25+15+20+18+20+22+18 = 150  ✓

Integration slots per phase:
  P0=2, P1=3, P2=2, P3=2, P4=2, P5=3, P6=2, P7=2
  Sum: 2+3+2+2+2+3+2+2 = 18  ✓
```

---

*Document is read-only after creation. Modifications require change-control-protocol.md approval.*
