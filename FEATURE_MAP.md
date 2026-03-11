# Feature Map

| Feature | Entry Point | Status | Key Folders |
|---------|-------------|--------|-------------|
| Service/Agent: PipelineComponents | application\pipelines\integration.py | Active | core\memory, application\pipelines... |
| Core Feature: create_pipeline_components | application\pipelines\integration.py | Active | core\memory, application\pipelines... |
| Core Feature: wrap_entrypoint_with_pipeline | application\pipelines\integration.py | Active | core\memory, application\pipelines... |
| Service/Agent: PipelineMonitor | application\pipelines\pipeline_monitor.py | Active | application\pipelines |
| API Route: health | apps\api\server.py | Active | core\braille, apps\api... |
| API Route: prometheus_metrics | apps\api\server.py | Active | core\braille, apps\api... |
| API Route: debug_metrics | apps\api\server.py | Active | core\braille, apps\api... |
| API Route: debug_perception_frame | apps\api\server.py | Active | core\braille, apps\api... |
| API Route: list_sessions | apps\api\server.py | Active | core\braille, apps\api... |
| API Route: get_session_logs | apps\api\server.py | Active | core\braille, apps\api... |
| API Route: create_session | apps\api\server.py | Active | core\braille, apps\api... |
| API Route: health_camera | apps\api\server.py | Active | core\braille, apps\api... |
| API Route: health_orchestrator | apps\api\server.py | Active | core\braille, apps\api... |
| API Route: health_workers | apps\api\server.py | Active | core\braille, apps\api... |
| API Route: health_services | apps\api\server.py | Active | core\braille, apps\api... |
| API Route: health_service_detail | apps\api\server.py | Active | core\braille, apps\api... |
| API Route: debug_stale_check | apps\api\server.py | Active | core\braille, apps\api... |
| API Route: debug_live_frames | apps\api\server.py | Active | core\braille, apps\api... |
| API Route: debug_frame_rate | apps\api\server.py | Active | core\braille, apps\api... |
| API Route: memory_delete_all | apps\api\server.py | Active | core\braille, apps\api... |
| API Route: braille_read | apps\api\server.py | Active | core\braille, apps\api... |
| API Route: debug_braille_frame | apps\api\server.py | Active | core\braille, apps\api... |
| API Route: debug_ocr_install | apps\api\server.py | Active | core\braille, apps\api... |
| API Route: debug_watchdog_status | apps\api\server.py | Active | core\braille, apps\api... |
| API Route: debug_dependency_status | apps\api\server.py | Active | core\braille, apps\api... |
| API Route: export_user_data | apps\api\server.py | Active | core\braille, apps\api... |
| API Route: erase_all_user_data | apps\api\server.py | Active | core\braille, apps\api... |
| API Route: face_health | apps\api\server.py | Active | core\braille, apps\api... |
| API Route: face_consent_grant | apps\api\server.py | Active | core\braille, apps\api... |
| API Route: face_consent_log | apps\api\server.py | Active | core\braille, apps\api... |
| API Route: face_detect_with_consent | apps\api\server.py | Active | core\braille, apps\api... |
| API Route: face_forget_all | apps\api\server.py | Active | core\braille, apps\api... |
| API Route: audio_health | apps\api\server.py | Active | core\braille, apps\api... |
| API Route: debug_ssl_frame | apps\api\server.py | Active | core\braille, apps\api... |
| API Route: action_health | apps\api\server.py | Active | core\braille, apps\api... |
| Service/Agent: AllyVisionAgent | apps\realtime\agent.py | Active | application\frame_processing, core\qr... |
| Core Feature: create_agent_session | apps\realtime\session_manager.py | Active | application\pipelines, application\frame_processing... |
| Core Feature: start_agent_session | apps\realtime\session_manager.py | Active | application\pipelines, application\frame_processing... |
| API Route: store_memory | core\memory\api_endpoints.py | Active | core\memory |
| API Route: search_memories | core\memory\api_endpoints.py | Active | core\memory |
| API Route: query_memories | core\memory\api_endpoints.py | Active | core\memory |
| API Route: get_memory | core\memory\api_endpoints.py | Active | core\memory |
| API Route: get_session_memories | core\memory\api_endpoints.py | Active | core\memory |
| API Route: get_recent_memories | core\memory\api_endpoints.py | Active | core\memory |
| API Route: set_consent | core\memory\api_endpoints.py | Active | core\memory |
| API Route: get_consent | core\memory\api_endpoints.py | Active | core\memory |
| API Route: delete_memory | core\memory\api_endpoints.py | Active | core\memory |
| API Route: delete_all_memories | core\memory\api_endpoints.py | Active | core\memory |
| API Route: delete_session_memories | core\memory\api_endpoints.py | Active | core\memory |
| API Route: run_maintenance | core\memory\api_endpoints.py | Active | core\memory |
| API Route: get_health | core\memory\api_endpoints.py | Active | core\memory |
| API Route: get_stats | core\memory\api_endpoints.py | Active | core\memory |
| API Route: debug_session | core\memory\api_endpoints.py | Active | core\memory |
| Service/Agent: OCRPipelineResult | core\ocr\__init__.py | Active | shared\schemas, core\ocr... |
| Service/Agent: OCRPipeline | core\ocr\__init__.py | Active | shared\schemas, core\ocr... |
| API Route: scan_qr | core\qr\qr_api.py | Active | core\qr |
| API Route: add_to_cache | core\qr\qr_api.py | Active | core\qr |
| API Route: get_history | core\qr\qr_api.py | Active | core\qr |
| API Route: debug_scan | core\qr\qr_api.py | Active | core\qr |
| Service/Agent: VoiceAskPipeline | core\speech\voice_ask_pipeline.py | Active | core\speech |
| API Route: process_perception_frame | core\vqa\api_endpoints.py | Active | core\vqa, core\speech... |
| API Route: ask_vqa_question | core\vqa\api_endpoints.py | Active | core\vqa, core\speech... |
| API Route: get_session_replay | core\vqa\api_endpoints.py | Active | core\vqa, core\speech... |
| API Route: delete_session | core\vqa\api_endpoints.py | Active | core\vqa, core\speech... |
| API Route: health_check | core\vqa\api_endpoints.py | Active | core\vqa, core\speech... |
| API Route: get_metrics | core\vqa\api_endpoints.py | Active | core\vqa, core\speech... |
| API Route: voice_ask | core\vqa\api_endpoints.py | Active | core\vqa, core\speech... |
| API Route: ask_priority_scene | core\vqa\api_endpoints.py | Active | core\vqa, core\speech... |
| API Route: debug_perception | core\vqa\api_endpoints.py | Active | core\vqa, core\speech... |
| Service/Agent: PerceptionPipeline | core\vqa\perception.py | Active | shared\schemas, core\vqa... |
| Core Feature: create_pipeline | core\vqa\perception.py | Active | shared\schemas, core\vqa... |
| Service/Agent: PipelineStageMetrics | infrastructure\monitoring\instrumentation.py | Active | infrastructure\monitoring |
| Service/Agent: ServiceName | infrastructure\monitoring\prometheus_metrics.py | Active | infrastructure\monitoring |
| Service/Agent: ServiceStatus | infrastructure\resilience\health_registry.py | Active | infrastructure\resilience |
| Service/Agent: ServiceHealth | infrastructure\resilience\health_registry.py | Active | infrastructure\resilience |
| Service/Agent: ServiceHealthRegistry | infrastructure\resilience\health_registry.py | Active | infrastructure\resilience |
| Service/Agent: ServiceMetrics | scripts\canary_analysis.py | Active | scripts |
| Service/Agent: PipelineProfiler | shared\utils\timing.py | Active | shared\utils |
| Service/Agent: TestPerceptionPipelineAPI | tests\test_ci_smoke.py | Active | application\frame_processing, tests... |
| Service/Agent: TestCreatePipeline | tests\test_ci_smoke.py | Active | application\frame_processing, tests... |
| Core Feature: test_mock_pipeline_detect | tests\test_ci_smoke.py | Active | application\frame_processing, tests... |
| Core Feature: test_non_mock_pipeline_has_detector | tests\test_ci_smoke.py | Active | application\frame_processing, tests... |
| Core Feature: test_pipeline_detect_callable | tests\test_ci_smoke.py | Active | application\frame_processing, tests... |
| Core Feature: test_producer_consumer_pipeline | tests\test_continuous_processing.py | Active | tests, shared\config... |
| Core Feature: test_ocr_pipeline_creates | tests\test_model_load.py | Active | core\qr, tests... |
| Service/Agent: TestOCRPipelineResult | tests\test_ocr_pipeline.py | Active | tests, core\ocr |
| Service/Agent: TestOCRPipeline | tests\test_ocr_pipeline.py | Active | tests, core\vqa... |
| Core Feature: test_preprocess_full_pipeline | tests\test_ocr_pipeline.py | Active | tests, core\ocr |
| Core Feature: test_global_pipeline_timeout | tests\test_orchestrator.py | Active | tests, shared\schemas... |
| Core Feature: test_preflight_no_pipeline | tests\test_runtime_diagnostics.py | Active | tests, shared\utils |
| Core Feature: test_preflight_with_mock_pipeline | tests\test_runtime_diagnostics.py | Active | tests, shared\utils |
| Service/Agent: TestPerceptionPipeline | tests\test_smoke_api.py | Active | tests\unit, application\pipelines... |
| Core Feature: test_ocr_pipeline_importable | tests\test_smoke_api.py | Active | tests, core\vqa... |
| Core Feature: test_full_pipeline | tests\test_spatial.py | Active | tests, core\vision... |
| Service/Agent: TestVoiceAskPipeline | tests\test_speech_vqa_bridge.py | Active | tests, core\speech |
| Core Feature: test_pipeline_initialization | tests\test_speech_vqa_bridge.py | Active | tests, core\speech |
| Service/Agent: MockServiceClient | tests\chaos\test_chaos.py | Active | tests\chaos, infrastructure\resilience... |
| Service/Agent: TestChaos04PipelineTimeout | tests\chaos\test_chaos.py | Active | tests\chaos, infrastructure\resilience... |
| Service/Agent: TestChaos08CascadingServiceFailure | tests\chaos\test_chaos.py | Active | tests\chaos, infrastructure\resilience... |
| Service/Agent: TestChaos15FlappingService | tests\chaos\test_chaos.py | Active | tests\chaos, infrastructure\resilience... |
| Core Feature: test_full_pipeline_timeout_300ms | tests\chaos\test_chaos.py | Active | tests\chaos, infrastructure\resilience... |
| Core Feature: mock_pipeline | tests\chaos\test_chaos.py | Active | tests\chaos, infrastructure\resilience... |
| Core Feature: _try_import_agent | tests\integration\test_agent_coordinator.py | Active | tests\integration, apps\realtime |
| Core Feature: test_agent_coordinator_importable | tests\integration\test_agent_coordinator.py | Active | tests\integration, apps\realtime |
| Core Feature: test_agent_inherits_from_agent_base | tests\integration\test_agent_coordinator.py | Active | tests\integration, apps\realtime |
| Core Feature: test_agent_has_all_function_tools | tests\integration\test_agent_coordinator.py | Active | tests\integration, apps\realtime |
| Core Feature: test_agent_file_under_500_loc | tests\integration\test_agent_coordinator.py | Active | tests\integration, apps\realtime |
| Service/Agent: TestServiceMetrics | tests\integration\test_canary.py | Active | tests\integration, scripts |
| Core Feature: test_pipeline_timeout_returns_partial | tests\integration\test_frame_spatial_integration.py | Active | tests\integration, application\frame_processing |
| Service/Agent: TestP1PipelineIntegration | tests\integration\test_p1_pipeline.py | Active | core\memory, tests\integration... |
| Core Feature: test_full_pipeline_types | tests\integration\test_p1_pipeline.py | Active | core\memory, tests\integration... |
| Core Feature: test_pipeline_latency_under_500ms | tests\integration\test_p1_pipeline.py | Active | core\memory, tests\integration... |
| Service/Agent: TestCDPipelineValidation | tests\integration\test_p5_cd_pipeline_validation.py | Active | tests\integration |
| Service/Agent: TestCDPipelineIntegration | tests\integration\test_p5_cd_pipeline_validation.py | Active | tests\integration |
| Service/Agent: TestCDPipelineReadinessReport | tests\integration\test_p5_cd_pipeline_validation.py | Active | tests\integration |
| Core Feature: test_generate_pipeline_readiness_report | tests\integration\test_p5_cd_pipeline_validation.py | Active | tests\integration |
| Service/Agent: TestActionPipelineIntegration | tests\integration\test_p6_integration.py | Active | tests\integration, core\audio... |
| Service/Agent: TestAudioPipelineIntegration | tests\integration\test_p6_integration.py | Active | tests\integration, core\audio... |
| Service/Agent: TestReasoningPipelineIntegration | tests\integration\test_p6_integration.py | Active | tests\integration, core\audio... |
| Service/Agent: TestVQAPipelineIntegration | tests\integration\test_p6_integration.py | Active | tests\integration, core\audio... |
| Core Feature: test_clip_to_context_pipeline | tests\integration\test_p6_integration.py | Active | tests\integration, core\audio... |
| Core Feature: test_action_pipeline_health | tests\integration\test_p6_integration.py | Active | tests\integration, core\audio... |
| Core Feature: test_detection_pipeline | tests\integration\test_p6_integration.py | Active | tests\integration, core\audio... |
| Core Feature: test_full_reasoning_pipeline | tests\integration\test_p6_integration.py | Active | tests\integration, core\audio... |
| Service/Agent: TestVisionPipelineSmoke | tests\integration\test_smoke.py | Active | core\braille, apps\api... |
| Service/Agent: TestMemoryPipelineSmoke | tests\integration\test_smoke.py | Active | core\braille, apps\api... |
| Service/Agent: TestTTSPipelineSmoke | tests\integration\test_smoke.py | Active | core\braille, apps\api... |
| Service/Agent: TestSTTPipelineSmoke | tests\integration\test_smoke.py | Active | core\braille, apps\api... |
| Service/Agent: TestOCRPipelineSmoke | tests\integration\test_smoke.py | Active | core\braille, apps\api... |
| Service/Agent: TestBraillePipelineSmoke | tests\integration\test_smoke.py | Active | core\braille, apps\api... |
| Core Feature: test_pipeline_cancellation_is_fast | tests\integration\test_smoke.py | Active | core\braille, apps\api... |
| Service/Agent: TestSpatialPipeline | tests\integration\test_spatial_pipeline.py | Active | shared\schemas, core\vision... |
| Service/Agent: TestAgentStartup | tests\performance\test_agent_startup.py | Active | tests\performance |
| Service/Agent: MockE2EPipeline | tests\performance\test_e2e_latency.py | Active | tests\performance |
| Service/Agent: TestMockE2EPipeline | tests\performance\test_e2e_latency.py | Active | tests\performance |
| Service/Agent: MockFramePipeline | tests\performance\test_frame_processing.py | Active | tests\performance |
| Service/Agent: TestMockFramePipeline | tests\performance\test_frame_processing.py | Active | tests\performance |
| Service/Agent: TestPipelineInstrumentation | tests\performance\test_frame_processing.py | Active | tests\performance |
| Core Feature: test_pipeline_parallel_execution | tests\performance\test_frame_processing.py | Active | tests\performance |
| Core Feature: test_pipeline_within_budget | tests\performance\test_frame_processing.py | Active | tests\performance |
| Core Feature: test_pipeline_average_metrics | tests\performance\test_frame_processing.py | Active | tests\performance |
| Core Feature: test_pipeline_component_calls | tests\performance\test_frame_processing.py | Active | tests\performance |
| Core Feature: test_pipeline_breakdown_accuracy | tests\performance\test_frame_processing.py | Active | tests\performance |
| Core Feature: test_optimized_pipeline_meets_budget | tests\performance\test_frame_processing.py | Active | tests\performance |
| Service/Agent: TestPipelineProfilerIntegration | tests\performance\test_hot_path_profiling.py | Active | shared\utils, tests\performance... |
| Core Feature: test_all_new_modules_have_agents_md | tests\performance\test_p1_architecture.py | Active | tests\performance |
| Service/Agent: TestFlappingServices | tests\performance\test_resilience_stress.py | Active | infrastructure\resilience, infrastructure\speech... |
| Core Feature: test_pipeline_timeout_enforced | tests\performance\test_resource_threshold.py | Active | shared\config, tests\performance |
| Core Feature: test_vision_pipeline_compliant | tests\performance\test_sla_compliance.py | Active | tests\performance |
| Core Feature: test_application_pipelines_is_hot | tests\unit\test_async_audit.py | Active | tests\unit, scripts |
| Service/Agent: TestAgentModulesDocumented | tests\unit\test_docs_accuracy.py | Active | tests\unit |
| Core Feature: test_agents_md_exists | tests\unit\test_docs_accuracy.py | Active | tests\unit |
| Core Feature: test_each_module_mentioned_in_agents_md | tests\unit\test_docs_accuracy.py | Active | tests\unit |
| Core Feature: test_no_phantom_modules_in_agents_md | tests\unit\test_docs_accuracy.py | Active | tests\unit |
| Core Feature: test_agents_md_not_outdated_god_file_reference | tests\unit\test_docs_accuracy.py | Active | tests\unit |
| Service/Agent: TestServiceStatus | tests\unit\test_health_registry.py | Active | infrastructure\resilience, tests\unit |
| Service/Agent: TestServiceHealth | tests\unit\test_health_registry.py | Active | infrastructure\resilience, tests\unit |
| Service/Agent: TestServiceHealthRegistryInitialization | tests\unit\test_health_registry.py | Active | infrastructure\resilience, tests\unit |
| Service/Agent: TestServiceHealthRegistryQueries | tests\unit\test_health_registry.py | Active | infrastructure\resilience, tests\unit |
| Service/Agent: TestServiceHealthRegistrySummary | tests\unit\test_health_registry.py | Active | infrastructure\resilience, tests\unit |
| Service/Agent: TestServiceHealthRegistryDegradation | tests\unit\test_health_registry.py | Active | infrastructure\resilience, tests\unit |
| Service/Agent: TestServiceHealthRegistryHealthScore | tests\unit\test_health_registry.py | Active | infrastructure\resilience, tests\unit |
| Service/Agent: TestServiceHealthRegistryServiceManagement | tests\unit\test_health_registry.py | Active | infrastructure\resilience, tests\unit |
| Service/Agent: TestServiceHealthRegistryHealth | tests\unit\test_health_registry.py | Active | infrastructure\resilience, tests\unit |
| Service/Agent: TestPipelineStageMetrics | tests\unit\test_metrics_instrumentation.py | Active | infrastructure\monitoring, tests\unit |
| Service/Agent: TestPipelineSpecificDecorators | tests\unit\test_metrics_instrumentation.py | Active | infrastructure\monitoring, tests\unit |
| Service/Agent: TestOCRPipelineFallback | tests\unit\test_ocr_engine_fallbacks.py | Active | shared\schemas, tests\unit... |
| Core Feature: test_pipeline_is_ready_attribute | tests\unit\test_ocr_engine_fallbacks.py | Active | shared\schemas, tests\unit... |
| Core Feature: test_pipeline_process_no_crash | tests\unit\test_ocr_engine_fallbacks.py | Active | shared\schemas, tests\unit... |
| Core Feature: test_ocr_pipeline_no_backend_returns_error | tests\unit\test_ocr_install_error.py | Active | shared\schemas, tests\unit... |
| Service/Agent: TestPerceptionPipelineExtended | tests\unit\test_perception.py | Active | shared\schemas, tests\unit... |
| Core Feature: test_pipeline_returns_result | tests\unit\test_perception.py | Active | shared\schemas, tests\unit... |
| Core Feature: test_pipeline_includes_timestamp | tests\unit\test_perception.py | Active | shared\schemas, tests\unit... |
| Core Feature: test_pipeline_image_size | tests\unit\test_perception.py | Active | shared\schemas, tests\unit... |
| Core Feature: test_pipeline_latency_under_threshold | tests\unit\test_perception.py | Active | shared\schemas, tests\unit... |
| Core Feature: test_pipeline_handles_numpy_input | tests\unit\test_perception.py | Active | shared\schemas, tests\unit... |
| Core Feature: test_create_pipeline_factory | tests\unit\test_perception.py | Active | shared\schemas, tests\unit... |
| Service/Agent: TestPipelineMonitorEdgeCases | tests\unit\test_pipeline_edge_cases.py | Active | tests\unit, application\pipelines |
| Service/Agent: TestPipelineIntegrationEntry | tests\unit\test_pipeline_edge_cases.py | Active | tests\unit, application\pipelines |
| Service/Agent: TestServiceName | tests\unit\test_prometheus_metrics.py | Active | infrastructure\monitoring, tests\unit |
| Service/Agent: TestSpeechPipelineMetrics | tests\unit\test_prometheus_metrics.py | Active | infrastructure\monitoring, tests\unit |
| Service/Agent: TestServiceConfigs | tests\unit\test_retry_policy.py | Active | infrastructure\resilience, tests\unit |
| Service/Agent: TestServiceRetryConfigs | tests\unit\test_retry_service_wiring.py | Active | infrastructure\speech\elevenlabs, infrastructure\resilience... |
| Service/Agent: TestCreateAgentSession | tests\unit\test_session_manager.py | Active | tests\unit, apps\realtime |
| Service/Agent: TestStartAgentSession | tests\unit\test_session_manager.py | Active | tests\unit, apps\realtime |
| Service/Agent: TestAgentLOCCompliance | tests\unit\test_tech_debt_checks.py | Active | tests\unit |
| Core Feature: test_agent_under_500_loc | tests\unit\test_tech_debt_checks.py | Active | tests\unit |
| Service/Agent: TestVoiceAskPipelineEdgeCases | tests\unit\test_tts_stt_edge_cases.py | Active | tests\unit, core\speech |
| Core Feature: test_pipeline_import | tests\unit\test_tts_stt_edge_cases.py | Active | tests\unit, core\speech |
| Core Feature: test_pipeline_with_mocked_dependencies | tests\unit\test_tts_stt_edge_cases.py | Active | tests\unit, core\speech |
| Core Feature: test_pipeline_stt_failure_is_handled | tests\unit\test_tts_stt_edge_cases.py | Active | tests\unit, core\speech |

