---
title: "Testing Strategy"
version: 1.0.0
date: 2026-02-22T18:00:00Z
architecture_mode: hybrid_cloud_local_gpu
---

# Testing Strategy

This document defines the comprehensive testing strategy for the Voice & Vision Assistant for Blind. It covers unit testing, integration testing, GPU stress testing, cloud timeout simulation, and performance benchmarks. All strategies are aligned with the existing test infrastructure (pytest, async auto mode, 429+ existing tests) and the hybrid cloud/local GPU architecture.

---

## 1. Unit Testing Strategy

### 1.1 Framework and Configuration

- **Framework**: pytest with `asyncio_mode = auto` (configured in `pyproject.toml`).
- **Coverage Tool**: `pytest-cov` (installed). Coverage CI command: `pytest tests/ --cov=. --cov-report=xml --timeout=180`.
- **Timeout**: `pytest-timeout` is configured in `pyproject.toml` but not currently installed (BACKLOG-021). Install to enforce 60s per-test timeout for unit tests.
- **Test Location**: `tests/unit/` — currently 12 test files with 143 passing, 1 failing, 13 errors.

### 1.2 Coverage Targets

| Metric | Target | Rationale |
|--------|:------:|-----------|
| Overall unit coverage | ≥80% | Industry standard for reliability-critical applications |
| Critical path coverage | 100% | Perception pipeline, memory store/query, QR scan, consent gates |
| Domain layer (`core/`) | ≥85% | Core business logic must be thoroughly tested |
| Application layer | ≥75% | Orchestration logic with mock dependencies |
| Shared layer | ≥90% | Cross-cutting utilities used by all layers |

### 1.3 Mocking Strategy

- **External dependencies**: All cloud services (qwen3.5:cloud, Deepgram, ElevenLabs, LiveKit, DuckDuckGo) must be mocked in unit tests.
- **GPU models**: Use mock detectors (`MockObjectDetector`), mock depth estimators (`SimpleDepthEstimator`), and mock embedders to avoid GPU dependency in unit tests.
- **File I/O**: Use `tmp_path` fixtures for FAISS index, QR cache, and consent file operations.
- **Pattern**: Define mock objects locally in test files (e.g., `MockDetector`, `MockSegmenter`, `MockEmbedder`).

### 1.4 Execution Commands

```bash
# Run all unit tests
pytest tests/unit/ -v --tb=short -q --timeout=60

# Run a single test file
pytest tests/unit/test_perception.py -v

# Run a single test class
pytest tests/unit/test_perception.py::TestPerceptionPipeline -v

# Run tests matching a keyword
pytest tests/unit/ -k "test_memory" -v

# Run with coverage
pytest tests/unit/ --cov=core --cov=application --cov=shared --cov-report=term-missing --timeout=60
```

### 1.5 Known Issues

- **13 broken tests** in `tests/unit/test_debug_endpoints.py` due to stale import path (`ModuleNotFoundError: No module named 'api_server'`). Tracked as BACKLOG-014 (P3).
- **1 test failure** in `tests/unit/test_cache_manager.py::TestCacheManager::test_history` due to history ordering assertion mismatch.

---

## 2. Integration Testing

### 2.1 Scope

Integration tests verify cross-module data flows without mocking internal boundaries. External cloud services are still mocked, but module-to-module interactions are tested with real implementations.

### 2.2 Test Markers

```python
@pytest.mark.integration
```

Tests are executed separately: `pytest tests/integration/ -v --tb=short -q --timeout=120`

### 2.3 Key Integration Flows

| Flow | Modules Under Test | Description |
|------|-------------------|-------------|
| Memory ingest → search → query | MemoryIngester → OllamaEmbedder → FAISSIndexer → MemoryRetriever → RAGReasoner | Full RAG pipeline with mock LLM and mock embedder |
| Perception → scene graph → VQA | PerceptionPipeline → SceneGraphBuilder → SpatialFuser → VQAReasoner | Visual pipeline with mock detector and mock LLM |
| QR scan → classify → cache | QRScanner → QRDecoder → CacheManager | QR pipeline with synthetic QR images |
| Frame → orchestrator → workers | LiveFrameManager → FrameOrchestrator → PerceptionWorkerPool | Frame processing pipeline with mock GPU models |
| Voice → route → respond | VoiceRouter → intent handler → LLMClient | Voice intent routing with mock STT output |
| Consent → gate → store | ConsentManager → MemoryIngester → FAISSIndexer | Consent enforcement across memory operations |

