## [1.0.0] — 2026-03-02

### Features

- **security**: complete P7 security scanning (T-133..T-136) and update task registry (fcf80473) `T-133` `T-136`
- **features**: complete Phase 6 Feature Evolution (9c08ffe3)
- **ops**: complete Phase 5 Operational Readiness (cedc1a6b)
- **perf**: complete Phase 4 Performance & Validation (T-073 through T-090) (c62f6cc9) `T-073` `T-090`
- **memory**: convert TextEmbedder to native async with retry â€” 17 tests (T-044) (967b6a25) `T-044`
- **application**: wire FrameOrchestrator to SpatialProcessor via spatial_binding (T-031) (6c3048ee) `T-031`
- **reasoning**: add ReasoningEngine MVP with QueryClassifier and routing (T-032) (670a1438) `T-032`
- **memory**: add validation, dedup, batch ingestion, error recovery to MemoryIngester (T-021) (e94744ba) `T-021`
- **spatial**: add clock-position output, verbosity levels, i18n hooks to MicroNavFormatter (T-017) (d1cd55f5) `T-017`
- **infrastructure/monitoring**: add MetricsCollector ABC, InMemoryMetrics, and NullMetrics (T-034) (5525c8a4) `T-034`
- **core/face**: add consent audit trail, TTL expiry, and revocation cascade (T-029) (8ef495ae) `T-029`
- **core/memory**: add score normalization, deduplication, and async wrapping to retriever (T-019) (b446e0c1) `T-019`
- **core/vision**: harden EdgeAwareSegmenter with real binary masks and edge extraction (T-015) (0073b7cd) `T-015`
- **infrastructure/storage**: add StorageAdapter ABC and LocalFileStorage implementation (T-033) (5c5043fd) `T-033`
- **application**: replace EventBus and SessionManager stubs with working MVPs (T-030) (9e18c45b) `T-030`
- **core/braille**: expand classifier with digits, punctuation, indicators, and state machine (T-027) (2552b08b) `T-027`
- **core/ocr**: add OCRResult type, retry logic, confidence merging, and fix fallback tests (T-026) (4ff21de1) `T-026`
- **core/memory**: add async embedding, batch embedding, and async fuse methods (T-020) (a900f9e5) `T-020`
- **core/memory**: harden FAISS indexer with atomic writes, SHA-256 checksums, and backup rotation (T-018) (ab3816a4) `T-018`
- **core/vision**: add YOLO ONNX detector and MiDaS depth estimator with model auto-download (T-013, T-014) (a51d504e) `T-013` `T-014`
- **scripts**: capture P0 baseline metrics for regression tracking (T-012) (9e9096b3) `T-012`
- **shared**: add SECRETS frozenset, validate_config(), and env var documentation (T-009) (b1257d6f) `T-009`
- **shared**: expand PII scrubber with patterns for all 7 API key formats (T-008) (14de260a) `T-008`
- **core**: add consent at-rest encryption with disk persistence (T-007) (c170e92b) `T-007`
- **shared**: add SecretProvider abstraction for secure credential access (T-001) (5b5f750f) `T-001`
- replace all-MiniLM-L6-v2 with qwen3-embedding:4b, remove calendar/email/contact/places (4b6e6e31)

### Bug Fixes

- **docker**: add non-root user and env_file secrets injection (T-003, T-004) (75c6adde) `T-003` `T-004`
- **shared**: delete duplicate encryption module and upgrade KDF to PBKDF2 (T-006) (f1ce8e8b) `T-006`

### Refactoring

- **realtime**: extract prompts + UserData, slim agent.py to 288 LOC (T-042) (1145eab7) `T-042`
- **realtime**: extract tool router with query classification and dispatch â€” 44 tests (T-041) (66e88819) `T-041`
- **realtime**: extract voice/search/QR into voice_controller.py â€” 7 tests (T-040) (be2aaf3b) `T-040`
- **realtime**: extract vision processing into vision_controller.py â€” 14 tests (T-039) (f1e879d8) `T-039`
- **shared**: replace 319-line duplicate init with thin re-export â€” 5 tests (T-047) (eb26e6fc) `T-047`
- **realtime**: extract session lifecycle into session_manager.py â€” 17 tests (T-038) (76323c35) `T-038`
- complete Phase 1-4 migration to Clean Architecture (c2b71b43)

