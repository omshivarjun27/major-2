# Project Directory Tree

```
.
├── .github
│   ├── commands
│   │   ├── gemini-invoke.toml
│   │   ├── gemini-plan-execute.toml
│   │   ├── gemini-review.toml
│   │   ├── gemini-scheduled-triage.toml
│   │   └── gemini-triage.toml
│   ├── workflows
│   │   ├── ci.yml
│   │   ├── deploy-production.yml
│   │   ├── deploy-staging.yml
│   │   ├── gemini-dispatch.yml
│   │   ├── gemini-invoke.yml
│   │   ├── gemini-plan-execute.yml
│   │   ├── gemini-review.yml
│   │   ├── gemini-scheduled-triage.yml
│   │   ├── gemini-triage.yml
│   │   └── security.yml
│   └── dependabot.yml
├── application
│   ├── event_bus
│   │   ├── __init__.py
│   │   ├── AGENTS.md
│   │   └── bus.py
│   ├── frame_processing
│   │   ├── __init__.py
│   │   ├── AGENTS.md
│   │   ├── confidence_cascade.py
│   │   ├── frame_orchestrator.py
│   │   ├── freshness.py
│   │   ├── live_frame_manager.py
│   │   └── spatial_binding.py
│   ├── pipelines
│   │   ├── __init__.py
│   │   ├── AGENTS.md
│   │   ├── audio_manager.py
│   │   ├── cancellation.py
│   │   ├── debouncer.py
│   │   ├── frame_sampler.py
│   │   ├── integration.py
│   │   ├── perception_pool.py
│   │   ├── perception_telemetry.py
│   │   ├── pipeline_monitor.py
│   │   ├── streaming_tts.py
│   │   ├── watchdog.py
│   │   └── worker_pool.py
│   ├── session_management
│   │   ├── __init__.py
│   │   ├── AGENTS.md
│   │   └── manager.py
│   ├── __init__.py
│   └── AGENTS.md
├── apps
│   ├── api
│   │   ├── __init__.py
│   │   ├── AGENTS.md
│   │   └── server.py
│   ├── cli
│   │   ├── __init__.py
│   │   ├── AGENTS.md
│   │   ├── session_logger.py
│   │   └── visualizer.py
│   ├── realtime
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── AGENTS.md
│   │   ├── entrypoint.py
│   │   ├── prompts.py
│   │   ├── session_manager.py
│   │   ├── tool_router.py
│   │   ├── user_data.py
│   │   ├── vision_controller.py
│   │   └── voice_controller.py
│   ├── __init__.py
│   └── AGENTS.md
├── configs
│   ├── AGENTS.md
│   ├── config.yaml
│   ├── development.yaml
│   ├── production.yaml
│   └── staging.yaml
├── core
│   ├── action
│   │   ├── __init__.py
│   │   ├── action_context.py
│   │   ├── action_recognizer.py
│   │   ├── AGENTS.md
│   │   └── clip_recognizer.py
│   ├── audio
│   │   ├── __init__.py
│   │   ├── AGENTS.md
│   │   ├── audio_event_detector.py
│   │   ├── audio_fusion.py
│   │   ├── enhanced_detector.py
│   │   └── ssl.py
│   ├── braille
│   │   ├── __init__.py
│   │   ├── AGENTS.md
│   │   ├── braille_capture.py
│   │   ├── braille_classifier.py
│   │   ├── braille_ocr.py
│   │   ├── braille_segmenter.py
│   │   ├── embossing_guidance.py
│   │   └── scenario_analysis.md
│   ├── face
│   │   ├── __init__.py
│   │   ├── AGENTS.md
│   │   ├── consent_audit.py
│   │   ├── face_detector.py
│   │   ├── face_embeddings.py
│   │   ├── face_social_cues.py
│   │   └── face_tracker.py
│   ├── memory
│   │   ├── __init__.py
│   │   ├── AGENTS.md
│   │   ├── api_endpoints.py
│   │   ├── api_schema.py
│   │   ├── cloud_sync.py
│   │   ├── config.py
│   │   ├── conflict_resolver.py
│   │   ├── embeddings.py
│   │   ├── event_detection.py
│   │   ├── faiss_sync.py
│   │   ├── index_factory.py
│   │   ├── indexer.py
│   │   ├── ingest.py
│   │   ├── llm_client.py
│   │   ├── maintenance.py
│   │   ├── offline_queue.py
│   │   ├── privacy_controls.py
│   │   ├── rag_reasoner.py
│   │   ├── README.md
│   │   ├── retriever.py
│   │   ├── scenario_analysis.md
│   │   ├── sqlite_manager.py
│   │   └── sqlite_sync.py
│   ├── ocr
│   │   ├── __init__.py
│   │   ├── AGENTS.md
│   │   └── engine.py
│   ├── qr
│   │   ├── __init__.py
│   │   ├── AGENTS.md
│   │   ├── ar_tag_handler.py
│   │   ├── cache_manager.py
│   │   ├── qr_api.py
│   │   ├── qr_decoder.py
│   │   └── qr_scanner.py
│   ├── qr_cache
│   ├── reasoning
│   │   ├── __init__.py
│   │   ├── AGENTS.md
│   │   ├── causal.py
│   │   ├── engine.py
│   │   ├── integration.py
│   │   ├── reasoning_foundation.py
│   │   ├── spatial.py
│   │   └── temporal.py
│   ├── speech
│   │   ├── __init__.py
│   │   ├── AGENTS.md
│   │   ├── speech_handler.py
│   │   ├── tts_handler.py
│   │   ├── voice_ask_pipeline.py
│   │   └── voice_router.py
│   ├── vision
│   │   ├── __init__.py
│   │   ├── AGENTS.md
│   │   ├── model_download.py
│   │   ├── model_loader.py
│   │   ├── spatial.py
│   │   └── visual.py
│   ├── vqa
│   │   ├── __init__.py
│   │   ├── AGENTS.md
│   │   ├── api_endpoints.py
│   │   ├── api_schema.py
│   │   ├── memory.py
│   │   ├── multi_frame_vqa.py
│   │   ├── orchestrator.py
│   │   ├── perception.py
│   │   ├── priority_scene.py
│   │   ├── scene_graph.py
│   │   ├── scene_narrator.py
│   │   ├── spatial_fuser.py
│   │   └── vqa_reasoner.py
│   ├── __init__.py
│   └── AGENTS.md
├── data
│   ├── audit
│   ├── cloud_storage
│   │   ├── custom-bucket
│   │   ├── faiss-indices
│   │   └── sqlite-sync
│   ├── consent
│   │   ├── device_123.json
│   │   ├── face_audit.jsonl
│   │   ├── test_device.json
│   │   └── test_out_device.json
│   ├── debug_frames
│   ├── memory_backup
│   │   └── backup_info.json
│   ├── memory_index
│   └── offline_queue
├── deployments
│   ├── canary
│   │   └── docker-compose.canary.yml
│   ├── compose
│   │   ├── docker-compose.dev.yml
│   │   ├── docker-compose.prod.yml
│   │   ├── docker-compose.staging.yml
│   │   └── docker-compose.test.yml
│   ├── docker
│   │   ├── AGENTS.md
│   │   └── Dockerfile
│   ├── grafana
│   │   ├── dashboards
│   │   │   ├── health-status.json
│   │   │   ├── pipeline-performance.json
│   │   │   ├── service-resilience.json
│   │   │   ├── system-health.json
│   │   │   └── user-activity.json
│   │   └── provisioning
│   │       ├── dashboards
│   │       │   └── dashboards.yml
│   │       └── datasources
│   │           └── prometheus.yml
│   ├── loki
│   │   ├── loki-config.yml
│   │   └── promtail-config.yml
│   ├── prometheus
│   │   ├── alert_rules.yml
│   │   ├── alertmanager.yml
│   │   └── prometheus.yml
│   └── AGENTS.md
├── docs
│   ├── analysis
│   │   ├── ci_checks
│   │   │   ├── build_output.txt
│   │   │   ├── pytest_unit_output.txt
│   │   │   ├── ruff_format_output.txt
│   │   │   └── ruff_output.txt
│   │   ├── issues
│   │   │   ├── ISSUE-001.md
│   │   │   ├── ISSUE-002.md
│   │   │   ├── ISSUE-003.md
│   │   │   ├── ISSUE-004.md
│   │   │   ├── ISSUE-005.md
│   │   │   ├── ISSUE-006.md
│   │   │   ├── ISSUE-007.md
│   │   │   ├── ISSUE-008.md
│   │   │   ├── ISSUE-009.md
│   │   │   ├── ISSUE-010.md
│   │   │   ├── ISSUE-011.md
│   │   │   ├── ISSUE-012.md
│   │   │   ├── ISSUE-013.md
│   │   │   ├── ISSUE-014.md
│   │   │   ├── ISSUE-015.md
│   │   │   ├── ISSUE-016.md
│   │   │   ├── ISSUE-017.md
│   │   │   ├── ISSUE-018.md
│   │   │   ├── ISSUE-019.md
│   │   │   ├── ISSUE-020.md
│   │   │   ├── ISSUE-021.md
│   │   │   ├── ISSUE-022.md
│   │   │   ├── ISSUE-023.md
│   │   │   ├── ISSUE-024.md
│   │   │   ├── ISSUE-025.md
│   │   │   └── ISSUE-026.md
│   │   ├── analysis_report.json
│   │   ├── architecture_risks.md
│   │   ├── ci_summary.json
│   │   ├── component_inventory.json
│   │   ├── data_flows.md
│   │   ├── data_model_inventory.json
│   │   ├── entry_points.json
│   │   ├── hybrid_readiness.md
│   │   ├── language_summary.json
│   │   ├── phase1_summary.md
│   │   ├── phase2_summary.md
│   │   ├── phase3_summary.md
│   │   ├── repo_index.json
│   │   ├── repo_tree.txt
│   │   ├── secrets_report.md
│   │   ├── security_scan.json
│   │   ├── test_summary.json
│   │   └── tooling_detected.json
│   ├── api
│   │   ├── openapi.json
│   │   └── README.md
│   ├── architecture
│   │   └── agent-decomposition.md
│   ├── audits
│   │   └── p2_async_audit.md
│   ├── backlog
│   │   └── prioritized_backlog.json
│   ├── baselines
│   │   ├── p0_metrics.json
│   │   ├── p1_metrics.json
│   │   └── p2_metrics.json
│   ├── performance
│   │   ├── baseline-metrics.json
│   │   ├── baseline-report.md
│   │   ├── hot-path-analysis.md
│   │   ├── hot-path-metrics.json
│   │   ├── load-test-results.md
│   │   └── vram-analysis.md
│   ├── PRD
│   │   ├── 04_hld
│   │   │   ├── deployment_diagram.mmd
│   │   │   ├── HLD.md
│   │   │   ├── HLD_diagram.mmd
│   │   │   └── metadata.json
│   │   ├── 05_lld
│   │   │   ├── LLD_async_boundaries.md
│   │   │   ├── LLD_data_models.json
│   │   │   ├── LLD_modules.md
│   │   │   ├── LLD_systems.md
│   │   │   └── metadata.json
│   │   ├── 06_api
│   │   │   ├── api_examples.json
│   │   │   ├── error_contracts.json
│   │   │   ├── metadata.json
│   │   │   └── openapi.yaml
│   │   ├── 07_requirements
│   │   │   └── traceability_matrix.md
│   │   ├── 08_security_privacy
│   │   │   ├── data_flow_privacy.md
│   │   │   ├── encryption_and_keys.md
│   │   │   ├── metadata.json
│   │   │   └── threat_model.md
│   │   ├── 09_testing
│   │   │   ├── e2e_test_matrix.csv
│   │   │   ├── metadata.json
│   │   │   └── test_plan.md
│   │   ├── 10_deployment_ci_cd
│   │   │   ├── ci_cd_pipeline.yaml
│   │   │   ├── deployment_architecture.md
│   │   │   └── metadata.json
│   │   ├── 11_monitoring_kpis
│   │   │   ├── alerts_and_runbooks.md
│   │   │   ├── metadata.json
│   │   │   └── monitoring_plan.md
│   │   ├── 15_diagrams
│   │   │   ├── component_diagram.mmd
│   │   │   ├── component_render_cmd.txt
│   │   │   └── sequence_user_upload_to_speech.mmd
│   │   ├── 00_cover.md
│   │   ├── 00_executive_summary.md
│   │   ├── 01_overview.md
│   │   ├── 02_scope.md
│   │   ├── 03_stakeholders.md
│   │   ├── 14_rollout_and_migration.md
│   │   ├── 15_release_plan.md
│   │   ├── 16_versioning_strategy.md
│   │   ├── 17_prd_validation_report.md
│   │   ├── final_package_manifest.json
│   │   └── metadata.json
│   ├── runbooks
│   │   ├── degradation-playbook.md
│   │   └── incident-response.md
│   ├── validations
│   │   ├── p2_async_verification.md
│   │   └── p2_god_file_split.md
│   ├── accessibility-audit.md
│   ├── AGENTS.md
│   ├── architecture.md
│   ├── benchmarking-protocol.md
│   ├── canary-deployment.md
│   ├── configuration.md
│   ├── DataFlow.md
│   ├── docs-index.md
│   ├── HLD.md
│   ├── LLD.md
│   ├── Memory.md
│   ├── opencode-bedrock-setup-guide.md
│   ├── operations-guide.md
│   ├── operations.md
│   ├── production-readiness-checklist.md
│   ├── progress.md
│   ├── quality-gate-report.md
│   ├── security.md
│   ├── SystemArchitecture.md
│   ├── tech-debt.md
│   ├── test-strategy.md
│   ├── upgrade-guide.md
│   ├── user-guide.md
│   └── validation-checkpoints.md
├── failures
│   ├── failures_index.jsonl
│   └── reproduce_all.sh
├── fixes
│   ├── fix_config_docs_undocumented_vars.diff
│   ├── fix_debug_endpoints_import.diff
│   ├── fix_health_registry_asyncio_get_event_loop.diff
│   ├── fix_ocr_easyocr_lazy_import.diff
│   ├── fix_pipeline_edge_cases_debouncer_api.diff
│   ├── fix_spatial_edge_cases_schema_api.diff
│   ├── fix_tts_failover_timing.diff
│   └── fix_tts_stt_edge_cases_intent_type.diff
├── infrastructure
│   ├── backup
│   │   ├── __init__.py
│   │   ├── faiss_backup.py
│   │   ├── scheduler.py
│   │   └── sqlite_backup.py
│   ├── llm
│   │   ├── embeddings
│   │   │   ├── __init__.py
│   │   │   └── AGENTS.md
│   │   ├── ollama
│   │   │   ├── __init__.py
│   │   │   ├── AGENTS.md
│   │   │   └── handler.py
│   │   ├── siliconflow
│   │   │   ├── __init__.py
│   │   │   └── AGENTS.md
│   │   ├── __init__.py
│   │   ├── AGENTS.md
│   │   ├── config.py
│   │   └── internet_search.py
│   ├── monitoring
│   │   ├── __init__.py
│   │   ├── AGENTS.md
│   │   ├── collector.py
│   │   ├── instrumentation.py
│   │   └── prometheus_metrics.py
│   ├── resilience
│   │   ├── __init__.py
│   │   ├── circuit_breaker.py
│   │   ├── degradation_coordinator.py
│   │   ├── error_classifier.py
│   │   ├── health_registry.py
│   │   ├── livekit_monitor.py
│   │   ├── retry_policy.py
│   │   └── timeout_config.py
│   ├── speech
│   │   ├── deepgram
│   │   │   ├── __init__.py
│   │   │   ├── AGENTS.md
│   │   │   └── resilience.py
│   │   ├── elevenlabs
│   │   │   ├── __init__.py
│   │   │   ├── AGENTS.md
│   │   │   └── tts_manager.py
│   │   ├── local
│   │   │   ├── __init__.py
│   │   │   ├── edge_tts_fallback.py
│   │   │   └── whisper_stt.py
│   │   ├── __init__.py
│   │   ├── AGENTS.md
│   │   ├── stt_failover.py
│   │   └── tts_failover.py
│   ├── storage
│   │   ├── __init__.py
│   │   ├── adapter.py
│   │   └── AGENTS.md
│   ├── tavus
│   │   ├── __init__.py
│   │   ├── adapter.py
│   │   └── AGENTS.md
│   ├── __init__.py
│   └── AGENTS.md
├── logs
│   ├── install.log
│   ├── run.log
│   ├── static_analysis.log
│   ├── tests.log
│   └── tests_unit_noocr.log
├── models
│   ├── midas_v21_small_256.onnx
│   └── yolov8n.onnx
├── my-first-extension
│   ├── example.js
│   ├── gemini-extension.json
│   ├── package.json
│   └── README.md
├── Papers
│   ├── fig
│   │   ├── block_diagram_prompt.txt
│   │   └── survey_outcomes_prompt.txt
│   ├── Health Related Papers
│   │   ├── 10072_2023_7082_OnlinePDF-1.pdf
│   │   ├── fpubh-10-912460.pdf
│   │   ├── fresc-04-1238158.pdf
│   │   ├── ijerph-18-13336-v2.pdf
│   │   ├── sensors-17-01497.pdf
│   │   └── sustainability-12-08689.pdf
│   ├── Overleaf_Project
│   │   ├── figures
│   │   │   ├── fig1_architecture.txt
│   │   │   ├── fig2_dataflow.txt
│   │   │   ├── fig3_fusion.txt
│   │   │   ├── fig4_deployment.txt
│   │   │   └── fig5_evaluation.txt
│   │   ├── sections
│   │   │   ├── acknowledgements.tex
│   │   │   ├── background.tex
│   │   │   ├── conclusion.tex
│   │   │   ├── discussion.tex
│   │   │   ├── experiments.tex
│   │   │   ├── intro.tex
│   │   │   ├── methods.tex
│   │   │   ├── related_work.tex
│   │   │   └── results.tex
│   │   ├── main.tex
│   │   ├── README_overleaf.txt
│   │   └── refs.bib
│   ├── PROJECT REPORTS
│   │   ├── Project Docs
│   │   │   ├── New folder
│   │   │   │   ├── BrailleToSpeech1.pdf
│   │   │   │   ├── BrailleToSpeech2.pdf
│   │   │   │   ├── BrailleToSpeech3.pdf
│   │   │   │   ├── ImageToSpeech1 (1).pdf
│   │   │   │   ├── ImageToSpeech1.pdf
│   │   │   │   ├── ImageToSpeech2.pdf
│   │   │   │   ├── ImageToSpeech3.pdf
│   │   │   │   ├── ImageToSpeech4.pdf
│   │   │   │   ├── ObjectRecognition.pdf
│   │   │   │   ├── TextToSpeech3.pdf
│   │   │   │   └── TextToSpeech4.pdf
│   │   │   ├── Aus Occup Therapy J - 2024 - Tan - Training and learning support for people with vision impairment in the use of.pdf
│   │   │   ├── BE_3rd__4th_2022_Scheme.pdf
│   │   │   ├── Braille_Text_to_Speech_Conversion - Copy.pdf
│   │   │   ├── Braille_Text_to_Speech_Conversion.pdf
│   │   │   ├── EXAM TIMEBTABLE.pdf
│   │   │   ├── Paper 10.pdf
│   │   │   ├── Paper 11.pdf
│   │   │   ├── Paper 12.pdf
│   │   │   ├── Paper 13.pdf
│   │   │   ├── Paper 14.pdf
│   │   │   ├── Paper 15.pdf
│   │   │   ├── Paper 16.pdf
│   │   │   ├── Paper 17.pdf
│   │   │   ├── Paper 18.pdf
│   │   │   ├── paper 19.pdf
│   │   │   ├── paper 20.pdf
│   │   │   ├── Paper 21.pdf
│   │   │   ├── Paper 22.pdf
│   │   │   ├── Paper 23.pdf
│   │   │   ├── Paper 24.pdf
│   │   │   ├── Paper 25.pdf
│   │   │   ├── Paper 26.pdf
│   │   │   ├── Paper 27.pdf
│   │   │   ├── Paper 28.pdf
│   │   │   ├── Paper 29.pdf
│   │   │   ├── Paper 30.pdf
│   │   │   ├── Paper 31.pdf
│   │   │   ├── Paper 32.pdf
│   │   │   ├── Paper 33.pdf
│   │   │   ├── Paper 34.pdf
│   │   │   ├── Paper 35.pdf
│   │   │   ├── Paper 36.pdf
│   │   │   ├── Paper 37.pdf
│   │   │   ├── Paper 38.pdf
│   │   │   ├── Paper 39.pdf
│   │   │   ├── paper 4.pdf
│   │   │   ├── Paper 40.pdf
│   │   │   ├── paper 41.pdf
│   │   │   ├── paper 42.pdf
│   │   │   ├── paper 44.pdf
│   │   │   ├── paper 5.pdf
│   │   │   ├── Paper 7.pdf
│   │   │   ├── Paper 8.pdf
│   │   │   ├── Paper 9.pdf
│   │   │   └── Sample_Synopsis_Template[1].docx
│   │   ├── Braille_Text_to_Speech_Conversion - Copy.pdf
│   │   ├── Braille_Text_to_Speech_Conversion.pdf
│   │   ├── Paper 12.pdf
│   │   ├── Paper 16.pdf
│   │   ├── Paper 17.pdf
│   │   ├── Paper 18.pdf
│   │   ├── paper 19.pdf
│   │   ├── paper 20.pdf
│   │   ├── Paper 21.pdf
│   │   ├── Paper 23.pdf
│   │   ├── Paper 24.pdf
│   │   ├── Paper 25.pdf
│   │   ├── Paper 26.pdf
│   │   ├── Paper 27.pdf
│   │   ├── Paper 34.pdf
│   │   ├── Paper 37.pdf
│   │   ├── paper 4.pdf
│   │   ├── Paper 40.pdf
│   │   ├── paper 41.pdf
│   │   ├── paper 42.pdf
│   │   ├── paper 44.pdf
│   │   └── Paper 8.pdf
│   ├── Technical papers
│   │   ├── 1-s2.0-S0167865518308602-main.pdf
│   │   ├── 1-s2.0-S1319157821002718-main.pdf
│   │   ├── 1-s2.0-S1687850726000038-main.pdf
│   │   ├── 1-s2.0-S2215016125002869-main.pdf
│   │   ├── 1-s2.0-S2405844024078563-main.pdf
│   │   ├── 1-s2.0-S2590137022001583-main.pdf
│   │   ├── 2-JOT1477.pdf
│   │   ├── 2025.naacl-long.310.pdf
│   │   ├── 2501.15819v1.pdf
│   │   ├── 28522.pdf
│   │   ├── 2910674.2910709.pdf
│   │   ├── 888-4021-1-PB.pdf
│   │   ├── 9Vol102No19.pdf
│   │   ├── A_Transformer-Based_Multimodal_Object_Detection_System_for_Real-World_Applications.pdf
│   │   ├── An-Integrated-OCR-Based-A.pdf
│   │   ├── An_Outdoor_Navigation_Assistance_System_for_Visually_Impaired_People_in_Public_Transportation.pdf
│   │   ├── assistive-object-recognition-system-for-visually-impaired-IJERTV9IS090382.pdf
│   │   ├── Blind-Aided_Target_Detection_Algorithm_Based_on_Cascading_Feature_Pyramids_With_Lightweight_Dual-Path_Downsampling.pdf
│   │   ├── Cursive_Text_Recognition_in_Natural_Scene_Images_Using_Deep_Convolutional_Recurrent_Neural_Network.pdf
│   │   ├── Daneshyari.com_382212.pdf
│   │   ├── document.pdf
│   │   ├── Dynamic_Crosswalk_Scene_Understanding_for_the_Visually_Impaired.pdf
│   │   ├── electronics-11-02266.pdf
│   │   ├── Emotion_Recognition_Using_a_Glasses-Type_Wearable_Device_via_Multi-Channel_Facial_Responses.pdf
│   │   ├── Enhancing_Accessibility_Through_Machine_Learning_A_Review_on_Visual_and_Hearing_Impairment_Technologies.pdf
│   │   ├── Enhancing_Object_Detection_in_Assistive_Technology_for_the_Visually_Impaired_A_DETR-Based_Approach.pdf
│   │   ├── ESWA_D_20_01112R2_1_.pdf
│   │   ├── frobt-06-00125.pdf
│   │   ├── guerreiro2020virtual.pdf
│   │   ├── i2164-2591-14-5-28_1748358698.50853.pdf
│   │   ├── information-13-00343.pdf
│   │   ├── information-16-00808.pdf
│   │   ├── Infrastructure_Enabled_Guided_Navigation_for_Visually_Impaired.pdf
│   │   ├── jdr20240086.pdf
│   │   ├── JITE-IIPv21p095-114Kumar8367.pdf
│   │   ├── Li_Optical_Braille_Recognition_Based_on_Semantic_Segmentation_Network_With_Auxiliary_CVPRW_2020_paper.pdf
│   │   ├── Multimodality-Based_Situational_Knowledge_for_Obstacle_Detection_and_Alert_Generation_to_Enhance_the_Navigation_Assistive_Systems.pdf
│   │   ├── nihms972545.pdf
│   │   ├── Obstacle_Avoidance_of_a_UAV_Using_Fast_Monocular_Depth_Estimation_for_a_Wide_Stereo_Camera.pdf
│   │   ├── Perception_Assistance_for_the_Visually_Impaired_Through_Smart_Objects_Concept_Implementation_and_Experiment_Scenario.pdf
│   │   ├── reading-assistant-for-blind-people-using-artificial-intelligence-IJERTCONV10IS09035.pdf
│   │   ├── ria_37.04_09.pdf
│   │   ├── S0167865518308602 (1).pdf
│   │   ├── S0167865518308602.pdf
│   │   ├── SBVQA_2.0_Robust_End-to-End_Speech-Based_Visual_Question_Answering_for_Open-Ended_Questions.pdf
│   │   ├── sensors-12-08236.pdf
│   │   ├── sensors-18-01506.pdf
│   │   ├── sensors-19-02771.pdf
│   │   ├── sensors-21-01249-v2.pdf
│   │   ├── sensors-23-04033.pdf
│   │   ├── sensors-24-00166.pdf
│   │   ├── StereoPilot_A_Wearable_Target_Location_System_for_Blind_and_Visually_Impaired_Using_Spatial_Audio_Rendering.pdf
│   │   ├── Supporting_navigation_of_outdoor_shopping_complexes_for_visuallyimpaired_users_through_multi-modal_data_fusion.pdf
│   │   ├── symmetry-12-01069-v2.pdf
│   │   ├── technologies-08-00037-v3.pdf
│   │   ├── technologies-13-00297.pdf
│   │   ├── Tilt_Correction_Toward_Building_Detection_of_Remote_Sensing_Images.pdf
│   │   ├── Tools and Technologies for Blind and Visually Impaired Navigation Support  A Review.pdf
│   │   └── TSP_CMES_68393.pdf
│   ├── _generate_docx.py
│   ├── author_choices.txt
│   ├── diagram_prompts.txt
│   ├── implementation_appendix.txt
│   ├── processing_report.txt
│   ├── read_errors.log
│   ├── README_generate_and_compile.md
│   ├── refs.bib
│   ├── sample paper 2.pdf
│   ├── sample paper.pdf
│   ├── survey_table.tex
│   ├── tables_content.csv
│   ├── tables_content.txt
│   ├── Voice_Vision_Assistant_Conference_Paper.docx
│   ├── VVA_Paper_Combined.tex
│   └── VVA_Paper_Combined_filled.tex
├── qr_cache
│   ├── 8114327bd1602239362b873814cfd613.json
│   ├── 94ca4bc858eddfa644322ea4c276fd63.json
│   ├── 9a7cd5efda286fbcdd26f89e64a360c5.json
│   └── _index.json
├── reports
│   ├── dast
│   │   └── .gitkeep
│   └── replace-embedding-qwen3-4b-test-report.md
├── research
│   ├── benchmarks
│   │   ├── benchmark_realtime.py
│   │   └── benchmark_results.json
│   ├── experiments
│   │   ├── scenarios
│   │   │   └── README.md
│   │   ├── __init__.py
│   │   ├── harness.py
│   │   └── scenario_generator.py
│   ├── reports
│   │   ├── REMEDIATION_PLAN.json
│   │   └── REMEDIATION_REPORT.json
│   └── AGENTS.md
├── scripts
│   ├── AGENTS.md
│   ├── async_audit.py
│   ├── canary_analysis.py
│   ├── canary_deploy.py
│   ├── canary_promote.py
│   ├── capture_baseline.py
│   ├── check_deps.py
│   ├── check_deps.sh
│   ├── download_models.py
│   ├── generate_release_notes.py
│   ├── generate_sbom.py
│   ├── generate_scenarios.py
│   ├── install_ocr_deps.sh
│   ├── profile_hot_path.py
│   ├── profile_vram.py
│   ├── run_chaos.py
│   ├── run_dast.py
│   ├── run_dep_scan.py
│   ├── run_load_test.sh
│   ├── run_local_dev.sh
│   ├── run_sast.py
│   ├── run_smoke.py
│   ├── security_audit.py
│   ├── validate_env.py
│   └── verify_hybrid_memory.py
├── shared
│   ├── config
│   │   ├── __init__.py
│   │   ├── AGENTS.md
│   │   ├── environment.py
│   │   ├── secret_provider.py
│   │   └── settings.py
│   ├── debug
│   │   ├── __init__.py
│   │   ├── AGENTS.md
│   │   ├── session_logger.py
│   │   └── visualizer.py
│   ├── logging
│   │   ├── __init__.py
│   │   ├── AGENTS.md
│   │   ├── correlation.py
│   │   ├── logging_config.py
│   │   └── rotation.py
│   ├── schemas
│   │   ├── __init__.py
│   │   └── AGENTS.md
│   ├── utils
│   │   ├── __init__.py
│   │   ├── AGENTS.md
│   │   ├── encryption.py
│   │   ├── helpers.py
│   │   ├── runtime_diagnostics.py
│   │   ├── startup_guards.py
│   │   ├── timing.py
│   │   └── vram_profiler.py
│   ├── __init__.py
│   ├── AGENTS.md
│   └── logging_config.py
├── tests
│   ├── chaos
│   │   ├── __init__.py
│   │   └── test_chaos.py
│   ├── fixtures
│   │   ├── braille
│   │   │   ├── sample_a.png
│   │   │   ├── sample_ab.png
│   │   │   ├── sample_dots_6.png
│   │   │   ├── sample_empty.png
│   │   │   ├── sample_hello.png
│   │   │   └── sample_noisy.png
│   │   ├── __init__.py
│   │   └── generate_braille_fixtures.py
│   ├── integration
│   │   ├── __init__.py
│   │   ├── AGENTS.md
│   │   ├── test_agent_coordinator.py
│   │   ├── test_canary.py
│   │   ├── test_deepgram.py
│   │   ├── test_failover_scenarios.py
│   │   ├── test_frame_spatial_integration.py
│   │   ├── test_memory_hybrid.py
│   │   ├── test_memory_search.py
│   │   ├── test_p0_security_smoke.py
│   │   ├── test_p1_pipeline.py
│   │   ├── test_p5_cd_pipeline_validation.py
│   │   ├── test_p5_monitoring_integration.py
│   │   ├── test_p5_runbook_execution.py
│   │   ├── test_p6_cloud_validation.py
│   │   ├── test_p6_integration.py
│   │   ├── test_qr_flow.py
│   │   ├── test_rag_reasoner.py
│   │   ├── test_rag_reasoner_claude.py
│   │   ├── test_siliconflow.py
│   │   ├── test_smoke.py
│   │   ├── test_spatial_pipeline.py
│   │   └── test_vqa_api.py
│   ├── load
│   │   ├── conftest.py
│   │   ├── locustfile.py
│   │   ├── README.md
│   │   ├── test_concurrent_users.py
│   │   └── test_load_infrastructure.py
│   ├── performance
│   │   ├── __init__.py
│   │   ├── AGENTS.md
│   │   ├── conftest.py
│   │   ├── test_access_control_fuzz.py
│   │   ├── test_agent_startup.py
│   │   ├── test_async_verification.py
│   │   ├── test_baseline_capture.py
│   │   ├── test_benchmark_report.py
│   │   ├── test_chaos.py
│   │   ├── test_consent_enforcement.py
│   │   ├── test_debug_access_control.py
│   │   ├── test_deterministic_replay.py
│   │   ├── test_docker_hardening.py
│   │   ├── test_e2e_latency.py
│   │   ├── test_embedding_optimization.py
│   │   ├── test_encryption_at_rest.py
│   │   ├── test_faiss_performance.py
│   │   ├── test_faiss_scaling.py
│   │   ├── test_frame_processing.py
│   │   ├── test_graceful_degradation.py
│   │   ├── test_hot_path_profiling.py
│   │   ├── test_instrumentation.py
│   │   ├── test_latency_sla.py
│   │   ├── test_llm_latency.py
│   │   ├── test_load_50_users.py
│   │   ├── test_memory_leak.py
│   │   ├── test_midas_latency.py
│   │   ├── test_model_checksums.py
│   │   ├── test_model_download_retry.py
│   │   ├── test_offline_behavior.py
│   │   ├── test_p0_baseline.py
│   │   ├── test_p1_architecture.py
│   │   ├── test_p1_validation.py
│   │   ├── test_p3_exit_criteria.py
│   │   ├── test_p4_exit_criteria.py
│   │   ├── test_pii_scrubbing.py
│   │   ├── test_quantization.py
│   │   ├── test_regression.py
│   │   ├── test_resilience_stress.py
│   │   ├── test_resource_monitoring.py
│   │   ├── test_resource_threshold.py
│   │   ├── test_secrets_scan.py
│   │   ├── test_sla_compliance.py
│   │   ├── test_speech_latency.py
│   │   ├── test_sustained_fps.py
│   │   ├── test_telemetry_optin.py
│   │   ├── test_vram_profiling.py
│   │   └── test_yolo_latency.py
│   ├── realtime
│   │   ├── __init__.py
│   │   ├── AGENTS.md
│   │   ├── benchmark.py
│   │   ├── calibrate_depth.py
│   │   ├── EVALUATION_FORMS.md
│   │   ├── metrics.py
│   │   ├── realtime_test.py
│   │   ├── replay_tool.py
│   │   ├── SAFETY_PROTOCOLS.md
│   │   ├── session_logger.py
│   │   └── TEST_PLAN.md
│   ├── smoke
│   │   ├── __init__.py
│   │   └── test_smoke.py
│   ├── unit
│   │   ├── __init__.py
│   │   ├── AGENTS.md
│   │   ├── test_action_context.py
│   │   ├── test_action_recognition_edge_cases.py
│   │   ├── test_async_audit.py
│   │   ├── test_async_blocking_regression.py
│   │   ├── test_audio_events_edge_cases.py
│   │   ├── test_backup_scheduler.py
│   │   ├── test_braille_classifier.py
│   │   ├── test_braille_segmenter.py
│   │   ├── test_cache_manager.py
│   │   ├── test_circuit_breaker.py
│   │   ├── test_clip_recognizer.py
│   │   ├── test_cloud_sync.py
│   │   ├── test_cloud_sync_architecture.py
│   │   ├── test_cloud_sync_edge_cases.py
│   │   ├── test_config_docs.py
│   │   ├── test_conflict_resolver.py
│   │   ├── test_debug_endpoints.py
│   │   ├── test_deepgram_circuit_breaker.py
│   │   ├── test_degradation_coordinator.py
│   │   ├── test_docs_accuracy.py
│   │   ├── test_duckduckgo_circuit_breaker.py
│   │   ├── test_edge_tts_fallback.py
│   │   ├── test_elevenlabs_circuit_breaker.py
│   │   ├── test_embedding_async.py
│   │   ├── test_embeddings.py
│   │   ├── test_embeddings_async.py
│   │   ├── test_enhanced_audio.py
│   │   ├── test_error_classifier.py
│   │   ├── test_event_bus.py
│   │   ├── test_face_consent.py
│   │   ├── test_face_engine_edge_cases.py
│   │   ├── test_face_tracker.py
│   │   ├── test_faiss_backup.py
│   │   ├── test_faiss_sync.py
│   │   ├── test_fusion.py
│   │   ├── test_health_registry.py
│   │   ├── test_import_boundaries.py
│   │   ├── test_indexer_persistence.py
│   │   ├── test_ingest_hardening.py
│   │   ├── test_livekit_circuit_breaker.py
│   │   ├── test_llm_client_async.py
│   │   ├── test_logging_correlation.py
│   │   ├── test_memory_ingest.py
│   │   ├── test_metrics_collector.py
│   │   ├── test_metrics_instrumentation.py
│   │   ├── test_midas_depth.py
│   │   ├── test_nav_formatter.py
│   │   ├── test_ocr_engine_fallbacks.py
│   │   ├── test_ocr_install_error.py
│   │   ├── test_offline_queue.py
│   │   ├── test_ollama_circuit_breaker.py
│   │   ├── test_perception.py
│   │   ├── test_pii_scrubber.py
│   │   ├── test_pipeline_edge_cases.py
│   │   ├── test_privacy_controls.py
│   │   ├── test_prometheus_metrics.py
│   │   ├── test_qr_decoder.py
│   │   ├── test_qr_scanner.py
│   │   ├── test_rag_reasoner_claude.py
│   │   ├── test_reasoning_edge_cases.py
│   │   ├── test_reasoning_engine.py
│   │   ├── test_reasoning_suite.py
│   │   ├── test_resilience_config.py
│   │   ├── test_retriever_mvp.py
│   │   ├── test_retry_policy.py
│   │   ├── test_retry_service_wiring.py
│   │   ├── test_scene_graph.py
│   │   ├── test_secret_provider.py
│   │   ├── test_security_tools.py
│   │   ├── test_segmentation.py
│   │   ├── test_session_management.py
│   │   ├── test_session_manager.py
│   │   ├── test_shared_reexports.py
│   │   ├── test_spatial_edge_cases.py
│   │   ├── test_sqlite_backup.py
│   │   ├── test_sqlite_sync.py
│   │   ├── test_storage_adapter.py
│   │   ├── test_stt_failover.py
│   │   ├── test_tavus_circuit_breaker.py
│   │   ├── test_tech_debt_checks.py
│   │   ├── test_timeout_config.py
│   │   ├── test_tool_router.py
│   │   ├── test_tts_failover.py
│   │   ├── test_tts_stt_edge_cases.py
│   │   ├── test_vision_controller.py
│   │   ├── test_voice_controller.py
│   │   ├── test_vqa_features.py
│   │   ├── test_vqa_reasoner.py
│   │   ├── test_whisper_stt.py
│   │   └── test_yolo_detector.py
│   ├── __init__.py
│   ├── AGENTS.md
│   ├── conftest.py
│   ├── conftest_vision.py
│   ├── generated_scenarios.json
│   ├── test_action_engine.py
│   ├── test_audio_engine.py
│   ├── test_ci_smoke.py
│   ├── test_confidence_cascade.py
│   ├── test_continuous_processing.py
│   ├── test_debug_visualizer.py
│   ├── test_encryption.py
│   ├── test_face_engine.py
│   ├── test_generated_scenarios.py
│   ├── test_live_pipeline.py
│   ├── test_memory_extensions.py
│   ├── test_model_load.py
│   ├── test_ocr_pipeline.py
│   ├── test_orchestrator.py
│   ├── test_perception_telemetry.py
│   ├── test_priority_scene.py
│   ├── test_runtime_diagnostics.py
│   ├── test_session_logger.py
│   ├── test_shared_types.py
│   ├── test_smoke_api.py
│   ├── test_spatial.py
│   ├── test_speech_vqa_bridge.py
│   ├── test_startup_guards.py
│   ├── test_tavus_adapter.py
│   └── test_tts_manager.py
├── ## Chat Customization Diagnostics.md
├── .bandit
├── .bandit-baseline.json
├── .dockerignore
├── .env
├── .env.example
├── .gitignore
├── AGENTS.md
├── bandit_out.json
├── bandit_out2.json
├── bandit_out3.json
├── C
├── CHANGELOG.md
├── CLAUDE.md
├── CODEBASE_ARCHITECTURE.md
├── CODEBASE_DATAFLOW.md
├── CODEBASE_MODULES.md
├── DIRECTORY_TREE.md
├── docker-compose.test.yml
├── Dockerfile
├── GEMINI.md
├── generate_tree.py
├── identities.json
├── import_linter_out.txt
├── knowledge_bundle.json
├── knowledge_embeddings.jsonl
├── Memory.md
├── MIGRATION_MAP.md
├── nul
├── pyproject.toml
├── pytest_collect_out.txt
├── pytest_out.txt
├── README.md
├── report.json
├── requirements-extras.txt
├── requirements.txt
└── temp_docs_append.md
```
