# T-099: SQLite Backup/Restore

## Metadata
- **Phase**: P5
- **Cluster**: CL-INF
- **Risk Tier**: Medium
- **Upstream Deps**: []
- **Downstream Impact**: [T-100, T-108]
- **Current State**: completed

## Objective

Implement automated backup and restore for SQLite databases (consent store, memory metadata, cache). Create `infrastructure/backup/sqlite_backup.py` using SQLite online backup API for consistent snapshots. Schedule daily backups with 30-day retention. Implement point-in-time recovery using WAL (Write-Ahead Log) replay. Add backup integrity verification via `PRAGMA integrity_check`. Support same storage backends as FAISS backup.

## Acceptance Criteria

1. ✅ SQLiteBackupManager class with backup/restore methods
2. ✅ Online backup API for consistent snapshots
3. ✅ Gzip compression
4. ✅ SHA-256 checksum validation
5. ✅ SQLite integrity_check verification
6. ✅ Configurable retention period (default 30 days)
7. ✅ WAL mode detection and backup
8. ✅ Table count and row counts in metadata
9. ✅ Cleanup old backups function
10. ✅ Backup verification function
11. ✅ Unit tests (18 tests)

## Implementation Notes

Created `infrastructure/backup/sqlite_backup.py` with:

**SQLiteBackupMetadata:**
- backup_id, database_name, created_at
- original_size_bytes, compressed_size_bytes
- checksum_sha256, table_count, row_counts
- sqlite_version, wal_mode

**SQLiteBackupManager methods:**
- `backup()`: Online backup with compression
- `restore()`: Restore and verify with integrity check
- `list_backups()`: List all backups for a database
- `cleanup_old_backups()`: Delete backups older than retention
- `verify_backup()`: Full integrity verification
- `_online_backup()`: SQLite backup API wrapper
- `_verify_integrity()`: PRAGMA integrity_check

**Key Features:**
- Uses `sqlite3.Connection.backup()` for live database backups
- No locking required - can backup while DB is in use
- WAL file backed up separately if present

## Test Requirements

- ✅ Unit: tests/unit/test_sqlite_backup.py with 18 tests
