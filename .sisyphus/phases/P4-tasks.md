# Phase 4: Performance & Validation

> **Phase Focus**: Vision pipeline profiling and optimization, YOLO INT8 quantization, MiDaS depth tuning, SLA enforcement, FAISS scaling, RAG query optimization, VRAM budgeting, hot-path benchmarking, Locust load testing, memory leak detection, CPU optimization, TTS/STT latency tuning, regression suite, and integration closeouts for SLA validation under load and VRAM budget verification.
> **Task Count**: 18 (T-073 through T-090)
> **Risk Classification**: HIGH for quantization, SLA enforcement, VRAM optimization, and integration closeouts. MEDIUM for profiling, benchmarking, and speech optimizations.
> **Priority Unlock**: T-073 Vision Pipeline Profiling, T-077 FAISS Index Scaling, T-080 VRAM Profiler (three independent entry points)

---

## T-073: vision-pipeline-profiling

- **Phase**: P4
- **Cluster**: CL-VIS
- **Objective**: Profile the complete vision pipeline (YOLO detection, segmentation, MiDaS depth, spatial fusion) to establish per-stage latency baselines. Use `cProfile` and `torch.cuda.Event` for GPU timing. Produce a flame graph and a stage-by-stage latency breakdown. Identify the top 3 bottlenecks. The vision pipeline must complete within 300ms total. Document baseline numbers for comparison after optimization tasks.
- **Upstream Deps**: []
- **Downstream Impact**: [`T-074`, `T-075`, `T-076`, `T-089`]
- **Risk Tier**: Medium
- **Test Layers**: [Benchmark]
- **Doc Mutation Map**: [`core/vision/AGENTS.md`, `docs/baselines/p4_vision_profile.json`, `AGENTS.md#performance-assumptions`]
- **Versioning Impact**: none
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: yes, profiling only, no code changes
- **Execution Environment**: Local GPU
- **Current State**: not_started

---

## T-074: yolo-int8-quantization

- **Phase**: P4
- **Cluster**: CL-VIS
- **Objective**: Quantize YOLO v8n model from FP32 to INT8 using ONNX Runtime quantization tools. Calibrate quantization using a representative dataset of 100 indoor scene images. Measure accuracy degradation (target: mAP drop < 2%). Measure inference speedup (target: >= 30% faster). Measure VRAM reduction (target: >= 40% smaller model). Produce quantized model at `models/yolov8n_int8.onnx`. Update model loader to auto-select INT8 when available.
- **Upstream Deps**: [`T-073`]
- **Downstream Impact**: [`T-076`, `T-089`]
- **Risk Tier**: High
- **Test Layers**: [Unit, Benchmark, Regression]
- **Doc Mutation Map**: [`core/vision/AGENTS.md`, `AGENTS.md#performance-assumptions`, `docs/models.md#quantization`]
- **Versioning Impact**: minor
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, depends on profiling baseline
- **Execution Environment**: Local GPU
- **Current State**: not_started

---

## T-075: midas-optimization

- **Phase**: P4
- **Cluster**: CL-VIS
- **Objective**: Optimize MiDaS depth estimation for the 300ms vision pipeline budget. Evaluate model variants (MiDaS small vs DPT-Hybrid vs ZoeDepth-NK) for speed-accuracy tradeoff. Implement resolution downscaling (640 to 320px input) with bilinear upscaling of depth output. Add frame-skip logic: reuse previous depth map if camera motion is below threshold. Target MiDaS stage completing in under 80ms.
- **Upstream Deps**: [`T-073`]
- **Downstream Impact**: [`T-076`, `T-089`]
- **Risk Tier**: High
- **Test Layers**: [Unit, Benchmark, Regression]
- **Doc Mutation Map**: [`core/vision/AGENTS.md`, `AGENTS.md#performance-assumptions`, `docs/models.md#depth-estimation`]
- **Versioning Impact**: minor
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: yes, independent from YOLO quantization
- **Execution Environment**: Local GPU
- **Current State**: not_started

---

## T-076: vision-pipeline-sla-enforcement

- **Phase**: P4
- **Cluster**: CL-VIS
- **Objective**: Enforce the 300ms vision pipeline SLA with a hard timeout wrapper. Implement `application/frame_processing/sla_enforcer.py` that aborts pipeline stages exceeding their time budget (detection: 100ms, segmentation: 50ms, depth: 80ms, fusion: 50ms, overhead: 20ms). When a stage times out, return partial results from completed stages rather than failing entirely. Add pipeline latency histogram for monitoring. Log SLA violations with stage name and actual duration.
- **Upstream Deps**: [`T-074`, `T-075`]
- **Downstream Impact**: [`T-082`, `T-089`]
- **Risk Tier**: High
- **Test Layers**: [Unit, Integration, Benchmark]
- **Doc Mutation Map**: [`application/frame_processing/AGENTS.md`, `AGENTS.md#latency-slas`, `docs/architecture.md#sla-enforcement`]
- **Versioning Impact**: minor
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, needs optimized models
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-077: faiss-index-scaling

