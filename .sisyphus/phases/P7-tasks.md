# Phase 7: Hardening & Release

> **Phase Focus**: SAST/DAST scanning, canary deployment, full regression suite (1000+ tests), release artifact packaging, production readiness certification.
> **Task Count**: 18 (T-133 through T-150)
> **Risk Classification**: HIGH for security scanning, load testing, chaos testing, and release packaging. MEDIUM for test completion, Docker optimization, and accessibility. LOW for documentation tasks.
> **Priority Unlock**: T-133 SAST Scanning Setup (parallel with T-134, T-137, T-138, T-139, T-140, T-141, T-143, T-144, T-145, T-146, T-147)

---

## T-133: sast-scanning-setup

- **Phase**: P7
- **Cluster**: CL-TQA
- **Objective**: Set up Static Application Security Testing (SAST) using Bandit for Python code analysis. Configure `bandit -r . -f json` with custom profile excluding false positives. Integrate SAST into CI pipeline as a required check. Target: zero critical and high findings. Configure baseline file to track known issues. Add pre-commit hook for SAST on changed files.
- **Upstream Deps**: []
- **Downstream Impact**: [`T-135`, `T-149`]
- **Risk Tier**: High
- **Test Layers**: [Unit, Regression]
- **Doc Mutation Map**: [`.github/workflows/AGENTS.md`, `AGENTS.md#security-risks`, `docs/security.md#sast`]
- **Versioning Impact**: patch
- **Governance Level**: elevated
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: yes, independent security tooling
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-134: dast-scanning-setup

- **Phase**: P7
- **Cluster**: CL-TQA
- **Objective**: Set up Dynamic Application Security Testing (DAST) using OWASP ZAP against the running REST API. Configure ZAP with the API spec (OpenAPI/Swagger). Scan for: SQL injection, XSS, CSRF, SSRF, auth bypass, information disclosure. Integrate into CI as a post-deployment validation step in staging. Target: zero critical and high findings. Generate HTML and JSON reports for each scan.
- **Upstream Deps**: []
- **Downstream Impact**: [`T-135`, `T-149`]
- **Risk Tier**: High
- **Test Layers**: [Integration, System]
- **Doc Mutation Map**: [`.github/workflows/AGENTS.md`, `AGENTS.md#security-risks`, `docs/security.md#dast`]
- **Versioning Impact**: patch
- **Governance Level**: elevated
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: yes, independent from SAST
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-135: dependency-vulnerability-scan

- **Phase**: P7
- **Cluster**: CL-TQA
- **Objective**: Set up dependency vulnerability scanning using Safety or pip-audit for Python packages. Scan all requirements files (requirements.txt, requirements-extras.txt). Integrate Trivy for Docker image vulnerability scanning. Configure severity thresholds: block on critical and high. Generate SBOM (Software Bill of Materials) in CycloneDX format. Add automated PR generation for vulnerable dependency updates via Dependabot configuration.
- **Upstream Deps**: [`T-133`, `T-134`]
- **Downstream Impact**: [`T-149`]
- **Risk Tier**: High
- **Test Layers**: [Unit, Regression]
- **Doc Mutation Map**: [`.github/workflows/AGENTS.md`, `AGENTS.md#security-risks`, `docs/security.md#dependency-scanning`]
- **Versioning Impact**: patch
- **Governance Level**: elevated
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: no, builds on SAST+DAST CI integration
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-136: security-hardening-audit

- **Phase**: P7
- **Cluster**: CL-TQA
- **Objective**: Conduct a comprehensive security hardening audit across the entire codebase. Verify: all API keys in vault (zero plaintext), Docker containers non-root, PII scrubbed from logs, encryption at rest for consent data, HTTPS enforced for all external calls, input validation on all API endpoints, rate limiting on public endpoints, CORS properly configured. Produce an audit report with pass/fail per check and remediation recommendations.
- **Upstream Deps**: [`T-135`]
- **Downstream Impact**: [`T-149`]
- **Risk Tier**: High
- **Test Layers**: [Integration, System, Regression]
- **Doc Mutation Map**: [`AGENTS.md#security-risks`, `docs/security.md#hardening-audit`]
- **Versioning Impact**: none
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, needs scanning results
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-137: load-test-50-users