### 2.4 Test Data

- **Test images**: Synthetic numpy arrays with known object placements for deterministic detection results.
- **Test transcripts**: Predefined text strings for memory ingestion.
- **Test QR codes**: Generated QR images with known payloads (URL, contact, location, transport).
- **Test embeddings**: Fixed 384-dimensional vectors for FAISS indexing.

### 2.5 Current State

- `tests/integration/` contains 7 test files.
- Integration tests use the `@pytest.mark.integration` marker.
- External cloud services are mocked at the infrastructure layer boundary.

---

## 3. GPU Stress Testing

### 3.1 Objective

Verify system stability under concurrent GPU workloads and validate VRAM budget adherence on the target RTX 4060 (8GB VRAM).

### 3.2 Test Scenarios

| Scenario | Configuration | Expected Behavior |
|----------|--------------|-------------------|
| Concurrent perception pipeline runs | 4 simultaneous `/debug/perception` requests with `SPATIAL_USE_YOLO=true`, `SPATIAL_USE_MIDAS=true` | All complete within 4x single-request time. No OOM. |
| Peak VRAM utilization | All GPU models active: YOLO (~200MB) + MiDaS (~100MB) + EasyOCR (~500MB) + qwen3-embedding:4b (~2GB) + Face (~300MB) | Peak VRAM ≤3.5GB. 60% headroom maintained. |
| VRAM monitoring validation | Submit requests while monitoring `torch.cuda.memory_allocated()` | Reported values match expected per-model allocations. |
| OOM recovery | Artificially constrain VRAM and trigger OOM condition | System falls back to CPU inference. Process does not crash. Error logged at WARNING level. |
| CPU fallback under CUDA error | Set `CUDA_VISIBLE_DEVICES=""` to disable GPU | All models automatically degrade to CPU. Perception results are valid (slower). |

### 3.3 Execution

```bash
# GPU stress tests (require GPU hardware)
pytest tests/performance/ -k "gpu" -v --timeout=300

# With YOLO and MiDaS active
SPATIAL_USE_YOLO=true SPATIAL_USE_MIDAS=true pytest tests/performance/ -k "perception" -v --timeout=300
```

### 3.4 Metrics to Collect

- `torch.cuda.memory_allocated()` before and after each model load.
- `torch.cuda.max_memory_allocated()` during concurrent runs.
- Per-request latency under concurrent load.
- CPU fallback activation count.

---

## 4. Cloud Timeout Simulation

### 4.1 Objective

Verify graceful degradation when cloud services are slow or unreachable. Test timeout enforcement via `asyncio.wait_for()`.

### 4.2 Test Scenarios

| Scenario | Mock Configuration | Expected Behavior |
|----------|-------------------|-------------------|
| Deepgram STT timeout | Mock WebSocket with 30s delay | Voice input pipeline returns timeout error. No hang. |
| ElevenLabs TTS timeout | Mock HTTPS with 15s delay | TTS falls back to silent output or error message. No hang. |
| qwen3.5:cloud LLM timeout | Mock `OllamaHandler` with 60s delay | `StubLLMClient` returns static fallback response. |
| DuckDuckGo search timeout | Mock HTTPS with 10s delay | Search returns "search unavailable" message. |
| All cloud services down | All cloud mocks return `ConnectionError` | System continues with local-only features (perception, QR, braille). LLM returns stub response. |
| Intermittent failures | Cloud mocks fail 50% of requests randomly | System handles partial failures. Successful requests return valid data. |

### 4.3 Implementation Pattern

```python
async def test_llm_timeout_fallback():
    """Verify StubLLMClient activates when qwen3.5:cloud times out."""
    mock_handler = MockOllamaHandler(delay_seconds=60)
    client = LLMClient(handler=mock_handler, timeout=5.0)

    result = await asyncio.wait_for(client.query("test prompt"), timeout=10.0)

    assert result is not None
    assert "context" in result.lower()  # StubLLMClient default response
```

