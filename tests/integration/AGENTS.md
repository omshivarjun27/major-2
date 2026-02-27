Purpose: Document integration test strategy for tests/integration/.
This directory hosts 7 test files for cross-module workflow validation.

Components: Cross-module test cases and harnesses.
- test_workflow_api_login.py
- test_workflow_memory_sync.py
- test_workflow_vqa_pipeline.py
- test_workflow_session_flow.py
- test_workflow_event_bus_http.py
- test_workflow_error_handling.py
- test_workflow_performance.py

Dependencies: pytest, test harness fixtures; environment controls.

Tasks: None implemented yet; placeholder for future integration tests.

Design: End-to-end validation across layers; mock external services.

Research: Review existing integration patterns; establish stable data contracts.

Risk: Stub status; potential flakiness if mocks diverge from reality.

Improvements: Centralized test doubles; deterministic timing.

Change Log:
2026-02-23: Created initial AGENTS.md stub for tests/integration.
