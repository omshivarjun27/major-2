"""Unit tests for backup scheduler module.

Tests T-100: Backup Scheduler Orchestrator
"""

import sqlite3
from pathlib import Path


def create_test_database(path: Path) -> None:
    """Create a minimal test SQLite database."""
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, data TEXT)")
    conn.execute("INSERT INTO test (data) VALUES ('test')")
    conn.commit()
    conn.close()


def create_test_faiss_index(path: Path) -> None:
    """Create a mock FAISS index file."""
    path.write_bytes(b"mock faiss index data" * 50)


class TestBackupJobResult:
    """Tests for BackupJobResult dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        from infrastructure.backup.scheduler import BackupJobResult, BackupStatus

        result = BackupJobResult(
            job_id="test_job",
            job_type="sqlite",
            target_name="test_db",
            status=BackupStatus.SUCCESS,
            started_at="2024-01-01T12:00:00+00:00",
            completed_at="2024-01-01T12:00:10+00:00",
            duration_seconds=10.5,
            backup_id="backup_123",
            compressed_size_bytes=1024,
        )

        d = result.to_dict()

        assert d["job_id"] == "test_job"
        assert d["status"] == "success"
        assert d["duration_seconds"] == 10.5


class TestBackupHealth:
    """Tests for BackupHealth dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        from infrastructure.backup.scheduler import BackupHealth

        health = BackupHealth(
            last_successful_backup="2024-01-01T12:00:00+00:00",
            total_backups_today=5,
            failed_backups_today=1,
            is_healthy=False,
            overdue_jobs=["job1", "job2"],
        )

        d = health.to_dict()

        assert d["total_backups_today"] == 5
        assert d["is_healthy"] is False
        assert len(d["overdue_jobs"]) == 2


class TestBackupJobConfig:
    """Tests for BackupJobConfig dataclass."""

    def test_from_dict(self):
        """Test creation from dictionary."""
        from infrastructure.backup.scheduler import BackupJobConfig

        data = {
            "job_id": "test_job",
            "job_type": "sqlite",
            "target_name": "test_db",
            "target_path": "/data/test.db",
            "cron_expression": "0 3 * * *",
            "enabled": True,
            "retention_days": 14,
        }

        config = BackupJobConfig.from_dict(data)

        assert config.job_id == "test_job"
        assert config.cron_expression == "0 3 * * *"
        assert config.retention_days == 14


