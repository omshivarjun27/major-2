# Phase 0: Foundation Hardening

> **Phase Focus**: Security remediation, secrets migration, Docker hardening, SAST baseline setup.
> **Task Count**: 12 (T-001 through T-012)
> **Risk Classification**: CRITICAL, single-task isolation mandatory.
> **Priority Unlock**: T-001 Secrets Migration

---

## T-001: secrets-migration

- **Phase**: P0
- **Cluster**: CL-SEC
- **Objective**: Migrate 7 API keys (LIVEKIT_API_KEY, DEEPGRAM_API_KEY, OLLAMA_API_KEY, ELEVEN_API_KEY, OLLAMA_VL_API_KEY, TAVUS_API_KEY, LIVEKIT_API_SECRET) from plaintext `.env` storage to a vault/KMS backend with runtime injection. This is the priority unlock task for Phase 0. Every downstream security task depends on secrets being properly managed before it can proceed. The migration must preserve backward compatibility for local development while enforcing vault-based retrieval in staging and production environments.
- **Upstream Deps**: []
- **Downstream Impact**: [`T-002`, `T-004`, `T-006`, `T-008`, `T-009`]
- **Risk Tier**: Critical
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`AGENTS.md#security-risks`, `shared/config/AGENTS.md`, `docs/deployment.md#secrets`]
- **Versioning Impact**: patch
- **Governance Level**: critical
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, Phase 0 requires single-task isolation
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-002: secrets-provider-abstraction

- **Phase**: P0
- **Cluster**: CL-SEC
- **Objective**: Create a SecretProvider interface in `shared/config/` with concrete implementations for three environments: local `.env` file (development), HashiCorp Vault (staging), and cloud KMS (production). The abstraction allows `shared/config/settings.py` to retrieve secrets through a unified API regardless of the backing store. Each provider must support key rotation notifications and health checks. This decouples the application from any single secrets backend and enables zero-downtime key rotation.
- **Upstream Deps**: [`T-001`]
- **Downstream Impact**: [`T-004`, `T-009`]
- **Risk Tier**: Critical
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`shared/config/AGENTS.md`, `AGENTS.md#repository-structure`, `docs/architecture.md#shared-config`]
- **Versioning Impact**: minor
- **Governance Level**: critical
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, Phase 0 requires single-task isolation
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-003: docker-non-root-user

- **Phase**: P0
- **Cluster**: CL-SEC
- **Objective**: Modify both `Dockerfile` (root) and `deployments/docker/Dockerfile` to run containers as a non-root user. Add a dedicated application user via `RUN useradd`, apply the `USER` directive, and fix file permissions on model directories, data volumes, and configuration files. Verify that the FastAPI server (port 8000) and LiveKit agent (port 8081) start correctly under the restricted user. This directly addresses security risk SR-2 and technical debt TD-005.
- **Upstream Deps**: []
- **Downstream Impact**: [`T-004`, `T-011`]
- **Risk Tier**: Critical
- **Test Layers**: [Integration, System]
- **Doc Mutation Map**: [`deployments/AGENTS.md`, `AGENTS.md#security-risks`, `docs/deployment.md#docker`]
- **Versioning Impact**: patch
- **Governance Level**: critical
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, Phase 0 requires single-task isolation
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-004: docker-secrets-injection

- **Phase**: P0
- **Cluster**: CL-SEC
- **Objective**: Configure Docker and Docker Compose to inject secrets via environment variables or mounted secret files instead of baking `.env` into images. Update `docker-compose.test.yml` and deployment configurations under `deployments/` to read secrets from the vault/KMS infrastructure established by T-001. Remove any `COPY .env` directives from Dockerfiles. Validate that containers start and authenticate with all 7 API services when secrets are injected at runtime rather than build time.
- **Upstream Deps**: [`T-001`, `T-003`]
- **Downstream Impact**: [`T-011`]
- **Risk Tier**: Critical
- **Test Layers**: [Integration, System]
- **Doc Mutation Map**: [`deployments/AGENTS.md`, `deployments/docker/AGENTS.md`, `docs/deployment.md#secrets-injection`]
- **Versioning Impact**: patch
- **Governance Level**: critical
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, Phase 0 requires single-task isolation
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-005: sast-ci-integration