- **Phase**: P7
- **Cluster**: CL-TQA
- **Objective**: Scale load testing from 10 (P4) to 50 concurrent users. Extend Locust test suite with realistic user scenarios including cloud sync traffic and reasoning queries. Run 1-hour sustained load test. Verify: 500ms hot-path SLA holds at P95, error rate < 0.5%, CPU < 85%, VRAM stable, no memory leaks, no connection pool exhaustion. Generate detailed performance report with degradation curves and bottleneck analysis.
- **Upstream Deps**: []
- **Downstream Impact**: [`T-149`]
- **Risk Tier**: High
- **Test Layers**: [Benchmark, System, Regression]
- **Doc Mutation Map**: [`tests/performance/AGENTS.md`, `docs/baselines/p7_load_test.json`, `AGENTS.md#performance-assumptions`]
- **Versioning Impact**: none
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: yes, independent load testing
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-138: chaos-testing-suite

- **Phase**: P7
- **Cluster**: CL-TQA
- **Objective**: Create a chaos testing suite that simulates real-world failure modes. Implement tests for: random service shutdown (kill Deepgram/ElevenLabs mock), network partition (block external traffic), VRAM exhaustion (allocate large tensors), disk full (fill temp storage), high CPU (spawn compute-intensive tasks), cascading failures (multiple services failing simultaneously). Verify system degrades gracefully and recovers automatically for each scenario. Target: 15 chaos test scenarios.
- **Upstream Deps**: []
- **Downstream Impact**: [`T-149`]
- **Risk Tier**: High
- **Test Layers**: [System, Regression]
- **Doc Mutation Map**: [`tests/performance/AGENTS.md`, `docs/testing.md#chaos-testing`]
- **Versioning Impact**: none
- **Governance Level**: elevated
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: yes, independent test suite
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-139: canary-deployment-setup

- **Phase**: P7
- **Cluster**: CL-OPS
- **Objective**: Implement canary deployment infrastructure for production releases. Configure traffic splitting: 10% to canary, 90% to stable. Implement automated canary analysis: compare error rate, latency, and resource utilization between canary and stable over 2-hour window. Auto-rollback if canary metrics degrade beyond threshold (error rate > 2x stable, P95 > 1.5x stable). Add manual promotion from canary to stable via CLI command. Integrate with monitoring for real-time canary health.
- **Upstream Deps**: []
- **Downstream Impact**: [`T-142`, `T-149`]
- **Risk Tier**: High
- **Test Layers**: [Integration, System]
- **Doc Mutation Map**: [`deployments/AGENTS.md`, `.github/workflows/AGENTS.md`, `docs/operations.md#canary-deployment`]
- **Versioning Impact**: minor
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: yes, deployment infrastructure
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-140: release-notes-automation

- **Phase**: P7
- **Cluster**: CL-GOV
- **Objective**: Automate release notes generation from git history and task metadata. Create `scripts/generate_release_notes.py` that: parses conventional commit messages, groups changes by category (features, fixes, performance, security), extracts Phase 7 task summaries, generates changelog in Markdown format, includes breaking changes section, adds upgrade instructions. Configure GitHub Release automation via Actions workflow.
- **Upstream Deps**: []
- **Downstream Impact**: [`T-148`]
- **Risk Tier**: Low
- **Test Layers**: [Unit]
- **Doc Mutation Map**: [`scripts/AGENTS.md`, `.github/workflows/AGENTS.md`, `docs/development.md#release-notes`]
- **Versioning Impact**: none
- **Governance Level**: standard
- **Regression Sensitivity**: low
- **Parallelization Eligible**: yes, documentation tooling
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-141: api-documentation-finalization

- **Phase**: P7
- **Cluster**: CL-GOV
- **Objective**: Finalize API documentation for all REST endpoints. Generate OpenAPI 3.0 spec from FastAPI auto-documentation. Review and enhance endpoint descriptions, request/response examples, error codes. Add authentication documentation. Create API versioning strategy document. Generate PDF version of API docs for offline reference. Verify all 28+ endpoints are documented with request/response schemas.
- **Upstream Deps**: []
- **Downstream Impact**: [`T-148`]
- **Risk Tier**: Low
- **Test Layers**: [Unit]
- **Doc Mutation Map**: [`apps/api/AGENTS.md`, `docs/api.md`, `AGENTS.md#documentation-coverage`]
- **Versioning Impact**: none
- **Governance Level**: standard
- **Regression Sensitivity**: low
- **Parallelization Eligible**: yes, documentation task
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-142: production-readiness-checklist