### 4.4 Execution

```bash
# Cloud timeout tests
pytest tests/unit/ -k "timeout or fallback" -v --timeout=120
pytest tests/integration/ -k "cloud" -v --timeout=120
```

---

## 5. Retry Validation Tests

### 5.1 Status

Retry/backoff and circuit breaker patterns are not yet implemented (BACKLOG-004, P1). The test cases below are designed for validation once the implementation is complete.

### 5.2 Planned Test Scenarios

| Scenario | Expected Behavior |
|----------|-------------------|
| Exponential backoff timing | 3 retries with delays of 1s, 2s, 4s (±10% jitter). Total elapsed time between 7s and 8.5s. |
| Circuit breaker opens after 3 failures | After 3 consecutive failures, subsequent calls fail immediately without hitting the service. |
| Circuit breaker half-open probe | After 30s cooldown, circuit breaker sends a single probe request. If successful, circuit closes. |
| Circuit breaker closes on recovery | After successful probe, normal request flow resumes. |
| Retry succeeds on 2nd attempt | First call fails, second succeeds. Response returned with no error. |
| Retry exhausted — all 3 attempts fail | After 3 retries, system returns fallback response. Error logged. |
| Per-service circuit breaker isolation | Deepgram circuit open does not affect ElevenLabs or qwen3.5:cloud circuits. |

### 5.3 Implementation Pattern

```python
async def test_exponential_backoff_timing():
    """Verify retry delays follow 1s, 2s, 4s pattern."""
    call_times = []
    mock_service = MockCloudService(
        fail_count=3,
        on_call=lambda: call_times.append(time.monotonic())
    )

    with pytest.raises(ServiceUnavailableError):
        await retry_with_backoff(mock_service.call, retries=3, base_delay=1.0)

    assert len(call_times) == 4  # initial + 3 retries
    delays = [call_times[i+1] - call_times[i] for i in range(3)]
    assert 0.9 <= delays[0] <= 1.2  # ~1s
    assert 1.8 <= delays[1] <= 2.4  # ~2s
    assert 3.6 <= delays[2] <= 4.8  # ~4s
```

---

## 6. Memory Ingestion Validation

### 6.1 Objective

Verify the complete memory lifecycle: store → embed → index → search → query.

### 6.2 Test Scenarios

| Scenario | Validation Criteria |
|----------|-------------------|
| Store a memory with transcript | Memory ID returned. `embedding_status` is `COMPLETED`. Summary generated. |
| Embedding dimension check | Generated embedding is exactly 384 dimensions (matches `qwen3-embedding:4b` output). |
| FAISS index persistence | After store, FAISS index file exists on disk. After reload, stored vectors are searchable. |
| Search returns relevant results | Storing "I visited the pharmacy" then searching "pharmacy visit" returns the memory with score > 0.5. |
| RAG query uses retrieved context | After storing memories, a RAG query references the stored content in its answer. Citations include memory IDs. |
| Consent gate blocks unauthorized store | With memory consent disabled, `/memory/store` returns an error. No embedding generated. No FAISS entry created. |
| TTL expiry | After TTL expires, memory is eligible for deletion. Expired memories are excluded from search results. |
| Concurrent memory ingestion | 10 simultaneous `/memory/store` requests complete without deadlock or data corruption. |

### 6.3 Execution

```bash
pytest tests/unit/ -k "memory" -v --timeout=60
pytest tests/integration/ -k "memory" -v --timeout=120
```

---

## 7. Vector Similarity Accuracy Tests

### 7.1 Objective

Verify that the embedding and FAISS search pipeline returns semantically meaningful results.

### 7.2 Test Scenarios

| Test Case | Input Pair | Expected Similarity |
|-----------|-----------|-------------------|
| Identical texts | "The cat sat on the mat" vs "The cat sat on the mat" | Score = 1.0 (exact match) |
| Semantically similar | "I went to the pharmacy to buy medicine" vs "Visited the drugstore for medication" | Score > 0.7 |
| Semantically different | "The weather is sunny today" vs "How to fix a car engine" | Score < 0.3 |
| Partial overlap | "Red car parked on the street" vs "A red vehicle near the road" | Score > 0.5 |
| Empty vs non-empty | "" vs "Some text content" | Graceful handling (no crash). Score near 0. |
| Long text | 5000-character transcript vs 100-character query | Search completes within 50ms. Relevant results returned. |