- **Phase**: P0
- **Cluster**: CL-SEC
- **Objective**: Integrate Bandit (Python SAST) into the existing GitHub Actions CI pipeline at `.github/workflows/ci.yml`. Configure Bandit to scan all Python source directories (shared, core, application, infrastructure, apps) and fail the build on critical or high severity findings. Add Bandit to `pyproject.toml` tool configuration with appropriate exclusion rules for test files and generated code. Establish a baseline report so future phases can track security regression.
- **Upstream Deps**: []
- **Downstream Impact**: [`T-010`]
- **Risk Tier**: Critical
- **Test Layers**: [Integration, Regression]
- **Doc Mutation Map**: [`.github/AGENTS.md`, `AGENTS.md#security-risks`, `docs/ci-cd.md#sast`]
- **Versioning Impact**: none
- **Governance Level**: critical
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, Phase 0 requires single-task isolation
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-006: encryption-utility-audit

- **Phase**: P0
- **Cluster**: CL-SEC
- **Objective**: Audit and harden `shared/utils/encryption.py` to ensure it uses AES-256 with proper key derivation (PBKDF2 or Argon2), authenticated encryption (AES-GCM or ChaCha20-Poly1305), and no hardcoded keys or initialization vectors. Remove the duplicate encryption file identified in TD-014. Verify that the encryption module integrates cleanly with the SecretProvider from T-001 for key material retrieval. Add explicit documentation of the cryptographic choices and their threat model coverage.
- **Upstream Deps**: [`T-001`]
- **Downstream Impact**: [`T-007`]
- **Risk Tier**: Critical
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`shared/utils/AGENTS.md`, `AGENTS.md#technical-debt`, `docs/security.md#encryption`]
- **Versioning Impact**: patch
- **Governance Level**: critical
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, Phase 0 requires single-task isolation
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-007: consent-state-encryption

- **Phase**: P0
- **Cluster**: CL-SEC
- **Objective**: Encrypt the local consent storage file used by `core/memory/api_endpoints.py`. Currently, consent state (SR-4) is stored as a plaintext local file with no protection against tampering or unauthorized reads. Using the hardened encryption utilities from T-006, add at-rest encryption to the consent file. Implement integrity verification on read so that tampered consent files are detected and rejected. Preserve the existing `/memory/consent` REST endpoint behavior while adding the encryption layer transparently.
- **Upstream Deps**: [`T-006`]
- **Downstream Impact**: [`T-011`]
- **Risk Tier**: Critical
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/memory/AGENTS.md`, `AGENTS.md#security-risks`, `docs/privacy.md#consent`]
- **Versioning Impact**: patch
- **Governance Level**: critical
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, Phase 0 requires single-task isolation
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-008: pii-scrubber-verification

- **Phase**: P0
- **Cluster**: CL-SEC
- **Objective**: Verify that the PII scrubber in `shared/logging/pii_scrubber.py` catches all 7 API key patterns (LIVEKIT_API_KEY, DEEPGRAM_API_KEY, OLLAMA_API_KEY, ELEVEN_API_KEY, OLLAMA_VL_API_KEY, TAVUS_API_KEY, LIVEKIT_API_SECRET) before they reach log output. Add any missing regex patterns for key formats that aren't currently covered. Write regression tests that inject each key format into log messages and assert redaction. This closes the gap between the existing PII scrubber (BASE-022) and the full set of secrets identified in T-001.
- **Upstream Deps**: [`T-001`]
- **Downstream Impact**: [`T-011`]
- **Risk Tier**: Critical
- **Test Layers**: [Unit, Regression]
- **Doc Mutation Map**: [`shared/logging/AGENTS.md`, `AGENTS.md#security-risks`, `docs/logging.md#pii-scrubbing`]
- **Versioning Impact**: patch
- **Governance Level**: critical
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, Phase 0 requires single-task isolation
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-009: env-var-documentation

