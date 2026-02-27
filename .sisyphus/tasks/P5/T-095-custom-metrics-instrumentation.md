# T-095: Custom Metrics Instrumentation

## Metadata
- **Phase**: P5
- **Cluster**: CL-OPS
- **Risk Tier**: Low
- **Upstream Deps**: [T-091]
- **Downstream Impact**: [T-108]
- **Current State**: completed

## Objective

Add custom Prometheus metrics instrumentation across all major components. Instrument:
- Vision pipeline (per-stage timing)
- RAG pipeline (embed/search/reason timing)
- Speech pipeline (STT/TTS timing)
- Circuit breakers (state transitions, recovery time)
- FAISS index (query count, vector count)
- WebRTC agent (session count, reconnections)

Use decorators and context managers for minimal code intrusion. Target: every SLA-relevant operation is measurable.

## Acceptance Criteria

1. ✅ Decorators for pipeline stage instrumentation
2. ✅ Context managers for timing operations
3. ✅ FAISS metrics tracker with query/vector counts
4. ✅ Circuit breaker metrics tracker with state transitions
5. ✅ WebRTC session tracker
6. ✅ Speech pipeline timing helpers (STT, TTS, LLM)
7. ✅ Graceful failure handling (metrics errors don't crash app)
8. ✅ Unit tests verify all instrumentation (41 tests)

## Implementation Notes

Created `infrastructure/monitoring/instrumentation.py` with:
- `VisionStage`, `RAGStage`, `SpeechStage` enums for type-safe stage names
- `timed_stage()` / `async_timed_stage()` context managers
- `@instrument_stage`, `@instrument_vision`, `@instrument_rag`, `@instrument_speech` decorators
- `FAISSMetricsTracker` class for FAISS operations
- `CircuitBreakerMetricsTracker` class for circuit breaker state
- `WebRTCMetricsTracker` class for WebRTC sessions
- `record_stt_latency`, `record_tts_latency`, `record_llm_latency` helpers
- `timed_stt`, `timed_tts`, `timed_llm` context managers
- Global singleton getters: `get_webrtc_tracker()`, `get_faiss_tracker()`, `get_circuit_breaker_tracker()`

## Test Requirements

- ✅ Unit: tests/unit/test_metrics_instrumentation.py with 41 tests
