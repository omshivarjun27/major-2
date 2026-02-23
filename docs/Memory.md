# Memory System

The Voice & Vision Assistant for Blind features a sophisticated memory system designed to provide context-aware assistance by recalling past interactions and visual scene descriptions. This system enables the assistant to answer questions about the user's environment and history with high precision and relevance.

## Hybrid Memory Architecture (Added 2026-02-22)

The memory system is built on a hybrid architecture that combines the strengths of semantic vector search with the reliability of structured relational storage. By separating the mathematical representation of memories from their textual content, the system achieves both high performance and data integrity.

### Overview

The architecture utilizes two complementary storage layers:
- **Semantic Memory (FAISS)**: Optimized for similarity-based retrieval using high-dimensional vector embeddings.
- **Structured Memory (SQLite)**: Optimized for deterministic state management, metadata storage, and exact content retrieval.

This hybrid approach ensures that the assistant can find relevant information based on meaning (semantics) while accurately reconstructing the original context from a trusted relational source.

### A. Semantic Memory (FAISS)

The semantic memory layer provides the core retrieval capability for the RAG (Retrieval-Augmented Generation) pipeline.

- **Purpose**: Fast approximate (or exact) nearest-neighbor search over high-dimensional text embeddings to identify relevant historical context.
- **Technology**: FAISS (Facebook AI Similarity Search) using the `IndexFlatL2` metric. This performs exhaustive L2 distance calculation, ensuring the highest retrieval accuracy for the current index size.
- **Embedding Model**: `qwen3-embedding:4b` (384 dimensions). This model is loaded locally on the NVIDIA RTX 4060, consuming approximately 2GB of VRAM.
- **Storage**: Binary index files are stored in the `data/memory_index/` directory. These files contain only the float32 vector representations.
- **Capacity**: The system is optimized for up to 5,000 vectors. Beyond this limit, the O(n) search latency of `IndexFlatL2` may impact real-time responsiveness, triggering the eviction policy.
- **Thread Safety**: Access to the FAISS index is managed through a `threading.RLock()`, ensuring that concurrent ingestion and retrieval operations do not corrupt the index state.
- **Inputs/Outputs**:
    - **Input**: 384-dimensional float32 query vector.
    - **Output**: A list of vector identifiers and their corresponding L2 distance scores. Lower scores indicate higher semantic similarity.

### B. Structured Memory (SQLite)

The structured memory layer serves as the primary repository for all textual data, system state, and user configurations.

- **Purpose**: Deterministic storage and retrieval of exact conversational content, metadata, user preferences, and performance telemetry.
- **Technology**: SQLite 3, an embedded, zero-configuration database engine that provides full ACID compliance.
- **Storage**: A single database file located at `data/app_state.db`.
- **Primary Tables**:
    - `conversation_logs`: Stores the timestamp, session identifier, original transcript, generated summary, and any associated scene graph references.
    - `user_preferences`: A flexible key-value store for managing persistent user settings and personalization parameters.
    - `engine_settings`: Captures snapshots of the system's runtime configuration for auditability and debugging.
    - `telemetry_logs`: Records high-frequency performance metrics and system events for health monitoring.
- **Thread Safety**: SQLite is configured in Write-Ahead Logging (WAL) mode with `check_same_thread=False` in the connection pool, allowing for high-concurrency read/write operations.
- **Inputs/Outputs**:
    - **Input**: A unique `rowid` or a set of filter criteria (e.g., time range, session ID).
    - **Output**: Structured records containing raw text, timestamps, and metadata.

### Retrieval Strategy

The system follows a multi-stage retrieval process to synthesize natural language answers from stored memories.

1. **Query Processing**: The user's voice input is converted to text and passed to the `MemoryRetriever`.
2. **Semantic Encoding**: The query text is converted into a 384-dimensional vector using the local `OllamaEmbedder`.
3. **Similarity Search**: The query vector is compared against the FAISS index. The top-K nearest neighbors (default K=5) are identified.
4. **Context Retrieval**: The `rowids` from the FAISS results are used to fetch the full records from the `conversation_logs` table in SQLite.
5. **Relevancy Filtering**: Results with L2 distance scores exceeding a configurable threshold are discarded to prevent the inclusion of irrelevant context.
6. **RAG Composition**: The `RAGReasoner` formats the retrieved context and the original query into a system prompt for the `qwen3.5:cloud` LLM.
7. **Natural Language Answer**: The LLM generates a response that is grounded in the provided memories, citing specific times or sessions where applicable.

### ID Synchronization and Integrity

The integrity of the hybrid store depends on the precise synchronization of identifiers between FAISS and SQLite.

