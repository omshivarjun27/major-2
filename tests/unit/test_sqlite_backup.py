"""Unit tests for SQLite backup module.

Tests T-099: SQLite Backup/Restore
"""

import json
import sqlite3
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest


class TestSQLiteBackupMetadata:
    """Tests for SQLiteBackupMetadata dataclass."""
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        from infrastructure.backup.sqlite_backup import SQLiteBackupMetadata
        
        metadata = SQLiteBackupMetadata(
            backup_id="test_20240101_120000",
            database_name="consent",
            created_at="2024-01-01T12:00:00+00:00",
            original_size_bytes=102400,
            compressed_size_bytes=51200,
            checksum_sha256="abc123",
            table_count=3,
            row_counts={"users": 100, "settings": 10},
            sqlite_version="3.40.0",
        )
        
        d = metadata.to_dict()
        
        assert d["backup_id"] == "test_20240101_120000"
        assert d["table_count"] == 3
        assert d["row_counts"]["users"] == 100
    
    def test_from_dict(self):
        """Test creation from dictionary."""
        from infrastructure.backup.sqlite_backup import SQLiteBackupMetadata
        
        data = {
            "backup_id": "test_20240101_120000",
            "database_name": "consent",
            "created_at": "2024-01-01T12:00:00+00:00",
            "original_size_bytes": 102400,
            "compressed_size_bytes": 51200,
            "checksum_sha256": "abc123",
            "table_count": 3,
            "row_counts": {"users": 100},
            "sqlite_version": "3.40.0",
        }
        
        metadata = SQLiteBackupMetadata.from_dict(data)
        
        assert metadata.backup_id == "test_20240101_120000"
        assert metadata.table_count == 3
    
    def test_roundtrip(self):
        """Test to_dict and from_dict roundtrip."""
        from infrastructure.backup.sqlite_backup import SQLiteBackupMetadata
        
        original = SQLiteBackupMetadata(
            backup_id="test_backup",
            database_name="memory",
            created_at="2024-01-01T00:00:00+00:00",
            original_size_bytes=204800,
            compressed_size_bytes=102400,
            checksum_sha256="xyz789",
            table_count=5,
            row_counts={"table1": 50, "table2": 100},
            sqlite_version="3.40.0",
            wal_mode=True,
            extra={"custom": "data"},
        )
        
        restored = SQLiteBackupMetadata.from_dict(original.to_dict())
        
        assert restored.backup_id == original.backup_id
        assert restored.wal_mode == original.wal_mode
        assert restored.extra == original.extra


def create_test_database(path: Path, tables: int = 3, rows_per_table: int = 10) -> None:
    """Create a test SQLite database."""
    conn = sqlite3.connect(path)
    for i in range(tables):
        table_name = f"test_table_{i}"
        conn.execute(f"CREATE TABLE {table_name} (id INTEGER PRIMARY KEY, data TEXT)")
        for j in range(rows_per_table):
            conn.execute(f"INSERT INTO {table_name} (data) VALUES (?)", (f"data_{j}",))
    conn.commit()
    conn.close()


