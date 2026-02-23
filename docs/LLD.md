# Low Level Design

## Hybrid Memory Architecture (Added 2026-02-22)

The low-level design of the memory engine emphasizes data integrity, thread safety, and efficient cross-referencing between structured relational data and high-dimensional vector embeddings. This section details the internal workings of each component and their interaction patterns.

### sqlite_manager.py Module Specification

*   **Layer**: Domain (`core/memory/`)
*   **File**: `core/memory/sqlite_manager.py`
*   **Description**: Manages structured state storage and metadata using an embedded SQLite database. It serves as the single source of truth for conversational history and system configuration.
*   **Public Interfaces**:
    *   `insert_conversation(session_id: str, transcript: str, summary: str, scene_graph_ref: str) -> int`: Persists a new conversation record. It uses an `INSERT` statement and returns the `rowid` of the newly created record, which is essential for indexing in FAISS.
    *   `get_conversation(rowid: int) -> ConversationLog`: Retrieves a single conversation record by its primary key. Returns a `ConversationLog` object or `None` if not found.
    *   `get_conversations_by_ids(rowids: List[int]) -> List[ConversationLog]`: Performs a bulk retrieval of conversation logs for RAG context. It uses the `IN` clause to minimize database round-trips.
    *   `update_preference(key: str, value: str)`: Stores or updates a user preference in the `user_preferences` table using an `INSERT OR REPLACE` pattern.
    *   `get_preference(key: str) -> str`: Retrieves a specific user preference by its key.
    *   `log_telemetry(event_type: str, payload: str)`: Records structured telemetry events for system auditing and performance tracking.
    *   `get_engine_setting(key: str) -> str`: Fetches system-level engine configurations from the `engine_settings` table.
*   **Thread Safety**: The module initializes the database connection with `check_same_thread=False` to allow multi-threaded access. Write operations are protected by a `threading.RLock()` to prevent database locks during concurrent ingestions and ensure that only one thread can modify the database at a time.
*   **Error Handling**: Employs a defensive approach where query failures result in empty return values rather than exceptions, ensuring the perception pipeline remains active even if storage fails. All SQL exceptions are caught and logged at the `ERROR` level.
*   **Database Path**: `data/app_state.db`
*   **Initialization**: Automatically executes schema migrations and table creation on the first instance access if the database file is missing or empty. It uses a series of `CREATE TABLE IF NOT EXISTS` statements.

#### Internal Logic: insert_conversation

1.  **Check Connection**: Ensure the SQLite connection is active and healthy.
2.  **Start Transaction**: Begin an implicit or explicit transaction to ensure atomicity and data consistency.
3.  **Execute Insert**: Run the SQL `INSERT` statement with sanitized parameters for `session_id`, `transcript`, `summary`, and `scene_graph_ref`.
4.  **Capture rowid**: Immediately after the insert, call `cursor.lastrowid` to get the generated primary key.
5.  **Commit**: Finalize the transaction to persist the data to the Write-Ahead Log (WAL).
6.  **Return ID**: Provide the `rowid` to the caller for vector cross-referencing.

#### Internal Logic: get_conversations_by_ids

1.  **Parameter Validation**: Ensure the input list of `rowids` is not empty.
2.  **Dynamic Query Construction**: Generate a parameterized query using the `IN` clause (e.g., `SELECT * FROM conversation_logs WHERE rowid IN (?, ?, ?)`).
3.  **Execute Select**: Run the query against the database and fetch all matching rows.
4.  **Object Mapping**: Transform the raw row tuples into `ConversationLog` dataclasses for easier downstream consumption.
5.  **Ordering**: Ensure the returned list maintains the same order or a consistent chronological order as requested.

### SQLite Schema Definition

The database schema is designed to support both conversational memory and application state:

```sql
CREATE TABLE IF NOT EXISTS conversation_logs (
    rowid INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    timestamp TEXT DEFAULT (datetime('now')),
    transcript TEXT NOT NULL,
    summary TEXT,
    scene_graph_ref TEXT,
    expiry TEXT
);

CREATE TABLE IF NOT EXISTS user_preferences (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS engine_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS telemetry_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT (datetime('now')),
    event_type TEXT NOT NULL,
    payload TEXT
);
```

### FAISSIndexer Updates

The `FAISSIndexer` (located in `core/memory/indexer.py`) is updated to integrate tightly with the `SQLiteManager`:

