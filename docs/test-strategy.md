# Test Strategy

## Hybrid Memory Architecture (Added 2026-02-22)

The hybrid memory system combines SQLite for structured conversation logs and metadata with FAISS for semantic vector search. This strategy outlines the testing approach to ensure data integrity, performance, and synchronization between these two distinct storage layers.

### 1. Unit Tests
Focus on isolating individual components of the `SQLiteManager` and `FAISSIndex` wrappers.

- `test_sqlite_insert_conversation`: Insert a conversation log and verify a valid rowid is returned.
- `test_sqlite_get_conversation`: Insert a record, retrieve it by its rowid, and verify the retrieved content matches the original input exactly.
- `test_sqlite_bulk_retrieval`: Insert 10 conversations and retrieve them using a list of multiple rowids to ensure efficient batch operations.
- `test_embedding_generation`: Generate a 384-dimension embedding using the local embedding model, verifying the output shape and data type.
- `test_faiss_add_and_search`: Add a vector associated with a specific rowid to the FAISS index, perform a similarity search with a similar vector, and verify the correct rowid is returned.

### 2. Integration Tests
Validate the complete data flow and synchronization between storage layers.

- `test_ingest_full_flow`: Execute a complete ingestion: insert into SQLite, generate an embedding, and store in FAISS. Verify that all stores remain consistent.
- `test_retrieve_full_flow`: Ingest a memory, then query using similar text. Verify that the system correctly retrieves and returns the relevant content from SQLite based on the FAISS search result.
- `test_id_synchronization`: Confirm that after ingestion, the SQLite rowid matches the FAISS vector position (or associated metadata ID) to maintain a 1:1 mapping.
- `test_consent_gate`: Verify that attempts to store data in the memory store are rejected if prior user consent has not been recorded.

### 3. Concurrency Tests
Ensure thread-safety and data integrity under load.

- `test_concurrent_writes`: Run 10 threads simultaneously ingesting memories to verify that no data corruption or race conditions occur.
- `test_concurrent_read_write`: Operate readers and writers simultaneously to ensure the system does not encounter deadlocks.
- `test_sqlite_wal_mode`: Confirm that Write-Ahead Logging (WAL) mode is active, allowing concurrent reads during write operations.

### 4. Crash Recovery Tests
Test the resilience of the storage system against unexpected process termination.

- `test_faiss_persistence_after_crash`: Simulate a process termination during a write operation, restart, and verify that the FAISS index remains consistent and loadable.
- `test_sqlite_journal_recovery`: Simulate a crash during a SQLite transaction and verify that the database automatically recovers to a consistent state upon restart.
- `test_orphan_detection`: Manually create an intentional orphan (a FAISS entry without a corresponding SQLite row) and verify that the system's audit tools correctly detect the anomaly.

### 5. Test Framework and Configuration
The project uses `pytest` as the primary testing framework.

- **Async Support**: Configured with `asyncio_mode = auto` to handle asynchronous database and embedding operations.
- **Fixtures**: Utilize `tmp_path` fixtures for isolating database files and FAISS indices during test execution.
- **Mocking**: The `OllamaEmbedder` should be mocked in unit tests to avoid GPU dependencies and ensure fast, deterministic execution.
- **Timeouts**: 
  - Unit tests: 60s timeout.
  - Integration tests: 120s timeout.