### 7.3 Distance Thresholds

- **FAISS IndexFlatL2**: Uses L2 (Euclidean) distance. Lower distance = more similar.
- **Score conversion**: Application converts L2 distance to a 0-1 similarity score.
- **Relevance threshold**: Results with score > 0.5 are considered relevant.
- **Top-k default**: k=5, configurable up to 50.

---

## 8. OCR Accuracy Validation

### 8.1 Objective

Verify the 3-tier OCR fallback pipeline (EasyOCR → Tesseract → MSER heuristic) against reference images.

### 8.2 Test Scenarios

| Scenario | Input | Expected Output | Tier |
|----------|-------|----------------|------|
| Clear printed text | High-contrast image with "Hello World" | "Hello World" (exact match) | EasyOCR (Tier 1) |
| Low-contrast text | Light gray text on white background | Partial or full text recognition | Tesseract (Tier 2 fallback) |
| Handwritten-style text | Image with handwritten characters | Best-effort recognition with confidence score | EasyOCR (Tier 1) |
| Multi-language text | Image with mixed English and numeric text | Correct extraction of alphanumeric content | EasyOCR (Tier 1) |
| No text in image | Plain photograph with no text | Empty string or "No text detected" message | All tiers attempted |
| Rotated text | 45-degree rotated text | Text recognized after preprocessing | EasyOCR or Tesseract |
| EasyOCR unavailable | `EASYOCR_AVAILABLE=false` | Tesseract used as primary. If unavailable, MSER heuristic. | Tier 2 or 3 |
| All backends unavailable | All OCR backends disabled | Helpful error message returned. No crash. | Graceful failure |

### 8.3 Auto-Probe Behavior

- At startup, the OCR engine probes for available backends (EasyOCR, Tesseract, MSER).
- The engine uses the highest-quality available backend.
- If no backend is available, the engine returns platform-specific install instructions.

### 8.4 Execution

```bash
pytest tests/unit/ -k "ocr" -v --timeout=60
```

---

## 9. QR Parsing Validation

### 9.1 Objective

Verify the multi-stage QR retry pipeline (raw → preprocessed → multi-scale) and content classification.

### 9.2 Test Scenarios

| Scenario | Input | Expected Output |
|----------|-------|----------------|
| Valid URL QR code | QR encoding "https://example.com" | Content type: `url`. Spoken message references the URL. |
| Location QR code | QR encoding "geo:37.7749,-122.4194" | Content type: `location`. Spoken message includes coordinates. |
| Transport QR code | QR encoding transit stop data | Content type: `transport`. Spoken message references route info. |
| Contact QR code | QR encoding vCard data | Content type: `contact`. Spoken message extracts name and phone. |
| WiFi QR code | QR encoding "WIFI:S:MyNetwork;T:WPA;P:password123;;" | Content type: `wifi`. Spoken message references network name. |
| No QR detected | Image without QR code | Empty detections list. No spoken message. |
| Low-quality QR | Blurry or partial QR image | Multi-stage retry: raw scan fails → preprocessed scan → multi-scale scan. |
| Multiple QR codes | Image with 2+ QR codes | All detected codes returned with individual classifications. |
| Cache hit | Repeat scan of same QR payload | `cached: true` in response. Result served from `qr_cache/`. |
| Cache TTL expiry | Scan after TTL expires | Fresh scan performed. New result cached. |
| Malicious payload | QR encoding `javascript:alert(1)` | Payload blocked or sanitized before TTS output (when BACKLOG-003 is implemented). |

### 9.3 Multi-Stage Retry Verification

The QR scanner implements a 3-level retry:
1. **Raw scan**: Direct pyzbar/OpenCV decode on original image.
2. **Preprocessed scan**: Contrast enhancement + binarization before decode.
3. **Multi-scale scan**: Resize image at multiple scales and attempt decode at each.

Test that retry cascades correctly: if raw scan fails, preprocessed is attempted; if preprocessed fails, multi-scale is attempted.

### 9.4 Execution

```bash
pytest tests/unit/ -k "qr" -v --timeout=60
```