- **Phase**: P4
- **Cluster**: CL-MEM
- **Objective**: Validate and optimize FAISS index performance beyond 5,000 vectors. Benchmark query latency at 1K, 5K, 10K, and 50K vector counts. Evaluate index types: Flat (exact), IVF (approximate), HNSW (graph-based). Select optimal index type for the 50ms query latency SLA. Implement index type auto-selection based on vector count thresholds. Add index compaction/rebuild scheduler for maintenance.
- **Upstream Deps**: []
- **Downstream Impact**: [`T-079`, `T-089`]
- **Risk Tier**: High
- **Test Layers**: [Unit, Benchmark]
- **Doc Mutation Map**: [`core/memory/AGENTS.md`, `AGENTS.md#performance-assumptions`, `docs/memory.md#faiss-scaling`]
- **Versioning Impact**: minor
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: yes, memory subsystem independent of vision
- **Execution Environment**: Local GPU
- **Current State**: not_started

---

## T-078: embedding-batch-optimization

- **Phase**: P4
- **Cluster**: CL-MEM
- **Objective**: Optimize Ollama embedding calls by implementing batch processing. Instead of single-vector embedding requests, batch up to 32 texts per API call. Implement `core/memory/batch_embedder.py` with configurable batch size, flush timeout (100ms), and queue management. Measure latency improvement: target 5x throughput increase for bulk ingestion. Ensure real-time single-query latency remains under 50ms by bypassing batching for interactive requests.
- **Upstream Deps**: []
- **Downstream Impact**: [`T-079`, `T-089`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration, Benchmark]
- **Doc Mutation Map**: [`core/memory/AGENTS.md`, `docs/memory.md#embedding-optimization`]
- **Versioning Impact**: minor
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: yes, independent optimization
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-079: rag-query-latency-optimization

- **Phase**: P4
- **Cluster**: CL-MEM
- **Objective**: Optimize the end-to-end RAG query pipeline (embed query, FAISS search, retrieve context, LLM reasoning) to complete within 200ms for interactive queries. Profile each stage. Implement result caching for repeated queries (LRU cache with 5-minute TTL). Add pre-computation of frequently accessed embeddings. Reduce context window size for LLM calls when full context exceeds token budget.
- **Upstream Deps**: [`T-077`, `T-078`]
- **Downstream Impact**: [`T-089`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration, Benchmark]
- **Doc Mutation Map**: [`core/memory/AGENTS.md`, `docs/memory.md#rag-optimization`, `AGENTS.md#latency-slas`]
- **Versioning Impact**: patch
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: no, depends on FAISS and embedding optimizations
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-080: vram-profiler

- **Phase**: P4
- **Cluster**: CL-TQA
- **Objective**: Build a VRAM profiling tool that measures GPU memory usage across all model loads. Create `tests/performance/vram_profiler.py` that tracks: YOLO model (FP32 vs INT8), MiDaS model, Whisper fallback model (when loaded), embedding model, and peak combined usage. Produce a VRAM budget report showing per-model allocation and total peak. Target: peak VRAM <= 3.5GB on RTX 4060 (leaving headroom for CUDA context and OS).
- **Upstream Deps**: []
- **Downstream Impact**: [`T-081`, `T-089`, `T-090`]
- **Risk Tier**: Medium
- **Test Layers**: [Benchmark]
- **Doc Mutation Map**: [`tests/performance/AGENTS.md`, `docs/baselines/p4_vram_budget.json`, `AGENTS.md#performance-assumptions`]
- **Versioning Impact**: none
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: yes, profiling tool independent of optimizations
- **Execution Environment**: Local GPU
- **Current State**: not_started

---

## T-081: vram-optimization

- **Phase**: P4
- **Cluster**: CL-TQA
- **Objective**: Optimize VRAM usage based on profiler results from T-080. Implement model unloading for inactive models (e.g., unload Whisper when Deepgram circuit is closed). Add CUDA memory pool management with explicit `torch.cuda.empty_cache()` calls between model switches. Implement gradient-free inference mode (`torch.no_grad()`) consistently across all model calls. Target: reduce peak VRAM by 20% vs baseline measurement.
- **Upstream Deps**: [`T-080`]
- **Downstream Impact**: [`T-089`, `T-090`]
- **Risk Tier**: High
- **Test Layers**: [Unit, Benchmark, Regression]
- **Doc Mutation Map**: [`core/vision/AGENTS.md`, `core/speech/AGENTS.md`, `AGENTS.md#performance-assumptions`]
- **Versioning Impact**: patch
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, depends on profiler results
- **Execution Environment**: Local GPU
- **Current State**: not_started

