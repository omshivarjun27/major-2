# T-075: locust-load-test-setup

> Phase: P4 | Cluster: CL-TQA | Risk: Medium | State: completed | created_at: 2026-02-27T20:00:00Z

## Objective

Set up Locust load testing infrastructure to validate system performance under concurrent user load. Create load test scenarios that simulate realistic usage patterns for the voice/vision assistant. Target: 10 simultaneous users on RTX 4060 hardware while maintaining <500ms hot path latency.

## Implementation Plan

1. Add `locust` to `requirements-extras.txt` as dev dependency.
2. Create `tests/load/` directory for load test files.
3. Implement `tests/load/locustfile.py` with user behavior scenarios:
   - `VoiceUser`: Simulates voice interaction (STT → LLM → TTS)
   - `VisionUser`: Simulates vision queries (image → VQA → TTS)
   - `MixedUser`: Combination of voice and vision
4. Create helper fixtures for test audio and images.
5. Configure Locust for headless CI execution.
6. Document load test execution procedures.

## Files to Create

| File | Purpose |
|------|---------|
| `tests/load/locustfile.py` | Main Locust test file |
| `tests/load/conftest.py` | Load test fixtures |
| `tests/load/README.md` | Load testing documentation |
| `scripts/run_load_test.sh` | Load test runner script |

## Acceptance Criteria

- [ ] Locust installed and configured
- [ ] VoiceUser, VisionUser, and MixedUser scenarios implemented
- [ ] Test fixtures for audio/image data available
- [ ] Headless execution works for CI integration
- [ ] Documentation covers local and CI execution
- [ ] Baseline load test runs successfully with 1 user

## Upstream Dependencies

T-073 (baseline capture)

## Downstream Unblocks

T-076 (concurrent user validation)

## Estimated Scope

Medium. Load test infrastructure, ~250-300 lines of code.