---

## 10. Performance Benchmarks

### 10.1 Latency Budgets

| Operation | Target Latency | Measurement Point |
|-----------|:-:|------------------|
| Frame processing (perception pipeline) | ≤250ms | From frame input to FusedFrameResult output |
| Detection + depth estimation | ≤250ms | Combined YOLO + MiDaS inference |
| TTS first audio chunk | ≤300ms | From text submission to first audio chunk from ElevenLabs |
| FAISS query (similarity search) | ≤50ms | From query vector to top-k results |
| Embedding generation | ≤200ms | From text input to 384-dim vector output |
| Frame freshness window | 500ms | Maximum frame age before rejection |
| Debounce window | 7s | Minimum interval between repeated navigation cues |
| QR scan (single attempt) | ≤100ms | From image input to decoded result |
| QR scan (full retry cascade) | ≤500ms | From image input through 3-level retry |

### 10.2 Throughput Targets

| Metric | Target | Context |
|--------|:------:|---------|
| Perception pipeline FPS | ≥4 FPS | Single-user, RTX 4060 GPU |
| Concurrent perception requests | ≥4 | Via PerceptionWorkerPool thread pool |
| Memory ingestion rate | ≥10/s | With mock embedder. With real qwen3-embedding:4b: ≥5/s |
| FAISS search at 5K vectors | ≤50ms | IndexFlatL2 O(n) scan limit |

### 10.3 Benchmark Test Implementation

```python
@pytest.mark.slow
class TestPerformanceBenchmarks:
    """Performance benchmark tests for latency SLAs."""

    def test_frame_processing_latency(self, sample_frame):
        """Frame processing must complete within 250ms."""
        start = time.monotonic()
        result = pipeline.process(sample_frame)
        elapsed = time.monotonic() - start
        assert elapsed < 0.250, f"Frame processing took {elapsed:.3f}s, exceeds 250ms SLA"

    def test_faiss_query_latency(self, populated_index):
        """FAISS query must complete within 50ms for 5K vectors."""
        query_vector = np.random.rand(384).astype(np.float32)
        start = time.monotonic()
        results = populated_index.search(query_vector, k=5)
        elapsed = time.monotonic() - start
        assert elapsed < 0.050, f"FAISS query took {elapsed:.3f}s, exceeds 50ms SLA"

    def test_embedding_generation_latency(self, embedder):
        """Embedding generation must complete within 200ms."""
        start = time.monotonic()
        embedding = embedder.embed_text("Test text for embedding")
        elapsed = time.monotonic() - start
        assert elapsed < 0.200, f"Embedding took {elapsed:.3f}s, exceeds 200ms SLA"
```

### 10.4 Execution

```bash
# Performance benchmarks
pytest tests/performance/ -v --timeout=300

# Slow-marked tests only
pytest tests/ -m slow -v --timeout=300
```

---

## Coverage Goals Summary

| Category | Target | Current State |
|----------|:------:|---------------|
| Unit test coverage (overall) | ≥80% | Not measured (requires `--cov` run) |
| Critical path coverage | 100% | Perception, memory, QR, consent |
| Integration test coverage | ≥60% | 7 integration test files exist |
| Performance test coverage | Latency SLAs verified | 16 performance test files exist |
| Total test count | 429+ | 157 collected in last scan (61 test files) |
| Test pass rate | ≥99% | 143/144 non-broken tests pass (99.3%) |

---

## CI Pipeline Integration

The testing strategy aligns with the existing CI pipeline (`.github/workflows/ci.yml`):

1. **secrets-scan**: Verifies `.env` has no real API keys.
2. **test**: Runs unit, integration, and full test suites across Python 3.10, 3.11, and 3.12.
3. **lint**: Executes `ruff check` and `lint-imports` for architectural boundary enforcement.
4. **docker**: Builds Docker image and runs smoke tests (main branch only).

### Recommended CI Enhancements

- Install `pytest-timeout` to enforce per-test timeout limits (BACKLOG-021).
- Add coverage reporting with `--cov-fail-under=80` to enforce minimum coverage.
- Add a dedicated GPU test stage for environments with NVIDIA hardware.
- Add cloud integration test stage with mock cloud services.
