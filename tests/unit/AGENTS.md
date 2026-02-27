Purpose: Document unit testing approach for tests/unit/.
This directory hosts 12 unit test files using pytest with async support.

Components: Test modules per core unit; placeholder references.
- test_core_vision.py
- test_core_memory.py
- test_core_ocr.py
- test_core_vqa.py
- test_core_speech.py
- test_core_audio.py
- test_infrastructure_llm.py
- test_infrastructure_storage.py

Dependencies: pytest, pytest-asyncio, and per-test fixtures defined in conftest.py.

Tasks: None implemented yet; reserved for future unit tests.

Design: Tests should be async-friendly; use pytest.mark.asyncio where needed.
The tests should validate inputs, outputs, and boundary conditions.

Research: Review existing test patterns in repository; align with 5-layer architecture.

Risk: Stub status present; low immediate risk; future tests may require maintenance.

Improvements: Add fixtures for core components; centralize mocks.

Change Log: 
2026-02-23: Created initial AGENTS.md stub for tests/unit.
