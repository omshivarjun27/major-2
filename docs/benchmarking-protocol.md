# Benchmarking Protocol

## Hybrid Memory Architecture (Added 2026-02-22)

The benchmarking protocol assesses the efficiency and responsiveness of the hybrid memory architecture. These metrics are critical for maintaining a seamless user experience, ensuring that memory retrieval and storage operations do not introduce perceptible delays.

### 1. Performance Metrics and Targets

#### SQLite Insert Latency
- **Metric**: Time to insert one `conversation_log` row.
- **Target**: < 5ms per insert.
- **Method**: Average over 1,000 sequential inserts.
- **Tool**: Python `time.perf_counter()`.

#### FAISS Search Latency
- **Metric**: Time for nearest-neighbour search across K=5.
- **Target**: < 10ms for 5,000 vectors using `IndexFlatL2`.
- **Method**: Average over 100 searches at various index sizes (100, 1K, 5K).
- **Tool**: Python `time.perf_counter()`.

#### Embedding Generation Latency
- **Metric**: Time to generate one 384-dimension embedding using the local `qwen3-embedding:4b` model.
- **Target**: < 200ms per embedding.
- **Method**: Average over 100 text inputs of varying lengths (ranging from 10 to 500 tokens).
- **Tool**: Python `time.perf_counter()`.

#### End-to-End Hybrid Retrieval Latency
- **Metric**: Total time from input query text to retrieved structured content.
- **Target**: < 300ms (includes embedding generation, FAISS search, and SQLite lookup).
- **Method**: Average over 50 queries executed against a 1K-vector index.
- **Breakdown**: Embedding time + FAISS search time + SQLite lookup time.

#### End-to-End RAG Response Latency
- **Metric**: Total time from user query to natural language response generation.
- **Target**: < 2000ms (includes the cloud LLM call to `qwen3.5:cloud`).
- **Method**: Average over 20 unique queries.

### 2. Benchmark Environment Configuration

To ensure results are comparable and reproducible, all benchmarks must be conducted using the following environment:

- **Hardware**: NVIDIA RTX 4060 (8GB VRAM).
- **Index Sizes**: Testing across 100, 1,000, and 5,000 vectors.
- **Embedding Model**: `qwen3-embedding:4b` (running on local GPU).
- **SQLite Configuration**: WAL mode enabled, database located at `data/app_state.db`.
- **FAISS Configuration**: `IndexFlatL2`, located at `data/memory_index/`.

### 3. Results Tracking Template

The following table structure should be used to record results during benchmarking sessions:

| Metric | 100 vectors | 1K vectors | 5K vectors | Target |
|--------|------------|------------|------------|--------|
| SQLite insert (ms) | — | — | — | < 5 |
| FAISS search K=5 (ms) | — | — | — | < 10 |
| Embedding gen (ms) | — | — | — | < 200 |
| E2E retrieval (ms) | — | — | — | < 300 |
| E2E RAG (ms) | — | — | — | < 2000 |

Periodic benchmarking is required after any significant changes to the embedding model or storage layer configuration to ensure performance targets continue to be met.