---
## Service/Agent: PipelineComponents
**Description:** Extracted service from code.
**Entry Point:** application\pipelines\integration.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\embeddings.py | Component of feature |
| core\memory\retriever.py | Component of feature |
| application\frame_processing\confidence_cascade.py | Component of feature |
| application\pipelines\integration.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\memory | Source directory |
| application\pipelines | Source directory |
| application\frame_processing | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: application\pipelines\integration.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Core Feature: create_pipeline_components
**Description:** Extracted core from code.
**Entry Point:** application\pipelines\integration.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\embeddings.py | Component of feature |
| core\memory\retriever.py | Component of feature |
| application\frame_processing\confidence_cascade.py | Component of feature |
| application\pipelines\integration.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\memory | Source directory |
| application\pipelines | Source directory |
| application\frame_processing | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: application\pipelines\integration.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: wrap_entrypoint_with_pipeline
**Description:** Extracted core from code.
**Entry Point:** application\pipelines\integration.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\embeddings.py | Component of feature |
| core\memory\retriever.py | Component of feature |
| application\frame_processing\confidence_cascade.py | Component of feature |
| application\pipelines\integration.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\memory | Source directory |
| application\pipelines | Source directory |
| application\frame_processing | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: application\pipelines\integration.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Service/Agent: PipelineMonitor
**Description:** Extracted service from code.
**Entry Point:** application\pipelines\pipeline_monitor.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| application\pipelines\pipeline_monitor.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| application\pipelines | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: application\pipelines\pipeline_monitor.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## API Route: health
**Description:** Extracted route from code.
**Entry Point:** apps\api\server.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\audio\__init__.py | Component of feature |
| application\pipelines\perception_telemetry.py | Component of feature |
| core\memory\indexer.py | Component of feature |
| core\vqa\api_endpoints.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\face\face_embeddings.py | Component of feature |
| shared\logging\logging_config.py | Component of feature |
| core\face\__init__.py | Component of feature |
| apps\cli\session_logger.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| application\pipelines\worker_pool.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\vqa\orchestrator.py | Component of feature |
| core\action\__init__.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| core\braille\__init__.py | Component of feature |
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| shared\utils\startup_guards.py | Component of feature |
| core\memory\config.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| infrastructure\resilience | Source directory |
| application\pipelines | Source directory |
| application\frame_processing | Source directory |
| core\qr | Source directory |
| infrastructure\monitoring | Source directory |
| core\memory | Source directory |
| shared\utils | Source directory |
| core\audio | Source directory |
| shared\logging | Source directory |
| shared\config | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |
| apps\cli | Source directory |
| core\face | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: process_perception_frame
- **Depends On / Used By:** API Route: ask_vqa_question
- **Depends On / Used By:** API Route: get_session_replay
- **Depends On / Used By:** API Route: delete_session
- **Depends On / Used By:** API Route: health_check
- **Depends On / Used By:** API Route: get_metrics
- **Depends On / Used By:** API Route: voice_ask
- **Depends On / Used By:** API Route: ask_priority_scene
- **Depends On / Used By:** API Route: debug_perception
- **Depends On / Used By:** API Route: store_memory
- **Depends On / Used By:** API Route: search_memories
- **Depends On / Used By:** API Route: query_memories
- **Depends On / Used By:** API Route: get_memory
- **Depends On / Used By:** API Route: get_session_memories
- **Depends On / Used By:** API Route: get_recent_memories
- **Depends On / Used By:** API Route: set_consent
- **Depends On / Used By:** API Route: get_consent
- **Depends On / Used By:** API Route: delete_memory
- **Depends On / Used By:** API Route: delete_all_memories
- **Depends On / Used By:** API Route: delete_session_memories
- **Depends On / Used By:** API Route: run_maintenance
- **Depends On / Used By:** API Route: get_health
- **Depends On / Used By:** API Route: get_stats
- **Depends On / Used By:** API Route: debug_session
- **Depends On / Used By:** Service/Agent: ServiceName
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: apps\api\server.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: prometheus_metrics
**Description:** Extracted route from code.
**Entry Point:** apps\api\server.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\audio\__init__.py | Component of feature |
| application\pipelines\perception_telemetry.py | Component of feature |
| core\memory\indexer.py | Component of feature |
| core\vqa\api_endpoints.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\face\face_embeddings.py | Component of feature |
| shared\logging\logging_config.py | Component of feature |
| core\face\__init__.py | Component of feature |
| apps\cli\session_logger.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| application\pipelines\worker_pool.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\vqa\orchestrator.py | Component of feature |
| core\action\__init__.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| core\braille\__init__.py | Component of feature |
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| shared\utils\startup_guards.py | Component of feature |
| core\memory\config.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| infrastructure\resilience | Source directory |
| application\pipelines | Source directory |
| application\frame_processing | Source directory |
| core\qr | Source directory |
| infrastructure\monitoring | Source directory |
| core\memory | Source directory |
| shared\utils | Source directory |
| core\audio | Source directory |
| shared\logging | Source directory |
| shared\config | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |
| apps\cli | Source directory |
| core\face | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: process_perception_frame
- **Depends On / Used By:** API Route: ask_vqa_question
- **Depends On / Used By:** API Route: get_session_replay
- **Depends On / Used By:** API Route: delete_session
- **Depends On / Used By:** API Route: health_check
- **Depends On / Used By:** API Route: get_metrics
- **Depends On / Used By:** API Route: voice_ask
- **Depends On / Used By:** API Route: ask_priority_scene
- **Depends On / Used By:** API Route: debug_perception
- **Depends On / Used By:** API Route: store_memory
- **Depends On / Used By:** API Route: search_memories
- **Depends On / Used By:** API Route: query_memories
- **Depends On / Used By:** API Route: get_memory
- **Depends On / Used By:** API Route: get_session_memories
- **Depends On / Used By:** API Route: get_recent_memories
- **Depends On / Used By:** API Route: set_consent
- **Depends On / Used By:** API Route: get_consent
- **Depends On / Used By:** API Route: delete_memory
- **Depends On / Used By:** API Route: delete_all_memories
- **Depends On / Used By:** API Route: delete_session_memories
- **Depends On / Used By:** API Route: run_maintenance
- **Depends On / Used By:** API Route: get_health
- **Depends On / Used By:** API Route: get_stats
- **Depends On / Used By:** API Route: debug_session
- **Depends On / Used By:** Service/Agent: ServiceName
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: apps\api\server.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: debug_metrics
**Description:** Extracted route from code.
**Entry Point:** apps\api\server.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\audio\__init__.py | Component of feature |
| application\pipelines\perception_telemetry.py | Component of feature |
| core\memory\indexer.py | Component of feature |
| core\vqa\api_endpoints.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\face\face_embeddings.py | Component of feature |
| shared\logging\logging_config.py | Component of feature |
| core\face\__init__.py | Component of feature |
| apps\cli\session_logger.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| application\pipelines\worker_pool.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\vqa\orchestrator.py | Component of feature |
| core\action\__init__.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| core\braille\__init__.py | Component of feature |
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| shared\utils\startup_guards.py | Component of feature |
| core\memory\config.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| infrastructure\resilience | Source directory |
| application\pipelines | Source directory |
| application\frame_processing | Source directory |
| core\qr | Source directory |
| infrastructure\monitoring | Source directory |
| core\memory | Source directory |
| shared\utils | Source directory |
| core\audio | Source directory |
| shared\logging | Source directory |
| shared\config | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |
| apps\cli | Source directory |
| core\face | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: process_perception_frame
- **Depends On / Used By:** API Route: ask_vqa_question
- **Depends On / Used By:** API Route: get_session_replay
- **Depends On / Used By:** API Route: delete_session
- **Depends On / Used By:** API Route: health_check
- **Depends On / Used By:** API Route: get_metrics
- **Depends On / Used By:** API Route: voice_ask
- **Depends On / Used By:** API Route: ask_priority_scene
- **Depends On / Used By:** API Route: debug_perception
- **Depends On / Used By:** API Route: store_memory
- **Depends On / Used By:** API Route: search_memories
- **Depends On / Used By:** API Route: query_memories
- **Depends On / Used By:** API Route: get_memory
- **Depends On / Used By:** API Route: get_session_memories
- **Depends On / Used By:** API Route: get_recent_memories
- **Depends On / Used By:** API Route: set_consent
- **Depends On / Used By:** API Route: get_consent
- **Depends On / Used By:** API Route: delete_memory
- **Depends On / Used By:** API Route: delete_all_memories
- **Depends On / Used By:** API Route: delete_session_memories
- **Depends On / Used By:** API Route: run_maintenance
- **Depends On / Used By:** API Route: get_health
- **Depends On / Used By:** API Route: get_stats
- **Depends On / Used By:** API Route: debug_session
- **Depends On / Used By:** Service/Agent: ServiceName
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: apps\api\server.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: debug_perception_frame
**Description:** Extracted route from code.
**Entry Point:** apps\api\server.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\audio\__init__.py | Component of feature |
| application\pipelines\perception_telemetry.py | Component of feature |
| core\memory\indexer.py | Component of feature |
| core\vqa\api_endpoints.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\face\face_embeddings.py | Component of feature |
| shared\logging\logging_config.py | Component of feature |
| core\face\__init__.py | Component of feature |
| apps\cli\session_logger.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| application\pipelines\worker_pool.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\vqa\orchestrator.py | Component of feature |
| core\action\__init__.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| core\braille\__init__.py | Component of feature |
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| shared\utils\startup_guards.py | Component of feature |
| core\memory\config.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| infrastructure\resilience | Source directory |
| application\pipelines | Source directory |
| application\frame_processing | Source directory |
| core\qr | Source directory |
| infrastructure\monitoring | Source directory |
| core\memory | Source directory |
| shared\utils | Source directory |
| core\audio | Source directory |
| shared\logging | Source directory |
| shared\config | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |
| apps\cli | Source directory |
| core\face | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: process_perception_frame
- **Depends On / Used By:** API Route: ask_vqa_question
- **Depends On / Used By:** API Route: get_session_replay
- **Depends On / Used By:** API Route: delete_session
- **Depends On / Used By:** API Route: health_check
- **Depends On / Used By:** API Route: get_metrics
- **Depends On / Used By:** API Route: voice_ask
- **Depends On / Used By:** API Route: ask_priority_scene
- **Depends On / Used By:** API Route: debug_perception
- **Depends On / Used By:** API Route: store_memory
- **Depends On / Used By:** API Route: search_memories
- **Depends On / Used By:** API Route: query_memories
- **Depends On / Used By:** API Route: get_memory
- **Depends On / Used By:** API Route: get_session_memories
- **Depends On / Used By:** API Route: get_recent_memories
- **Depends On / Used By:** API Route: set_consent
- **Depends On / Used By:** API Route: get_consent
- **Depends On / Used By:** API Route: delete_memory
- **Depends On / Used By:** API Route: delete_all_memories
- **Depends On / Used By:** API Route: delete_session_memories
- **Depends On / Used By:** API Route: run_maintenance
- **Depends On / Used By:** API Route: get_health
- **Depends On / Used By:** API Route: get_stats
- **Depends On / Used By:** API Route: debug_session
- **Depends On / Used By:** Service/Agent: ServiceName
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: apps\api\server.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: list_sessions
**Description:** Extracted route from code.
**Entry Point:** apps\api\server.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\audio\__init__.py | Component of feature |
| application\pipelines\perception_telemetry.py | Component of feature |
| core\memory\indexer.py | Component of feature |
| core\vqa\api_endpoints.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\face\face_embeddings.py | Component of feature |
| shared\logging\logging_config.py | Component of feature |
| core\face\__init__.py | Component of feature |
| apps\cli\session_logger.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| application\pipelines\worker_pool.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\vqa\orchestrator.py | Component of feature |
| core\action\__init__.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| core\braille\__init__.py | Component of feature |
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| shared\utils\startup_guards.py | Component of feature |
| core\memory\config.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| infrastructure\resilience | Source directory |
| application\pipelines | Source directory |
| application\frame_processing | Source directory |
| core\qr | Source directory |
| infrastructure\monitoring | Source directory |
| core\memory | Source directory |
| shared\utils | Source directory |
| core\audio | Source directory |
| shared\logging | Source directory |
| shared\config | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |
| apps\cli | Source directory |
| core\face | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: process_perception_frame
- **Depends On / Used By:** API Route: ask_vqa_question
- **Depends On / Used By:** API Route: get_session_replay
- **Depends On / Used By:** API Route: delete_session
- **Depends On / Used By:** API Route: health_check
- **Depends On / Used By:** API Route: get_metrics
- **Depends On / Used By:** API Route: voice_ask
- **Depends On / Used By:** API Route: ask_priority_scene
- **Depends On / Used By:** API Route: debug_perception
- **Depends On / Used By:** API Route: store_memory
- **Depends On / Used By:** API Route: search_memories
- **Depends On / Used By:** API Route: query_memories
- **Depends On / Used By:** API Route: get_memory
- **Depends On / Used By:** API Route: get_session_memories
- **Depends On / Used By:** API Route: get_recent_memories
- **Depends On / Used By:** API Route: set_consent
- **Depends On / Used By:** API Route: get_consent
- **Depends On / Used By:** API Route: delete_memory
- **Depends On / Used By:** API Route: delete_all_memories
- **Depends On / Used By:** API Route: delete_session_memories
- **Depends On / Used By:** API Route: run_maintenance
- **Depends On / Used By:** API Route: get_health
- **Depends On / Used By:** API Route: get_stats
- **Depends On / Used By:** API Route: debug_session
- **Depends On / Used By:** Service/Agent: ServiceName
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: apps\api\server.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: get_session_logs
**Description:** Extracted route from code.
**Entry Point:** apps\api\server.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\audio\__init__.py | Component of feature |
| application\pipelines\perception_telemetry.py | Component of feature |
| core\memory\indexer.py | Component of feature |
| core\vqa\api_endpoints.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\face\face_embeddings.py | Component of feature |
| shared\logging\logging_config.py | Component of feature |
| core\face\__init__.py | Component of feature |
| apps\cli\session_logger.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| application\pipelines\worker_pool.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\vqa\orchestrator.py | Component of feature |
| core\action\__init__.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| core\braille\__init__.py | Component of feature |
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| shared\utils\startup_guards.py | Component of feature |
| core\memory\config.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| infrastructure\resilience | Source directory |
| application\pipelines | Source directory |
| application\frame_processing | Source directory |
| core\qr | Source directory |
| infrastructure\monitoring | Source directory |
| core\memory | Source directory |
| shared\utils | Source directory |
| core\audio | Source directory |
| shared\logging | Source directory |
| shared\config | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |
| apps\cli | Source directory |
| core\face | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: process_perception_frame
- **Depends On / Used By:** API Route: ask_vqa_question
- **Depends On / Used By:** API Route: get_session_replay
- **Depends On / Used By:** API Route: delete_session
- **Depends On / Used By:** API Route: health_check
- **Depends On / Used By:** API Route: get_metrics
- **Depends On / Used By:** API Route: voice_ask
- **Depends On / Used By:** API Route: ask_priority_scene
- **Depends On / Used By:** API Route: debug_perception
- **Depends On / Used By:** API Route: store_memory
- **Depends On / Used By:** API Route: search_memories
- **Depends On / Used By:** API Route: query_memories
- **Depends On / Used By:** API Route: get_memory
- **Depends On / Used By:** API Route: get_session_memories
- **Depends On / Used By:** API Route: get_recent_memories
- **Depends On / Used By:** API Route: set_consent
- **Depends On / Used By:** API Route: get_consent
- **Depends On / Used By:** API Route: delete_memory
- **Depends On / Used By:** API Route: delete_all_memories
- **Depends On / Used By:** API Route: delete_session_memories
- **Depends On / Used By:** API Route: run_maintenance
- **Depends On / Used By:** API Route: get_health
- **Depends On / Used By:** API Route: get_stats
- **Depends On / Used By:** API Route: debug_session
- **Depends On / Used By:** Service/Agent: ServiceName
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: apps\api\server.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: create_session
**Description:** Extracted route from code.
**Entry Point:** apps\api\server.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\audio\__init__.py | Component of feature |
| application\pipelines\perception_telemetry.py | Component of feature |
| core\memory\indexer.py | Component of feature |
| core\vqa\api_endpoints.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\face\face_embeddings.py | Component of feature |
| shared\logging\logging_config.py | Component of feature |
| core\face\__init__.py | Component of feature |
| apps\cli\session_logger.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| application\pipelines\worker_pool.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\vqa\orchestrator.py | Component of feature |
| core\action\__init__.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| core\braille\__init__.py | Component of feature |
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| shared\utils\startup_guards.py | Component of feature |
| core\memory\config.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| infrastructure\resilience | Source directory |
| application\pipelines | Source directory |
| application\frame_processing | Source directory |
| core\qr | Source directory |
| infrastructure\monitoring | Source directory |
| core\memory | Source directory |
| shared\utils | Source directory |
| core\audio | Source directory |
| shared\logging | Source directory |
| shared\config | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |
| apps\cli | Source directory |
| core\face | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: process_perception_frame
- **Depends On / Used By:** API Route: ask_vqa_question
- **Depends On / Used By:** API Route: get_session_replay
- **Depends On / Used By:** API Route: delete_session
- **Depends On / Used By:** API Route: health_check
- **Depends On / Used By:** API Route: get_metrics
- **Depends On / Used By:** API Route: voice_ask
- **Depends On / Used By:** API Route: ask_priority_scene
- **Depends On / Used By:** API Route: debug_perception
- **Depends On / Used By:** API Route: store_memory
- **Depends On / Used By:** API Route: search_memories
- **Depends On / Used By:** API Route: query_memories
- **Depends On / Used By:** API Route: get_memory
- **Depends On / Used By:** API Route: get_session_memories
- **Depends On / Used By:** API Route: get_recent_memories
- **Depends On / Used By:** API Route: set_consent
- **Depends On / Used By:** API Route: get_consent
- **Depends On / Used By:** API Route: delete_memory
- **Depends On / Used By:** API Route: delete_all_memories
- **Depends On / Used By:** API Route: delete_session_memories
- **Depends On / Used By:** API Route: run_maintenance
- **Depends On / Used By:** API Route: get_health
- **Depends On / Used By:** API Route: get_stats
- **Depends On / Used By:** API Route: debug_session
- **Depends On / Used By:** Service/Agent: ServiceName
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: apps\api\server.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: health_camera
**Description:** Extracted route from code.
**Entry Point:** apps\api\server.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\audio\__init__.py | Component of feature |
| application\pipelines\perception_telemetry.py | Component of feature |
| core\memory\indexer.py | Component of feature |
| core\vqa\api_endpoints.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\face\face_embeddings.py | Component of feature |
| shared\logging\logging_config.py | Component of feature |
| core\face\__init__.py | Component of feature |
| apps\cli\session_logger.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| application\pipelines\worker_pool.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\vqa\orchestrator.py | Component of feature |
| core\action\__init__.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| core\braille\__init__.py | Component of feature |
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| shared\utils\startup_guards.py | Component of feature |
| core\memory\config.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| infrastructure\resilience | Source directory |
| application\pipelines | Source directory |
| application\frame_processing | Source directory |
| core\qr | Source directory |
| infrastructure\monitoring | Source directory |
| core\memory | Source directory |
| shared\utils | Source directory |
| core\audio | Source directory |
| shared\logging | Source directory |
| shared\config | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |
| apps\cli | Source directory |
| core\face | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: process_perception_frame
- **Depends On / Used By:** API Route: ask_vqa_question
- **Depends On / Used By:** API Route: get_session_replay
- **Depends On / Used By:** API Route: delete_session
- **Depends On / Used By:** API Route: health_check
- **Depends On / Used By:** API Route: get_metrics
- **Depends On / Used By:** API Route: voice_ask
- **Depends On / Used By:** API Route: ask_priority_scene
- **Depends On / Used By:** API Route: debug_perception
- **Depends On / Used By:** API Route: store_memory
- **Depends On / Used By:** API Route: search_memories
- **Depends On / Used By:** API Route: query_memories
- **Depends On / Used By:** API Route: get_memory
- **Depends On / Used By:** API Route: get_session_memories
- **Depends On / Used By:** API Route: get_recent_memories
- **Depends On / Used By:** API Route: set_consent
- **Depends On / Used By:** API Route: get_consent
- **Depends On / Used By:** API Route: delete_memory
- **Depends On / Used By:** API Route: delete_all_memories
- **Depends On / Used By:** API Route: delete_session_memories
- **Depends On / Used By:** API Route: run_maintenance
- **Depends On / Used By:** API Route: get_health
- **Depends On / Used By:** API Route: get_stats
- **Depends On / Used By:** API Route: debug_session
- **Depends On / Used By:** Service/Agent: ServiceName
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: apps\api\server.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: health_orchestrator
**Description:** Extracted route from code.
**Entry Point:** apps\api\server.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\audio\__init__.py | Component of feature |
| application\pipelines\perception_telemetry.py | Component of feature |
| core\memory\indexer.py | Component of feature |
| core\vqa\api_endpoints.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\face\face_embeddings.py | Component of feature |
| shared\logging\logging_config.py | Component of feature |
| core\face\__init__.py | Component of feature |
| apps\cli\session_logger.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| application\pipelines\worker_pool.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\vqa\orchestrator.py | Component of feature |
| core\action\__init__.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| core\braille\__init__.py | Component of feature |
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| shared\utils\startup_guards.py | Component of feature |
| core\memory\config.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| infrastructure\resilience | Source directory |
| application\pipelines | Source directory |
| application\frame_processing | Source directory |
| core\qr | Source directory |
| infrastructure\monitoring | Source directory |
| core\memory | Source directory |
| shared\utils | Source directory |
| core\audio | Source directory |
| shared\logging | Source directory |
| shared\config | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |
| apps\cli | Source directory |
| core\face | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: process_perception_frame
- **Depends On / Used By:** API Route: ask_vqa_question
- **Depends On / Used By:** API Route: get_session_replay
- **Depends On / Used By:** API Route: delete_session
- **Depends On / Used By:** API Route: health_check
- **Depends On / Used By:** API Route: get_metrics
- **Depends On / Used By:** API Route: voice_ask
- **Depends On / Used By:** API Route: ask_priority_scene
- **Depends On / Used By:** API Route: debug_perception
- **Depends On / Used By:** API Route: store_memory
- **Depends On / Used By:** API Route: search_memories
- **Depends On / Used By:** API Route: query_memories
- **Depends On / Used By:** API Route: get_memory
- **Depends On / Used By:** API Route: get_session_memories
- **Depends On / Used By:** API Route: get_recent_memories
- **Depends On / Used By:** API Route: set_consent
- **Depends On / Used By:** API Route: get_consent
- **Depends On / Used By:** API Route: delete_memory
- **Depends On / Used By:** API Route: delete_all_memories
- **Depends On / Used By:** API Route: delete_session_memories
- **Depends On / Used By:** API Route: run_maintenance
- **Depends On / Used By:** API Route: get_health
- **Depends On / Used By:** API Route: get_stats
- **Depends On / Used By:** API Route: debug_session
- **Depends On / Used By:** Service/Agent: ServiceName
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: apps\api\server.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: health_workers
**Description:** Extracted route from code.
**Entry Point:** apps\api\server.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\audio\__init__.py | Component of feature |
| application\pipelines\perception_telemetry.py | Component of feature |
| core\memory\indexer.py | Component of feature |
| core\vqa\api_endpoints.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\face\face_embeddings.py | Component of feature |
| shared\logging\logging_config.py | Component of feature |
| core\face\__init__.py | Component of feature |
| apps\cli\session_logger.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| application\pipelines\worker_pool.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\vqa\orchestrator.py | Component of feature |
| core\action\__init__.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| core\braille\__init__.py | Component of feature |
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| shared\utils\startup_guards.py | Component of feature |
| core\memory\config.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| infrastructure\resilience | Source directory |
| application\pipelines | Source directory |
| application\frame_processing | Source directory |
| core\qr | Source directory |
| infrastructure\monitoring | Source directory |
| core\memory | Source directory |
| shared\utils | Source directory |
| core\audio | Source directory |
| shared\logging | Source directory |
| shared\config | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |
| apps\cli | Source directory |
| core\face | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: process_perception_frame
- **Depends On / Used By:** API Route: ask_vqa_question
- **Depends On / Used By:** API Route: get_session_replay
- **Depends On / Used By:** API Route: delete_session
- **Depends On / Used By:** API Route: health_check
- **Depends On / Used By:** API Route: get_metrics
- **Depends On / Used By:** API Route: voice_ask
- **Depends On / Used By:** API Route: ask_priority_scene
- **Depends On / Used By:** API Route: debug_perception
- **Depends On / Used By:** API Route: store_memory
- **Depends On / Used By:** API Route: search_memories
- **Depends On / Used By:** API Route: query_memories
- **Depends On / Used By:** API Route: get_memory
- **Depends On / Used By:** API Route: get_session_memories
- **Depends On / Used By:** API Route: get_recent_memories
- **Depends On / Used By:** API Route: set_consent
- **Depends On / Used By:** API Route: get_consent
- **Depends On / Used By:** API Route: delete_memory
- **Depends On / Used By:** API Route: delete_all_memories
- **Depends On / Used By:** API Route: delete_session_memories
- **Depends On / Used By:** API Route: run_maintenance
- **Depends On / Used By:** API Route: get_health
- **Depends On / Used By:** API Route: get_stats
- **Depends On / Used By:** API Route: debug_session
- **Depends On / Used By:** Service/Agent: ServiceName
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: apps\api\server.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: health_services
**Description:** Extracted route from code.
**Entry Point:** apps\api\server.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\audio\__init__.py | Component of feature |
| application\pipelines\perception_telemetry.py | Component of feature |
| core\memory\indexer.py | Component of feature |
| core\vqa\api_endpoints.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\face\face_embeddings.py | Component of feature |
| shared\logging\logging_config.py | Component of feature |
| core\face\__init__.py | Component of feature |
| apps\cli\session_logger.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| application\pipelines\worker_pool.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\vqa\orchestrator.py | Component of feature |
| core\action\__init__.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| core\braille\__init__.py | Component of feature |
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| shared\utils\startup_guards.py | Component of feature |
| core\memory\config.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| infrastructure\resilience | Source directory |
| application\pipelines | Source directory |
| application\frame_processing | Source directory |
| core\qr | Source directory |
| infrastructure\monitoring | Source directory |
| core\memory | Source directory |
| shared\utils | Source directory |
| core\audio | Source directory |
| shared\logging | Source directory |
| shared\config | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |
| apps\cli | Source directory |
| core\face | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: process_perception_frame
- **Depends On / Used By:** API Route: ask_vqa_question
- **Depends On / Used By:** API Route: get_session_replay
- **Depends On / Used By:** API Route: delete_session
- **Depends On / Used By:** API Route: health_check
- **Depends On / Used By:** API Route: get_metrics
- **Depends On / Used By:** API Route: voice_ask
- **Depends On / Used By:** API Route: ask_priority_scene
- **Depends On / Used By:** API Route: debug_perception
- **Depends On / Used By:** API Route: store_memory
- **Depends On / Used By:** API Route: search_memories
- **Depends On / Used By:** API Route: query_memories
- **Depends On / Used By:** API Route: get_memory
- **Depends On / Used By:** API Route: get_session_memories
- **Depends On / Used By:** API Route: get_recent_memories
- **Depends On / Used By:** API Route: set_consent
- **Depends On / Used By:** API Route: get_consent
- **Depends On / Used By:** API Route: delete_memory
- **Depends On / Used By:** API Route: delete_all_memories
- **Depends On / Used By:** API Route: delete_session_memories
- **Depends On / Used By:** API Route: run_maintenance
- **Depends On / Used By:** API Route: get_health
- **Depends On / Used By:** API Route: get_stats
- **Depends On / Used By:** API Route: debug_session
- **Depends On / Used By:** Service/Agent: ServiceName
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: apps\api\server.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: health_service_detail
**Description:** Extracted route from code.
**Entry Point:** apps\api\server.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\audio\__init__.py | Component of feature |
| application\pipelines\perception_telemetry.py | Component of feature |
| core\memory\indexer.py | Component of feature |
| core\vqa\api_endpoints.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\face\face_embeddings.py | Component of feature |
| shared\logging\logging_config.py | Component of feature |
| core\face\__init__.py | Component of feature |
| apps\cli\session_logger.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| application\pipelines\worker_pool.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\vqa\orchestrator.py | Component of feature |
| core\action\__init__.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| core\braille\__init__.py | Component of feature |
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| shared\utils\startup_guards.py | Component of feature |
| core\memory\config.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| infrastructure\resilience | Source directory |
| application\pipelines | Source directory |
| application\frame_processing | Source directory |
| core\qr | Source directory |
| infrastructure\monitoring | Source directory |
| core\memory | Source directory |
| shared\utils | Source directory |
| core\audio | Source directory |
| shared\logging | Source directory |
| shared\config | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |
| apps\cli | Source directory |
| core\face | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: process_perception_frame
- **Depends On / Used By:** API Route: ask_vqa_question
- **Depends On / Used By:** API Route: get_session_replay
- **Depends On / Used By:** API Route: delete_session
- **Depends On / Used By:** API Route: health_check
- **Depends On / Used By:** API Route: get_metrics
- **Depends On / Used By:** API Route: voice_ask
- **Depends On / Used By:** API Route: ask_priority_scene
- **Depends On / Used By:** API Route: debug_perception
- **Depends On / Used By:** API Route: store_memory
- **Depends On / Used By:** API Route: search_memories
- **Depends On / Used By:** API Route: query_memories
- **Depends On / Used By:** API Route: get_memory
- **Depends On / Used By:** API Route: get_session_memories
- **Depends On / Used By:** API Route: get_recent_memories
- **Depends On / Used By:** API Route: set_consent
- **Depends On / Used By:** API Route: get_consent
- **Depends On / Used By:** API Route: delete_memory
- **Depends On / Used By:** API Route: delete_all_memories
- **Depends On / Used By:** API Route: delete_session_memories
- **Depends On / Used By:** API Route: run_maintenance
- **Depends On / Used By:** API Route: get_health
- **Depends On / Used By:** API Route: get_stats
- **Depends On / Used By:** API Route: debug_session
- **Depends On / Used By:** Service/Agent: ServiceName
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: apps\api\server.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: debug_stale_check
**Description:** Extracted route from code.
**Entry Point:** apps\api\server.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\audio\__init__.py | Component of feature |
| application\pipelines\perception_telemetry.py | Component of feature |
| core\memory\indexer.py | Component of feature |
| core\vqa\api_endpoints.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\face\face_embeddings.py | Component of feature |
| shared\logging\logging_config.py | Component of feature |
| core\face\__init__.py | Component of feature |
| apps\cli\session_logger.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| application\pipelines\worker_pool.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\vqa\orchestrator.py | Component of feature |
| core\action\__init__.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| core\braille\__init__.py | Component of feature |
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| shared\utils\startup_guards.py | Component of feature |
| core\memory\config.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| infrastructure\resilience | Source directory |
| application\pipelines | Source directory |
| application\frame_processing | Source directory |
| core\qr | Source directory |
| infrastructure\monitoring | Source directory |
| core\memory | Source directory |
| shared\utils | Source directory |
| core\audio | Source directory |
| shared\logging | Source directory |
| shared\config | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |
| apps\cli | Source directory |
| core\face | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: process_perception_frame
- **Depends On / Used By:** API Route: ask_vqa_question
- **Depends On / Used By:** API Route: get_session_replay
- **Depends On / Used By:** API Route: delete_session
- **Depends On / Used By:** API Route: health_check
- **Depends On / Used By:** API Route: get_metrics
- **Depends On / Used By:** API Route: voice_ask
- **Depends On / Used By:** API Route: ask_priority_scene
- **Depends On / Used By:** API Route: debug_perception
- **Depends On / Used By:** API Route: store_memory
- **Depends On / Used By:** API Route: search_memories
- **Depends On / Used By:** API Route: query_memories
- **Depends On / Used By:** API Route: get_memory
- **Depends On / Used By:** API Route: get_session_memories
- **Depends On / Used By:** API Route: get_recent_memories
- **Depends On / Used By:** API Route: set_consent
- **Depends On / Used By:** API Route: get_consent
- **Depends On / Used By:** API Route: delete_memory
- **Depends On / Used By:** API Route: delete_all_memories
- **Depends On / Used By:** API Route: delete_session_memories
- **Depends On / Used By:** API Route: run_maintenance
- **Depends On / Used By:** API Route: get_health
- **Depends On / Used By:** API Route: get_stats
- **Depends On / Used By:** API Route: debug_session
- **Depends On / Used By:** Service/Agent: ServiceName
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: apps\api\server.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: debug_live_frames
**Description:** Extracted route from code.
**Entry Point:** apps\api\server.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\audio\__init__.py | Component of feature |
| application\pipelines\perception_telemetry.py | Component of feature |
| core\memory\indexer.py | Component of feature |
| core\vqa\api_endpoints.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\face\face_embeddings.py | Component of feature |
| shared\logging\logging_config.py | Component of feature |
| core\face\__init__.py | Component of feature |
| apps\cli\session_logger.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| application\pipelines\worker_pool.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\vqa\orchestrator.py | Component of feature |
| core\action\__init__.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| core\braille\__init__.py | Component of feature |
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| shared\utils\startup_guards.py | Component of feature |
| core\memory\config.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| infrastructure\resilience | Source directory |
| application\pipelines | Source directory |
| application\frame_processing | Source directory |
| core\qr | Source directory |
| infrastructure\monitoring | Source directory |
| core\memory | Source directory |
| shared\utils | Source directory |
| core\audio | Source directory |
| shared\logging | Source directory |
| shared\config | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |
| apps\cli | Source directory |
| core\face | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: process_perception_frame
- **Depends On / Used By:** API Route: ask_vqa_question
- **Depends On / Used By:** API Route: get_session_replay
- **Depends On / Used By:** API Route: delete_session
- **Depends On / Used By:** API Route: health_check
- **Depends On / Used By:** API Route: get_metrics
- **Depends On / Used By:** API Route: voice_ask
- **Depends On / Used By:** API Route: ask_priority_scene
- **Depends On / Used By:** API Route: debug_perception
- **Depends On / Used By:** API Route: store_memory
- **Depends On / Used By:** API Route: search_memories
- **Depends On / Used By:** API Route: query_memories
- **Depends On / Used By:** API Route: get_memory
- **Depends On / Used By:** API Route: get_session_memories
- **Depends On / Used By:** API Route: get_recent_memories
- **Depends On / Used By:** API Route: set_consent
- **Depends On / Used By:** API Route: get_consent
- **Depends On / Used By:** API Route: delete_memory
- **Depends On / Used By:** API Route: delete_all_memories
- **Depends On / Used By:** API Route: delete_session_memories
- **Depends On / Used By:** API Route: run_maintenance
- **Depends On / Used By:** API Route: get_health
- **Depends On / Used By:** API Route: get_stats
- **Depends On / Used By:** API Route: debug_session
- **Depends On / Used By:** Service/Agent: ServiceName
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: apps\api\server.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: debug_frame_rate
**Description:** Extracted route from code.
**Entry Point:** apps\api\server.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\audio\__init__.py | Component of feature |
| application\pipelines\perception_telemetry.py | Component of feature |
| core\memory\indexer.py | Component of feature |
| core\vqa\api_endpoints.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\face\face_embeddings.py | Component of feature |
| shared\logging\logging_config.py | Component of feature |
| core\face\__init__.py | Component of feature |
| apps\cli\session_logger.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| application\pipelines\worker_pool.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\vqa\orchestrator.py | Component of feature |
| core\action\__init__.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| core\braille\__init__.py | Component of feature |
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| shared\utils\startup_guards.py | Component of feature |
| core\memory\config.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| infrastructure\resilience | Source directory |
| application\pipelines | Source directory |
| application\frame_processing | Source directory |
| core\qr | Source directory |
| infrastructure\monitoring | Source directory |
| core\memory | Source directory |
| shared\utils | Source directory |
| core\audio | Source directory |
| shared\logging | Source directory |
| shared\config | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |
| apps\cli | Source directory |
| core\face | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: process_perception_frame
- **Depends On / Used By:** API Route: ask_vqa_question
- **Depends On / Used By:** API Route: get_session_replay
- **Depends On / Used By:** API Route: delete_session
- **Depends On / Used By:** API Route: health_check
- **Depends On / Used By:** API Route: get_metrics
- **Depends On / Used By:** API Route: voice_ask
- **Depends On / Used By:** API Route: ask_priority_scene
- **Depends On / Used By:** API Route: debug_perception
- **Depends On / Used By:** API Route: store_memory
- **Depends On / Used By:** API Route: search_memories
- **Depends On / Used By:** API Route: query_memories
- **Depends On / Used By:** API Route: get_memory
- **Depends On / Used By:** API Route: get_session_memories
- **Depends On / Used By:** API Route: get_recent_memories
- **Depends On / Used By:** API Route: set_consent
- **Depends On / Used By:** API Route: get_consent
- **Depends On / Used By:** API Route: delete_memory
- **Depends On / Used By:** API Route: delete_all_memories
- **Depends On / Used By:** API Route: delete_session_memories
- **Depends On / Used By:** API Route: run_maintenance
- **Depends On / Used By:** API Route: get_health
- **Depends On / Used By:** API Route: get_stats
- **Depends On / Used By:** API Route: debug_session
- **Depends On / Used By:** Service/Agent: ServiceName
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: apps\api\server.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: memory_delete_all
**Description:** Extracted route from code.
**Entry Point:** apps\api\server.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\audio\__init__.py | Component of feature |
| application\pipelines\perception_telemetry.py | Component of feature |
| core\memory\indexer.py | Component of feature |
| core\vqa\api_endpoints.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\face\face_embeddings.py | Component of feature |
| shared\logging\logging_config.py | Component of feature |
| core\face\__init__.py | Component of feature |
| apps\cli\session_logger.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| application\pipelines\worker_pool.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\vqa\orchestrator.py | Component of feature |
| core\action\__init__.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| core\braille\__init__.py | Component of feature |
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| shared\utils\startup_guards.py | Component of feature |
| core\memory\config.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| infrastructure\resilience | Source directory |
| application\pipelines | Source directory |
| application\frame_processing | Source directory |
| core\qr | Source directory |
| infrastructure\monitoring | Source directory |
| core\memory | Source directory |
| shared\utils | Source directory |
| core\audio | Source directory |
| shared\logging | Source directory |
| shared\config | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |
| apps\cli | Source directory |
| core\face | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: process_perception_frame
- **Depends On / Used By:** API Route: ask_vqa_question
- **Depends On / Used By:** API Route: get_session_replay
- **Depends On / Used By:** API Route: delete_session
- **Depends On / Used By:** API Route: health_check
- **Depends On / Used By:** API Route: get_metrics
- **Depends On / Used By:** API Route: voice_ask
- **Depends On / Used By:** API Route: ask_priority_scene
- **Depends On / Used By:** API Route: debug_perception
- **Depends On / Used By:** API Route: store_memory
- **Depends On / Used By:** API Route: search_memories
- **Depends On / Used By:** API Route: query_memories
- **Depends On / Used By:** API Route: get_memory
- **Depends On / Used By:** API Route: get_session_memories
- **Depends On / Used By:** API Route: get_recent_memories
- **Depends On / Used By:** API Route: set_consent
- **Depends On / Used By:** API Route: get_consent
- **Depends On / Used By:** API Route: delete_memory
- **Depends On / Used By:** API Route: delete_all_memories
- **Depends On / Used By:** API Route: delete_session_memories
- **Depends On / Used By:** API Route: run_maintenance
- **Depends On / Used By:** API Route: get_health
- **Depends On / Used By:** API Route: get_stats
- **Depends On / Used By:** API Route: debug_session
- **Depends On / Used By:** Service/Agent: ServiceName
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: apps\api\server.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: braille_read
**Description:** Extracted route from code.
**Entry Point:** apps\api\server.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\audio\__init__.py | Component of feature |
| application\pipelines\perception_telemetry.py | Component of feature |
| core\memory\indexer.py | Component of feature |
| core\vqa\api_endpoints.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\face\face_embeddings.py | Component of feature |
| shared\logging\logging_config.py | Component of feature |
| core\face\__init__.py | Component of feature |
| apps\cli\session_logger.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| application\pipelines\worker_pool.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\vqa\orchestrator.py | Component of feature |
| core\action\__init__.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| core\braille\__init__.py | Component of feature |
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| shared\utils\startup_guards.py | Component of feature |
| core\memory\config.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| infrastructure\resilience | Source directory |
| application\pipelines | Source directory |
| application\frame_processing | Source directory |
| core\qr | Source directory |
| infrastructure\monitoring | Source directory |
| core\memory | Source directory |
| shared\utils | Source directory |
| core\audio | Source directory |
| shared\logging | Source directory |
| shared\config | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |
| apps\cli | Source directory |
| core\face | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: process_perception_frame
- **Depends On / Used By:** API Route: ask_vqa_question
- **Depends On / Used By:** API Route: get_session_replay
- **Depends On / Used By:** API Route: delete_session
- **Depends On / Used By:** API Route: health_check
- **Depends On / Used By:** API Route: get_metrics
- **Depends On / Used By:** API Route: voice_ask
- **Depends On / Used By:** API Route: ask_priority_scene
- **Depends On / Used By:** API Route: debug_perception
- **Depends On / Used By:** API Route: store_memory
- **Depends On / Used By:** API Route: search_memories
- **Depends On / Used By:** API Route: query_memories
- **Depends On / Used By:** API Route: get_memory
- **Depends On / Used By:** API Route: get_session_memories
- **Depends On / Used By:** API Route: get_recent_memories
- **Depends On / Used By:** API Route: set_consent
- **Depends On / Used By:** API Route: get_consent
- **Depends On / Used By:** API Route: delete_memory
- **Depends On / Used By:** API Route: delete_all_memories
- **Depends On / Used By:** API Route: delete_session_memories
- **Depends On / Used By:** API Route: run_maintenance
- **Depends On / Used By:** API Route: get_health
- **Depends On / Used By:** API Route: get_stats
- **Depends On / Used By:** API Route: debug_session
- **Depends On / Used By:** Service/Agent: ServiceName
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: apps\api\server.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: debug_braille_frame
**Description:** Extracted route from code.
**Entry Point:** apps\api\server.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\audio\__init__.py | Component of feature |
| application\pipelines\perception_telemetry.py | Component of feature |
| core\memory\indexer.py | Component of feature |
| core\vqa\api_endpoints.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\face\face_embeddings.py | Component of feature |
| shared\logging\logging_config.py | Component of feature |
| core\face\__init__.py | Component of feature |
| apps\cli\session_logger.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| application\pipelines\worker_pool.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\vqa\orchestrator.py | Component of feature |
| core\action\__init__.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| core\braille\__init__.py | Component of feature |
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| shared\utils\startup_guards.py | Component of feature |
| core\memory\config.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| infrastructure\resilience | Source directory |
| application\pipelines | Source directory |
| application\frame_processing | Source directory |
| core\qr | Source directory |
| infrastructure\monitoring | Source directory |
| core\memory | Source directory |
| shared\utils | Source directory |
| core\audio | Source directory |
| shared\logging | Source directory |
| shared\config | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |
| apps\cli | Source directory |
| core\face | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: process_perception_frame
- **Depends On / Used By:** API Route: ask_vqa_question
- **Depends On / Used By:** API Route: get_session_replay
- **Depends On / Used By:** API Route: delete_session
- **Depends On / Used By:** API Route: health_check
- **Depends On / Used By:** API Route: get_metrics
- **Depends On / Used By:** API Route: voice_ask
- **Depends On / Used By:** API Route: ask_priority_scene
- **Depends On / Used By:** API Route: debug_perception
- **Depends On / Used By:** API Route: store_memory
- **Depends On / Used By:** API Route: search_memories
- **Depends On / Used By:** API Route: query_memories
- **Depends On / Used By:** API Route: get_memory
- **Depends On / Used By:** API Route: get_session_memories
- **Depends On / Used By:** API Route: get_recent_memories
- **Depends On / Used By:** API Route: set_consent
- **Depends On / Used By:** API Route: get_consent
- **Depends On / Used By:** API Route: delete_memory
- **Depends On / Used By:** API Route: delete_all_memories
- **Depends On / Used By:** API Route: delete_session_memories
- **Depends On / Used By:** API Route: run_maintenance
- **Depends On / Used By:** API Route: get_health
- **Depends On / Used By:** API Route: get_stats
- **Depends On / Used By:** API Route: debug_session
- **Depends On / Used By:** Service/Agent: ServiceName
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: apps\api\server.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: debug_ocr_install
**Description:** Extracted route from code.
**Entry Point:** apps\api\server.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\audio\__init__.py | Component of feature |
| application\pipelines\perception_telemetry.py | Component of feature |
| core\memory\indexer.py | Component of feature |
| core\vqa\api_endpoints.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\face\face_embeddings.py | Component of feature |
| shared\logging\logging_config.py | Component of feature |
| core\face\__init__.py | Component of feature |
| apps\cli\session_logger.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| application\pipelines\worker_pool.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\vqa\orchestrator.py | Component of feature |
| core\action\__init__.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| core\braille\__init__.py | Component of feature |
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| shared\utils\startup_guards.py | Component of feature |
| core\memory\config.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| infrastructure\resilience | Source directory |
| application\pipelines | Source directory |
| application\frame_processing | Source directory |
| core\qr | Source directory |
| infrastructure\monitoring | Source directory |
| core\memory | Source directory |
| shared\utils | Source directory |
| core\audio | Source directory |
| shared\logging | Source directory |
| shared\config | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |
| apps\cli | Source directory |
| core\face | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: process_perception_frame
- **Depends On / Used By:** API Route: ask_vqa_question
- **Depends On / Used By:** API Route: get_session_replay
- **Depends On / Used By:** API Route: delete_session
- **Depends On / Used By:** API Route: health_check
- **Depends On / Used By:** API Route: get_metrics
- **Depends On / Used By:** API Route: voice_ask
- **Depends On / Used By:** API Route: ask_priority_scene
- **Depends On / Used By:** API Route: debug_perception
- **Depends On / Used By:** API Route: store_memory
- **Depends On / Used By:** API Route: search_memories
- **Depends On / Used By:** API Route: query_memories
- **Depends On / Used By:** API Route: get_memory
- **Depends On / Used By:** API Route: get_session_memories
- **Depends On / Used By:** API Route: get_recent_memories
- **Depends On / Used By:** API Route: set_consent
- **Depends On / Used By:** API Route: get_consent
- **Depends On / Used By:** API Route: delete_memory
- **Depends On / Used By:** API Route: delete_all_memories
- **Depends On / Used By:** API Route: delete_session_memories
- **Depends On / Used By:** API Route: run_maintenance
- **Depends On / Used By:** API Route: get_health
- **Depends On / Used By:** API Route: get_stats
- **Depends On / Used By:** API Route: debug_session
- **Depends On / Used By:** Service/Agent: ServiceName
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: apps\api\server.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: debug_watchdog_status
**Description:** Extracted route from code.
**Entry Point:** apps\api\server.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\audio\__init__.py | Component of feature |
| application\pipelines\perception_telemetry.py | Component of feature |
| core\memory\indexer.py | Component of feature |
| core\vqa\api_endpoints.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\face\face_embeddings.py | Component of feature |
| shared\logging\logging_config.py | Component of feature |
| core\face\__init__.py | Component of feature |
| apps\cli\session_logger.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| application\pipelines\worker_pool.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\vqa\orchestrator.py | Component of feature |
| core\action\__init__.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| core\braille\__init__.py | Component of feature |
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| shared\utils\startup_guards.py | Component of feature |
| core\memory\config.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| infrastructure\resilience | Source directory |
| application\pipelines | Source directory |
| application\frame_processing | Source directory |
| core\qr | Source directory |
| infrastructure\monitoring | Source directory |
| core\memory | Source directory |
| shared\utils | Source directory |
| core\audio | Source directory |
| shared\logging | Source directory |
| shared\config | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |
| apps\cli | Source directory |
| core\face | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: process_perception_frame
- **Depends On / Used By:** API Route: ask_vqa_question
- **Depends On / Used By:** API Route: get_session_replay
- **Depends On / Used By:** API Route: delete_session
- **Depends On / Used By:** API Route: health_check
- **Depends On / Used By:** API Route: get_metrics
- **Depends On / Used By:** API Route: voice_ask
- **Depends On / Used By:** API Route: ask_priority_scene
- **Depends On / Used By:** API Route: debug_perception
- **Depends On / Used By:** API Route: store_memory
- **Depends On / Used By:** API Route: search_memories
- **Depends On / Used By:** API Route: query_memories
- **Depends On / Used By:** API Route: get_memory
- **Depends On / Used By:** API Route: get_session_memories
- **Depends On / Used By:** API Route: get_recent_memories
- **Depends On / Used By:** API Route: set_consent
- **Depends On / Used By:** API Route: get_consent
- **Depends On / Used By:** API Route: delete_memory
- **Depends On / Used By:** API Route: delete_all_memories
- **Depends On / Used By:** API Route: delete_session_memories
- **Depends On / Used By:** API Route: run_maintenance
- **Depends On / Used By:** API Route: get_health
- **Depends On / Used By:** API Route: get_stats
- **Depends On / Used By:** API Route: debug_session
- **Depends On / Used By:** Service/Agent: ServiceName
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: apps\api\server.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: debug_dependency_status
**Description:** Extracted route from code.
**Entry Point:** apps\api\server.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\audio\__init__.py | Component of feature |
| application\pipelines\perception_telemetry.py | Component of feature |
| core\memory\indexer.py | Component of feature |
| core\vqa\api_endpoints.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\face\face_embeddings.py | Component of feature |
| shared\logging\logging_config.py | Component of feature |
| core\face\__init__.py | Component of feature |
| apps\cli\session_logger.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| application\pipelines\worker_pool.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\vqa\orchestrator.py | Component of feature |
| core\action\__init__.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| core\braille\__init__.py | Component of feature |
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| shared\utils\startup_guards.py | Component of feature |
| core\memory\config.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| infrastructure\resilience | Source directory |
| application\pipelines | Source directory |
| application\frame_processing | Source directory |
| core\qr | Source directory |
| infrastructure\monitoring | Source directory |
| core\memory | Source directory |
| shared\utils | Source directory |
| core\audio | Source directory |
| shared\logging | Source directory |
| shared\config | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |
| apps\cli | Source directory |
| core\face | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: process_perception_frame
- **Depends On / Used By:** API Route: ask_vqa_question
- **Depends On / Used By:** API Route: get_session_replay
- **Depends On / Used By:** API Route: delete_session
- **Depends On / Used By:** API Route: health_check
- **Depends On / Used By:** API Route: get_metrics
- **Depends On / Used By:** API Route: voice_ask
- **Depends On / Used By:** API Route: ask_priority_scene
- **Depends On / Used By:** API Route: debug_perception
- **Depends On / Used By:** API Route: store_memory
- **Depends On / Used By:** API Route: search_memories
- **Depends On / Used By:** API Route: query_memories
- **Depends On / Used By:** API Route: get_memory
- **Depends On / Used By:** API Route: get_session_memories
- **Depends On / Used By:** API Route: get_recent_memories
- **Depends On / Used By:** API Route: set_consent
- **Depends On / Used By:** API Route: get_consent
- **Depends On / Used By:** API Route: delete_memory
- **Depends On / Used By:** API Route: delete_all_memories
- **Depends On / Used By:** API Route: delete_session_memories
- **Depends On / Used By:** API Route: run_maintenance
- **Depends On / Used By:** API Route: get_health
- **Depends On / Used By:** API Route: get_stats
- **Depends On / Used By:** API Route: debug_session
- **Depends On / Used By:** Service/Agent: ServiceName
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: apps\api\server.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: export_user_data
**Description:** Extracted route from code.
**Entry Point:** apps\api\server.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\audio\__init__.py | Component of feature |
| application\pipelines\perception_telemetry.py | Component of feature |
| core\memory\indexer.py | Component of feature |
| core\vqa\api_endpoints.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\face\face_embeddings.py | Component of feature |
| shared\logging\logging_config.py | Component of feature |
| core\face\__init__.py | Component of feature |
| apps\cli\session_logger.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| application\pipelines\worker_pool.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\vqa\orchestrator.py | Component of feature |
| core\action\__init__.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| core\braille\__init__.py | Component of feature |
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| shared\utils\startup_guards.py | Component of feature |
| core\memory\config.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| infrastructure\resilience | Source directory |
| application\pipelines | Source directory |
| application\frame_processing | Source directory |
| core\qr | Source directory |
| infrastructure\monitoring | Source directory |
| core\memory | Source directory |
| shared\utils | Source directory |
| core\audio | Source directory |
| shared\logging | Source directory |
| shared\config | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |
| apps\cli | Source directory |
| core\face | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: process_perception_frame
- **Depends On / Used By:** API Route: ask_vqa_question
- **Depends On / Used By:** API Route: get_session_replay
- **Depends On / Used By:** API Route: delete_session
- **Depends On / Used By:** API Route: health_check
- **Depends On / Used By:** API Route: get_metrics
- **Depends On / Used By:** API Route: voice_ask
- **Depends On / Used By:** API Route: ask_priority_scene
- **Depends On / Used By:** API Route: debug_perception
- **Depends On / Used By:** API Route: store_memory
- **Depends On / Used By:** API Route: search_memories
- **Depends On / Used By:** API Route: query_memories
- **Depends On / Used By:** API Route: get_memory
- **Depends On / Used By:** API Route: get_session_memories
- **Depends On / Used By:** API Route: get_recent_memories
- **Depends On / Used By:** API Route: set_consent
- **Depends On / Used By:** API Route: get_consent
- **Depends On / Used By:** API Route: delete_memory
- **Depends On / Used By:** API Route: delete_all_memories
- **Depends On / Used By:** API Route: delete_session_memories
- **Depends On / Used By:** API Route: run_maintenance
- **Depends On / Used By:** API Route: get_health
- **Depends On / Used By:** API Route: get_stats
- **Depends On / Used By:** API Route: debug_session
- **Depends On / Used By:** Service/Agent: ServiceName
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: apps\api\server.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: erase_all_user_data
**Description:** Extracted route from code.
**Entry Point:** apps\api\server.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\audio\__init__.py | Component of feature |
| application\pipelines\perception_telemetry.py | Component of feature |
| core\memory\indexer.py | Component of feature |
| core\vqa\api_endpoints.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\face\face_embeddings.py | Component of feature |
| shared\logging\logging_config.py | Component of feature |
| core\face\__init__.py | Component of feature |
| apps\cli\session_logger.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| application\pipelines\worker_pool.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\vqa\orchestrator.py | Component of feature |
| core\action\__init__.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| core\braille\__init__.py | Component of feature |
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| shared\utils\startup_guards.py | Component of feature |
| core\memory\config.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| infrastructure\resilience | Source directory |
| application\pipelines | Source directory |
| application\frame_processing | Source directory |
| core\qr | Source directory |
| infrastructure\monitoring | Source directory |
| core\memory | Source directory |
| shared\utils | Source directory |
| core\audio | Source directory |
| shared\logging | Source directory |
| shared\config | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |
| apps\cli | Source directory |
| core\face | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: process_perception_frame
- **Depends On / Used By:** API Route: ask_vqa_question
- **Depends On / Used By:** API Route: get_session_replay
- **Depends On / Used By:** API Route: delete_session
- **Depends On / Used By:** API Route: health_check
- **Depends On / Used By:** API Route: get_metrics
- **Depends On / Used By:** API Route: voice_ask
- **Depends On / Used By:** API Route: ask_priority_scene
- **Depends On / Used By:** API Route: debug_perception
- **Depends On / Used By:** API Route: store_memory
- **Depends On / Used By:** API Route: search_memories
- **Depends On / Used By:** API Route: query_memories
- **Depends On / Used By:** API Route: get_memory
- **Depends On / Used By:** API Route: get_session_memories
- **Depends On / Used By:** API Route: get_recent_memories
- **Depends On / Used By:** API Route: set_consent
- **Depends On / Used By:** API Route: get_consent
- **Depends On / Used By:** API Route: delete_memory
- **Depends On / Used By:** API Route: delete_all_memories
- **Depends On / Used By:** API Route: delete_session_memories
- **Depends On / Used By:** API Route: run_maintenance
- **Depends On / Used By:** API Route: get_health
- **Depends On / Used By:** API Route: get_stats
- **Depends On / Used By:** API Route: debug_session
- **Depends On / Used By:** Service/Agent: ServiceName
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: apps\api\server.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: face_health
**Description:** Extracted route from code.
**Entry Point:** apps\api\server.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\audio\__init__.py | Component of feature |
| application\pipelines\perception_telemetry.py | Component of feature |
| core\memory\indexer.py | Component of feature |
| core\vqa\api_endpoints.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\face\face_embeddings.py | Component of feature |
| shared\logging\logging_config.py | Component of feature |
| core\face\__init__.py | Component of feature |
| apps\cli\session_logger.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| application\pipelines\worker_pool.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\vqa\orchestrator.py | Component of feature |
| core\action\__init__.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| core\braille\__init__.py | Component of feature |
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| shared\utils\startup_guards.py | Component of feature |
| core\memory\config.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| infrastructure\resilience | Source directory |
| application\pipelines | Source directory |
| application\frame_processing | Source directory |
| core\qr | Source directory |
| infrastructure\monitoring | Source directory |
| core\memory | Source directory |
| shared\utils | Source directory |
| core\audio | Source directory |
| shared\logging | Source directory |
| shared\config | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |
| apps\cli | Source directory |
| core\face | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: process_perception_frame
- **Depends On / Used By:** API Route: ask_vqa_question
- **Depends On / Used By:** API Route: get_session_replay
- **Depends On / Used By:** API Route: delete_session
- **Depends On / Used By:** API Route: health_check
- **Depends On / Used By:** API Route: get_metrics
- **Depends On / Used By:** API Route: voice_ask
- **Depends On / Used By:** API Route: ask_priority_scene
- **Depends On / Used By:** API Route: debug_perception
- **Depends On / Used By:** API Route: store_memory
- **Depends On / Used By:** API Route: search_memories
- **Depends On / Used By:** API Route: query_memories
- **Depends On / Used By:** API Route: get_memory
- **Depends On / Used By:** API Route: get_session_memories
- **Depends On / Used By:** API Route: get_recent_memories
- **Depends On / Used By:** API Route: set_consent
- **Depends On / Used By:** API Route: get_consent
- **Depends On / Used By:** API Route: delete_memory
- **Depends On / Used By:** API Route: delete_all_memories
- **Depends On / Used By:** API Route: delete_session_memories
- **Depends On / Used By:** API Route: run_maintenance
- **Depends On / Used By:** API Route: get_health
- **Depends On / Used By:** API Route: get_stats
- **Depends On / Used By:** API Route: debug_session
- **Depends On / Used By:** Service/Agent: ServiceName
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: apps\api\server.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: face_consent_grant
**Description:** Extracted route from code.
**Entry Point:** apps\api\server.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\audio\__init__.py | Component of feature |
| application\pipelines\perception_telemetry.py | Component of feature |
| core\memory\indexer.py | Component of feature |
| core\vqa\api_endpoints.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\face\face_embeddings.py | Component of feature |
| shared\logging\logging_config.py | Component of feature |
| core\face\__init__.py | Component of feature |
| apps\cli\session_logger.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| application\pipelines\worker_pool.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\vqa\orchestrator.py | Component of feature |
| core\action\__init__.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| core\braille\__init__.py | Component of feature |
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| shared\utils\startup_guards.py | Component of feature |
| core\memory\config.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| infrastructure\resilience | Source directory |
| application\pipelines | Source directory |
| application\frame_processing | Source directory |
| core\qr | Source directory |
| infrastructure\monitoring | Source directory |
| core\memory | Source directory |
| shared\utils | Source directory |
| core\audio | Source directory |
| shared\logging | Source directory |
| shared\config | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |
| apps\cli | Source directory |
| core\face | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: process_perception_frame
- **Depends On / Used By:** API Route: ask_vqa_question
- **Depends On / Used By:** API Route: get_session_replay
- **Depends On / Used By:** API Route: delete_session
- **Depends On / Used By:** API Route: health_check
- **Depends On / Used By:** API Route: get_metrics
- **Depends On / Used By:** API Route: voice_ask
- **Depends On / Used By:** API Route: ask_priority_scene
- **Depends On / Used By:** API Route: debug_perception
- **Depends On / Used By:** API Route: store_memory
- **Depends On / Used By:** API Route: search_memories
- **Depends On / Used By:** API Route: query_memories
- **Depends On / Used By:** API Route: get_memory
- **Depends On / Used By:** API Route: get_session_memories
- **Depends On / Used By:** API Route: get_recent_memories
- **Depends On / Used By:** API Route: set_consent
- **Depends On / Used By:** API Route: get_consent
- **Depends On / Used By:** API Route: delete_memory
- **Depends On / Used By:** API Route: delete_all_memories
- **Depends On / Used By:** API Route: delete_session_memories
- **Depends On / Used By:** API Route: run_maintenance
- **Depends On / Used By:** API Route: get_health
- **Depends On / Used By:** API Route: get_stats
- **Depends On / Used By:** API Route: debug_session
- **Depends On / Used By:** Service/Agent: ServiceName
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: apps\api\server.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: face_consent_log
**Description:** Extracted route from code.
**Entry Point:** apps\api\server.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\audio\__init__.py | Component of feature |
| application\pipelines\perception_telemetry.py | Component of feature |
| core\memory\indexer.py | Component of feature |
| core\vqa\api_endpoints.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\face\face_embeddings.py | Component of feature |
| shared\logging\logging_config.py | Component of feature |
| core\face\__init__.py | Component of feature |
| apps\cli\session_logger.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| application\pipelines\worker_pool.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\vqa\orchestrator.py | Component of feature |
| core\action\__init__.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| core\braille\__init__.py | Component of feature |
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| shared\utils\startup_guards.py | Component of feature |
| core\memory\config.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| infrastructure\resilience | Source directory |
| application\pipelines | Source directory |
| application\frame_processing | Source directory |
| core\qr | Source directory |
| infrastructure\monitoring | Source directory |
| core\memory | Source directory |
| shared\utils | Source directory |
| core\audio | Source directory |
| shared\logging | Source directory |
| shared\config | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |
| apps\cli | Source directory |
| core\face | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: process_perception_frame
- **Depends On / Used By:** API Route: ask_vqa_question
- **Depends On / Used By:** API Route: get_session_replay
- **Depends On / Used By:** API Route: delete_session
- **Depends On / Used By:** API Route: health_check
- **Depends On / Used By:** API Route: get_metrics
- **Depends On / Used By:** API Route: voice_ask
- **Depends On / Used By:** API Route: ask_priority_scene
- **Depends On / Used By:** API Route: debug_perception
- **Depends On / Used By:** API Route: store_memory
- **Depends On / Used By:** API Route: search_memories
- **Depends On / Used By:** API Route: query_memories
- **Depends On / Used By:** API Route: get_memory
- **Depends On / Used By:** API Route: get_session_memories
- **Depends On / Used By:** API Route: get_recent_memories
- **Depends On / Used By:** API Route: set_consent
- **Depends On / Used By:** API Route: get_consent
- **Depends On / Used By:** API Route: delete_memory
- **Depends On / Used By:** API Route: delete_all_memories
- **Depends On / Used By:** API Route: delete_session_memories
- **Depends On / Used By:** API Route: run_maintenance
- **Depends On / Used By:** API Route: get_health
- **Depends On / Used By:** API Route: get_stats
- **Depends On / Used By:** API Route: debug_session
- **Depends On / Used By:** Service/Agent: ServiceName
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: apps\api\server.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: face_detect_with_consent
**Description:** Extracted route from code.
**Entry Point:** apps\api\server.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\audio\__init__.py | Component of feature |
| application\pipelines\perception_telemetry.py | Component of feature |
| core\memory\indexer.py | Component of feature |
| core\vqa\api_endpoints.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\face\face_embeddings.py | Component of feature |
| shared\logging\logging_config.py | Component of feature |
| core\face\__init__.py | Component of feature |
| apps\cli\session_logger.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| application\pipelines\worker_pool.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\vqa\orchestrator.py | Component of feature |
| core\action\__init__.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| core\braille\__init__.py | Component of feature |
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| shared\utils\startup_guards.py | Component of feature |
| core\memory\config.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| infrastructure\resilience | Source directory |
| application\pipelines | Source directory |
| application\frame_processing | Source directory |
| core\qr | Source directory |
| infrastructure\monitoring | Source directory |
| core\memory | Source directory |
| shared\utils | Source directory |
| core\audio | Source directory |
| shared\logging | Source directory |
| shared\config | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |
| apps\cli | Source directory |
| core\face | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: process_perception_frame
- **Depends On / Used By:** API Route: ask_vqa_question
- **Depends On / Used By:** API Route: get_session_replay
- **Depends On / Used By:** API Route: delete_session
- **Depends On / Used By:** API Route: health_check
- **Depends On / Used By:** API Route: get_metrics
- **Depends On / Used By:** API Route: voice_ask
- **Depends On / Used By:** API Route: ask_priority_scene
- **Depends On / Used By:** API Route: debug_perception
- **Depends On / Used By:** API Route: store_memory
- **Depends On / Used By:** API Route: search_memories
- **Depends On / Used By:** API Route: query_memories
- **Depends On / Used By:** API Route: get_memory
- **Depends On / Used By:** API Route: get_session_memories
- **Depends On / Used By:** API Route: get_recent_memories
- **Depends On / Used By:** API Route: set_consent
- **Depends On / Used By:** API Route: get_consent
- **Depends On / Used By:** API Route: delete_memory
- **Depends On / Used By:** API Route: delete_all_memories
- **Depends On / Used By:** API Route: delete_session_memories
- **Depends On / Used By:** API Route: run_maintenance
- **Depends On / Used By:** API Route: get_health
- **Depends On / Used By:** API Route: get_stats
- **Depends On / Used By:** API Route: debug_session
- **Depends On / Used By:** Service/Agent: ServiceName
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: apps\api\server.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: face_forget_all
**Description:** Extracted route from code.
**Entry Point:** apps\api\server.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\audio\__init__.py | Component of feature |
| application\pipelines\perception_telemetry.py | Component of feature |
| core\memory\indexer.py | Component of feature |
| core\vqa\api_endpoints.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\face\face_embeddings.py | Component of feature |
| shared\logging\logging_config.py | Component of feature |
| core\face\__init__.py | Component of feature |
| apps\cli\session_logger.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| application\pipelines\worker_pool.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\vqa\orchestrator.py | Component of feature |
| core\action\__init__.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| core\braille\__init__.py | Component of feature |
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| shared\utils\startup_guards.py | Component of feature |
| core\memory\config.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| infrastructure\resilience | Source directory |
| application\pipelines | Source directory |
| application\frame_processing | Source directory |
| core\qr | Source directory |
| infrastructure\monitoring | Source directory |
| core\memory | Source directory |
| shared\utils | Source directory |
| core\audio | Source directory |
| shared\logging | Source directory |
| shared\config | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |
| apps\cli | Source directory |
| core\face | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: process_perception_frame
- **Depends On / Used By:** API Route: ask_vqa_question
- **Depends On / Used By:** API Route: get_session_replay
- **Depends On / Used By:** API Route: delete_session
- **Depends On / Used By:** API Route: health_check
- **Depends On / Used By:** API Route: get_metrics
- **Depends On / Used By:** API Route: voice_ask
- **Depends On / Used By:** API Route: ask_priority_scene
- **Depends On / Used By:** API Route: debug_perception
- **Depends On / Used By:** API Route: store_memory
- **Depends On / Used By:** API Route: search_memories
- **Depends On / Used By:** API Route: query_memories
- **Depends On / Used By:** API Route: get_memory
- **Depends On / Used By:** API Route: get_session_memories
- **Depends On / Used By:** API Route: get_recent_memories
- **Depends On / Used By:** API Route: set_consent
- **Depends On / Used By:** API Route: get_consent
- **Depends On / Used By:** API Route: delete_memory
- **Depends On / Used By:** API Route: delete_all_memories
- **Depends On / Used By:** API Route: delete_session_memories
- **Depends On / Used By:** API Route: run_maintenance
- **Depends On / Used By:** API Route: get_health
- **Depends On / Used By:** API Route: get_stats
- **Depends On / Used By:** API Route: debug_session
- **Depends On / Used By:** Service/Agent: ServiceName
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: apps\api\server.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: audio_health
**Description:** Extracted route from code.
**Entry Point:** apps\api\server.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\audio\__init__.py | Component of feature |
| application\pipelines\perception_telemetry.py | Component of feature |
| core\memory\indexer.py | Component of feature |
| core\vqa\api_endpoints.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\face\face_embeddings.py | Component of feature |
| shared\logging\logging_config.py | Component of feature |
| core\face\__init__.py | Component of feature |
| apps\cli\session_logger.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| application\pipelines\worker_pool.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\vqa\orchestrator.py | Component of feature |
| core\action\__init__.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| core\braille\__init__.py | Component of feature |
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| shared\utils\startup_guards.py | Component of feature |
| core\memory\config.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| infrastructure\resilience | Source directory |
| application\pipelines | Source directory |
| application\frame_processing | Source directory |
| core\qr | Source directory |
| infrastructure\monitoring | Source directory |
| core\memory | Source directory |
| shared\utils | Source directory |
| core\audio | Source directory |
| shared\logging | Source directory |
| shared\config | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |
| apps\cli | Source directory |
| core\face | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: process_perception_frame
- **Depends On / Used By:** API Route: ask_vqa_question
- **Depends On / Used By:** API Route: get_session_replay
- **Depends On / Used By:** API Route: delete_session
- **Depends On / Used By:** API Route: health_check
- **Depends On / Used By:** API Route: get_metrics
- **Depends On / Used By:** API Route: voice_ask
- **Depends On / Used By:** API Route: ask_priority_scene
- **Depends On / Used By:** API Route: debug_perception
- **Depends On / Used By:** API Route: store_memory
- **Depends On / Used By:** API Route: search_memories
- **Depends On / Used By:** API Route: query_memories
- **Depends On / Used By:** API Route: get_memory
- **Depends On / Used By:** API Route: get_session_memories
- **Depends On / Used By:** API Route: get_recent_memories
- **Depends On / Used By:** API Route: set_consent
- **Depends On / Used By:** API Route: get_consent
- **Depends On / Used By:** API Route: delete_memory
- **Depends On / Used By:** API Route: delete_all_memories
- **Depends On / Used By:** API Route: delete_session_memories
- **Depends On / Used By:** API Route: run_maintenance
- **Depends On / Used By:** API Route: get_health
- **Depends On / Used By:** API Route: get_stats
- **Depends On / Used By:** API Route: debug_session
- **Depends On / Used By:** Service/Agent: ServiceName
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: apps\api\server.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: debug_ssl_frame
**Description:** Extracted route from code.
**Entry Point:** apps\api\server.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\audio\__init__.py | Component of feature |
| application\pipelines\perception_telemetry.py | Component of feature |
| core\memory\indexer.py | Component of feature |
| core\vqa\api_endpoints.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\face\face_embeddings.py | Component of feature |
| shared\logging\logging_config.py | Component of feature |
| core\face\__init__.py | Component of feature |
| apps\cli\session_logger.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| application\pipelines\worker_pool.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\vqa\orchestrator.py | Component of feature |
| core\action\__init__.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| core\braille\__init__.py | Component of feature |
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| shared\utils\startup_guards.py | Component of feature |
| core\memory\config.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| infrastructure\resilience | Source directory |
| application\pipelines | Source directory |
| application\frame_processing | Source directory |
| core\qr | Source directory |
| infrastructure\monitoring | Source directory |
| core\memory | Source directory |
| shared\utils | Source directory |
| core\audio | Source directory |
| shared\logging | Source directory |
| shared\config | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |
| apps\cli | Source directory |
| core\face | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: process_perception_frame
- **Depends On / Used By:** API Route: ask_vqa_question
- **Depends On / Used By:** API Route: get_session_replay
- **Depends On / Used By:** API Route: delete_session
- **Depends On / Used By:** API Route: health_check
- **Depends On / Used By:** API Route: get_metrics
- **Depends On / Used By:** API Route: voice_ask
- **Depends On / Used By:** API Route: ask_priority_scene
- **Depends On / Used By:** API Route: debug_perception
- **Depends On / Used By:** API Route: store_memory
- **Depends On / Used By:** API Route: search_memories
- **Depends On / Used By:** API Route: query_memories
- **Depends On / Used By:** API Route: get_memory
- **Depends On / Used By:** API Route: get_session_memories
- **Depends On / Used By:** API Route: get_recent_memories
- **Depends On / Used By:** API Route: set_consent
- **Depends On / Used By:** API Route: get_consent
- **Depends On / Used By:** API Route: delete_memory
- **Depends On / Used By:** API Route: delete_all_memories
- **Depends On / Used By:** API Route: delete_session_memories
- **Depends On / Used By:** API Route: run_maintenance
- **Depends On / Used By:** API Route: get_health
- **Depends On / Used By:** API Route: get_stats
- **Depends On / Used By:** API Route: debug_session
- **Depends On / Used By:** Service/Agent: ServiceName
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: apps\api\server.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: action_health
**Description:** Extracted route from code.
**Entry Point:** apps\api\server.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\audio\__init__.py | Component of feature |
| application\pipelines\perception_telemetry.py | Component of feature |
| core\memory\indexer.py | Component of feature |
| core\vqa\api_endpoints.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\face\face_embeddings.py | Component of feature |
| shared\logging\logging_config.py | Component of feature |
| core\face\__init__.py | Component of feature |
| apps\cli\session_logger.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| application\pipelines\worker_pool.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\vqa\orchestrator.py | Component of feature |
| core\action\__init__.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| core\braille\__init__.py | Component of feature |
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| shared\utils\startup_guards.py | Component of feature |
| core\memory\config.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| infrastructure\resilience | Source directory |
| application\pipelines | Source directory |
| application\frame_processing | Source directory |
| core\qr | Source directory |
| infrastructure\monitoring | Source directory |
| core\memory | Source directory |
| shared\utils | Source directory |
| core\audio | Source directory |
| shared\logging | Source directory |
| shared\config | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |
| apps\cli | Source directory |
| core\face | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: process_perception_frame
- **Depends On / Used By:** API Route: ask_vqa_question
- **Depends On / Used By:** API Route: get_session_replay
- **Depends On / Used By:** API Route: delete_session
- **Depends On / Used By:** API Route: health_check
- **Depends On / Used By:** API Route: get_metrics
- **Depends On / Used By:** API Route: voice_ask
- **Depends On / Used By:** API Route: ask_priority_scene
- **Depends On / Used By:** API Route: debug_perception
- **Depends On / Used By:** API Route: store_memory
- **Depends On / Used By:** API Route: search_memories
- **Depends On / Used By:** API Route: query_memories
- **Depends On / Used By:** API Route: get_memory
- **Depends On / Used By:** API Route: get_session_memories
- **Depends On / Used By:** API Route: get_recent_memories
- **Depends On / Used By:** API Route: set_consent
- **Depends On / Used By:** API Route: get_consent
- **Depends On / Used By:** API Route: delete_memory
- **Depends On / Used By:** API Route: delete_all_memories
- **Depends On / Used By:** API Route: delete_session_memories
- **Depends On / Used By:** API Route: run_maintenance
- **Depends On / Used By:** API Route: get_health
- **Depends On / Used By:** API Route: get_stats
- **Depends On / Used By:** API Route: debug_session
- **Depends On / Used By:** Service/Agent: ServiceName
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: apps\api\server.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## Service/Agent: AllyVisionAgent
**Description:** Extracted service from code.
**Entry Point:** apps\realtime\agent.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| application\frame_processing\freshness.py | Component of feature |
| core\speech\voice_router.py | Component of feature |
| apps\cli\session_logger.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| apps\realtime\session_manager.py | Component of feature |
| apps\realtime\prompts.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| apps\realtime\__init__.py | Component of feature |
| core\ocr\__init__.py | Component of feature |
| apps\realtime\user_data.py | Component of feature |
| shared\utils\timing.py | Component of feature |
| apps\realtime\agent.py | Component of feature |
| apps\realtime\tool_router.py | Component of feature |
| core\vqa\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| application\frame_processing | Source directory |
| core\qr | Source directory |
| shared\utils | Source directory |
| shared\config | Source directory |
| core\vqa | Source directory |
| apps\cli | Source directory |
| core\ocr | Source directory |
| core\speech | Source directory |
| apps\realtime | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: PipelineProfiler
- **Depends On / Used By:** Service/Agent: OCRPipelineResult
- **Depends On / Used By:** Service/Agent: OCRPipeline
- **Depends On / Used By:** Core Feature: create_agent_session
- **Depends On / Used By:** Core Feature: start_agent_session