*   **Mapping Strategy**: Instead of managing complex internal IDs, the indexer uses the SQLite `rowid` as the vector ID. This eliminates the need for a separate ID-to-vector mapping table.
*   **add(rowid, vector)**: Inserts the 384-dimensional embedding into the FAISS index at a position directly associated with the provided `rowid`. The `vector` must be a normalized `numpy.ndarray` of type `float32`.
*   **search(query_vector, k)**: Returns a list of tuples containing the `rowid` and the L2 distance for the top `k` matches. The distances are used to filter out low-confidence results.
*   **Safety**: Synchronizes index modifications using `threading.RLock()` to ensure consistency between the vector index and the relational store. This lock is shared across all threads accessing the index.
*   **Persistence**: Serializes the `IndexFlatL2` to `data/memory_index/` using FAISS native `write_index` methods. The index is re-loaded on system startup.

### MemoryIngester Updates

The ingestion flow is updated to follow a strict sequential pipeline to ensure data consistency between the relational and vector stores:

1.  **Consent Validation**: Verify user has opted into memory storage by checking the `user_preferences` table.
2.  **Relational Storage**: Call `SQLiteManager.insert_conversation()` to store the raw text, summary, and scene graph reference. Capture the returned `rowid`.
3.  **Vector Generation**: Call `OllamaEmbedder.embed_text()` to generate a 384-dimensional embedding using the local `qwen3-embedding:4b` model. This is done in a thread pool to avoid blocking the event loop.
4.  **Vector Indexing**: Call `FAISSIndexer.add(rowid, vector)` to map the vector to the relational record.
5.  **Completion**: Return the `rowid` as the final `memory_id` for use in the perception pipeline responses.

### MemoryRetriever Updates

The retrieval flow leverages the hybrid architecture to provide fast, relevant context for RAG:

1.  **Query Embedding**: Call `OllamaEmbedder.embed_text(query)` to convert the natural language query into a 384-dimensional vector.
2.  **Similarity Search**: Call `FAISSIndexer.search(query_vector, k=5)` to retrieve the `rowids` of the most relevant past interactions based on L2 distance.
3.  **Content Retrieval**: Call `SQLiteManager.get_conversations_by_ids(rowids)` to fetch the full structured logs associated with those IDs. This provides the context for the reasoning engine.
4.  **Reasoning**: Pass the query and retrieved context to `RAGReasoner.reason(query, context)`. The reasoning engine uses a specific system prompt to constrain the LLM.
5.  **Output**: Generate and return a contextually grounded natural language response via `qwen3.5:cloud`. The response includes citations to the specific memories used.

### Concurrency Considerations

To maintain high performance in a multi-user, real-time environment:

*   **SQLite WAL Mode**: Enabled to support concurrent read operations while a write operation is in progress. This significantly improves responsiveness under load.
*   **Locking Granularity**: `threading.RLock()` is used in both the indexer and the SQLite manager to serialize writes while allowing non-blocking reads where possible. This prevents data corruption during simultaneous ingestion requests.
*   **Async Integration**: Both the relational database and the vector index are accessed from the async event loop using `asyncio.to_thread()` or `run_in_executor()` to prevent blocking the main perception and speech pipelines.
*   **I/O Throttling**: Persistence operations for the FAISS index are debounced to prevent excessive disk I/O during periods of high ingestion activity.

### Failure Mode Analysis

*   **SQLite Write Failure**: If the relational insert fails, the ingestion is aborted before the vector index is modified. This prevents orphaned vectors in the FAISS index.
*   **Ollama Timeout**: If embedding generation times out, the system falls back to a non-contextual response and logs a warning.
*   **FAISS Corruption**: If the vector index file is corrupted on disk, the system re-builds it by iterating over the `conversation_logs` table in SQLite and re-embedding the content.
*   **VRAM Exhaustion**: If the GPU runs out of memory for embeddings, the system falls back to a CPU-based embedding model (e.g., a smaller Sentence-Transformer) to maintain functionality.

### Data Migration and Versioning

The memory engine includes a lightweight migration framework to handle changes to the SQLite schema over time. Each database instance contains a `schema_version` in the `engine_settings` table. During initialization, the `SQLiteManager` checks this version and applies the necessary `ALTER TABLE` or `CREATE TABLE` statements to bring the database up to the current specification. This ensures that user data is preserved across system updates.

### Performance Benchmarks (Design Targets)

*   **SQLite Insert**: ≤ 50ms (in WAL mode)
*   **SQLite Bulk Fetch (k=5)**: ≤ 20ms
*   **FAISS Search (k=5)**: ≤ 10ms (IndexFlatL2)
*   **End-to-End Retrieval (Embedding + Search + Fetch)**: ≤ 150ms

These targets are based on benchmarks performed on the target NVIDIA RTX 4060 hardware and ensure that the memory engine provides a responsive experience for the user.