### Tests

- **performance**: add P1 architecture check + metrics snapshot â€” 7 tests (T-037) (eb543bdb) `T-037`
- **integration**: add P1 end-to-end pipeline integration â€” 6 tests (T-036) (6dd8bbe3) `T-036`
- **performance**: add P1 exit criteria validation suite â€” 9 tests (T-035) (2225f93f) `T-035`
- **vqa**: add 9 unit tests for VQAReasoner, QuickAnswers, MicroNavFormatter (T-025) (61526a0b) `T-025`
- **vqa**: add 6 extended tests for PerceptionPipeline (T-024) (f186e7fb) `T-024`
- **vqa**: add 8 unit tests for SceneGraphBuilder (T-023) (2034fcf8) `T-023`
- **spatial**: add 8 integration tests for SpatialProcessor.process_frame (T-016) (b9c088c9) `T-016`
- **core/memory**: add 8 unit tests for CloudSyncAdapter and StubCloudBackend (T-022) (57a6e2c6) `T-022`
- **core/face**: add comprehensive face tracker unit tests (T-028) (6a67a796) `T-028`
- **integration**: add P0 security integration smoke tests (T-011) (27d8792b) `T-011`

### Documentation

- **sisyphus**: materialize 25 P1 task files with codebase-verified implementation specs (d168287d)
- **sisyphus**: materialize 12 P0 task files with codebase-verified implementation specs (32fd458f)
- **sisyphus**: revise P0 task objectives for codebase feasibility (v2 scope adjustment) (a146ea92)
- **sisyphus**: complete 150-task enumeration with full DAG validation (F1-F4 PASS) (9e844bca)
- **sisyphus**: resolve cross-phase DAG edges and inject stabilization checkpoints (37f95ece)
- **sisyphus**: enumerate Phase 7 Hardening (18 tasks T-133..T-150) â€” all 150 tasks complete (258cbec7) `T-133` `T-150`
- **sisyphus**: enumerate Phase 6 Feature Evolution (22 tasks T-111..T-132) (7d9b3abe) `T-111` `T-132`
- **sisyphus**: enumerate Phase 5 Operations (20 tasks T-091..T-110) (fd8c7bd7) `T-091` `T-110`
- **sisyphus**: enumerate Phase 4 Performance (18 tasks T-073..T-090) (a0319d7e) `T-073` `T-090`
- **sisyphus**: enumerate Phase 3 Resilience (20 tasks T-053..T-072) (59cf603d) `T-053` `T-072`
- **sisyphus**: enumerate Phase 2 Architecture Remediation (15 tasks T-038..T-052) (c924c6ce) `T-038` `T-052`
- **sisyphus**: enumerate Phase 1 Core Completion (25 tasks T-013..T-037) (e953f9d7) `T-013` `T-037`
- **sisyphus**: enumerate Phase 0 Foundation Hardening (12 tasks T-001..T-012) (e6ae1017) `T-001` `T-012`
- **sisyphus**: lock task schema, fix version mapping, resolve 18-task arithmetic gap (1a2306ba)
- restructure and update master documentation index (885c8b84)
- add hierarchical AGENTS.md knowledge base (0ce7d8a0)

### CI / DevOps

- **security**: add Bandit SAST and pip-audit dependency scanning (T-005, T-010) (c2095df4) `T-005` `T-010`

### Chores

- Add survey content and paper updates (71aedf6f)
- Full codebase push to major-2 repository (723dd332)
- Initial commit from workspace (723bfc72)
- Update README.md (2cf6def3)
- Update README.md (4a189e48)
- Update files (b8345214)
- Update files (25c7b01a)
- avatar added (5ecbecc5)


