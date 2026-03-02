# T-147: Smoke Test Suite

**Status**: not_started
**Priority**: P7 — Testing
**Created**: 2026-03-02

## Summary
Create post-deployment smoke test suite covering health endpoints, WebRTC connect, TTS output, STT input, vision pipeline, memory queries, and QR scan. Each test completes in <30s.

## Deliverables
- `tests/smoke/` directory with smoke test suite
- Smoke test runner script (`scripts/run_smoke.py`)
- CI/CD integration for post-deployment smoke testing
- Smoke test report template

## Acceptance Criteria
- [ ] Health endpoint smoke test verifies API availability
- [ ] WebRTC connection smoke test validates LiveKit connectivity
- [ ] TTS output smoke test confirms audio generation
- [ ] STT input smoke test confirms speech recognition
- [ ] Vision pipeline smoke test validates frame processing
- [ ] Memory query smoke test confirms RAG pipeline
- [ ] QR scan smoke test validates QR detection
- [ ] Each individual smoke test completes in < 30 seconds