### Debug Entry Points
> When debugging this feature, start here:
- Primary: apps\realtime\agent.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Core Feature: create_agent_session
**Description:** Extracted core from code.
**Entry Point:** apps\realtime\session_manager.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| application\frame_processing\freshness.py | Component of feature |
| core\speech\voice_router.py | Component of feature |
| apps\cli\session_logger.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| apps\realtime\session_manager.py | Component of feature |
| infrastructure\llm\internet_search.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\vqa\__init__.py | Component of feature |
| application\pipelines\debouncer.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| shared\utils\runtime_diagnostics.py | Component of feature |
| core\ocr\__init__.py | Component of feature |
| infrastructure\llm\ollama\handler.py | Component of feature |
| core\vision\visual.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| application\pipelines | Source directory |
| application\frame_processing | Source directory |
| core\qr | Source directory |
| core\vision | Source directory |
| shared\utils | Source directory |
| infrastructure\llm | Source directory |
| shared\config | Source directory |
| core\vqa | Source directory |
| apps\cli | Source directory |
| infrastructure\llm\ollama | Source directory |
| core\ocr | Source directory |
| core\speech | Source directory |
| apps\realtime | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: OCRPipelineResult
- **Depends On / Used By:** Service/Agent: OCRPipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: apps\realtime\session_manager.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: start_agent_session
**Description:** Extracted core from code.
**Entry Point:** apps\realtime\session_manager.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| application\frame_processing\freshness.py | Component of feature |
| core\speech\voice_router.py | Component of feature |
| apps\cli\session_logger.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| apps\realtime\session_manager.py | Component of feature |
| infrastructure\llm\internet_search.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\vqa\__init__.py | Component of feature |
| application\pipelines\debouncer.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| shared\utils\runtime_diagnostics.py | Component of feature |
| core\ocr\__init__.py | Component of feature |
| infrastructure\llm\ollama\handler.py | Component of feature |
| core\vision\visual.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| application\pipelines | Source directory |
| application\frame_processing | Source directory |
| core\qr | Source directory |
| core\vision | Source directory |
| shared\utils | Source directory |
| infrastructure\llm | Source directory |
| shared\config | Source directory |
| core\vqa | Source directory |
| apps\cli | Source directory |
| infrastructure\llm\ollama | Source directory |
| core\ocr | Source directory |
| core\speech | Source directory |
| apps\realtime | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: OCRPipelineResult
- **Depends On / Used By:** Service/Agent: OCRPipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: apps\realtime\session_manager.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## API Route: store_memory
**Description:** Extracted route from code.
**Entry Point:** core\memory\api_endpoints.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\memory | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: core\memory\api_endpoints.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: search_memories
**Description:** Extracted route from code.
**Entry Point:** core\memory\api_endpoints.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\memory | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: core\memory\api_endpoints.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: query_memories
**Description:** Extracted route from code.
**Entry Point:** core\memory\api_endpoints.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\memory | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: core\memory\api_endpoints.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: get_memory
**Description:** Extracted route from code.
**Entry Point:** core\memory\api_endpoints.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\memory | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: core\memory\api_endpoints.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: get_session_memories
**Description:** Extracted route from code.
**Entry Point:** core\memory\api_endpoints.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\memory | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: core\memory\api_endpoints.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: get_recent_memories
**Description:** Extracted route from code.
**Entry Point:** core\memory\api_endpoints.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\memory | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: core\memory\api_endpoints.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: set_consent
**Description:** Extracted route from code.
**Entry Point:** core\memory\api_endpoints.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\memory | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: core\memory\api_endpoints.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: get_consent
**Description:** Extracted route from code.
**Entry Point:** core\memory\api_endpoints.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\memory | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: core\memory\api_endpoints.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: delete_memory
**Description:** Extracted route from code.
**Entry Point:** core\memory\api_endpoints.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\memory | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: core\memory\api_endpoints.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: delete_all_memories
**Description:** Extracted route from code.
**Entry Point:** core\memory\api_endpoints.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\memory | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: core\memory\api_endpoints.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: delete_session_memories
**Description:** Extracted route from code.
**Entry Point:** core\memory\api_endpoints.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\memory | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: core\memory\api_endpoints.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: run_maintenance
**Description:** Extracted route from code.
**Entry Point:** core\memory\api_endpoints.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\memory | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: core\memory\api_endpoints.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: get_health
**Description:** Extracted route from code.
**Entry Point:** core\memory\api_endpoints.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\memory | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: core\memory\api_endpoints.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: get_stats
**Description:** Extracted route from code.
**Entry Point:** core\memory\api_endpoints.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\memory | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: core\memory\api_endpoints.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: debug_session
**Description:** Extracted route from code.
**Entry Point:** core\memory\api_endpoints.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\api_endpoints.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\memory | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: core\memory\api_endpoints.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## Service/Agent: OCRPipelineResult
**Description:** Extracted service from code.
**Entry Point:** core\ocr\__init__.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| shared\schemas\__init__.py | Component of feature |
| core\ocr\__init__.py | Component of feature |
| shared\logging\logging_config.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| shared\schemas | Source directory |
| core\ocr | Source directory |
| shared\logging | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: core\ocr\__init__.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: OCRPipeline
**Description:** Extracted service from code.
**Entry Point:** core\ocr\__init__.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| shared\schemas\__init__.py | Component of feature |
| core\ocr\__init__.py | Component of feature |
| shared\logging\logging_config.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| shared\schemas | Source directory |
| core\ocr | Source directory |
| shared\logging | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: core\ocr\__init__.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## API Route: scan_qr
**Description:** Extracted route from code.
**Entry Point:** core\qr\qr_api.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\qr\qr_api.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\qr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: core\qr\qr_api.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: add_to_cache
**Description:** Extracted route from code.
**Entry Point:** core\qr\qr_api.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\qr\qr_api.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\qr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: core\qr\qr_api.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: get_history
**Description:** Extracted route from code.
**Entry Point:** core\qr\qr_api.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\qr\qr_api.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\qr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: core\qr\qr_api.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: debug_scan
**Description:** Extracted route from code.
**Entry Point:** core\qr\qr_api.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\qr\qr_api.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\qr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: core\qr\qr_api.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## Service/Agent: VoiceAskPipeline
**Description:** Extracted service from code.
**Entry Point:** core\speech\voice_ask_pipeline.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\speech\voice_ask_pipeline.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\speech | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: core\speech\voice_ask_pipeline.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## API Route: process_perception_frame
**Description:** Extracted route from code.
**Entry Point:** core\vqa\api_endpoints.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\vqa\api_endpoints.py | Component of feature |
| shared\debug\__init__.py | Component of feature |
| core\speech\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\vqa | Source directory |
| core\speech | Source directory |
| shared\debug | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: core\vqa\api_endpoints.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: ask_vqa_question
**Description:** Extracted route from code.
**Entry Point:** core\vqa\api_endpoints.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\vqa\api_endpoints.py | Component of feature |
| shared\debug\__init__.py | Component of feature |
| core\speech\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\vqa | Source directory |
| core\speech | Source directory |
| shared\debug | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: core\vqa\api_endpoints.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: get_session_replay
**Description:** Extracted route from code.
**Entry Point:** core\vqa\api_endpoints.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\vqa\api_endpoints.py | Component of feature |
| shared\debug\__init__.py | Component of feature |
| core\speech\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\vqa | Source directory |
| core\speech | Source directory |
| shared\debug | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: core\vqa\api_endpoints.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: delete_session
**Description:** Extracted route from code.
**Entry Point:** core\vqa\api_endpoints.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\vqa\api_endpoints.py | Component of feature |
| shared\debug\__init__.py | Component of feature |
| core\speech\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\vqa | Source directory |
| core\speech | Source directory |
| shared\debug | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: core\vqa\api_endpoints.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: health_check
**Description:** Extracted route from code.
**Entry Point:** core\vqa\api_endpoints.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\vqa\api_endpoints.py | Component of feature |
| shared\debug\__init__.py | Component of feature |
| core\speech\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\vqa | Source directory |
| core\speech | Source directory |
| shared\debug | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: core\vqa\api_endpoints.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: get_metrics
**Description:** Extracted route from code.
**Entry Point:** core\vqa\api_endpoints.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\vqa\api_endpoints.py | Component of feature |
| shared\debug\__init__.py | Component of feature |
| core\speech\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\vqa | Source directory |
| core\speech | Source directory |
| shared\debug | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: core\vqa\api_endpoints.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: voice_ask
**Description:** Extracted route from code.
**Entry Point:** core\vqa\api_endpoints.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\vqa\api_endpoints.py | Component of feature |
| shared\debug\__init__.py | Component of feature |
| core\speech\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\vqa | Source directory |
| core\speech | Source directory |
| shared\debug | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: core\vqa\api_endpoints.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: ask_priority_scene
**Description:** Extracted route from code.
**Entry Point:** core\vqa\api_endpoints.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\vqa\api_endpoints.py | Component of feature |
| shared\debug\__init__.py | Component of feature |
| core\speech\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\vqa | Source directory |
| core\speech | Source directory |
| shared\debug | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: core\vqa\api_endpoints.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## API Route: debug_perception
**Description:** Extracted route from code.
**Entry Point:** core\vqa\api_endpoints.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\vqa\api_endpoints.py | Component of feature |
| shared\debug\__init__.py | Component of feature |
| core\speech\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\vqa | Source directory |
| core\speech | Source directory |
| shared\debug | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: core\vqa\api_endpoints.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: route

