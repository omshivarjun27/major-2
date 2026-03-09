#!/usr/bin/env bash
# failures/reproduce_all.sh — Reproduce all failing tests
# Run from repo root: bash failures/reproduce_all.sh
set -e
PYTHON=".venv/Scripts/python.exe"

echo "=== FAILURE F001: test_debug_endpoints (ModuleNotFoundError: api_server) ==="
$PYTHON -m pytest tests/unit/test_debug_endpoints.py -v --tb=short 2>&1 | tail -10

echo "=== FAILURE F002: test_health_registry (asyncio.get_event_loop RuntimeError) ==="
$PYTHON -m pytest "tests/unit/test_health_registry.py::TestServiceHealthRegistryQueries::test_get_service_health_open_circuit" -v --tb=short 2>&1 | tail -15

echo "=== FAILURE F003: test_pipeline_edge_cases (Debouncer API mismatch) ==="
$PYTHON -m pytest "tests/unit/test_pipeline_edge_cases.py::TestDebouncerEdgeCases::test_first_cue_always_passes" -v --tb=short 2>&1 | tail -10

echo "=== FAILURE F004: test_spatial_edge_cases (DepthMap/Direction schema mismatch) ==="
$PYTHON -m pytest "tests/unit/test_spatial_edge_cases.py::TestDepthMapEdgeCases::test_single_pixel_depth_map" -v --tb=short 2>&1 | tail -10

echo "=== FAILURE F005: test_tts_failover (timing too tight) ==="
$PYTHON -m pytest "tests/unit/test_tts_failover.py::TestFailoverStatistics::test_record_failback" -v --tb=short 2>&1 | tail -10

echo "=== FAILURE F006: test_tts_stt_edge_cases (IntentType.VISUAL missing) ==="
$PYTHON -m pytest "tests/unit/test_tts_stt_edge_cases.py::TestVoiceRouterEdgeCases::test_intent_type_enum_values" -v --tb=short 2>&1 | tail -10

echo "=== FAILURE F007: test_ocr (hangs — easyocr eager import on Windows) ==="
echo "Running with 60s timeout..."
$PYTHON -m pytest tests/unit/test_ocr_engine_fallbacks.py --timeout=60 -v --tb=short 2>&1 | tail -15

echo "=== FAILURE F008: test_config_docs (undocumented env vars) ==="
$PYTHON -m pytest "tests/unit/test_config_docs.py::TestConfigDocumentation::test_all_config_keys_documented" -v --tb=short 2>&1 | tail -15