---

## T-082: hot-path-end-to-end-benchmark

- **Phase**: P4
- **Cluster**: CL-TQA
- **Objective**: Create a comprehensive end-to-end hot path benchmark that measures total latency from voice input to voice output. Instrument all pipeline stages: STT (target 100ms), VQA/reasoning (target 300ms), TTS (target 100ms), totaling 500ms. Create `tests/performance/hot_path_benchmark.py` with statistical analysis: P50, P95, P99 latencies over 100 iterations. Test with realistic audio samples and camera frames. Fail if P95 exceeds 500ms.
- **Upstream Deps**: [`T-076`]
- **Downstream Impact**: [`T-083`, `T-089`]
- **Risk Tier**: High
- **Test Layers**: [Benchmark, System]
- **Doc Mutation Map**: [`tests/performance/AGENTS.md`, `docs/baselines/p4_hot_path.json`, `AGENTS.md#latency-slas`]
- **Versioning Impact**: none
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, needs SLA enforcement in place
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-083: locust-load-testing

- **Phase**: P4
- **Cluster**: CL-TQA
- **Objective**: Set up Locust load testing infrastructure for the REST API and WebRTC agent. Create `tests/performance/locustfile.py` with user scenarios: visual query (upload image + get description), text query (ask question + get answer), memory query (RAG retrieval). Configure for 10 concurrent users with 1-second ramp-up. Measure: requests/second, P50/P95/P99 latency, error rate, CPU/memory usage. Fail if P95 > 500ms or error rate > 1% at 10 concurrent users.
- **Upstream Deps**: [`T-082`]
- **Downstream Impact**: [`T-089`]
- **Risk Tier**: High
- **Test Layers**: [Benchmark, System]
- **Doc Mutation Map**: [`tests/performance/AGENTS.md`, `AGENTS.md#performance-assumptions`, `docs/testing.md#load-testing`]
- **Versioning Impact**: none
- **Governance Level**: elevated
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: no, needs hot path benchmark passing first
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-084: memory-leak-detection

- **Phase**: P4
- **Cluster**: CL-TQA
- **Objective**: Implement memory leak detection for long-running operation. Create `tests/performance/memory_leak_test.py` that runs the system under continuous load for 1 hour, sampling RSS and VRAM every 30 seconds. Use tracemalloc for Python heap tracking. Detect leaks using linear regression on memory samples: fail if slope > 1MB/hour for RSS or 0.5MB/hour for VRAM. Test both the REST API server and the WebRTC agent separately.
- **Upstream Deps**: []
- **Downstream Impact**: [`T-089`]
- **Risk Tier**: Medium
- **Test Layers**: [Benchmark, Regression]
- **Doc Mutation Map**: [`tests/performance/AGENTS.md`, `docs/baselines/p4_memory_stability.json`]
- **Versioning Impact**: none
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: yes, independent long-running test
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-085: cpu-utilization-optimization

- **Phase**: P4
- **Cluster**: CL-TQA
- **Objective**: Profile and optimize CPU utilization under peak load. Target: CPU < 80% at 10 concurrent users. Profile async task scheduling to identify event loop blocking. Move CPU-intensive operations (image preprocessing, FAISS search, audio resampling) to thread pool executors via `asyncio.run_in_executor()`. Implement process affinity for model inference threads. Measure and log CPU utilization per core during load tests.
- **Upstream Deps**: [`T-083`]
- **Downstream Impact**: [`T-089`]
- **Risk Tier**: Medium
- **Test Layers**: [Benchmark, Regression]
- **Doc Mutation Map**: [`AGENTS.md#performance-assumptions`, `docs/baselines/p4_cpu_profile.json`]
- **Versioning Impact**: patch
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: no, needs load test infrastructure
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-086: tts-latency-optimization

- **Phase**: P4
- **Cluster**: CL-TQA
- **Objective**: Optimize TTS latency to meet the 100ms target. Profile ElevenLabs API call chain: connection setup, request serialization, streaming response handling. Implement response streaming so the first audio chunk starts playing before the full response arrives. Add pre-warming of TTS connections at session start. Cache frequently used phrases (greetings, error messages) for zero-latency playback. Measure TTFB (time to first byte) vs full response time.
- **Upstream Deps**: []
- **Downstream Impact**: [`T-089`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Benchmark]
- **Doc Mutation Map**: [`core/speech/AGENTS.md`, `infrastructure/speech/AGENTS.md`, `AGENTS.md#latency-slas`]
- **Versioning Impact**: patch
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: yes, speech optimization independent of vision
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-087: stt-latency-optimization