---
## Service/Agent: PerceptionPipeline
**Description:** Extracted service from code.
**Entry Point:** core\vqa\perception.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| shared\schemas\__init__.py | Component of feature |
| core\vqa\perception.py | Component of feature |
| shared\logging\logging_config.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| shared\schemas | Source directory |
| core\vqa | Source directory |
| shared\logging | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: core\vqa\perception.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Core Feature: create_pipeline
**Description:** Extracted core from code.
**Entry Point:** core\vqa\perception.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| shared\schemas\__init__.py | Component of feature |
| core\vqa\perception.py | Component of feature |
| shared\logging\logging_config.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| shared\schemas | Source directory |
| core\vqa | Source directory |
| shared\logging | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: core\vqa\perception.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Service/Agent: PipelineStageMetrics
**Description:** Extracted service from code.
**Entry Point:** infrastructure\monitoring\instrumentation.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| infrastructure\monitoring\instrumentation.py | Component of feature |
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| infrastructure\monitoring | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: ServiceName

### Debug Entry Points
> When debugging this feature, start here:
- Primary: infrastructure\monitoring\instrumentation.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: ServiceName
**Description:** Extracted service from code.
**Entry Point:** infrastructure\monitoring\prometheus_metrics.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| infrastructure\monitoring\collector.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| infrastructure\monitoring | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: infrastructure\monitoring\prometheus_metrics.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: ServiceStatus
**Description:** Extracted service from code.
**Entry Point:** infrastructure\resilience\health_registry.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| infrastructure\resilience\circuit_breaker.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| infrastructure\resilience | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: infrastructure\resilience\health_registry.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: ServiceHealth
**Description:** Extracted service from code.
**Entry Point:** infrastructure\resilience\health_registry.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| infrastructure\resilience\circuit_breaker.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| infrastructure\resilience | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: infrastructure\resilience\health_registry.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: ServiceHealthRegistry
**Description:** Extracted service from code.
**Entry Point:** infrastructure\resilience\health_registry.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| infrastructure\resilience\circuit_breaker.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| infrastructure\resilience | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: infrastructure\resilience\health_registry.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: ServiceMetrics
**Description:** Extracted service from code.
**Entry Point:** scripts\canary_analysis.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| scripts\canary_analysis.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| scripts | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: scripts\canary_analysis.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: PipelineProfiler
**Description:** Extracted service from code.
**Entry Point:** shared\utils\timing.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| shared\utils\timing.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| shared\utils | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: shared\utils\timing.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestPerceptionPipelineAPI
**Description:** Extracted service from code.
**Entry Point:** tests\test_ci_smoke.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| shared\schemas\__init__.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\ocr\__init__.py | Component of feature |
| tests\test_ci_smoke.py | Component of feature |
| core\vqa\perception.py | Component of feature |
| core\vqa\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| application\frame_processing | Source directory |
| tests | Source directory |
| core\vqa | Source directory |
| shared\schemas | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: PerceptionPipeline
- **Depends On / Used By:** Core Feature: create_pipeline
- **Depends On / Used By:** Service/Agent: OCRPipelineResult
- **Depends On / Used By:** Service/Agent: OCRPipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\test_ci_smoke.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestCreatePipeline
**Description:** Extracted service from code.
**Entry Point:** tests\test_ci_smoke.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| shared\schemas\__init__.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\ocr\__init__.py | Component of feature |
| tests\test_ci_smoke.py | Component of feature |
| core\vqa\perception.py | Component of feature |
| core\vqa\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| application\frame_processing | Source directory |
| tests | Source directory |
| core\vqa | Source directory |
| shared\schemas | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: PerceptionPipeline
- **Depends On / Used By:** Core Feature: create_pipeline
- **Depends On / Used By:** Service/Agent: OCRPipelineResult
- **Depends On / Used By:** Service/Agent: OCRPipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\test_ci_smoke.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Core Feature: test_mock_pipeline_detect
**Description:** Extracted core from code.
**Entry Point:** tests\test_ci_smoke.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| shared\schemas\__init__.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\ocr\__init__.py | Component of feature |
| tests\test_ci_smoke.py | Component of feature |
| core\vqa\perception.py | Component of feature |
| core\vqa\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| application\frame_processing | Source directory |
| tests | Source directory |
| core\vqa | Source directory |
| shared\schemas | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: PerceptionPipeline
- **Depends On / Used By:** Core Feature: create_pipeline
- **Depends On / Used By:** Service/Agent: OCRPipelineResult
- **Depends On / Used By:** Service/Agent: OCRPipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\test_ci_smoke.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: test_non_mock_pipeline_has_detector
**Description:** Extracted core from code.
**Entry Point:** tests\test_ci_smoke.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| shared\schemas\__init__.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\ocr\__init__.py | Component of feature |
| tests\test_ci_smoke.py | Component of feature |
| core\vqa\perception.py | Component of feature |
| core\vqa\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| application\frame_processing | Source directory |
| tests | Source directory |
| core\vqa | Source directory |
| shared\schemas | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: PerceptionPipeline
- **Depends On / Used By:** Core Feature: create_pipeline
- **Depends On / Used By:** Service/Agent: OCRPipelineResult
- **Depends On / Used By:** Service/Agent: OCRPipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\test_ci_smoke.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: test_pipeline_detect_callable
**Description:** Extracted core from code.
**Entry Point:** tests\test_ci_smoke.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| shared\schemas\__init__.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| core\ocr\__init__.py | Component of feature |
| tests\test_ci_smoke.py | Component of feature |
| core\vqa\perception.py | Component of feature |
| core\vqa\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| application\frame_processing | Source directory |
| tests | Source directory |
| core\vqa | Source directory |
| shared\schemas | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: PerceptionPipeline
- **Depends On / Used By:** Core Feature: create_pipeline
- **Depends On / Used By:** Service/Agent: OCRPipelineResult
- **Depends On / Used By:** Service/Agent: OCRPipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\test_ci_smoke.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: test_producer_consumer_pipeline
**Description:** Extracted core from code.
**Entry Point:** tests\test_continuous_processing.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| application\frame_processing\freshness.py | Component of feature |
| tests\test_continuous_processing.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| application\pipelines\worker_pool.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| application\pipelines\debouncer.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests | Source directory |
| shared\config | Source directory |
| application\pipelines | Source directory |
| application\frame_processing | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\test_continuous_processing.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: test_ocr_pipeline_creates
**Description:** Extracted core from code.
**Entry Point:** tests\test_model_load.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\test_model_load.py | Component of feature |
| core\qr\qr_scanner.py | Component of feature |
| core\ocr\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\qr | Source directory |
| tests | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: OCRPipelineResult
- **Depends On / Used By:** Service/Agent: OCRPipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\test_model_load.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Service/Agent: TestOCRPipelineResult
**Description:** Extracted service from code.
**Entry Point:** tests\test_ocr_pipeline.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\test_ocr_pipeline.py | Component of feature |
| core\ocr\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: OCRPipelineResult
- **Depends On / Used By:** Service/Agent: OCRPipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\test_ocr_pipeline.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestOCRPipeline
**Description:** Extracted service from code.
**Entry Point:** tests\test_ocr_pipeline.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\test_ocr_pipeline.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| tests\test_smoke_api.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| core\ocr\__init__.py | Component of feature |
| core\vqa\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests | Source directory |
| core\vqa | Source directory |
| core\ocr | Source directory |
| application\pipelines | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: OCRPipelineResult
- **Depends On / Used By:** Service/Agent: OCRPipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\test_ocr_pipeline.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Core Feature: test_preprocess_full_pipeline
**Description:** Extracted core from code.
**Entry Point:** tests\test_ocr_pipeline.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\test_ocr_pipeline.py | Component of feature |
| core\ocr\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: OCRPipelineResult
- **Depends On / Used By:** Service/Agent: OCRPipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\test_ocr_pipeline.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: test_global_pipeline_timeout
**Description:** Extracted core from code.
**Entry Point:** tests\test_orchestrator.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| shared\schemas\__init__.py | Component of feature |
| core\vqa\orchestrator.py | Component of feature |
| tests\test_orchestrator.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests | Source directory |
| shared\schemas | Source directory |
| core\vqa | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\test_orchestrator.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: test_preflight_no_pipeline
**Description:** Extracted core from code.
**Entry Point:** tests\test_runtime_diagnostics.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| shared\utils\runtime_diagnostics.py | Component of feature |
| tests\test_runtime_diagnostics.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests | Source directory |
| shared\utils | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\test_runtime_diagnostics.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: test_preflight_with_mock_pipeline
**Description:** Extracted core from code.
**Entry Point:** tests\test_runtime_diagnostics.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| shared\utils\runtime_diagnostics.py | Component of feature |
| tests\test_runtime_diagnostics.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests | Source directory |
| shared\utils | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\test_runtime_diagnostics.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Service/Agent: TestPerceptionPipeline
**Description:** Extracted service from code.
**Entry Point:** tests\test_smoke_api.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| shared\schemas\__init__.py | Component of feature |
| tests\test_smoke_api.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| tests\unit\test_perception.py | Component of feature |
| core\ocr\__init__.py | Component of feature |
| core\vqa\perception.py | Component of feature |
| core\vqa\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\unit | Source directory |
| application\pipelines | Source directory |
| tests | Source directory |
| core\vqa | Source directory |
| shared\schemas | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: PerceptionPipeline
- **Depends On / Used By:** Core Feature: create_pipeline
- **Depends On / Used By:** Service/Agent: OCRPipelineResult
- **Depends On / Used By:** Service/Agent: OCRPipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\test_smoke_api.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Core Feature: test_ocr_pipeline_importable
**Description:** Extracted core from code.
**Entry Point:** tests\test_smoke_api.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| application\pipelines\watchdog.py | Component of feature |
| tests\test_smoke_api.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| core\ocr\__init__.py | Component of feature |
| core\vqa\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests | Source directory |
| core\vqa | Source directory |
| core\ocr | Source directory |
| application\pipelines | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: OCRPipelineResult
- **Depends On / Used By:** Service/Agent: OCRPipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\test_smoke_api.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: test_full_pipeline
**Description:** Extracted core from code.
**Entry Point:** tests\test_spatial.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\vqa\scene_graph.py | Component of feature |
| tests\test_spatial.py | Component of feature |
| core\vision\spatial.py | Component of feature |
| core\vqa\perception.py | Component of feature |
| core\vqa\spatial_fuser.py | Component of feature |
| tests\unit\test_fusion.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests | Source directory |
| core\vision | Source directory |
| tests\unit | Source directory |
| core\vqa | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: PerceptionPipeline
- **Depends On / Used By:** Core Feature: create_pipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\test_spatial.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Service/Agent: TestVoiceAskPipeline
**Description:** Extracted service from code.
**Entry Point:** tests\test_speech_vqa_bridge.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\test_speech_vqa_bridge.py | Component of feature |
| core\speech\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests | Source directory |
| core\speech | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\test_speech_vqa_bridge.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Core Feature: test_pipeline_initialization
**Description:** Extracted core from code.
**Entry Point:** tests\test_speech_vqa_bridge.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\test_speech_vqa_bridge.py | Component of feature |
| core\speech\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests | Source directory |
| core\speech | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\test_speech_vqa_bridge.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Service/Agent: MockServiceClient
**Description:** Extracted service from code.
**Entry Point:** tests\chaos\test_chaos.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| infrastructure\resilience\circuit_breaker.py | Component of feature |
| tests\chaos\test_chaos.py | Component of feature |
| tests\performance\test_chaos.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\chaos | Source directory |
| infrastructure\resilience | Source directory |
| tests\performance | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\chaos\test_chaos.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestChaos04PipelineTimeout
**Description:** Extracted service from code.
**Entry Point:** tests\chaos\test_chaos.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| infrastructure\resilience\circuit_breaker.py | Component of feature |
| tests\chaos\test_chaos.py | Component of feature |
| tests\performance\test_chaos.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\chaos | Source directory |
| infrastructure\resilience | Source directory |
| tests\performance | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\chaos\test_chaos.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestChaos08CascadingServiceFailure
**Description:** Extracted service from code.
**Entry Point:** tests\chaos\test_chaos.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| infrastructure\resilience\circuit_breaker.py | Component of feature |
| tests\chaos\test_chaos.py | Component of feature |
| tests\performance\test_chaos.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\chaos | Source directory |
| infrastructure\resilience | Source directory |
| tests\performance | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\chaos\test_chaos.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestChaos15FlappingService
**Description:** Extracted service from code.
**Entry Point:** tests\chaos\test_chaos.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| infrastructure\resilience\circuit_breaker.py | Component of feature |
| tests\chaos\test_chaos.py | Component of feature |
| tests\performance\test_chaos.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\chaos | Source directory |
| infrastructure\resilience | Source directory |
| tests\performance | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\chaos\test_chaos.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Core Feature: test_full_pipeline_timeout_300ms
**Description:** Extracted core from code.
**Entry Point:** tests\chaos\test_chaos.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| infrastructure\resilience\circuit_breaker.py | Component of feature |
| tests\chaos\test_chaos.py | Component of feature |
| tests\performance\test_chaos.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\chaos | Source directory |
| infrastructure\resilience | Source directory |
| tests\performance | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\chaos\test_chaos.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: mock_pipeline
**Description:** Extracted core from code.
**Entry Point:** tests\chaos\test_chaos.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| infrastructure\resilience\circuit_breaker.py | Component of feature |
| tests\chaos\test_chaos.py | Component of feature |
| tests\performance\test_chaos.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\chaos | Source directory |
| infrastructure\resilience | Source directory |
| tests\performance | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\chaos\test_chaos.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: _try_import_agent
**Description:** Extracted core from code.
**Entry Point:** tests\integration\test_agent_coordinator.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| apps\realtime\vision_controller.py | Component of feature |
| apps\realtime\session_manager.py | Component of feature |
| apps\realtime\voice_controller.py | Component of feature |
| apps\realtime\prompts.py | Component of feature |
| apps\realtime\tool_router.py | Component of feature |
| apps\realtime\user_data.py | Component of feature |
| apps\realtime\agent.py | Component of feature |
| tests\integration\test_agent_coordinator.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\integration | Source directory |
| apps\realtime | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: AllyVisionAgent
- **Depends On / Used By:** Core Feature: create_agent_session
- **Depends On / Used By:** Core Feature: start_agent_session

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\integration\test_agent_coordinator.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: test_agent_coordinator_importable
**Description:** Extracted core from code.
**Entry Point:** tests\integration\test_agent_coordinator.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| apps\realtime\vision_controller.py | Component of feature |
| apps\realtime\session_manager.py | Component of feature |
| apps\realtime\voice_controller.py | Component of feature |
| apps\realtime\prompts.py | Component of feature |
| apps\realtime\tool_router.py | Component of feature |
| apps\realtime\user_data.py | Component of feature |
| apps\realtime\agent.py | Component of feature |
| tests\integration\test_agent_coordinator.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\integration | Source directory |
| apps\realtime | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: AllyVisionAgent
- **Depends On / Used By:** Core Feature: create_agent_session
- **Depends On / Used By:** Core Feature: start_agent_session

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\integration\test_agent_coordinator.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: test_agent_inherits_from_agent_base
**Description:** Extracted core from code.
**Entry Point:** tests\integration\test_agent_coordinator.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| apps\realtime\vision_controller.py | Component of feature |
| apps\realtime\session_manager.py | Component of feature |
| apps\realtime\voice_controller.py | Component of feature |
| apps\realtime\prompts.py | Component of feature |
| apps\realtime\tool_router.py | Component of feature |
| apps\realtime\user_data.py | Component of feature |
| apps\realtime\agent.py | Component of feature |
| tests\integration\test_agent_coordinator.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\integration | Source directory |
| apps\realtime | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: AllyVisionAgent
- **Depends On / Used By:** Core Feature: create_agent_session
- **Depends On / Used By:** Core Feature: start_agent_session

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\integration\test_agent_coordinator.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: test_agent_has_all_function_tools
**Description:** Extracted core from code.
**Entry Point:** tests\integration\test_agent_coordinator.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| apps\realtime\vision_controller.py | Component of feature |
| apps\realtime\session_manager.py | Component of feature |
| apps\realtime\voice_controller.py | Component of feature |
| apps\realtime\prompts.py | Component of feature |
| apps\realtime\tool_router.py | Component of feature |
| apps\realtime\user_data.py | Component of feature |
| apps\realtime\agent.py | Component of feature |
| tests\integration\test_agent_coordinator.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\integration | Source directory |
| apps\realtime | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: AllyVisionAgent
- **Depends On / Used By:** Core Feature: create_agent_session
- **Depends On / Used By:** Core Feature: start_agent_session

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\integration\test_agent_coordinator.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: test_agent_file_under_500_loc
**Description:** Extracted core from code.
**Entry Point:** tests\integration\test_agent_coordinator.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| apps\realtime\vision_controller.py | Component of feature |
| apps\realtime\session_manager.py | Component of feature |
| apps\realtime\voice_controller.py | Component of feature |
| apps\realtime\prompts.py | Component of feature |
| apps\realtime\tool_router.py | Component of feature |
| apps\realtime\user_data.py | Component of feature |
| apps\realtime\agent.py | Component of feature |
| tests\integration\test_agent_coordinator.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\integration | Source directory |
| apps\realtime | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: AllyVisionAgent
- **Depends On / Used By:** Core Feature: create_agent_session
- **Depends On / Used By:** Core Feature: start_agent_session

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\integration\test_agent_coordinator.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Service/Agent: TestServiceMetrics
**Description:** Extracted service from code.
**Entry Point:** tests\integration\test_canary.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\integration\test_canary.py | Component of feature |
| scripts\canary_analysis.py | Component of feature |
| scripts\canary_deploy.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\integration | Source directory |
| scripts | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: ServiceMetrics

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\integration\test_canary.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Core Feature: test_pipeline_timeout_returns_partial
**Description:** Extracted core from code.
**Entry Point:** tests\integration\test_frame_spatial_integration.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| application\frame_processing\spatial_binding.py | Component of feature |
| tests\integration\test_frame_spatial_integration.py | Component of feature |
| application\frame_processing\frame_orchestrator.py | Component of feature |
| application\frame_processing\live_frame_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\integration | Source directory |
| application\frame_processing | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\integration\test_frame_spatial_integration.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Service/Agent: TestP1PipelineIntegration
**Description:** Extracted service from code.
**Entry Point:** tests\integration\test_p1_pipeline.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\embeddings.py | Component of feature |
| core\vqa\scene_graph.py | Component of feature |
| shared\schemas\__init__.py | Component of feature |
| tests\integration\test_p1_pipeline.py | Component of feature |
| core\memory\indexer.py | Component of feature |
| core\vision\spatial.py | Component of feature |
| core\memory\retriever.py | Component of feature |
| core\reasoning\engine.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\memory | Source directory |
| tests\integration | Source directory |
| core\reasoning | Source directory |
| core\vision | Source directory |
| core\vqa | Source directory |
| shared\schemas | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\integration\test_p1_pipeline.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Core Feature: test_full_pipeline_types
**Description:** Extracted core from code.
**Entry Point:** tests\integration\test_p1_pipeline.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\embeddings.py | Component of feature |
| core\vqa\scene_graph.py | Component of feature |
| shared\schemas\__init__.py | Component of feature |
| tests\integration\test_p1_pipeline.py | Component of feature |
| core\memory\indexer.py | Component of feature |
| core\vision\spatial.py | Component of feature |
| core\memory\retriever.py | Component of feature |
| core\reasoning\engine.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\memory | Source directory |
| tests\integration | Source directory |
| core\reasoning | Source directory |
| core\vision | Source directory |
| core\vqa | Source directory |
| shared\schemas | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\integration\test_p1_pipeline.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: test_pipeline_latency_under_500ms
**Description:** Extracted core from code.
**Entry Point:** tests\integration\test_p1_pipeline.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\embeddings.py | Component of feature |
| core\vqa\scene_graph.py | Component of feature |
| shared\schemas\__init__.py | Component of feature |
| tests\integration\test_p1_pipeline.py | Component of feature |
| core\memory\indexer.py | Component of feature |
| core\vision\spatial.py | Component of feature |
| core\memory\retriever.py | Component of feature |
| core\reasoning\engine.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\memory | Source directory |
| tests\integration | Source directory |
| core\reasoning | Source directory |
| core\vision | Source directory |
| core\vqa | Source directory |
| shared\schemas | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\integration\test_p1_pipeline.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Service/Agent: TestCDPipelineValidation
**Description:** Extracted service from code.
**Entry Point:** tests\integration\test_p5_cd_pipeline_validation.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\integration\test_p5_cd_pipeline_validation.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\integration | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\integration\test_p5_cd_pipeline_validation.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestCDPipelineIntegration
**Description:** Extracted service from code.
**Entry Point:** tests\integration\test_p5_cd_pipeline_validation.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\integration\test_p5_cd_pipeline_validation.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\integration | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\integration\test_p5_cd_pipeline_validation.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestCDPipelineReadinessReport
**Description:** Extracted service from code.
**Entry Point:** tests\integration\test_p5_cd_pipeline_validation.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\integration\test_p5_cd_pipeline_validation.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\integration | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\integration\test_p5_cd_pipeline_validation.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Core Feature: test_generate_pipeline_readiness_report
**Description:** Extracted core from code.
**Entry Point:** tests\integration\test_p5_cd_pipeline_validation.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\integration\test_p5_cd_pipeline_validation.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\integration | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\integration\test_p5_cd_pipeline_validation.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Service/Agent: TestActionPipelineIntegration
**Description:** Extracted service from code.
**Entry Point:** tests\integration\test_p6_integration.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\integration\test_p6_integration.py | Component of feature |
| core\action\action_context.py | Component of feature |
| core\reasoning\reasoning_foundation.py | Component of feature |
| core\reasoning\causal.py | Component of feature |
| core\vqa\multi_frame_vqa.py | Component of feature |
| core\reasoning\temporal.py | Component of feature |
| core\reasoning\spatial.py | Component of feature |
| core\audio\enhanced_detector.py | Component of feature |
| core\vqa\scene_narrator.py | Component of feature |
| core\reasoning\integration.py | Component of feature |
| core\action\clip_recognizer.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\integration | Source directory |
| core\audio | Source directory |
| core\reasoning | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\integration\test_p6_integration.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestAudioPipelineIntegration
**Description:** Extracted service from code.
**Entry Point:** tests\integration\test_p6_integration.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\integration\test_p6_integration.py | Component of feature |
| core\action\action_context.py | Component of feature |
| core\reasoning\reasoning_foundation.py | Component of feature |
| core\reasoning\causal.py | Component of feature |
| core\vqa\multi_frame_vqa.py | Component of feature |
| core\reasoning\temporal.py | Component of feature |
| core\reasoning\spatial.py | Component of feature |
| core\audio\enhanced_detector.py | Component of feature |
| core\vqa\scene_narrator.py | Component of feature |
| core\reasoning\integration.py | Component of feature |
| core\action\clip_recognizer.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\integration | Source directory |
| core\audio | Source directory |
| core\reasoning | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\integration\test_p6_integration.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestReasoningPipelineIntegration
**Description:** Extracted service from code.
**Entry Point:** tests\integration\test_p6_integration.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\integration\test_p6_integration.py | Component of feature |
| core\action\action_context.py | Component of feature |
| core\reasoning\reasoning_foundation.py | Component of feature |
| core\reasoning\causal.py | Component of feature |
| core\vqa\multi_frame_vqa.py | Component of feature |
| core\reasoning\temporal.py | Component of feature |
| core\reasoning\spatial.py | Component of feature |
| core\audio\enhanced_detector.py | Component of feature |
| core\vqa\scene_narrator.py | Component of feature |
| core\reasoning\integration.py | Component of feature |
| core\action\clip_recognizer.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\integration | Source directory |
| core\audio | Source directory |
| core\reasoning | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\integration\test_p6_integration.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestVQAPipelineIntegration
**Description:** Extracted service from code.
**Entry Point:** tests\integration\test_p6_integration.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\integration\test_p6_integration.py | Component of feature |
| core\action\action_context.py | Component of feature |
| core\reasoning\reasoning_foundation.py | Component of feature |
| core\reasoning\causal.py | Component of feature |
| core\vqa\multi_frame_vqa.py | Component of feature |
| core\reasoning\temporal.py | Component of feature |
| core\reasoning\spatial.py | Component of feature |
| core\audio\enhanced_detector.py | Component of feature |
| core\vqa\scene_narrator.py | Component of feature |
| core\reasoning\integration.py | Component of feature |
| core\action\clip_recognizer.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\integration | Source directory |
| core\audio | Source directory |
| core\reasoning | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\integration\test_p6_integration.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Core Feature: test_clip_to_context_pipeline
**Description:** Extracted core from code.
**Entry Point:** tests\integration\test_p6_integration.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\integration\test_p6_integration.py | Component of feature |
| core\action\action_context.py | Component of feature |
| core\reasoning\reasoning_foundation.py | Component of feature |
| core\reasoning\causal.py | Component of feature |
| core\vqa\multi_frame_vqa.py | Component of feature |
| core\reasoning\temporal.py | Component of feature |
| core\reasoning\spatial.py | Component of feature |
| core\audio\enhanced_detector.py | Component of feature |
| core\vqa\scene_narrator.py | Component of feature |
| core\reasoning\integration.py | Component of feature |
| core\action\clip_recognizer.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\integration | Source directory |
| core\audio | Source directory |
| core\reasoning | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\integration\test_p6_integration.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: test_action_pipeline_health
**Description:** Extracted core from code.
**Entry Point:** tests\integration\test_p6_integration.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\integration\test_p6_integration.py | Component of feature |
| core\action\action_context.py | Component of feature |
| core\reasoning\reasoning_foundation.py | Component of feature |
| core\reasoning\causal.py | Component of feature |
| core\vqa\multi_frame_vqa.py | Component of feature |
| core\reasoning\temporal.py | Component of feature |
| core\reasoning\spatial.py | Component of feature |
| core\audio\enhanced_detector.py | Component of feature |
| core\vqa\scene_narrator.py | Component of feature |
| core\reasoning\integration.py | Component of feature |
| core\action\clip_recognizer.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\integration | Source directory |
| core\audio | Source directory |
| core\reasoning | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\integration\test_p6_integration.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: test_detection_pipeline
**Description:** Extracted core from code.
**Entry Point:** tests\integration\test_p6_integration.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\integration\test_p6_integration.py | Component of feature |
| core\action\action_context.py | Component of feature |
| core\reasoning\reasoning_foundation.py | Component of feature |
| core\reasoning\causal.py | Component of feature |
| core\vqa\multi_frame_vqa.py | Component of feature |
| core\reasoning\temporal.py | Component of feature |
| core\reasoning\spatial.py | Component of feature |
| core\audio\enhanced_detector.py | Component of feature |
| core\vqa\scene_narrator.py | Component of feature |
| core\reasoning\integration.py | Component of feature |
| core\action\clip_recognizer.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\integration | Source directory |
| core\audio | Source directory |
| core\reasoning | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\integration\test_p6_integration.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: test_full_reasoning_pipeline
**Description:** Extracted core from code.
**Entry Point:** tests\integration\test_p6_integration.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\integration\test_p6_integration.py | Component of feature |
| core\action\action_context.py | Component of feature |
| core\reasoning\reasoning_foundation.py | Component of feature |
| core\reasoning\causal.py | Component of feature |
| core\vqa\multi_frame_vqa.py | Component of feature |
| core\reasoning\temporal.py | Component of feature |
| core\reasoning\spatial.py | Component of feature |
| core\audio\enhanced_detector.py | Component of feature |
| core\vqa\scene_narrator.py | Component of feature |
| core\reasoning\integration.py | Component of feature |
| core\action\clip_recognizer.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\integration | Source directory |
| core\audio | Source directory |
| core\reasoning | Source directory |
| core\vqa | Source directory |
| core\action | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\integration\test_p6_integration.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Service/Agent: TestVisionPipelineSmoke
**Description:** Extracted service from code.
**Entry Point:** tests\integration\test_smoke.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\__init__.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| core\speech\tts_handler.py | Component of feature |
| shared\schemas\__init__.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| core\speech\speech_handler.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\ocr\__init__.py | Component of feature |
| tests\smoke\test_smoke.py | Component of feature |
| tests\integration\test_smoke.py | Component of feature |
| core\vision\spatial.py | Component of feature |
| core\braille\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| core\qr | Source directory |
| tests\smoke | Source directory |
| tests\integration | Source directory |
| core\vision | Source directory |
| core\memory | Source directory |
| shared\config | Source directory |
| shared\schemas | Source directory |
| core\ocr | Source directory |
| core\speech | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: health
- **Depends On / Used By:** API Route: prometheus_metrics
- **Depends On / Used By:** API Route: debug_metrics
- **Depends On / Used By:** API Route: debug_perception_frame
- **Depends On / Used By:** API Route: list_sessions
- **Depends On / Used By:** API Route: get_session_logs
- **Depends On / Used By:** API Route: create_session
- **Depends On / Used By:** API Route: health_camera
- **Depends On / Used By:** API Route: health_orchestrator
- **Depends On / Used By:** API Route: health_workers
- **Depends On / Used By:** API Route: health_services
- **Depends On / Used By:** API Route: health_service_detail
- **Depends On / Used By:** API Route: debug_stale_check
- **Depends On / Used By:** API Route: debug_live_frames
- **Depends On / Used By:** API Route: debug_frame_rate
- **Depends On / Used By:** API Route: memory_delete_all
- **Depends On / Used By:** API Route: braille_read
- **Depends On / Used By:** API Route: debug_braille_frame
- **Depends On / Used By:** API Route: debug_ocr_install
- **Depends On / Used By:** API Route: debug_watchdog_status
- **Depends On / Used By:** API Route: debug_dependency_status
- **Depends On / Used By:** API Route: export_user_data
- **Depends On / Used By:** API Route: erase_all_user_data
- **Depends On / Used By:** API Route: face_health
- **Depends On / Used By:** API Route: face_consent_grant
- **Depends On / Used By:** API Route: face_consent_log
- **Depends On / Used By:** API Route: face_detect_with_consent
- **Depends On / Used By:** API Route: face_forget_all
- **Depends On / Used By:** API Route: audio_health
- **Depends On / Used By:** API Route: debug_ssl_frame
- **Depends On / Used By:** API Route: action_health
- **Depends On / Used By:** Service/Agent: OCRPipelineResult
- **Depends On / Used By:** Service/Agent: OCRPipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\integration\test_smoke.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestMemoryPipelineSmoke
**Description:** Extracted service from code.
**Entry Point:** tests\integration\test_smoke.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\__init__.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| core\speech\tts_handler.py | Component of feature |
| shared\schemas\__init__.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| core\speech\speech_handler.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\ocr\__init__.py | Component of feature |
| tests\smoke\test_smoke.py | Component of feature |
| tests\integration\test_smoke.py | Component of feature |
| core\vision\spatial.py | Component of feature |
| core\braille\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| core\qr | Source directory |
| tests\smoke | Source directory |
| tests\integration | Source directory |
| core\vision | Source directory |
| core\memory | Source directory |
| shared\config | Source directory |
| shared\schemas | Source directory |
| core\ocr | Source directory |
| core\speech | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: health
- **Depends On / Used By:** API Route: prometheus_metrics
- **Depends On / Used By:** API Route: debug_metrics
- **Depends On / Used By:** API Route: debug_perception_frame
- **Depends On / Used By:** API Route: list_sessions
- **Depends On / Used By:** API Route: get_session_logs
- **Depends On / Used By:** API Route: create_session
- **Depends On / Used By:** API Route: health_camera
- **Depends On / Used By:** API Route: health_orchestrator
- **Depends On / Used By:** API Route: health_workers
- **Depends On / Used By:** API Route: health_services
- **Depends On / Used By:** API Route: health_service_detail
- **Depends On / Used By:** API Route: debug_stale_check
- **Depends On / Used By:** API Route: debug_live_frames
- **Depends On / Used By:** API Route: debug_frame_rate
- **Depends On / Used By:** API Route: memory_delete_all
- **Depends On / Used By:** API Route: braille_read
- **Depends On / Used By:** API Route: debug_braille_frame
- **Depends On / Used By:** API Route: debug_ocr_install
- **Depends On / Used By:** API Route: debug_watchdog_status
- **Depends On / Used By:** API Route: debug_dependency_status
- **Depends On / Used By:** API Route: export_user_data
- **Depends On / Used By:** API Route: erase_all_user_data
- **Depends On / Used By:** API Route: face_health
- **Depends On / Used By:** API Route: face_consent_grant
- **Depends On / Used By:** API Route: face_consent_log
- **Depends On / Used By:** API Route: face_detect_with_consent
- **Depends On / Used By:** API Route: face_forget_all
- **Depends On / Used By:** API Route: audio_health
- **Depends On / Used By:** API Route: debug_ssl_frame
- **Depends On / Used By:** API Route: action_health
- **Depends On / Used By:** Service/Agent: OCRPipelineResult
- **Depends On / Used By:** Service/Agent: OCRPipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\integration\test_smoke.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestTTSPipelineSmoke
**Description:** Extracted service from code.
**Entry Point:** tests\integration\test_smoke.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\__init__.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| core\speech\tts_handler.py | Component of feature |
| shared\schemas\__init__.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| core\speech\speech_handler.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\ocr\__init__.py | Component of feature |
| tests\smoke\test_smoke.py | Component of feature |
| tests\integration\test_smoke.py | Component of feature |
| core\vision\spatial.py | Component of feature |
| core\braille\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| core\qr | Source directory |
| tests\smoke | Source directory |
| tests\integration | Source directory |
| core\vision | Source directory |
| core\memory | Source directory |
| shared\config | Source directory |
| shared\schemas | Source directory |
| core\ocr | Source directory |
| core\speech | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: health
- **Depends On / Used By:** API Route: prometheus_metrics
- **Depends On / Used By:** API Route: debug_metrics
- **Depends On / Used By:** API Route: debug_perception_frame
- **Depends On / Used By:** API Route: list_sessions
- **Depends On / Used By:** API Route: get_session_logs
- **Depends On / Used By:** API Route: create_session
- **Depends On / Used By:** API Route: health_camera
- **Depends On / Used By:** API Route: health_orchestrator
- **Depends On / Used By:** API Route: health_workers
- **Depends On / Used By:** API Route: health_services
- **Depends On / Used By:** API Route: health_service_detail
- **Depends On / Used By:** API Route: debug_stale_check
- **Depends On / Used By:** API Route: debug_live_frames
- **Depends On / Used By:** API Route: debug_frame_rate
- **Depends On / Used By:** API Route: memory_delete_all
- **Depends On / Used By:** API Route: braille_read
- **Depends On / Used By:** API Route: debug_braille_frame
- **Depends On / Used By:** API Route: debug_ocr_install
- **Depends On / Used By:** API Route: debug_watchdog_status
- **Depends On / Used By:** API Route: debug_dependency_status
- **Depends On / Used By:** API Route: export_user_data
- **Depends On / Used By:** API Route: erase_all_user_data
- **Depends On / Used By:** API Route: face_health
- **Depends On / Used By:** API Route: face_consent_grant
- **Depends On / Used By:** API Route: face_consent_log
- **Depends On / Used By:** API Route: face_detect_with_consent
- **Depends On / Used By:** API Route: face_forget_all
- **Depends On / Used By:** API Route: audio_health
- **Depends On / Used By:** API Route: debug_ssl_frame
- **Depends On / Used By:** API Route: action_health
- **Depends On / Used By:** Service/Agent: OCRPipelineResult
- **Depends On / Used By:** Service/Agent: OCRPipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\integration\test_smoke.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestSTTPipelineSmoke
**Description:** Extracted service from code.
**Entry Point:** tests\integration\test_smoke.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\__init__.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| core\speech\tts_handler.py | Component of feature |
| shared\schemas\__init__.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| core\speech\speech_handler.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\ocr\__init__.py | Component of feature |
| tests\smoke\test_smoke.py | Component of feature |
| tests\integration\test_smoke.py | Component of feature |
| core\vision\spatial.py | Component of feature |
| core\braille\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| core\qr | Source directory |
| tests\smoke | Source directory |
| tests\integration | Source directory |
| core\vision | Source directory |
| core\memory | Source directory |
| shared\config | Source directory |
| shared\schemas | Source directory |
| core\ocr | Source directory |
| core\speech | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: health
- **Depends On / Used By:** API Route: prometheus_metrics
- **Depends On / Used By:** API Route: debug_metrics
- **Depends On / Used By:** API Route: debug_perception_frame
- **Depends On / Used By:** API Route: list_sessions
- **Depends On / Used By:** API Route: get_session_logs
- **Depends On / Used By:** API Route: create_session
- **Depends On / Used By:** API Route: health_camera
- **Depends On / Used By:** API Route: health_orchestrator
- **Depends On / Used By:** API Route: health_workers
- **Depends On / Used By:** API Route: health_services
- **Depends On / Used By:** API Route: health_service_detail
- **Depends On / Used By:** API Route: debug_stale_check
- **Depends On / Used By:** API Route: debug_live_frames
- **Depends On / Used By:** API Route: debug_frame_rate
- **Depends On / Used By:** API Route: memory_delete_all
- **Depends On / Used By:** API Route: braille_read
- **Depends On / Used By:** API Route: debug_braille_frame
- **Depends On / Used By:** API Route: debug_ocr_install
- **Depends On / Used By:** API Route: debug_watchdog_status
- **Depends On / Used By:** API Route: debug_dependency_status
- **Depends On / Used By:** API Route: export_user_data
- **Depends On / Used By:** API Route: erase_all_user_data
- **Depends On / Used By:** API Route: face_health
- **Depends On / Used By:** API Route: face_consent_grant
- **Depends On / Used By:** API Route: face_consent_log
- **Depends On / Used By:** API Route: face_detect_with_consent
- **Depends On / Used By:** API Route: face_forget_all
- **Depends On / Used By:** API Route: audio_health
- **Depends On / Used By:** API Route: debug_ssl_frame
- **Depends On / Used By:** API Route: action_health
- **Depends On / Used By:** Service/Agent: OCRPipelineResult
- **Depends On / Used By:** Service/Agent: OCRPipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\integration\test_smoke.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestOCRPipelineSmoke
**Description:** Extracted service from code.
**Entry Point:** tests\integration\test_smoke.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\__init__.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| core\speech\tts_handler.py | Component of feature |
| shared\schemas\__init__.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| core\speech\speech_handler.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\ocr\__init__.py | Component of feature |
| tests\smoke\test_smoke.py | Component of feature |
| tests\integration\test_smoke.py | Component of feature |
| core\vision\spatial.py | Component of feature |
| core\braille\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| core\qr | Source directory |
| tests\smoke | Source directory |
| tests\integration | Source directory |
| core\vision | Source directory |
| core\memory | Source directory |
| shared\config | Source directory |
| shared\schemas | Source directory |
| core\ocr | Source directory |
| core\speech | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: health
- **Depends On / Used By:** API Route: prometheus_metrics
- **Depends On / Used By:** API Route: debug_metrics
- **Depends On / Used By:** API Route: debug_perception_frame
- **Depends On / Used By:** API Route: list_sessions
- **Depends On / Used By:** API Route: get_session_logs
- **Depends On / Used By:** API Route: create_session
- **Depends On / Used By:** API Route: health_camera
- **Depends On / Used By:** API Route: health_orchestrator
- **Depends On / Used By:** API Route: health_workers
- **Depends On / Used By:** API Route: health_services
- **Depends On / Used By:** API Route: health_service_detail
- **Depends On / Used By:** API Route: debug_stale_check
- **Depends On / Used By:** API Route: debug_live_frames
- **Depends On / Used By:** API Route: debug_frame_rate
- **Depends On / Used By:** API Route: memory_delete_all
- **Depends On / Used By:** API Route: braille_read
- **Depends On / Used By:** API Route: debug_braille_frame
- **Depends On / Used By:** API Route: debug_ocr_install
- **Depends On / Used By:** API Route: debug_watchdog_status
- **Depends On / Used By:** API Route: debug_dependency_status
- **Depends On / Used By:** API Route: export_user_data
- **Depends On / Used By:** API Route: erase_all_user_data
- **Depends On / Used By:** API Route: face_health
- **Depends On / Used By:** API Route: face_consent_grant
- **Depends On / Used By:** API Route: face_consent_log
- **Depends On / Used By:** API Route: face_detect_with_consent
- **Depends On / Used By:** API Route: face_forget_all
- **Depends On / Used By:** API Route: audio_health
- **Depends On / Used By:** API Route: debug_ssl_frame
- **Depends On / Used By:** API Route: action_health
- **Depends On / Used By:** Service/Agent: OCRPipelineResult
- **Depends On / Used By:** Service/Agent: OCRPipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\integration\test_smoke.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestBraillePipelineSmoke
**Description:** Extracted service from code.
**Entry Point:** tests\integration\test_smoke.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\__init__.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| core\speech\tts_handler.py | Component of feature |
| shared\schemas\__init__.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| core\speech\speech_handler.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\ocr\__init__.py | Component of feature |
| tests\smoke\test_smoke.py | Component of feature |
| tests\integration\test_smoke.py | Component of feature |
| core\vision\spatial.py | Component of feature |
| core\braille\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| core\qr | Source directory |
| tests\smoke | Source directory |
| tests\integration | Source directory |
| core\vision | Source directory |
| core\memory | Source directory |
| shared\config | Source directory |
| shared\schemas | Source directory |
| core\ocr | Source directory |
| core\speech | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: health
- **Depends On / Used By:** API Route: prometheus_metrics
- **Depends On / Used By:** API Route: debug_metrics
- **Depends On / Used By:** API Route: debug_perception_frame
- **Depends On / Used By:** API Route: list_sessions
- **Depends On / Used By:** API Route: get_session_logs
- **Depends On / Used By:** API Route: create_session
- **Depends On / Used By:** API Route: health_camera
- **Depends On / Used By:** API Route: health_orchestrator
- **Depends On / Used By:** API Route: health_workers
- **Depends On / Used By:** API Route: health_services
- **Depends On / Used By:** API Route: health_service_detail
- **Depends On / Used By:** API Route: debug_stale_check
- **Depends On / Used By:** API Route: debug_live_frames
- **Depends On / Used By:** API Route: debug_frame_rate
- **Depends On / Used By:** API Route: memory_delete_all
- **Depends On / Used By:** API Route: braille_read
- **Depends On / Used By:** API Route: debug_braille_frame
- **Depends On / Used By:** API Route: debug_ocr_install
- **Depends On / Used By:** API Route: debug_watchdog_status
- **Depends On / Used By:** API Route: debug_dependency_status
- **Depends On / Used By:** API Route: export_user_data
- **Depends On / Used By:** API Route: erase_all_user_data
- **Depends On / Used By:** API Route: face_health
- **Depends On / Used By:** API Route: face_consent_grant
- **Depends On / Used By:** API Route: face_consent_log
- **Depends On / Used By:** API Route: face_detect_with_consent
- **Depends On / Used By:** API Route: face_forget_all
- **Depends On / Used By:** API Route: audio_health
- **Depends On / Used By:** API Route: debug_ssl_frame
- **Depends On / Used By:** API Route: action_health
- **Depends On / Used By:** Service/Agent: OCRPipelineResult
- **Depends On / Used By:** Service/Agent: OCRPipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\integration\test_smoke.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Core Feature: test_pipeline_cancellation_is_fast
**Description:** Extracted core from code.
**Entry Point:** tests\integration\test_smoke.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\memory\__init__.py | Component of feature |
| shared\config\__init__.py | Component of feature |
| core\speech\tts_handler.py | Component of feature |
| shared\schemas\__init__.py | Component of feature |
| core\qr\__init__.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| core\speech\speech_handler.py | Component of feature |
| apps\api\server.py | Component of feature |
| core\ocr\__init__.py | Component of feature |
| tests\smoke\test_smoke.py | Component of feature |
| tests\integration\test_smoke.py | Component of feature |
| core\vision\spatial.py | Component of feature |
| core\braille\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| core\braille | Source directory |
| apps\api | Source directory |
| core\qr | Source directory |
| tests\smoke | Source directory |
| tests\integration | Source directory |
| core\vision | Source directory |
| core\memory | Source directory |
| shared\config | Source directory |
| shared\schemas | Source directory |
| core\ocr | Source directory |
| core\speech | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** API Route: health
- **Depends On / Used By:** API Route: prometheus_metrics
- **Depends On / Used By:** API Route: debug_metrics
- **Depends On / Used By:** API Route: debug_perception_frame
- **Depends On / Used By:** API Route: list_sessions
- **Depends On / Used By:** API Route: get_session_logs
- **Depends On / Used By:** API Route: create_session
- **Depends On / Used By:** API Route: health_camera
- **Depends On / Used By:** API Route: health_orchestrator
- **Depends On / Used By:** API Route: health_workers
- **Depends On / Used By:** API Route: health_services
- **Depends On / Used By:** API Route: health_service_detail
- **Depends On / Used By:** API Route: debug_stale_check
- **Depends On / Used By:** API Route: debug_live_frames
- **Depends On / Used By:** API Route: debug_frame_rate
- **Depends On / Used By:** API Route: memory_delete_all
- **Depends On / Used By:** API Route: braille_read
- **Depends On / Used By:** API Route: debug_braille_frame
- **Depends On / Used By:** API Route: debug_ocr_install
- **Depends On / Used By:** API Route: debug_watchdog_status
- **Depends On / Used By:** API Route: debug_dependency_status
- **Depends On / Used By:** API Route: export_user_data
- **Depends On / Used By:** API Route: erase_all_user_data
- **Depends On / Used By:** API Route: face_health
- **Depends On / Used By:** API Route: face_consent_grant
- **Depends On / Used By:** API Route: face_consent_log
- **Depends On / Used By:** API Route: face_detect_with_consent
- **Depends On / Used By:** API Route: face_forget_all
- **Depends On / Used By:** API Route: audio_health
- **Depends On / Used By:** API Route: debug_ssl_frame
- **Depends On / Used By:** API Route: action_health
- **Depends On / Used By:** Service/Agent: OCRPipelineResult
- **Depends On / Used By:** Service/Agent: OCRPipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\integration\test_smoke.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Service/Agent: TestSpatialPipeline
**Description:** Extracted service from code.
**Entry Point:** tests\integration\test_spatial_pipeline.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\integration\test_spatial_pipeline.py | Component of feature |
| shared\schemas\__init__.py | Component of feature |
| core\vision\spatial.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| shared\schemas | Source directory |
| core\vision | Source directory |
| tests\integration | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\integration\test_spatial_pipeline.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestAgentStartup
**Description:** Extracted service from code.
**Entry Point:** tests\performance\test_agent_startup.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\performance\test_agent_startup.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\performance | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\performance\test_agent_startup.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: MockE2EPipeline
**Description:** Extracted service from code.
**Entry Point:** tests\performance\test_e2e_latency.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\performance\test_e2e_latency.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\performance | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\performance\test_e2e_latency.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestMockE2EPipeline
**Description:** Extracted service from code.
**Entry Point:** tests\performance\test_e2e_latency.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\performance\test_e2e_latency.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\performance | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\performance\test_e2e_latency.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: MockFramePipeline
**Description:** Extracted service from code.
**Entry Point:** tests\performance\test_frame_processing.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\performance\test_frame_processing.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\performance | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\performance\test_frame_processing.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestMockFramePipeline
**Description:** Extracted service from code.
**Entry Point:** tests\performance\test_frame_processing.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\performance\test_frame_processing.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\performance | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\performance\test_frame_processing.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestPipelineInstrumentation
**Description:** Extracted service from code.
**Entry Point:** tests\performance\test_frame_processing.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\performance\test_frame_processing.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\performance | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\performance\test_frame_processing.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Core Feature: test_pipeline_parallel_execution
**Description:** Extracted core from code.
**Entry Point:** tests\performance\test_frame_processing.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\performance\test_frame_processing.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\performance | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\performance\test_frame_processing.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: test_pipeline_within_budget
**Description:** Extracted core from code.
**Entry Point:** tests\performance\test_frame_processing.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\performance\test_frame_processing.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\performance | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\performance\test_frame_processing.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: test_pipeline_average_metrics
**Description:** Extracted core from code.
**Entry Point:** tests\performance\test_frame_processing.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\performance\test_frame_processing.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\performance | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\performance\test_frame_processing.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: test_pipeline_component_calls
**Description:** Extracted core from code.
**Entry Point:** tests\performance\test_frame_processing.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\performance\test_frame_processing.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\performance | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\performance\test_frame_processing.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: test_pipeline_breakdown_accuracy
**Description:** Extracted core from code.
**Entry Point:** tests\performance\test_frame_processing.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\performance\test_frame_processing.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\performance | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\performance\test_frame_processing.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: test_optimized_pipeline_meets_budget
**Description:** Extracted core from code.
**Entry Point:** tests\performance\test_frame_processing.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\performance\test_frame_processing.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\performance | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\performance\test_frame_processing.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Service/Agent: TestPipelineProfilerIntegration
**Description:** Extracted service from code.
**Entry Point:** tests\performance\test_hot_path_profiling.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| scripts\profile_hot_path.py | Component of feature |
| shared\utils\timing.py | Component of feature |
| tests\performance\test_hot_path_profiling.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| shared\utils | Source directory |
| tests\performance | Source directory |
| scripts | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: PipelineProfiler

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\performance\test_hot_path_profiling.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Core Feature: test_all_new_modules_have_agents_md
**Description:** Extracted core from code.
**Entry Point:** tests\performance\test_p1_architecture.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\performance\test_p1_architecture.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\performance | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\performance\test_p1_architecture.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Service/Agent: TestFlappingServices
**Description:** Extracted service from code.
**Entry Point:** tests\performance\test_resilience_stress.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| infrastructure\speech\tts_failover.py | Component of feature |
| infrastructure\resilience\circuit_breaker.py | Component of feature |
| infrastructure\speech\stt_failover.py | Component of feature |
| tests\performance\test_resilience_stress.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| infrastructure\resilience\degradation_coordinator.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| infrastructure\resilience | Source directory |
| infrastructure\speech | Source directory |
| tests\performance | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\performance\test_resilience_stress.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Core Feature: test_pipeline_timeout_enforced
**Description:** Extracted core from code.
**Entry Point:** tests\performance\test_resource_threshold.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\performance\test_resource_threshold.py | Component of feature |
| shared\config\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| shared\config | Source directory |
| tests\performance | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\performance\test_resource_threshold.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: test_vision_pipeline_compliant
**Description:** Extracted core from code.
**Entry Point:** tests\performance\test_sla_compliance.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\performance\test_sla_compliance.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\performance | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\performance\test_sla_compliance.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: test_application_pipelines_is_hot
**Description:** Extracted core from code.
**Entry Point:** tests\unit\test_async_audit.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\unit\test_async_audit.py | Component of feature |
| scripts\async_audit.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\unit | Source directory |
| scripts | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_async_audit.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Service/Agent: TestAgentModulesDocumented
**Description:** Extracted service from code.
**Entry Point:** tests\unit\test_docs_accuracy.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\unit\test_docs_accuracy.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\unit | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_docs_accuracy.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Core Feature: test_agents_md_exists
**Description:** Extracted core from code.
**Entry Point:** tests\unit\test_docs_accuracy.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\unit\test_docs_accuracy.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\unit | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_docs_accuracy.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: test_each_module_mentioned_in_agents_md
**Description:** Extracted core from code.
**Entry Point:** tests\unit\test_docs_accuracy.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\unit\test_docs_accuracy.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\unit | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_docs_accuracy.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: test_no_phantom_modules_in_agents_md
**Description:** Extracted core from code.
**Entry Point:** tests\unit\test_docs_accuracy.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\unit\test_docs_accuracy.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\unit | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_docs_accuracy.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: test_agents_md_not_outdated_god_file_reference
**Description:** Extracted core from code.
**Entry Point:** tests\unit\test_docs_accuracy.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\unit\test_docs_accuracy.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\unit | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_docs_accuracy.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Service/Agent: TestServiceStatus
**Description:** Extracted service from code.
**Entry Point:** tests\unit\test_health_registry.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\unit\test_health_registry.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| infrastructure\resilience\circuit_breaker.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| infrastructure\resilience | Source directory |
| tests\unit | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_health_registry.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestServiceHealth
**Description:** Extracted service from code.
**Entry Point:** tests\unit\test_health_registry.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\unit\test_health_registry.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| infrastructure\resilience\circuit_breaker.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| infrastructure\resilience | Source directory |
| tests\unit | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_health_registry.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestServiceHealthRegistryInitialization
**Description:** Extracted service from code.
**Entry Point:** tests\unit\test_health_registry.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\unit\test_health_registry.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| infrastructure\resilience\circuit_breaker.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| infrastructure\resilience | Source directory |
| tests\unit | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_health_registry.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestServiceHealthRegistryQueries
**Description:** Extracted service from code.
**Entry Point:** tests\unit\test_health_registry.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\unit\test_health_registry.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| infrastructure\resilience\circuit_breaker.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| infrastructure\resilience | Source directory |
| tests\unit | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_health_registry.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestServiceHealthRegistrySummary
**Description:** Extracted service from code.
**Entry Point:** tests\unit\test_health_registry.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\unit\test_health_registry.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| infrastructure\resilience\circuit_breaker.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| infrastructure\resilience | Source directory |
| tests\unit | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_health_registry.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestServiceHealthRegistryDegradation
**Description:** Extracted service from code.
**Entry Point:** tests\unit\test_health_registry.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\unit\test_health_registry.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| infrastructure\resilience\circuit_breaker.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| infrastructure\resilience | Source directory |
| tests\unit | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_health_registry.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestServiceHealthRegistryHealthScore
**Description:** Extracted service from code.
**Entry Point:** tests\unit\test_health_registry.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\unit\test_health_registry.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| infrastructure\resilience\circuit_breaker.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| infrastructure\resilience | Source directory |
| tests\unit | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_health_registry.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestServiceHealthRegistryServiceManagement
**Description:** Extracted service from code.
**Entry Point:** tests\unit\test_health_registry.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\unit\test_health_registry.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| infrastructure\resilience\circuit_breaker.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| infrastructure\resilience | Source directory |
| tests\unit | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_health_registry.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestServiceHealthRegistryHealth
**Description:** Extracted service from code.
**Entry Point:** tests\unit\test_health_registry.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\unit\test_health_registry.py | Component of feature |
| infrastructure\resilience\health_registry.py | Component of feature |
| infrastructure\resilience\circuit_breaker.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| infrastructure\resilience | Source directory |
| tests\unit | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: ServiceStatus
- **Depends On / Used By:** Service/Agent: ServiceHealth
- **Depends On / Used By:** Service/Agent: ServiceHealthRegistry

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_health_registry.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestPipelineStageMetrics
**Description:** Extracted service from code.
**Entry Point:** tests\unit\test_metrics_instrumentation.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| infrastructure\monitoring\instrumentation.py | Component of feature |
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| tests\unit\test_metrics_instrumentation.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| infrastructure\monitoring | Source directory |
| tests\unit | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: PipelineStageMetrics
- **Depends On / Used By:** Service/Agent: ServiceName

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_metrics_instrumentation.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestPipelineSpecificDecorators
**Description:** Extracted service from code.
**Entry Point:** tests\unit\test_metrics_instrumentation.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| infrastructure\monitoring\instrumentation.py | Component of feature |
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| tests\unit\test_metrics_instrumentation.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| infrastructure\monitoring | Source directory |
| tests\unit | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: PipelineStageMetrics
- **Depends On / Used By:** Service/Agent: ServiceName

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_metrics_instrumentation.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestOCRPipelineFallback
**Description:** Extracted service from code.
**Entry Point:** tests\unit\test_ocr_engine_fallbacks.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| shared\schemas\__init__.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| tests\unit\test_ocr_engine_fallbacks.py | Component of feature |
| core\ocr\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| shared\schemas | Source directory |
| tests\unit | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: OCRPipelineResult
- **Depends On / Used By:** Service/Agent: OCRPipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_ocr_engine_fallbacks.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Core Feature: test_pipeline_is_ready_attribute
**Description:** Extracted core from code.
**Entry Point:** tests\unit\test_ocr_engine_fallbacks.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| shared\schemas\__init__.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| tests\unit\test_ocr_engine_fallbacks.py | Component of feature |
| core\ocr\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| shared\schemas | Source directory |
| tests\unit | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: OCRPipelineResult
- **Depends On / Used By:** Service/Agent: OCRPipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_ocr_engine_fallbacks.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: test_pipeline_process_no_crash
**Description:** Extracted core from code.
**Entry Point:** tests\unit\test_ocr_engine_fallbacks.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| shared\schemas\__init__.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| tests\unit\test_ocr_engine_fallbacks.py | Component of feature |
| core\ocr\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| shared\schemas | Source directory |
| tests\unit | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: OCRPipelineResult
- **Depends On / Used By:** Service/Agent: OCRPipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_ocr_engine_fallbacks.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: test_ocr_pipeline_no_backend_returns_error
**Description:** Extracted core from code.
**Entry Point:** tests\unit\test_ocr_install_error.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\unit\test_ocr_install_error.py | Component of feature |
| shared\schemas\__init__.py | Component of feature |
| core\ocr\engine.py | Component of feature |
| core\ocr\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| shared\schemas | Source directory |
| tests\unit | Source directory |
| core\ocr | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: OCRPipelineResult
- **Depends On / Used By:** Service/Agent: OCRPipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_ocr_install_error.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Service/Agent: TestPerceptionPipelineExtended
**Description:** Extracted service from code.
**Entry Point:** tests\unit\test_perception.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\unit\test_perception.py | Component of feature |
| core\vqa\perception.py | Component of feature |
| shared\schemas\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| shared\schemas | Source directory |
| tests\unit | Source directory |
| core\vqa | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: PerceptionPipeline
- **Depends On / Used By:** Core Feature: create_pipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_perception.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Core Feature: test_pipeline_returns_result
**Description:** Extracted core from code.
**Entry Point:** tests\unit\test_perception.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\unit\test_perception.py | Component of feature |
| core\vqa\perception.py | Component of feature |
| shared\schemas\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| shared\schemas | Source directory |
| tests\unit | Source directory |
| core\vqa | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: PerceptionPipeline
- **Depends On / Used By:** Core Feature: create_pipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_perception.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: test_pipeline_includes_timestamp
**Description:** Extracted core from code.
**Entry Point:** tests\unit\test_perception.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\unit\test_perception.py | Component of feature |
| core\vqa\perception.py | Component of feature |
| shared\schemas\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| shared\schemas | Source directory |
| tests\unit | Source directory |
| core\vqa | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: PerceptionPipeline
- **Depends On / Used By:** Core Feature: create_pipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_perception.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: test_pipeline_image_size
**Description:** Extracted core from code.
**Entry Point:** tests\unit\test_perception.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\unit\test_perception.py | Component of feature |
| core\vqa\perception.py | Component of feature |
| shared\schemas\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| shared\schemas | Source directory |
| tests\unit | Source directory |
| core\vqa | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: PerceptionPipeline
- **Depends On / Used By:** Core Feature: create_pipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_perception.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: test_pipeline_latency_under_threshold
**Description:** Extracted core from code.
**Entry Point:** tests\unit\test_perception.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\unit\test_perception.py | Component of feature |
| core\vqa\perception.py | Component of feature |
| shared\schemas\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| shared\schemas | Source directory |
| tests\unit | Source directory |
| core\vqa | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: PerceptionPipeline
- **Depends On / Used By:** Core Feature: create_pipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_perception.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: test_pipeline_handles_numpy_input
**Description:** Extracted core from code.
**Entry Point:** tests\unit\test_perception.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\unit\test_perception.py | Component of feature |
| core\vqa\perception.py | Component of feature |
| shared\schemas\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| shared\schemas | Source directory |
| tests\unit | Source directory |
| core\vqa | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: PerceptionPipeline
- **Depends On / Used By:** Core Feature: create_pipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_perception.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: test_create_pipeline_factory
**Description:** Extracted core from code.
**Entry Point:** tests\unit\test_perception.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\unit\test_perception.py | Component of feature |
| core\vqa\perception.py | Component of feature |
| shared\schemas\__init__.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| shared\schemas | Source directory |
| tests\unit | Source directory |
| core\vqa | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: PerceptionPipeline
- **Depends On / Used By:** Core Feature: create_pipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_perception.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Service/Agent: TestPipelineMonitorEdgeCases
**Description:** Extracted service from code.
**Entry Point:** tests\unit\test_pipeline_edge_cases.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| application\pipelines\perception_pool.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| application\pipelines\frame_sampler.py | Component of feature |
| tests\unit\test_pipeline_edge_cases.py | Component of feature |
| application\pipelines\integration.py | Component of feature |
| application\pipelines\cancellation.py | Component of feature |
| application\pipelines\pipeline_monitor.py | Component of feature |
| application\pipelines\debouncer.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\unit | Source directory |
| application\pipelines | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: PipelineMonitor
- **Depends On / Used By:** Service/Agent: PipelineComponents
- **Depends On / Used By:** Core Feature: create_pipeline_components
- **Depends On / Used By:** Core Feature: wrap_entrypoint_with_pipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_pipeline_edge_cases.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestPipelineIntegrationEntry
**Description:** Extracted service from code.
**Entry Point:** tests\unit\test_pipeline_edge_cases.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| application\pipelines\perception_pool.py | Component of feature |
| application\pipelines\watchdog.py | Component of feature |
| application\pipelines\frame_sampler.py | Component of feature |
| tests\unit\test_pipeline_edge_cases.py | Component of feature |
| application\pipelines\integration.py | Component of feature |
| application\pipelines\cancellation.py | Component of feature |
| application\pipelines\pipeline_monitor.py | Component of feature |
| application\pipelines\debouncer.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\unit | Source directory |
| application\pipelines | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: PipelineMonitor
- **Depends On / Used By:** Service/Agent: PipelineComponents
- **Depends On / Used By:** Core Feature: create_pipeline_components
- **Depends On / Used By:** Core Feature: wrap_entrypoint_with_pipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_pipeline_edge_cases.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestServiceName
**Description:** Extracted service from code.
**Entry Point:** tests\unit\test_prometheus_metrics.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| tests\unit\test_prometheus_metrics.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| infrastructure\monitoring | Source directory |
| tests\unit | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: ServiceName

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_prometheus_metrics.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestSpeechPipelineMetrics
**Description:** Extracted service from code.
**Entry Point:** tests\unit\test_prometheus_metrics.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| infrastructure\monitoring\prometheus_metrics.py | Component of feature |
| tests\unit\test_prometheus_metrics.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| infrastructure\monitoring | Source directory |
| tests\unit | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: ServiceName

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_prometheus_metrics.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestServiceConfigs
**Description:** Extracted service from code.
**Entry Point:** tests\unit\test_retry_policy.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\unit\test_retry_policy.py | Component of feature |
| infrastructure\resilience\circuit_breaker.py | Component of feature |
| infrastructure\resilience\retry_policy.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| infrastructure\resilience | Source directory |
| tests\unit | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_retry_policy.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestServiceRetryConfigs
**Description:** Extracted service from code.
**Entry Point:** tests\unit\test_retry_service_wiring.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| infrastructure\resilience\circuit_breaker.py | Component of feature |
| infrastructure\speech\elevenlabs\tts_manager.py | Component of feature |
| tests\unit\test_retry_service_wiring.py | Component of feature |
| infrastructure\llm\internet_search.py | Component of feature |
| infrastructure\tavus\adapter.py | Component of feature |
| infrastructure\llm\ollama\handler.py | Component of feature |
| infrastructure\resilience\retry_policy.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| infrastructure\speech\elevenlabs | Source directory |
| infrastructure\resilience | Source directory |
| tests\unit | Source directory |
| infrastructure\llm | Source directory |
| infrastructure\tavus | Source directory |
| infrastructure\llm\ollama | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_retry_service_wiring.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestCreateAgentSession
**Description:** Extracted service from code.
**Entry Point:** tests\unit\test_session_manager.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| apps\realtime\__init__.py | Component of feature |
| tests\unit\test_session_manager.py | Component of feature |
| apps\realtime\session_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\unit | Source directory |
| apps\realtime | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Core Feature: create_agent_session
- **Depends On / Used By:** Core Feature: start_agent_session

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_session_manager.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestStartAgentSession
**Description:** Extracted service from code.
**Entry Point:** tests\unit\test_session_manager.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| apps\realtime\__init__.py | Component of feature |
| tests\unit\test_session_manager.py | Component of feature |
| apps\realtime\session_manager.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\unit | Source directory |
| apps\realtime | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Core Feature: create_agent_session
- **Depends On / Used By:** Core Feature: start_agent_session

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_session_manager.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Service/Agent: TestAgentLOCCompliance
**Description:** Extracted service from code.
**Entry Point:** tests\unit\test_tech_debt_checks.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\unit\test_tech_debt_checks.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\unit | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_tech_debt_checks.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Core Feature: test_agent_under_500_loc
**Description:** Extracted core from code.
**Entry Point:** tests\unit\test_tech_debt_checks.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| tests\unit\test_tech_debt_checks.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\unit | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- None mapped

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_tech_debt_checks.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Service/Agent: TestVoiceAskPipelineEdgeCases
**Description:** Extracted service from code.
**Entry Point:** tests\unit\test_tts_stt_edge_cases.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\speech\voice_router.py | Component of feature |
| core\speech\tts_handler.py | Component of feature |
| core\speech\speech_handler.py | Component of feature |
| core\speech\voice_ask_pipeline.py | Component of feature |
| tests\unit\test_tts_stt_edge_cases.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\unit | Source directory |
| core\speech | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: VoiceAskPipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_tts_stt_edge_cases.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: service