- **Canonical Identifier**: The SQLite `rowid` is treated as the source of truth for all memory IDs.
- **Mapping**: Each entry in the FAISS index corresponds to a specific `rowid` in the `conversation_logs` table.
- **Orphan Management**: The system includes a background utility to detect "orphan" vectors (vectors in FAISS without a corresponding SQLite row) and "missing" vectors (rows in SQLite without a corresponding FAISS entry).
- **Atomic Operations**: Ingestion and deletion are performed as atomic operations across both backends. If a write fails in one layer, the system attempts to rollback or compensate in the other to maintain consistency.

### Privacy, Retention, and Consent

Privacy is a fundamental design principle of the memory system, emphasizing user control and data minimization.

- **Opt-In Only**: The memory system is disabled by default (`MEMORY_ENABLED=false`). Users must explicitly grant consent via the `/memory/consent` API before any data is stored.
- **Retention Policy**: Memories are automatically expired after a configurable period, typically 30 days. This is enforced by a periodic maintenance task that prunes both SQLite and FAISS records.
- **User-Directed Deletion**: Users can delete specific memories by ID or purge their entire history at any time.
- **No Raw Media Storage**: To minimize privacy risks, the system does not store raw audio recordings or camera images. Only the derived text transcripts and semantic embeddings are persisted.
- **Local Control**: The most sensitive part of the process—semantic embedding—is performed locally on the user's hardware, ensuring that raw textual data is not transmitted to external services for indexing.

This comprehensive memory architecture ensures that the Voice & Vision Assistant provides intelligent, context-aware support while strictly adhering to performance requirements and privacy standards.

### Technical Specifications

The following table provides detailed technical parameters for the memory engine's core components.

| Parameter | Specification |
|-----------|---------------|
| Vector Dimensions | 384 (float32) |
| FAISS Index Type | IDMap with IndexFlatL2 |
| Distance Metric | Euclidean (L2) |
| SQLite Version | 3.3x+ |
| Database Journal Mode | WAL (Write-Ahead Logging) |
| Memory Concurrency | Thread-safe via RLock (FAISS) and WAL (SQLite) |
| Ingestion Latency | 50-200ms (dependent on Ollama load) |
| Retrieval Latency | < 50ms (for up to 5,000 vectors) |

### Scalability and Performance

While the system is currently optimized for a local workstation (RTX 4060), the Hybrid Memory Architecture provides a clear path for future performance tuning.

1. **Vector Quantization**: As the index grows beyond 5,000 entries, the `IndexFlatL2` can be replaced with `IndexIVFFlat` or `IndexHNSW` to maintain sub-100ms retrieval times at the cost of slight approximation.
2. **Database Indexing**: SQLite primary keys and additional indexes on `timestamp` and `session_id` ensure that metadata lookup remains O(log n) even as the database size increases.
3. **VRAM Management**: The `qwen3-embedding:4b` model is managed by the Ollama runtime, which handles model offloading and memory allocation dynamically based on other active perception tasks (e.g., YOLO or MiDaS).

### Implementation Roadmap

The memory engine is subject to ongoing refinement to enhance its robustness and feature set.

- **Automated Re-indexing**: Development of a background task to re-calculate embeddings if the underlying model is upgraded to a higher-dimensional space.
- **Enhanced Privacy Controls**: Granular consent management allowing users to opt-in to specific types of memory (e.g., "remember my preferences but not my conversations").
- **Cross-Session Reasoning**: Improving the RAG pipeline to better synthesize context from multiple independent sessions for complex queries.

### Conclusion

The Hybrid Memory Architecture represents a balanced approach to the conflicting requirements of high-speed semantic search and reliable data management. By leveraging FAISS and SQLite in tandem, the Voice & Vision Assistant delivers a responsive and contextually aware experience while maintaining the highest standards of data integrity and user privacy.

### Error Handling and Recovery Protocols

The memory system includes robust mechanisms to handle runtime errors and data corruption in both its semantic and structured layers.

1. **Transaction Integrity**: The system treats ingestion as an atomic operation. If the SQLite write fails, the embedding process and FAISS indexing are bypassed. If the FAISS write fails, the SQLite record remains but is marked with an `indexing_failed` status for future re-try or reconciliation.
2. **Persistence Safeguards**: FAISS index updates are staged in memory and flushed to disk incrementally, reducing the risk of a full index corruption during unexpected system power-offs.
3. **Database Consistency Checks**: On system startup, the `MemoryIngester` runs a consistency check to ensure that the number of records in the `conversation_logs` table matches the vector count in the FAISS index. Discrepancies trigger an automated rebuild of the FAISS index from the stored SQLite text.
4. **Graceful Degradation**: If the FAISS index is completely unavailable, the system falls back to a deterministic time-range search in the SQLite database, ensuring that recent context can still be retrieved without semantic similarity capabilities.

This comprehensive approach to error management ensures that the Voice & Vision Assistant remains reliable and consistent even under adverse operating conditions.