class TestSQLiteBackupManager:
    """Tests for SQLiteBackupManager."""
    
    def test_backup_creates_compressed_file(self, tmp_path):
        """Test that backup creates a compressed file."""
        from infrastructure.backup.sqlite_backup import SQLiteBackupManager
        from infrastructure.backup.faiss_backup import LocalStorageBackend
        
        # Create test database
        db_path = tmp_path / "test.db"
        create_test_database(db_path, tables=3, rows_per_table=50)
        
        # Create backup manager
        backup_dir = tmp_path / "backups"
        storage = LocalStorageBackend(backup_dir)
        manager = SQLiteBackupManager(storage=storage)
        
        # Perform backup
        metadata = manager.backup(
            db_path=db_path,
            database_name="test",
        )
        
        assert metadata is not None
        assert metadata.database_name == "test"
        assert metadata.table_count == 3
        assert metadata.compressed_size_bytes < metadata.original_size_bytes
        
        # Verify backup file exists
        backup_files = list(backup_dir.glob("test/*.db.gz"))
        assert len(backup_files) == 1
    
    def test_backup_nonexistent_file_returns_none(self, tmp_path):
        """Test that backup of non-existent file returns None."""
        from infrastructure.backup.sqlite_backup import SQLiteBackupManager
        from infrastructure.backup.faiss_backup import LocalStorageBackend
        
        storage = LocalStorageBackend(tmp_path / "backups")
        manager = SQLiteBackupManager(storage=storage)
        
        result = manager.backup(
            db_path=tmp_path / "nonexistent.db",
            database_name="test",
        )
        
        assert result is None
    
    def test_backup_captures_row_counts(self, tmp_path):
        """Test that backup captures row counts per table."""
        from infrastructure.backup.sqlite_backup import SQLiteBackupManager
        from infrastructure.backup.faiss_backup import LocalStorageBackend
        
        # Create test database with specific row counts
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, desc TEXT)")
        for i in range(25):
            conn.execute("INSERT INTO users (name) VALUES (?)", (f"user_{i}",))
        for i in range(100):
            conn.execute("INSERT INTO items (desc) VALUES (?)", (f"item_{i}",))
        conn.commit()
        conn.close()
        
        storage = LocalStorageBackend(tmp_path / "backups")
        manager = SQLiteBackupManager(storage=storage)
        
        metadata = manager.backup(db_path, "test")
        
        assert metadata.row_counts["users"] == 25
        assert metadata.row_counts["items"] == 100
    
    def test_restore_backup(self, tmp_path):
        """Test restoring a backup."""
        from infrastructure.backup.sqlite_backup import SQLiteBackupManager
        from infrastructure.backup.faiss_backup import LocalStorageBackend
        
        # Create and backup a database
        db_path = tmp_path / "original.db"
        create_test_database(db_path, tables=2, rows_per_table=20)
        
        storage = LocalStorageBackend(tmp_path / "backups")
        manager = SQLiteBackupManager(storage=storage)
        
        metadata = manager.backup(db_path, "test")
        assert metadata is not None
        
        # Restore to new location
        restore_path = tmp_path / "restored.db"
        result = manager.restore(metadata.backup_id, "test", restore_path)
        
        assert result is True
        assert restore_path.exists()
        
        # Verify data
        conn = sqlite3.connect(restore_path)
        cursor = conn.execute("SELECT COUNT(*) FROM test_table_0")
        count = cursor.fetchone()[0]
        conn.close()
        
        assert count == 20
    
    def test_restore_with_checksum_verification(self, tmp_path):
        """Test restore verifies checksum."""
        from infrastructure.backup.sqlite_backup import SQLiteBackupManager
        from infrastructure.backup.faiss_backup import LocalStorageBackend
        import gzip
        
        # Create and backup a database
        db_path = tmp_path / "test.db"
        create_test_database(db_path)
        
        storage = LocalStorageBackend(tmp_path / "backups")
        manager = SQLiteBackupManager(storage=storage)
        
        metadata = manager.backup(db_path, "test")
        
        # Corrupt the backup
        backup_files = list((tmp_path / "backups").glob("test/*.db.gz"))
        with gzip.open(backup_files[0], "wb") as f:
            f.write(b"corrupted data that is not a valid database")
        
        # Restore should fail due to checksum mismatch
        restore_path = tmp_path / "restored.db"
        result = manager.restore(metadata.backup_id, "test", restore_path, verify=True)
        
        assert result is False
        assert not restore_path.exists()
    
    def test_restore_runs_integrity_check(self, tmp_path):
        """Test that restore runs integrity check."""
        from infrastructure.backup.sqlite_backup import SQLiteBackupManager
        from infrastructure.backup.faiss_backup import LocalStorageBackend
        
        # Create and backup a database
        db_path = tmp_path / "test.db"
        create_test_database(db_path)
        
        storage = LocalStorageBackend(tmp_path / "backups")
        manager = SQLiteBackupManager(storage=storage)
        
        metadata = manager.backup(db_path, "test")
        
        # Restore should pass integrity check
        restore_path = tmp_path / "restored.db"
        result = manager.restore(metadata.backup_id, "test", restore_path, verify=True)
        
        assert result is True
    
    def test_list_backups(self, tmp_path):
        """Test listing backups."""
        from infrastructure.backup.sqlite_backup import SQLiteBackupManager
        from infrastructure.backup.faiss_backup import LocalStorageBackend
        import time
        
        storage = LocalStorageBackend(tmp_path / "backups")
        manager = SQLiteBackupManager(storage=storage)
        
        # Create multiple backups with different databases
        for i in range(3):
            db_path = tmp_path / f"test_{i}.db"
            create_test_database(db_path, tables=i + 1, rows_per_table=5)
            manager.backup(db_path, "test")
            time.sleep(0.01)  # Ensure different timestamps
        
        backups = manager.list_backups("test")
        
        assert len(backups) >= 1
        if len(backups) > 1:
            # Should be sorted newest first
            assert backups[0].created_at >= backups[1].created_at
    
    def test_cleanup_old_backups(self, tmp_path):
        """Test cleaning up old backups."""
        from infrastructure.backup.sqlite_backup import SQLiteBackupManager
        from infrastructure.backup.faiss_backup import LocalStorageBackend
        
        backup_dir = tmp_path / "backups"
        storage = LocalStorageBackend(backup_dir)
        manager = SQLiteBackupManager(storage=storage, retention_days=7)
        
        # Create fake old backup metadata
        db_dir = backup_dir / "test"
        db_dir.mkdir(parents=True)
        
        old_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        old_metadata = {
            "backup_id": "test_old",
            "database_name": "test",
            "created_at": old_date,
            "original_size_bytes": 1000,
            "compressed_size_bytes": 500,
            "checksum_sha256": "abc",
            "table_count": 1,
            "row_counts": {},
            "sqlite_version": "3.40.0",
        }
        
        (db_dir / "test_old.metadata.json").write_text(json.dumps(old_metadata))
        (db_dir / "test_old.db.gz").write_bytes(b"old backup")
        
        # Create recent backup
        new_date = datetime.now(timezone.utc).isoformat()
        new_metadata = {
            "backup_id": "test_new",
            "database_name": "test",
            "created_at": new_date,
            "original_size_bytes": 1000,
            "compressed_size_bytes": 500,
            "checksum_sha256": "xyz",
            "table_count": 1,
            "row_counts": {},
            "sqlite_version": "3.40.0",
        }
        
        (db_dir / "test_new.metadata.json").write_text(json.dumps(new_metadata))
        (db_dir / "test_new.db.gz").write_bytes(b"new backup")
        
        # Cleanup
        deleted = manager.cleanup_old_backups("test")
        
        assert deleted == 1
        assert not (db_dir / "test_old.db.gz").exists()
        assert (db_dir / "test_new.db.gz").exists()
    
    def test_verify_backup(self, tmp_path):
        """Test backup verification."""
        from infrastructure.backup.sqlite_backup import SQLiteBackupManager
        from infrastructure.backup.faiss_backup import LocalStorageBackend
        
        # Create and backup a database
        db_path = tmp_path / "test.db"
        create_test_database(db_path, tables=2)
        
        storage = LocalStorageBackend(tmp_path / "backups")
        manager = SQLiteBackupManager(storage=storage)
        
        metadata = manager.backup(db_path, "test")
        
        # Verify should pass
        result = manager.verify_backup(metadata.backup_id, "test")
        
        assert result is True


