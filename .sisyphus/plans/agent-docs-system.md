# Plan: agent-docs-system

Create/update AGENTS.md files across the entire repository following the Autonomous Agent Documentation System (AADS) specification.

## Naming Decision
Keep `AGENTS.md` (uppercase, plural) as canonical filename — 14 files already use this convention.
User's "Agent.md" request honored as concept (richer per-directory documentation), not literal filename.

## Phase 1: Update Root AGENTS.md (10-section format)
 [x] 1.1 Rewrite root AGENTS.md with 10-section enterprise structure: Project Overview, Global Architecture Map, Repository Structure Map, Global Task Intelligence, Architectural Thinking Log, Research Layer, Risk Radar, Technical Debt Register, Documentation & Coverage Status, Change Log + 6 reusable templates

## Phase 2: Update Existing Layer-Level AGENTS.md (6 files → 9-section format)
 [x] 2.1 Update `core/AGENTS.md` with 9-section folder structure
 [x] 2.2 Update `application/AGENTS.md` with 9-section folder structure
 [x] 2.3 Update `infrastructure/AGENTS.md` with 9-section folder structure
 [x] 2.4 Update `apps/AGENTS.md` with 9-section folder structure
 [x] 2.5 Update `shared/AGENTS.md` with 9-section folder structure
 [x] 2.6 Update `tests/AGENTS.md` with 9-section folder structure

## Phase 3: Update Existing Subsystem AGENTS.md (7 files → 9-section format)
 [x] 3.1 Update `core/vqa/AGENTS.md` with 9-section folder structure
 [x] 3.2 Update `core/memory/AGENTS.md` with 9-section folder structure
 [x] 3.3 Update `core/vision/AGENTS.md` with 9-section folder structure
 [x] 3.4 Update `core/ocr/AGENTS.md` with 9-section folder structure
 [x] 3.5 Update `application/pipelines/AGENTS.md` with 9-section folder structure
 [x] 3.6 Update `application/frame_processing/AGENTS.md` with 9-section folder structure
 [x] 3.7 Update `tests/performance/AGENTS.md` with 9-section folder structure

## Phase 4: Create NEW AGENTS.md — Core Layer Subdirectories (7 files)
 [x] 4.1 Create `core/braille/AGENTS.md` with 9-section folder structure
 [x] 4.2 Create `core/qr/AGENTS.md` with 9-section folder structure
 [x] 4.3 Create `core/face/AGENTS.md` with 9-section folder structure
 [x] 4.4 Create `core/speech/AGENTS.md` with 9-section folder structure
 [x] 4.5 Create `core/audio/AGENTS.md` with 9-section folder structure
 [x] 4.6 Create `core/action/AGENTS.md` with 9-section folder structure
 [x] 4.7 Create `core/reasoning/AGENTS.md` with 9-section folder structure (placeholder module — document its status)

## Phase 5: Create NEW AGENTS.md — Apps Layer Subdirectories (3 files)
 [x] 5.1 Create `apps/api/AGENTS.md` with 9-section folder structure
 [x] 5.2 Create `apps/realtime/AGENTS.md` with 9-section folder structure
 [x] 5.3 Create `apps/cli/AGENTS.md` with 9-section folder structure

## Phase 6: Create NEW AGENTS.md — Infrastructure Subdirectories (5+5 files)
 [x] 6.1 Create `infrastructure/llm/AGENTS.md` with 9-section folder structure
 [x] 6.2 Create `infrastructure/speech/AGENTS.md` with 9-section folder structure
 [x] 6.3 Create `infrastructure/tavus/AGENTS.md` with 9-section folder structure
 [x] 6.4 Create `infrastructure/storage/AGENTS.md` with 9-section folder structure (stub module)
 [x] 6.5 Create `infrastructure/monitoring/AGENTS.md` with 9-section folder structure (stub module)
 [x] 6.6 Create `infrastructure/llm/ollama/AGENTS.md` with 9-section folder structure
 [x] 6.7 Create `infrastructure/llm/siliconflow/AGENTS.md` with 9-section folder structure
 [x] 6.8 Create `infrastructure/llm/embeddings/AGENTS.md` with 9-section folder structure
 [x] 6.9 Create `infrastructure/speech/deepgram/AGENTS.md` with 9-section folder structure
 [x] 6.10 Create `infrastructure/speech/elevenlabs/AGENTS.md` with 9-section folder structure

## Phase 7: Create NEW AGENTS.md — Shared Layer Subdirectories (5 files)
 [x] 7.1 Create `shared/config/AGENTS.md` with 9-section folder structure
 [x] 7.2 Create `shared/schemas/AGENTS.md` with 9-section folder structure
 [x] 7.3 Create `shared/logging/AGENTS.md` with 9-section folder structure
 [x] 7.4 Create `shared/utils/AGENTS.md` with 9-section folder structure
 [x] 7.5 Create `shared/debug/AGENTS.md` with 9-section folder structure

## Phase 8: Create NEW AGENTS.md — Application Subdirectories (2 files)
 [x] 8.1 Create `application/event_bus/AGENTS.md` with 9-section folder structure (stub module)
 [x] 8.2 Create `application/session_management/AGENTS.md` with 9-section folder structure (stub module)

## Phase 9: Create NEW AGENTS.md — Test Subdirectories (3 files)
 [x] 9.1 Create `tests/unit/AGENTS.md` with 9-section folder structure
 [x] 9.2 Create `tests/integration/AGENTS.md` with 9-section folder structure
 [x] 9.3 Create `tests/realtime/AGENTS.md` with 9-section folder structure

## Phase 10: Create NEW AGENTS.md — Support Directories (6 files)
 [x] 10.1 Create `configs/AGENTS.md` with 9-section folder structure
 [x] 10.2 Create `deployments/AGENTS.md` with 9-section folder structure
 [x] 10.3 Create `scripts/AGENTS.md` with 9-section folder structure
 [x] 10.4 Create `docs/AGENTS.md` with 9-section folder structure
 [x] 10.5 Create `research/AGENTS.md` with 9-section folder structure
 [x] 10.6 Create `deployments/docker/AGENTS.md` with 9-section folder structure

## Phase 11: Final Verification & Synchronization
 [x] 11.1 Verify all AGENTS.md files exist (50 total — confirmed via glob)
 [x] 11.2 Scan all files for prohibited terms — 0 violations found
 [x] 11.3 Verify root AGENTS.md cross-references all folder AGENTS.md files — Section 9 updated with 100% coverage
 [x] 11.4 Update docs/docs-index.md Documentation Coverage Matrix — 25/25 modules, health score 79/100
 [x] 11.5 Update docs/progress.md — 63% completion, M16 100%, health score 78/100

---
Total tasks: 52 (1 root + 13 updates + 37 new + 5 verification)
Parallelization: Phases 4-10 tasks within each phase are independent and can run in parallel (batches of 3-5)
Sequential dependencies: Phase 1 must complete before Phases 2-3; Phase 11 requires all prior phases