- **Phase**: P7
- **Cluster**: CL-GOV
- **Objective**: Create and execute a production readiness checklist. Verify: monitoring active (Prometheus + Grafana), alerts configured and tested, runbooks documented and validated, CD pipeline functional, canary deployment tested, backup/restore tested, security scans clean, load tests passing at 50 users, all environment configs validated, secrets managed securely, logging and tracing operational. Track each item as pass/fail with evidence links. This is the formal sign-off gate for production.
- **Upstream Deps**: [`T-136`, `T-137`, `T-139`]
- **Downstream Impact**: [`T-148`, `T-149`]
- **Risk Tier**: High
- **Test Layers**: [System, Regression]
- **Doc Mutation Map**: [`docs/operations.md#production-checklist`, `AGENTS.md#documentation-coverage`]
- **Versioning Impact**: none
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, needs security + load + canary results
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-143: user-documentation

- **Phase**: P7
- **Cluster**: CL-GOV
- **Objective**: Create user-facing documentation for blind/low-vision users. Document: voice commands and interactions, feature capabilities (vision, spatial, memory, QR/AR, braille, action recognition), configuration options, troubleshooting common issues, accessibility guidelines followed. Create quick-start guide for first-time users. Use clear, simple language (reading level: 8th grade). Ensure documentation is screen-reader compatible (proper heading hierarchy, alt-text for any diagrams).
- **Upstream Deps**: []
- **Downstream Impact**: [`T-148`]
- **Risk Tier**: Low
- **Test Layers**: [Unit, Accessibility]
- **Doc Mutation Map**: [`docs/user-guide/`, `AGENTS.md#documentation-coverage`]
- **Versioning Impact**: none
- **Governance Level**: standard
- **Regression Sensitivity**: low
- **Parallelization Eligible**: yes, documentation task
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-144: regression-test-completion

- **Phase**: P7
- **Cluster**: CL-TQA
- **Objective**: Ensure the test suite reaches 1000+ test functions. Identify coverage gaps across all modules. Add tests for: edge cases in cloud sync (network timeout during sync, partial sync failure), reasoning engine (ambiguous inputs, contradictory evidence), action recognition (low-light video, occluded subjects), performance regression (all SLA targets). Run full coverage report and target > 85% line coverage for core/ and application/ modules.
- **Upstream Deps**: []
- **Downstream Impact**: [`T-149`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration, System, Regression]
- **Doc Mutation Map**: [`tests/AGENTS.md`, `AGENTS.md#documentation-coverage`]
- **Versioning Impact**: none
- **Governance Level**: standard
- **Regression Sensitivity**: low
- **Parallelization Eligible**: yes, test writing independent
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-145: accessibility-compliance

- **Phase**: P7
- **Cluster**: CL-TQA
- **Objective**: Conduct accessibility compliance audit for all user-facing components. Verify: TTS announcements are clear and appropriately paced, voice commands have confirmation feedback, error messages are descriptive and actionable, spatial descriptions use consistent directional language, degradation notifications are immediate and informative. Test with screen readers (NVDA, VoiceOver) on all documentation. Produce a WCAG 2.1 AA compliance report.
- **Upstream Deps**: []
- **Downstream Impact**: [`T-149`]
- **Risk Tier**: Medium
- **Test Layers**: [Accessibility, System]
- **Doc Mutation Map**: [`docs/accessibility.md`, `AGENTS.md#documentation-coverage`]
- **Versioning Impact**: none
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: yes, independent audit
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-146: docker-image-optimization

- **Phase**: P7
- **Cluster**: CL-OPS
- **Objective**: Optimize the production Docker image for size and security. Implement multi-stage build with minimal runtime image (python:3.11-slim). Remove development dependencies, test files, and documentation from the runtime image. Add health check HEALTHCHECK instruction. Pin all base image versions. Run Trivy scan on final image. Target: image size < 1.5GB, zero critical vulnerabilities, startup time < 30 seconds. Tag image with semantic version from release.
- **Upstream Deps**: []
- **Downstream Impact**: [`T-148`]
- **Risk Tier**: Medium
- **Test Layers**: [Integration, System]
- **Doc Mutation Map**: [`deployments/AGENTS.md`, `docs/operations.md#docker`]
- **Versioning Impact**: patch
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: yes, Docker optimization independent
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-147: smoke-test-suite