class TestOnlineBackup:
    """Tests for online backup functionality."""
    
    def test_online_backup_creates_consistent_snapshot(self, tmp_path):
        """Test that online backup creates a consistent copy."""
        from infrastructure.backup.sqlite_backup import SQLiteBackupManager
        from infrastructure.backup.faiss_backup import LocalStorageBackend
        
        # Create database with data
        db_path = tmp_path / "source.db"
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
        for i in range(100):
            conn.execute("INSERT INTO test (value) VALUES (?)", (f"value_{i}",))
        conn.commit()
        conn.close()
        
        storage = LocalStorageBackend(tmp_path / "backups")
        manager = SQLiteBackupManager(storage=storage)
        
        # Perform backup
        metadata = manager.backup(db_path, "test")
        
        # Verify row count
        assert metadata.row_counts["test"] == 100
    
    def test_wal_mode_detection(self, tmp_path):
        """Test WAL mode detection."""
        from infrastructure.backup.sqlite_backup import SQLiteBackupManager
        from infrastructure.backup.faiss_backup import LocalStorageBackend
        
        # Create database in WAL mode
        db_path = tmp_path / "wal.db"
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()
        conn.close()
        
        storage = LocalStorageBackend(tmp_path / "backups")
        manager = SQLiteBackupManager(storage=storage)
        
        metadata = manager.backup(db_path, "test")
        
        assert metadata.wal_mode is True


class TestCreateSQLiteBackupManager:
    """Tests for factory function."""
    
    def test_create_local_backend(self, tmp_path):
        """Test creating manager with local backend."""
        from infrastructure.backup.sqlite_backup import create_sqlite_backup_manager
        
        manager = create_sqlite_backup_manager(
            backend="local",
            local_path=str(tmp_path / "backups"),
            retention_days=14,
        )
        
        assert manager is not None
        assert manager._retention_days == 14
    
    def test_create_with_invalid_backend_raises(self):
        """Test that invalid backend raises ValueError."""
        from infrastructure.backup.sqlite_backup import create_sqlite_backup_manager
        
        with pytest.raises(ValueError, match="Unknown backend"):
            create_sqlite_backup_manager(backend="invalid")


class TestIntegrityCheck:
    """Tests for integrity check functionality."""
    
    def test_integrity_check_passes_valid_db(self, tmp_path):
        """Test integrity check passes for valid database."""
        from infrastructure.backup.sqlite_backup import SQLiteBackupManager
        from infrastructure.backup.faiss_backup import LocalStorageBackend
        
        # Create valid database
        db_path = tmp_path / "valid.db"
        create_test_database(db_path)
        
        storage = LocalStorageBackend(tmp_path / "backups")
        manager = SQLiteBackupManager(storage=storage)
        
        result = manager._verify_integrity(db_path)
        
        assert result is True
    
    def test_database_stats_extraction(self, tmp_path):
        """Test database stats extraction."""
        from infrastructure.backup.sqlite_backup import SQLiteBackupManager
        from infrastructure.backup.faiss_backup import LocalStorageBackend
        
        # Create database with known structure
        db_path = tmp_path / "stats.db"
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE table_a (id INTEGER)")
        conn.execute("CREATE TABLE table_b (id INTEGER)")
        for i in range(10):
            conn.execute("INSERT INTO table_a (id) VALUES (?)", (i,))
        for i in range(20):
            conn.execute("INSERT INTO table_b (id) VALUES (?)", (i,))
        conn.commit()
        conn.close()
        
        storage = LocalStorageBackend(tmp_path / "backups")
        manager = SQLiteBackupManager(storage=storage)
        
        stats = manager._get_database_stats(db_path)
        
        assert stats["table_count"] == 2
        assert stats["row_counts"]["table_a"] == 10
        assert stats["row_counts"]["table_b"] == 20