---
## Core Feature: test_pipeline_import
**Description:** Extracted core from code.
**Entry Point:** tests\unit\test_tts_stt_edge_cases.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\speech\voice_router.py | Component of feature |
| core\speech\tts_handler.py | Component of feature |
| core\speech\speech_handler.py | Component of feature |
| core\speech\voice_ask_pipeline.py | Component of feature |
| tests\unit\test_tts_stt_edge_cases.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\unit | Source directory |
| core\speech | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: VoiceAskPipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_tts_stt_edge_cases.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: test_pipeline_with_mocked_dependencies
**Description:** Extracted core from code.
**Entry Point:** tests\unit\test_tts_stt_edge_cases.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\speech\voice_router.py | Component of feature |
| core\speech\tts_handler.py | Component of feature |
| core\speech\speech_handler.py | Component of feature |
| core\speech\voice_ask_pipeline.py | Component of feature |
| tests\unit\test_tts_stt_edge_cases.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\unit | Source directory |
| core\speech | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: VoiceAskPipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_tts_stt_edge_cases.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Core Feature: test_pipeline_stt_failure_is_handled
**Description:** Extracted core from code.
**Entry Point:** tests\unit\test_tts_stt_edge_cases.py
**Status:** Active

### Files
| File Path | Role |
|-----------|------|
| core\speech\voice_router.py | Component of feature |
| core\speech\tts_handler.py | Component of feature |
| core\speech\speech_handler.py | Component of feature |
| core\speech\voice_ask_pipeline.py | Component of feature |
| tests\unit\test_tts_stt_edge_cases.py | Component of feature |

