"""Infrastructure backup utilities for Voice & Vision Assistant.

Provides backup and restore procedures for:
- FAISS vector indices (T-098)
- SQLite databases (T-099)
- Unified backup scheduler (T-100)
"""

from infrastructure.backup.faiss_backup import (
    FAISSBackupManager,
    BackupMetadata,
    LocalStorageBackend,
    S3StorageBackend,
    create_faiss_backup_manager,
)
from infrastructure.backup.sqlite_backup import (
    SQLiteBackupManager,
    SQLiteBackupMetadata,
    create_sqlite_backup_manager,
)
from infrastructure.backup.scheduler import (
    BackupScheduler,
    BackupJobConfig,
    BackupJobResult,
    BackupHealth,
    BackupStatus,
    create_backup_scheduler,
    get_default_backup_jobs,
)

__all__ = [
    # FAISS backup
    "FAISSBackupManager",
    "BackupMetadata",
    "LocalStorageBackend",
    "S3StorageBackend",
    "create_faiss_backup_manager",
    # SQLite backup
    "SQLiteBackupManager",
    "SQLiteBackupMetadata",
    "create_sqlite_backup_manager",
    # Scheduler
    "BackupScheduler",
    "BackupJobConfig",
    "BackupJobResult",
    "BackupHealth",
    "BackupStatus",
    "create_backup_scheduler",
    "get_default_backup_jobs",
]