- **Phase**: P4
- **Cluster**: CL-TQA
- **Objective**: Optimize STT latency to meet the 100ms target. Profile Deepgram real-time streaming: WebSocket connection overhead, audio chunk size, interim vs final result timing. Optimize audio chunk size for balance between latency and accuracy (target: 100ms chunks). Implement voice activity detection (VAD) to skip silence periods. Pre-establish WebSocket connection at session start to eliminate cold-start overhead.
- **Upstream Deps**: []
- **Downstream Impact**: [`T-089`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Benchmark]
- **Doc Mutation Map**: [`core/speech/AGENTS.md`, `infrastructure/speech/AGENTS.md`, `AGENTS.md#latency-slas`]
- **Versioning Impact**: patch
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: yes, speech optimization independent of vision
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-088: performance-regression-suite

- **Phase**: P4
- **Cluster**: CL-TQA
- **Objective**: Create a performance regression test suite that runs automatically in CI. Create `tests/performance/test_regression.py` with benchmark assertions: vision pipeline < 300ms, RAG query < 200ms, hot path < 500ms, VRAM < 3.5GB. Store baseline numbers in `docs/baselines/p4_regression_baselines.json`. Tests compare current run against baselines with 10% tolerance. Fail CI if any metric regresses beyond tolerance. Add `@pytest.mark.slow` marker for optional exclusion in fast CI runs.
- **Upstream Deps**: [`T-082`, `T-079`]
- **Downstream Impact**: [`T-089`]
- **Risk Tier**: Medium
- **Test Layers**: [Benchmark, Regression]
- **Doc Mutation Map**: [`tests/performance/AGENTS.md`, `docs/baselines/p4_regression_baselines.json`, `.github/workflows/ci.yml`]
- **Versioning Impact**: none
- **Governance Level**: standard
- **Regression Sensitivity**: low
- **Parallelization Eligible**: no, needs benchmarks established
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-089: p4-sla-validation-under-load

- **Phase**: P4
- **Cluster**: CL-TQA
- **Objective**: Integration closeout task. Run the Locust load test at 10 concurrent users and verify all SLA targets hold simultaneously: 500ms hot-path P95, 300ms vision pipeline P95, 200ms RAG query P95, 100ms STT P95, 100ms TTS P95. Run for 30 minutes continuous. Produce a comprehensive performance report with charts showing latency distribution, throughput curve, and resource utilization over time. Fail if any SLA is violated at the target concurrency.
- **Upstream Deps**: [`T-083`, `T-085`, `T-088`]
- **Downstream Impact**: [`T-090`]
- **Risk Tier**: High
- **Test Layers**: [Integration, Benchmark, System, Regression]
- **Doc Mutation Map**: [`tests/integration/AGENTS.md`, `docs/baselines/p4_sla_report.json`, `AGENTS.md#documentation-coverage`]
- **Versioning Impact**: none
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, final integration validation
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-090: p4-vram-budget-verification

- **Phase**: P4
- **Cluster**: CL-OPS
- **Objective**: Integration closeout task. Run the VRAM profiler with ALL models loaded simultaneously (YOLO INT8, MiDaS, Whisper fallback, embedding model) and verify peak VRAM <= 3.5GB on RTX 4060. Test model hot-swapping scenarios (load Whisper during Deepgram failure, then unload). Verify no CUDA OOM errors occur during 1-hour stress test. Produce a final VRAM budget allocation document showing per-model usage and remaining headroom.
- **Upstream Deps**: [`T-081`, `T-089`]
- **Downstream Impact**: []
- **Risk Tier**: High
- **Test Layers**: [Benchmark, Regression]
- **Doc Mutation Map**: [`docs/baselines/p4_vram_budget.json`, `AGENTS.md#performance-assumptions`, `AGENTS.md#documentation-coverage`]
- **Versioning Impact**: none
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, final phase verification
- **Execution Environment**: Local GPU
- **Current State**: not_started

---

## Phase Exit Criteria

1. All tasks in this phase have `current_state: completed`
2. Zero failing tests across all `test_layers` specified by tasks in this phase
3. Every entry in every task's `doc_mutation_map` has been verified as updated
4. No unresolved `blocked` tasks remain
5. Regression suite shows no coverage drop compared to phase entry baseline
6. 500ms hot-path SLA validated under 10 concurrent users (P95)
7. VRAM usage <= 3.5GB on RTX 4060 with all models loaded
8. CPU utilization < 80% under peak load
9. No memory leaks detected in 1-hour continuous operation test
10. Vision pipeline completing within 300ms (P95)

## Downstream Notes

- P5 monitoring will consume latency histograms and VRAM metrics from P4 benchmarks
- P5 alert thresholds will be based on the SLA baselines established in P4
- P6 feature additions must not regress any P4 performance baselines (enforced by regression suite)
- P7 load test at 50 concurrent users builds on top of P4's 10-user infrastructure
- VRAM headroom of ~2.5GB (3.5GB used of 6GB) allows P6 features some GPU budget