### Folders
| Folder Path | Role |
|-------------|------|
| tests\unit | Source directory |
| core\speech | Source directory |

### Dependencies
- **Models/Schemas:** None explicitly mapped
- **Shared Services:** None explicitly mapped
- **External APIs:** None explicitly mapped
- **Environment Variables:** None explicitly mapped
- **Config Keys:** None explicitly mapped

### Connected Features
- **Depends On / Used By:** Service/Agent: VoiceAskPipeline

### Debug Entry Points
> When debugging this feature, start here:
- Primary: tests\unit\test_tts_stt_edge_cases.py — Entry Point

### Code Insights
> Key implementation details found by reading the actual source:
- Type: core

---
## Orphaned Files/Folders
> These files have no identified feature ownership or are not referenced by any feature.

- feature_mapper.py
- generate_agents.py
- get_dirs.py
- application\__init__.py
- application\frame_processing\__init__.py
- application\pipelines\audio_manager.py
- application\pipelines\streaming_tts.py
- application\pipelines\__init__.py
- apps\__init__.py
- apps\api\__init__.py
- apps\cli\visualizer.py
- apps\realtime\entrypoint.py
- core\__init__.py
- core\braille\braille_capture.py
- core\braille\braille_ocr.py
- core\braille\embossing_guidance.py
- core\face\consent_audit.py
- core\qr\ar_tag_handler.py
- core\reasoning\__init__.py
- core\vqa\api_schema.py
- core\vqa\memory.py
- core\vqa\priority_scene.py
- infrastructure\__init__.py
- infrastructure\llm\__init__.py
- infrastructure\llm\embeddings\__init__.py
- infrastructure\llm\ollama\__init__.py
- infrastructure\llm\siliconflow\__init__.py
- infrastructure\resilience\__init__.py
- infrastructure\speech\deepgram\__init__.py
- infrastructure\speech\elevenlabs\__init__.py
- infrastructure\storage\__init__.py
- infrastructure\tavus\__init__.py
- Papers\_generate_docx.py
- research\benchmarks\benchmark_realtime.py
- research\experiments\harness.py
- research\experiments\scenario_generator.py
- research\experiments\__init__.py
- scripts\canary_promote.py
- scripts\check_deps.py
- scripts\generate_release_notes.py
- scripts\generate_sbom.py
- scripts\generate_scenarios.py
- scripts\run_chaos.py
- scripts\run_smoke.py
- scripts\validate_env.py
- scripts\verify_hybrid_memory.py
- shared\logging_config.py
- shared\config\environment.py
- shared\debug\session_logger.py
- shared\debug\visualizer.py
- shared\logging\__init__.py
- shared\utils\helpers.py
- shared\utils\__init__.py
- tests\conftest.py
- tests\test_action_engine.py
- tests\test_audio_engine.py
- tests\test_confidence_cascade.py
- tests\test_debug_visualizer.py
- tests\test_encryption.py
- tests\test_face_engine.py
- tests\test_generated_scenarios.py
- tests\test_live_pipeline.py
- tests\test_memory_extensions.py
- tests\test_perception_telemetry.py
- tests\test_priority_scene.py
- tests\test_session_logger.py
- tests\test_shared_types.py
- tests\test_startup_guards.py
- tests\test_tavus_adapter.py
- tests\test_tts_manager.py
- tests\__init__.py
- tests\chaos\__init__.py
- tests\fixtures\generate_braille_fixtures.py
- tests\fixtures\__init__.py
- tests\integration\test_deepgram.py
- tests\integration\test_failover_scenarios.py
- tests\integration\test_memory_hybrid.py
- tests\integration\test_memory_search.py
- tests\integration\test_p0_security_smoke.py
- tests\integration\test_p5_monitoring_integration.py
- tests\integration\test_p5_runbook_execution.py
- tests\integration\test_p6_cloud_validation.py
- tests\integration\test_qr_flow.py
- tests\integration\test_rag_reasoner.py
- tests\integration\test_rag_reasoner_claude.py
- tests\integration\test_siliconflow.py
- tests\integration\test_vqa_api.py
- tests\integration\__init__.py
- tests\load\conftest.py
- tests\load\test_concurrent_users.py
- tests\load\test_load_infrastructure.py
- tests\performance\conftest.py
- tests\performance\test_access_control_fuzz.py
- tests\performance\test_async_verification.py
- tests\performance\test_baseline_capture.py
- tests\performance\test_benchmark_report.py
- tests\performance\test_consent_enforcement.py
- tests\performance\test_debug_access_control.py
- tests\performance\test_deterministic_replay.py
- tests\performance\test_docker_hardening.py
- tests\performance\test_embedding_optimization.py
- tests\performance\test_encryption_at_rest.py
- tests\performance\test_faiss_performance.py
- tests\performance\test_faiss_scaling.py
- tests\performance\test_graceful_degradation.py
- tests\performance\test_instrumentation.py
- tests\performance\test_latency_sla.py
- tests\performance\test_llm_latency.py
- tests\performance\test_load_50_users.py
- tests\performance\test_memory_leak.py
- tests\performance\test_midas_latency.py
- tests\performance\test_model_checksums.py
- tests\performance\test_model_download_retry.py
- tests\performance\test_offline_behavior.py
- tests\performance\test_p0_baseline.py
- tests\performance\test_p1_validation.py
- tests\performance\test_p3_exit_criteria.py
- tests\performance\test_p4_exit_criteria.py
- tests\performance\test_pii_scrubbing.py
- tests\performance\test_quantization.py
- tests\performance\test_regression.py
- tests\performance\test_resource_monitoring.py
- tests\performance\test_secrets_scan.py
- tests\performance\test_speech_latency.py
- tests\performance\test_sustained_fps.py
- tests\performance\test_telemetry_optin.py
- tests\performance\test_vram_profiling.py
- tests\performance\test_yolo_latency.py
- tests\performance\__init__.py
- tests\realtime\benchmark.py
- tests\realtime\calibrate_depth.py
- tests\realtime\metrics.py
- tests\realtime\realtime_test.py
- tests\realtime\replay_tool.py
- tests\realtime\session_logger.py
- tests\realtime\__init__.py
- tests\smoke\__init__.py
- tests\unit\test_action_context.py
- tests\unit\test_action_recognition_edge_cases.py
- tests\unit\test_async_blocking_regression.py
- tests\unit\test_audio_events_edge_cases.py
- tests\unit\test_backup_scheduler.py
- tests\unit\test_braille_classifier.py
- tests\unit\test_braille_segmenter.py
- tests\unit\test_cache_manager.py
- tests\unit\test_circuit_breaker.py
- tests\unit\test_clip_recognizer.py
- tests\unit\test_cloud_sync.py
- tests\unit\test_cloud_sync_architecture.py
- tests\unit\test_cloud_sync_edge_cases.py
- tests\unit\test_config_docs.py
- tests\unit\test_conflict_resolver.py
- tests\unit\test_debug_endpoints.py
- tests\unit\test_deepgram_circuit_breaker.py
- tests\unit\test_degradation_coordinator.py
- tests\unit\test_duckduckgo_circuit_breaker.py
- tests\unit\test_edge_tts_fallback.py
- tests\unit\test_elevenlabs_circuit_breaker.py
- tests\unit\test_embeddings.py
- tests\unit\test_embeddings_async.py
- tests\unit\test_embedding_async.py
- tests\unit\test_enhanced_audio.py
- tests\unit\test_error_classifier.py
- tests\unit\test_event_bus.py
- tests\unit\test_face_consent.py
- tests\unit\test_face_engine_edge_cases.py
- tests\unit\test_face_tracker.py
- tests\unit\test_faiss_backup.py
- tests\unit\test_faiss_sync.py
- tests\unit\test_import_boundaries.py
- tests\unit\test_indexer_persistence.py
- tests\unit\test_ingest_hardening.py
- tests\unit\test_livekit_circuit_breaker.py
- tests\unit\test_llm_client_async.py
- tests\unit\test_logging_correlation.py
- tests\unit\test_memory_ingest.py
- tests\unit\test_metrics_collector.py
- tests\unit\test_midas_depth.py
- tests\unit\test_nav_formatter.py
- tests\unit\test_offline_queue.py
- tests\unit\test_ollama_circuit_breaker.py
- tests\unit\test_pii_scrubber.py
- tests\unit\test_privacy_controls.py
- tests\unit\test_qr_decoder.py
- tests\unit\test_qr_scanner.py
- tests\unit\test_rag_reasoner_claude.py
- tests\unit\test_reasoning_edge_cases.py
- tests\unit\test_reasoning_engine.py
- tests\unit\test_reasoning_suite.py
- tests\unit\test_resilience_config.py
- tests\unit\test_retriever_mvp.py
- tests\unit\test_scene_graph.py
- tests\unit\test_secret_provider.py
- tests\unit\test_security_tools.py
- tests\unit\test_segmentation.py
- tests\unit\test_session_management.py
- tests\unit\test_shared_reexports.py
- tests\unit\test_spatial_edge_cases.py
- tests\unit\test_sqlite_backup.py
- tests\unit\test_sqlite_sync.py
- tests\unit\test_storage_adapter.py
- tests\unit\test_stt_failover.py
- tests\unit\test_tavus_circuit_breaker.py
- tests\unit\test_timeout_config.py
- tests\unit\test_tool_router.py
- tests\unit\test_tts_failover.py
- tests\unit\test_vision_controller.py
- tests\unit\test_voice_controller.py
- tests\unit\test_vqa_features.py
- tests\unit\test_vqa_reasoner.py
- tests\unit\test_whisper_stt.py
- tests\unit\test_yolo_detector.py
- tests\unit\__init__.py