- **Phase**: P7
- **Cluster**: CL-OPS
- **Objective**: Create a comprehensive smoke test suite for post-deployment validation. Tests verify: API endpoints respond (200 on /health, /health/services), WebRTC agent connects, TTS produces audio output, STT processes audio input, vision pipeline processes an image, memory queries return results, QR scanner detects test QR code. Each test must complete within 30 seconds. Suite runs as part of CD pipeline and canary validation.
- **Upstream Deps**: []
- **Downstream Impact**: [`T-149`]
- **Risk Tier**: Medium
- **Test Layers**: [System, Canary]
- **Doc Mutation Map**: [`tests/AGENTS.md`, `.github/workflows/AGENTS.md`, `docs/testing.md#smoke-tests`]
- **Versioning Impact**: none
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: yes, test suite development
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-148: p7-release-documentation

- **Phase**: P7
- **Cluster**: CL-GOV
- **Objective**: Integration closeout adjacent. Compile all documentation into a release-ready state. Verify: API docs complete, user guide complete, operations guide complete, architecture docs current, security docs updated with scan results. Generate release notes. Create upgrade guide from current version. Verify all AGENTS.md files reflect current module state. Ensure no stale references to pre-refactoring code (agent.py monolith references removed). Final documentation sign-off.
- **Upstream Deps**: [`T-140`, `T-141`, `T-142`, `T-143`, `T-146`]
- **Downstream Impact**: [`T-149`]
- **Risk Tier**: Low
- **Test Layers**: [Unit]
- **Doc Mutation Map**: [`docs/`, `AGENTS.md`, `AGENTS.md#documentation-coverage`]
- **Versioning Impact**: none
- **Governance Level**: standard
- **Regression Sensitivity**: low
- **Parallelization Eligible**: no, needs all doc tasks
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-149: p7-final-regression-suite

- **Phase**: P7
- **Cluster**: CL-TQA
- **Objective**: Integration closeout (1 of 2). Execute the complete 1000+ test regression suite. All tests must pass. Run SAST (zero critical/high), DAST (zero critical/high), dependency scan (zero critical/high). Execute chaos test suite. Verify load test at 50 concurrent users passes all SLA targets. Verify accessibility audit passes WCAG 2.1 AA. Produce a comprehensive quality gate report with pass/fail for each category. This is the penultimate gate before release.
- **Upstream Deps**: [`T-138`, `T-144`, `T-147`, `T-148`]
- **Downstream Impact**: [`T-150`]
- **Risk Tier**: High
- **Test Layers**: [Unit, Integration, System, Regression, Benchmark, Accessibility]
- **Doc Mutation Map**: [`tests/AGENTS.md`, `docs/quality-gate.md`, `AGENTS.md#documentation-coverage`]
- **Versioning Impact**: none
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, final validation
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-150: p7-release-artifact-packaging

- **Phase**: P7
- **Cluster**: CL-OPS
- **Objective**: CAPSTONE TASK. Package the final release artifacts. Build and tag the production Docker image with semantic version. Push to container registry. Create GitHub Release with auto-generated release notes. Publish release SBOM (Software Bill of Materials). Execute canary deployment to production (10% traffic, 2 hours). Monitor canary metrics. Upon successful canary: promote to 100% traffic. Archive release artifacts (Docker image digest, SBOM, test reports, security scan results). This is the final task in the 150-task master plan.
- **Upstream Deps**: [`T-149`]
- **Downstream Impact**: []
- **Risk Tier**: High
- **Test Layers**: [System, Canary]
- **Doc Mutation Map**: [`deployments/AGENTS.md`, `AGENTS.md#documentation-coverage`, `docs/releases/`]
- **Versioning Impact**: major
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, final release task
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## Phase Exit Criteria

1. All tasks in this phase have `current_state: completed`
2. SAST scan: zero critical and high findings
3. DAST scan: zero critical and high findings
4. Dependency vulnerability scan: zero critical and high findings
5. Full regression test suite passing (100% of 1000+ tests)
6. Load test at 50 concurrent users: 500ms SLA maintained, error rate < 0.5%
7. Canary deployment successful (10% traffic for 2 hours, no errors)
8. All documentation complete and reviewed
9. Production readiness checklist all pass
10. Release artifacts packaged and archived

## Downstream Notes

- This is the final phase. Successful completion means production release readiness.
- Post-release: establish Phase 8+ for maintenance, monitoring, and iterative improvement.
- All baseline metrics from this phase become the production SLA targets.