class TestBackupScheduler:
    """Tests for BackupScheduler class."""

    def test_initialization(self, tmp_path):
        """Test scheduler initialization."""
        from infrastructure.backup.scheduler import BackupScheduler

        scheduler = BackupScheduler(
            storage_backend="local",
            local_backup_path=str(tmp_path / "backups"),
        )

        assert scheduler._storage_backend == "local"
        assert not scheduler._running

    def test_register_job(self, tmp_path):
        """Test registering a backup job."""
        from infrastructure.backup.scheduler import BackupJobConfig, BackupScheduler

        scheduler = BackupScheduler(local_backup_path=str(tmp_path / "backups"))

        config = BackupJobConfig(
            job_id="test_job",
            job_type="sqlite",
            target_name="test",
            target_path=tmp_path / "test.db",
            cron_expression="0 2 * * *",
        )

        scheduler.register_job(config)

        assert "test_job" in scheduler._jobs

    def test_unregister_job(self, tmp_path):
        """Test unregistering a backup job."""
        from infrastructure.backup.scheduler import BackupJobConfig, BackupScheduler

        scheduler = BackupScheduler(local_backup_path=str(tmp_path / "backups"))

        config = BackupJobConfig(
            job_id="test_job",
            job_type="sqlite",
            target_name="test",
            target_path=tmp_path / "test.db",
            cron_expression="0 2 * * *",
        )

        scheduler.register_job(config)
        result = scheduler.unregister_job("test_job")

        assert result is True
        assert "test_job" not in scheduler._jobs

    def test_unregister_nonexistent_job(self, tmp_path):
        """Test unregistering a non-existent job."""
        from infrastructure.backup.scheduler import BackupScheduler

        scheduler = BackupScheduler(local_backup_path=str(tmp_path / "backups"))
        result = scheduler.unregister_job("nonexistent")

        assert result is False

    def test_run_sqlite_backup(self, tmp_path):
        """Test running a SQLite backup job."""
        from infrastructure.backup.scheduler import (
            BackupJobConfig,
            BackupScheduler,
            BackupStatus,
        )

        # Create test database
        db_path = tmp_path / "test.db"
        create_test_database(db_path)

        scheduler = BackupScheduler(local_backup_path=str(tmp_path / "backups"))

        config = BackupJobConfig(
            job_id="sqlite_test",
            job_type="sqlite",
            target_name="test",
            target_path=db_path,
            cron_expression="0 2 * * *",
            verify_after_backup=False,  # Skip verification for speed
        )

        scheduler.register_job(config)
        result = scheduler.run_backup("sqlite_test")

        assert result.status == BackupStatus.SUCCESS
        assert result.backup_id is not None
        assert result.compressed_size_bytes > 0

    def test_run_faiss_backup(self, tmp_path):
        """Test running a FAISS backup job."""
        from infrastructure.backup.scheduler import (
            BackupJobConfig,
            BackupScheduler,
            BackupStatus,
        )

        # Create mock FAISS index
        index_path = tmp_path / "index.faiss"
        create_test_faiss_index(index_path)

        scheduler = BackupScheduler(local_backup_path=str(tmp_path / "backups"))

        config = BackupJobConfig(
            job_id="faiss_test",
            job_type="faiss",
            target_name="test_index",
            target_path=index_path,
            cron_expression="0 2 * * *",
            verify_after_backup=False,
        )

        scheduler.register_job(config)
        result = scheduler.run_backup("faiss_test")

        assert result.status == BackupStatus.SUCCESS
        assert result.backup_id is not None

    def test_run_backup_unknown_job(self, tmp_path):
        """Test running a non-existent job."""
        from infrastructure.backup.scheduler import BackupScheduler, BackupStatus

        scheduler = BackupScheduler(local_backup_path=str(tmp_path / "backups"))
        result = scheduler.run_backup("nonexistent")

        assert result.status == BackupStatus.FAILED
        assert "not found" in result.error_message

    def test_run_disabled_job(self, tmp_path):
        """Test running a disabled job."""
        from infrastructure.backup.scheduler import (
            BackupJobConfig,
            BackupScheduler,
            BackupStatus,
        )

        scheduler = BackupScheduler(local_backup_path=str(tmp_path / "backups"))

        config = BackupJobConfig(
            job_id="disabled_job",
            job_type="sqlite",
            target_name="test",
            target_path=tmp_path / "test.db",
            cron_expression="0 2 * * *",
            enabled=False,
        )

        scheduler.register_job(config)
        result = scheduler.run_backup("disabled_job")

        assert result.status == BackupStatus.SKIPPED

    def test_get_job_status(self, tmp_path):
        """Test getting job status."""
        from infrastructure.backup.scheduler import (
            BackupJobConfig,
            BackupScheduler,
        )

        # Create test database
        db_path = tmp_path / "test.db"
        create_test_database(db_path)

        scheduler = BackupScheduler(local_backup_path=str(tmp_path / "backups"))

        config = BackupJobConfig(
            job_id="test_job",
            job_type="sqlite",
            target_name="test",
            target_path=db_path,
            cron_expression="0 2 * * *",
            verify_after_backup=False,
        )

        scheduler.register_job(config)
        scheduler.run_backup("test_job")

        status = scheduler.get_job_status("test_job")

        assert status is not None
        assert status.job_id == "test_job"

    def test_get_health(self, tmp_path):
        """Test getting health status."""
        from infrastructure.backup.scheduler import (
            BackupJobConfig,
            BackupScheduler,
        )

        # Create test database
        db_path = tmp_path / "test.db"
        create_test_database(db_path)

        scheduler = BackupScheduler(
            local_backup_path=str(tmp_path / "backups"),
            overdue_threshold_hours=24,
        )

        config = BackupJobConfig(
            job_id="test_job",
            job_type="sqlite",
            target_name="test",
            target_path=db_path,
            cron_expression="0 2 * * *",
            verify_after_backup=False,
        )

        scheduler.register_job(config)
        scheduler.run_backup("test_job")

        health = scheduler.get_health()

        assert health.total_backups_today >= 1
        assert health.is_healthy is True

    def test_health_detects_overdue_jobs(self, tmp_path):
        """Test that health detects overdue jobs."""
        from infrastructure.backup.scheduler import (
            BackupJobConfig,
            BackupScheduler,
        )

        scheduler = BackupScheduler(
            local_backup_path=str(tmp_path / "backups"),
            overdue_threshold_hours=1,  # 1 hour threshold
        )

        config = BackupJobConfig(
            job_id="overdue_job",
            job_type="sqlite",
            target_name="test",
            target_path=tmp_path / "test.db",
            cron_expression="0 2 * * *",
            enabled=True,
        )

        scheduler.register_job(config)
        # Don't run the job - it should be overdue

        health = scheduler.get_health()

        assert "overdue_job" in health.overdue_jobs
        assert health.is_healthy is False

    def test_run_all_now(self, tmp_path):
        """Test running all jobs immediately."""
        from infrastructure.backup.scheduler import (
            BackupJobConfig,
            BackupScheduler,
            BackupStatus,
        )

        # Create test files
        db_path = tmp_path / "test.db"
        create_test_database(db_path)

        index_path = tmp_path / "index.faiss"
        create_test_faiss_index(index_path)

        scheduler = BackupScheduler(local_backup_path=str(tmp_path / "backups"))

        scheduler.register_job(BackupJobConfig(
            job_id="sqlite_job",
            job_type="sqlite",
            target_name="test_db",
            target_path=db_path,
            cron_expression="0 2 * * *",
            verify_after_backup=False,
        ))

        scheduler.register_job(BackupJobConfig(
            job_id="faiss_job",
            job_type="faiss",
            target_name="test_index",
            target_path=index_path,
            cron_expression="0 3 * * *",
            verify_after_backup=False,
        ))

        results = scheduler.run_all_now()

        assert len(results) == 2
        assert results["sqlite_job"].status == BackupStatus.SUCCESS
        assert results["faiss_job"].status == BackupStatus.SUCCESS


