Purpose: Document live pipeline tests for tests/realtime/.
This directory contains 5 test files for live pipeline harness; hardware required.

Components: Real-time components and test harness.
- agent_stress_test.py
- frame_latency_test.py
- voice_sync_test.py
- streaming_quality_test.py
- end_to_end_realtime_test.py

Dependencies: pytest, async test harness; hardware prerequisites.

Tasks: None implemented yet; reserved for hardware-driven tests.

Design: Tests assume camera/audio input; rely on LiveKit/WebRTC stack if enabled.

Research: Consider deterministic synthetic feeds if hardware unavailable.

Risk: Stub status; hardware variability may cause flaky tests.

Improvements: Provide mocks for non-hardware portions; document test environment.

Change Log:
2026-02-23: Created initial AGENTS.md stub for tests/realtime.