- **Phase**: P0
- **Cluster**: CL-SEC
- **Objective**: Document all 85+ environment variables defined in `shared/config/settings.py` with human-readable descriptions, default values, type information, and security classifications (public, internal, secret). Group variables by functional area (LiveKit, Deepgram, Ollama, ElevenLabs, Tavus, spatial perception, QR scanning, memory, general). Mark which variables contain secrets and must be sourced from the SecretProvider. This addresses TD-012 and gives operators a complete reference for configuring deployments without guessing at undocumented knobs.
- **Upstream Deps**: [`T-002`]
- **Downstream Impact**: [`T-012`]
- **Risk Tier**: Critical
- **Test Layers**: [Unit]
- **Doc Mutation Map**: [`shared/config/AGENTS.md`, `docs/configuration.md`, `AGENTS.md#technical-debt`]
- **Versioning Impact**: none
- **Governance Level**: critical
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, Phase 0 requires single-task isolation
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-010: dependency-vulnerability-scan

- **Phase**: P0
- **Cluster**: CL-SEC
- **Objective**: Add `pip-audit` or `safety` dependency vulnerability scanning to the GitHub Actions CI pipeline. Configure the scanner to check `requirements.txt` and `requirements-extras.txt` against known vulnerability databases and fail the build on critical findings. Produce a machine-readable report (JSON) that can be archived as a CI artifact. Combine this with the Bandit SAST step from T-005 to create a comprehensive security gate in CI that blocks merges when critical vulnerabilities are present in either code or dependencies.
- **Upstream Deps**: [`T-005`]
- **Downstream Impact**: [`T-011`]
- **Risk Tier**: Critical
- **Test Layers**: [Integration, Regression]
- **Doc Mutation Map**: [`.github/AGENTS.md`, `AGENTS.md#security-risks`, `docs/ci-cd.md#dependency-scanning`]
- **Versioning Impact**: none
- **Governance Level**: critical
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, Phase 0 requires single-task isolation
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-011: p0-security-integration-smoke-test

- **Phase**: P0
- **Cluster**: CL-TQA
- **Objective**: End-to-end verification that secrets injection, non-root Docker execution, and PII scrubbing work together as a cohesive security layer. Create `tests/integration/test_p0_security_smoke.py` with test scenarios that: (1) start a Docker container as non-root, (2) verify secrets are injected at runtime and accessible to the application, (3) confirm that none of the 7 API keys appear in any log output, and (4) validate that the consent file is encrypted at rest. This is one of the two integration/stabilization closeout tasks for Phase 0.
- **Upstream Deps**: [`T-001`, `T-003`, `T-004`, `T-008`]
- **Downstream Impact**: [`T-012`]
- **Risk Tier**: Critical
- **Test Layers**: [Integration, System]
- **Doc Mutation Map**: [`tests/AGENTS.md`, `AGENTS.md#documentation-coverage`]
- **Versioning Impact**: none
- **Governance Level**: critical
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, Phase 0 requires single-task isolation
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-012: p0-baseline-metrics-capture

- **Phase**: P0
- **Cluster**: CL-OPS
- **Objective**: Record current VRAM usage, pipeline latency (hot path end-to-end, vision processing, OCR, memory query), test pass rate, LOC counts per module, and stub inventory counts before Phase 1 begins. Produce a structured artifact at `docs/baselines/p0_metrics.json` containing all measurements with timestamps. This snapshot serves as the regression baseline for every subsequent phase. Without it, performance and quality claims in later phases have no reference point. This is the second integration/stabilization closeout task for Phase 0.
- **Upstream Deps**: [`T-011`]
- **Downstream Impact**: []
- **Risk Tier**: Critical
- **Test Layers**: [Benchmark]
- **Doc Mutation Map**: [`docs/baselines/AGENTS.md`, `AGENTS.md#performance-assumptions`]
- **Versioning Impact**: none
- **Governance Level**: critical
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, Phase 0 requires single-task isolation
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## Phase Exit Criteria

1. All tasks in this phase have `current_state: completed`
2. Zero failing tests across all `test_layers` specified by tasks in this phase
3. Every entry in every task's `doc_mutation_map` has been verified as updated
4. No unresolved `blocked` tasks remain
5. Regression suite shows no coverage drop compared to phase entry baseline
6. All 7 API keys rotated and stored in vault/KMS (zero plaintext in .env)
7. Docker containers running as non-root user confirmed
8. Zero critical security issues from SAST scan
9. Secrets management infrastructure verified operational

## Downstream Notes

- P1 Core Completion depends on secrets infrastructure being operational for cloud API testing
- P2 agent.py refactoring assumes Docker hardening is complete
- P3 circuit breakers for cloud services require secrets management from T-001/T-002