class TestBackupCallbacks:
    """Tests for backup callbacks."""

    def test_on_backup_complete_callback(self, tmp_path):
        """Test that success callback is called."""
        from infrastructure.backup.scheduler import (
            BackupJobConfig,
            BackupScheduler,
            BackupStatus,
        )

        callback_results = []

        def on_complete(result):
            callback_results.append(result)

        db_path = tmp_path / "test.db"
        create_test_database(db_path)

        scheduler = BackupScheduler(
            local_backup_path=str(tmp_path / "backups"),
            on_backup_complete=on_complete,
        )

        config = BackupJobConfig(
            job_id="test_job",
            job_type="sqlite",
            target_name="test",
            target_path=db_path,
            cron_expression="0 2 * * *",
            verify_after_backup=False,
        )

        scheduler.register_job(config)
        scheduler.run_backup("test_job")

        assert len(callback_results) == 1
        assert callback_results[0].status == BackupStatus.SUCCESS

    def test_on_backup_failed_callback(self, tmp_path):
        """Test that failure callback is called."""
        from infrastructure.backup.scheduler import (
            BackupJobConfig,
            BackupScheduler,
            BackupStatus,
        )

        callback_results = []

        def on_failed(result):
            callback_results.append(result)

        scheduler = BackupScheduler(
            local_backup_path=str(tmp_path / "backups"),
            on_backup_failed=on_failed,
        )

        # Register job with non-existent file
        config = BackupJobConfig(
            job_id="failing_job",
            job_type="sqlite",
            target_name="test",
            target_path=tmp_path / "nonexistent.db",
            cron_expression="0 2 * * *",
        )

        scheduler.register_job(config)
        scheduler.run_backup("failing_job")

        assert len(callback_results) == 1
        assert callback_results[0].status == BackupStatus.FAILED


class TestRestoreTest:
    """Tests for restore testing functionality."""

    def test_restore_test_success(self, tmp_path):
        """Test successful restore test."""
        from infrastructure.backup.scheduler import (
            BackupJobConfig,
            BackupScheduler,
        )

        db_path = tmp_path / "test.db"
        create_test_database(db_path)

        scheduler = BackupScheduler(local_backup_path=str(tmp_path / "backups"))

        config = BackupJobConfig(
            job_id="test_job",
            job_type="sqlite",
            target_name="test",
            target_path=db_path,
            cron_expression="0 2 * * *",
            verify_after_backup=False,
        )

        scheduler.register_job(config)
        scheduler.run_backup("test_job")

        result = scheduler.test_restore("test_job")

        assert result is True

    def test_restore_test_no_backups(self, tmp_path):
        """Test restore test with no backups."""
        from infrastructure.backup.scheduler import (
            BackupJobConfig,
            BackupScheduler,
        )

        scheduler = BackupScheduler(local_backup_path=str(tmp_path / "backups"))

        config = BackupJobConfig(
            job_id="empty_job",
            job_type="sqlite",
            target_name="empty",
            target_path=tmp_path / "test.db",
            cron_expression="0 2 * * *",
        )

        scheduler.register_job(config)
        # Don't run backup

        result = scheduler.test_restore("empty_job")

        assert result is False


class TestDefaultBackupJobs:
    """Tests for default backup job configurations."""

    def test_get_default_jobs(self):
        """Test getting default backup jobs."""
        from infrastructure.backup.scheduler import get_default_backup_jobs

        jobs = get_default_backup_jobs()

        assert len(jobs) == 4

        job_ids = [j.job_id for j in jobs]
        assert "faiss_memory" in job_ids
        assert "sqlite_consent" in job_ids
        assert "sqlite_memory_meta" in job_ids
        assert "sqlite_cache" in job_ids

    def test_default_jobs_have_cron(self):
        """Test that default jobs have cron expressions."""
        from infrastructure.backup.scheduler import get_default_backup_jobs

        jobs = get_default_backup_jobs()

        for job in jobs:
            assert job.cron_expression is not None
            parts = job.cron_expression.split()
            assert len(parts) == 5  # Standard cron format


class TestCreateBackupScheduler:
    """Tests for factory function."""

    def test_create_local_scheduler(self, tmp_path):
        """Test creating scheduler with local backend."""
        from infrastructure.backup.scheduler import create_backup_scheduler

        scheduler = create_backup_scheduler(
            storage_backend="local",
            local_backup_path=str(tmp_path / "backups"),
            overdue_threshold_hours=48,
        )

        assert scheduler is not None
        assert scheduler._overdue_threshold_hours == 48
