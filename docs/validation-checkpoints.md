# Validation Checkpoints

## Hybrid Memory Architecture (Added 2026-02-22)

The following checklist is used to validate the operational integrity of the hybrid memory system. This process ensures that both the structured (SQLite) and semantic (FAISS) storage layers are correctly configured and synchronized.

| # | Checkpoint | Validation Method | Expected Result | Status |
|---|-----------|-------------------|-----------------|--------|
| 1 | SQLite database file exists | `os.path.exists('data/app_state.db')` | File present | ☐ |
| 2 | SQLite tables created | `SELECT name FROM sqlite_master WHERE type='table'` | 4 tables: conversation_logs, user_preferences, engine_settings, telemetry_logs | ☐ |
| 3 | FAISS index file exists | `os.path.exists('data/memory_index/')` | Directory with index files | ☐ |
| 4 | FAISS index dimension correct | `faiss_index.d == 384` | Dimension = 384 | ☐ |
| 5 | No orphan FAISS IDs | For each FAISS vector ID, verify corresponding SQLite row exists | Zero orphans | ☐ |
| 6 | No orphan SQLite rows | For each SQLite conversation_log row, verify corresponding FAISS vector exists | Zero orphans | ☐ |
| 7 | ID synchronization verified | Insert test record, verify SQLite rowid matches FAISS vector position | IDs match | ☐ |
| 8 | Embedding dimension consistency | `len(OllamaEmbedder.embed_text("test")) == 384` | 384-dim vector | ☐ |
| 9 | SQLite WAL mode active | `PRAGMA journal_mode` returns 'wal' | WAL mode | ☐ |
| 10 | Memory consent gate functional | Store attempt without consent returns error | Rejected | ☐ |

### Validation Phases

#### Pre-deployment Validation
All checkpoints in the above table must be verified manually or through automated scripts before any production deployment. Failure to meet any of the checkpoints should halt the deployment process.

#### Runtime Validation
The system performs periodic integrity checks via the `/health` endpoint. This includes background orphan detection and index health monitoring. If an inconsistency is detected, an alert is triggered in the telemetry logs.

### Recovery Procedure

In the event that synchronization is lost between the SQLite database and the FAISS index, the following steps should be followed to restore system integrity:

1. **Stop Application**: Halt all active services that write to the memory store to prevent further data corruption.
2. **Backup Existing Data**: Create a timestamped backup of both `data/app_state.db` and the `data/memory_index/` directory.
3. **Wipe FAISS Index**: Delete the contents of the `data/memory_index/` directory to prepare for a fresh rebuild.
4. **Initiate Index Rebuild**: Use the `MemoryRebuilder` utility to iterate through every row in the SQLite `conversation_logs` table.
5. **Re-generate Embeddings**: For each log entry, generate a new embedding using the current embedding model (qwen3-embedding:4b).
6. **Re-populate FAISS**: Add each newly generated vector to the fresh FAISS index, ensuring the mapping to the original SQLite rowid is maintained.
7. **Verify Synchronization**: Run checkpoints 5, 6, and 7 from the validation table to confirm that synchronization has been successfully restored.
8. **Resume Operation**: Restart the application and verify end-to-end functionality through a set of integration tests.
