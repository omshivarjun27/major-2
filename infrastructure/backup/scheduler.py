"""Unified backup scheduler for FAISS and SQLite backups.

Orchestrates scheduled backups using APScheduler with configurable cron
expressions. Provides health monitoring, backup verification, and alerting.

Task: T-100 - Backup Scheduler Orchestrator
"""

from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Backup Job Status
# ─────────────────────────────────────────────────────────────────────────────

class BackupStatus(Enum):
    """Status of a backup job."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class BackupJobResult:
    """Result of a backup job execution."""
    job_id: str
    job_type: str  # "faiss" or "sqlite"
    target_name: str
    status: BackupStatus
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: float = 0.0
    backup_id: Optional[str] = None
    compressed_size_bytes: int = 0
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "target_name": self.target_name,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": round(self.duration_seconds, 2),
            "backup_id": self.backup_id,
            "compressed_size_bytes": self.compressed_size_bytes,
            "error_message": self.error_message,
        }


@dataclass
class BackupHealth:
    """Health status of backup system."""
    last_successful_backup: Optional[str] = None
    last_backup_attempt: Optional[str] = None
    total_backups_today: int = 0
    failed_backups_today: int = 0
    total_backup_size_bytes: int = 0
    is_healthy: bool = True
    overdue_jobs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "last_successful_backup": self.last_successful_backup,
            "last_backup_attempt": self.last_backup_attempt,
            "total_backups_today": self.total_backups_today,
            "failed_backups_today": self.failed_backups_today,
            "total_backup_size_bytes": self.total_backup_size_bytes,
            "is_healthy": self.is_healthy,
            "overdue_jobs": self.overdue_jobs,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Backup Job Configuration
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BackupJobConfig:
    """Configuration for a scheduled backup job."""
    job_id: str
    job_type: str  # "faiss" or "sqlite"
    target_name: str
    target_path: Path
    cron_expression: str  # e.g., "0 2 * * *" for 2 AM daily
    enabled: bool = True
    retention_days: int = 30
    verify_after_backup: bool = True
    extra_config: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BackupJobConfig":
        """Create from dictionary."""
        return cls(
            job_id=data["job_id"],
            job_type=data["job_type"],
            target_name=data["target_name"],
            target_path=Path(data["target_path"]),
            cron_expression=data.get("cron_expression", "0 2 * * *"),
            enabled=data.get("enabled", True),
            retention_days=data.get("retention_days", 30),
            verify_after_backup=data.get("verify_after_backup", True),
            extra_config=data.get("extra_config", {}),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Backup Scheduler
# ─────────────────────────────────────────────────────────────────────────────

class BackupScheduler:
    """Unified scheduler for FAISS and SQLite backups.

    Features:
    - Configurable cron schedules per job
    - Health monitoring with overdue detection
    - Automatic cleanup of old backups
    - Backup verification after completion
    - Prometheus metrics integration
    - Alert callbacks for failures
    """

    def __init__(
        self,
        storage_backend: str = "local",
        local_backup_path: Optional[str] = None,
        s3_bucket: Optional[str] = None,
        s3_endpoint: Optional[str] = None,
        overdue_threshold_hours: int = 24,
        on_backup_complete: Optional[Callable[[BackupJobResult], None]] = None,
        on_backup_failed: Optional[Callable[[BackupJobResult], None]] = None,
    ):
        """Initialize backup scheduler.

        Args:
            storage_backend: Storage backend type ("local" or "s3")
            local_backup_path: Path for local backups
            s3_bucket: S3 bucket for remote backups
            s3_endpoint: S3 endpoint URL
            overdue_threshold_hours: Hours after which a backup is considered overdue
            on_backup_complete: Callback for successful backups
            on_backup_failed: Callback for failed backups
        """
        self._storage_backend = storage_backend
        self._local_backup_path = local_backup_path or os.environ.get(
            "BACKUP_PATH", "data/backups"
        )
        self._s3_bucket = s3_bucket
        self._s3_endpoint = s3_endpoint
        self._overdue_threshold_hours = overdue_threshold_hours
        self._on_backup_complete = on_backup_complete
        self._on_backup_failed = on_backup_failed

        # Job registry
        self._jobs: Dict[str, BackupJobConfig] = {}
        self._job_results: Dict[str, BackupJobResult] = {}
        self._last_run_times: Dict[str, datetime] = {}

        # Scheduler state
        self._scheduler = None
        self._running = False
        self._lock = threading.RLock()

        # Initialize backup managers lazily
        self._faiss_manager = None
        self._sqlite_manager = None

    def _get_faiss_manager(self):
        """Lazily initialize FAISS backup manager."""
        if self._faiss_manager is None:
            from infrastructure.backup.faiss_backup import create_faiss_backup_manager
            self._faiss_manager = create_faiss_backup_manager(
                backend=self._storage_backend,
                local_path=f"{self._local_backup_path}/faiss",
                s3_bucket=self._s3_bucket,
                s3_endpoint=self._s3_endpoint,
            )
        return self._faiss_manager

    def _get_sqlite_manager(self):
        """Lazily initialize SQLite backup manager."""
        if self._sqlite_manager is None:
            from infrastructure.backup.sqlite_backup import create_sqlite_backup_manager
            self._sqlite_manager = create_sqlite_backup_manager(
                backend=self._storage_backend,
                local_path=f"{self._local_backup_path}/sqlite",
                s3_bucket=self._s3_bucket,
                s3_endpoint=self._s3_endpoint,
            )
        return self._sqlite_manager

    def register_job(self, config: BackupJobConfig) -> None:
        """Register a backup job.

        Args:
            config: Job configuration
        """
        with self._lock:
            self._jobs[config.job_id] = config
            logger.info(
                "Registered backup job: %s (%s: %s) - cron: %s",
                config.job_id,
                config.job_type,
                config.target_name,
                config.cron_expression,
            )

    def unregister_job(self, job_id: str) -> bool:
        """Unregister a backup job.

        Args:
            job_id: Job ID to remove

        Returns:
            True if job was removed
        """
        with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
                logger.info("Unregistered backup job: %s", job_id)
                return True
            return False

    def run_backup(self, job_id: str) -> BackupJobResult:
        """Run a backup job immediately.

        Args:
            job_id: Job ID to run

        Returns:
            BackupJobResult with execution details
        """
        with self._lock:
            if job_id not in self._jobs:
                return BackupJobResult(
                    job_id=job_id,
                    job_type="unknown",
                    target_name="unknown",
                    status=BackupStatus.FAILED,
                    error_message=f"Job not found: {job_id}",
                )

            config = self._jobs[job_id]

        if not config.enabled:
            return BackupJobResult(
                job_id=job_id,
                job_type=config.job_type,
                target_name=config.target_name,
                status=BackupStatus.SKIPPED,
                error_message="Job is disabled",
            )

        started_at = datetime.now(timezone.utc)
        result = BackupJobResult(
            job_id=job_id,
            job_type=config.job_type,
            target_name=config.target_name,
            status=BackupStatus.RUNNING,
            started_at=started_at.isoformat(),
        )

        try:
            if config.job_type == "faiss":
                metadata = self._run_faiss_backup(config)
            elif config.job_type == "sqlite":
                metadata = self._run_sqlite_backup(config)
            else:
                raise ValueError(f"Unknown job type: {config.job_type}")

            if metadata:
                result.status = BackupStatus.SUCCESS
                result.backup_id = metadata.backup_id
                result.compressed_size_bytes = metadata.compressed_size_bytes

                # Verify if configured
                if config.verify_after_backup:
                    self._verify_backup(config, metadata.backup_id)

                # Cleanup old backups
                self._cleanup_old_backups(config)
            else:
                result.status = BackupStatus.FAILED
                result.error_message = "Backup returned no metadata"

        except Exception as e:
            result.status = BackupStatus.FAILED
            result.error_message = str(e)
            logger.error("Backup job %s failed: %s", job_id, e, exc_info=True)

        completed_at = datetime.now(timezone.utc)
        result.completed_at = completed_at.isoformat()
        result.duration_seconds = (completed_at - started_at).total_seconds()

        # Update state
        with self._lock:
            self._job_results[job_id] = result
            self._last_run_times[job_id] = completed_at

        # Emit metrics
        self._emit_metrics(result)

        # Call callbacks
        if result.status == BackupStatus.SUCCESS:
            if self._on_backup_complete:
                try:
                    self._on_backup_complete(result)
                except Exception as e:
                    logger.error("Backup complete callback failed: %s", e)
        elif result.status == BackupStatus.FAILED:
            if self._on_backup_failed:
                try:
                    self._on_backup_failed(result)
                except Exception as e:
                    logger.error("Backup failed callback failed: %s", e)

        return result

    def _run_faiss_backup(self, config: BackupJobConfig):
        """Run FAISS backup."""
        manager = self._get_faiss_manager()
        return manager.backup(
            index_path=config.target_path,
            index_name=config.target_name,
            vector_count=config.extra_config.get("vector_count", 0),
            dimension=config.extra_config.get("dimension", 0),
            incremental=config.extra_config.get("incremental", True),
        )

    def _run_sqlite_backup(self, config: BackupJobConfig):
        """Run SQLite backup."""
        manager = self._get_sqlite_manager()
        return manager.backup(
            db_path=config.target_path,
            database_name=config.target_name,
            include_wal=config.extra_config.get("include_wal", True),
        )

    def _verify_backup(self, config: BackupJobConfig, backup_id: str) -> bool:
        """Verify a backup after creation."""
        try:
            if config.job_type == "faiss":
                return self._get_faiss_manager().verify_backup(backup_id, config.target_name)
            elif config.job_type == "sqlite":
                return self._get_sqlite_manager().verify_backup(backup_id, config.target_name)
            return False
        except Exception as e:
            logger.error("Backup verification failed for %s: %s", backup_id, e)
            return False

    def _cleanup_old_backups(self, config: BackupJobConfig) -> int:
        """Clean up old backups for a job."""
        try:
            if config.job_type == "faiss":
                return self._get_faiss_manager().cleanup_old_backups(config.target_name)
            elif config.job_type == "sqlite":
                return self._get_sqlite_manager().cleanup_old_backups(config.target_name)
            return 0
        except Exception as e:
            logger.error("Backup cleanup failed for %s: %s", config.target_name, e)
            return 0

    def _emit_metrics(self, result: BackupJobResult) -> None:
        """Emit Prometheus metrics for backup result."""
        try:
            from infrastructure.monitoring import get_metrics
            metrics = get_metrics()

            # Record backup size
            if result.compressed_size_bytes > 0:
                metrics.set_queue_size(
                    f"backup_{result.job_type}_{result.target_name}_size",
                    result.compressed_size_bytes,
                )

            # Record duration as histogram
            if result.duration_seconds > 0:
                metrics.record_inference(
                    f"backup_{result.job_type}",
                    result.duration_seconds,
                )

            # Record errors
            if result.status == BackupStatus.FAILED:
                metrics.record_error("backup", f"{result.job_type}_failure")

        except Exception as e:
            logger.debug("Failed to emit backup metrics: %s", e)

    def get_health(self) -> BackupHealth:
        """Get backup system health status.

        Returns:
            BackupHealth with current status
        """
        health = BackupHealth()
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        with self._lock:
            for job_id, result in self._job_results.items():
                # Track last successful backup
                if result.status == BackupStatus.SUCCESS and result.completed_at:
                    if (health.last_successful_backup is None or
                        result.completed_at > health.last_successful_backup):
                        health.last_successful_backup = result.completed_at

                # Track last attempt
                if result.completed_at:
                    if (health.last_backup_attempt is None or
                        result.completed_at > health.last_backup_attempt):
                        health.last_backup_attempt = result.completed_at

                # Count today's backups
                if result.completed_at:
                    completed = datetime.fromisoformat(result.completed_at.replace("Z", "+00:00"))
                    if completed >= today_start:
                        health.total_backups_today += 1
                        if result.status == BackupStatus.FAILED:
                            health.failed_backups_today += 1

                # Track total size
                health.total_backup_size_bytes += result.compressed_size_bytes

            # Check for overdue jobs
            overdue_threshold = now.timestamp() - (self._overdue_threshold_hours * 3600)
            for job_id, config in self._jobs.items():
                if not config.enabled:
                    continue

                last_run = self._last_run_times.get(job_id)
                if last_run is None or last_run.timestamp() < overdue_threshold:
                    health.overdue_jobs.append(job_id)

        # Determine overall health
        health.is_healthy = (
            health.failed_backups_today == 0 and
            len(health.overdue_jobs) == 0
        )

        return health

    def get_job_status(self, job_id: str) -> Optional[BackupJobResult]:
        """Get the last result for a job.

        Args:
            job_id: Job ID

        Returns:
            Last BackupJobResult or None
        """
        with self._lock:
            return self._job_results.get(job_id)

    def get_all_job_statuses(self) -> Dict[str, BackupJobResult]:
        """Get all job statuses.

        Returns:
            Dictionary of job_id to BackupJobResult
        """
        with self._lock:
            return dict(self._job_results)

    def start(self) -> None:
        """Start the scheduler.

        Requires APScheduler to be installed.
        """
        if self._running:
            logger.warning("Scheduler already running")
            return

        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.cron import CronTrigger
        except ImportError:
            raise RuntimeError("APScheduler not installed. Run: pip install apscheduler")

        self._scheduler = BackgroundScheduler()

        with self._lock:
            for job_id, config in self._jobs.items():
                if config.enabled:
                    # Parse cron expression
                    parts = config.cron_expression.split()
                    if len(parts) == 5:
                        trigger = CronTrigger(
                            minute=parts[0],
                            hour=parts[1],
                            day=parts[2],
                            month=parts[3],
                            day_of_week=parts[4],
                        )
                        self._scheduler.add_job(
                            self.run_backup,
                            trigger=trigger,
                            args=[job_id],
                            id=job_id,
                            name=f"backup_{config.job_type}_{config.target_name}",
                        )
                        logger.info("Scheduled job %s: %s", job_id, config.cron_expression)

        self._scheduler.start()
        self._running = True
        logger.info("Backup scheduler started with %d jobs", len(self._jobs))

    def stop(self) -> None:
        """Stop the scheduler."""
        if self._scheduler and self._running:
            self._scheduler.shutdown(wait=True)
            self._running = False
            logger.info("Backup scheduler stopped")

    def run_all_now(self) -> Dict[str, BackupJobResult]:
        """Run all registered backup jobs immediately.

        Returns:
            Dictionary of job_id to BackupJobResult
        """
        results = {}
        with self._lock:
            job_ids = list(self._jobs.keys())

        for job_id in job_ids:
            results[job_id] = self.run_backup(job_id)

        return results

    def test_restore(self, job_id: str) -> bool:
        """Test restore capability for a job.

        Performs a test restore to a temporary location and validates.

        Args:
            job_id: Job ID to test

        Returns:
            True if restore test passed
        """
        import tempfile

        with self._lock:
            if job_id not in self._jobs:
                logger.error("Job not found: %s", job_id)
                return False
            config = self._jobs[job_id]

        try:
            # Get latest backup
            if config.job_type == "faiss":
                manager = self._get_faiss_manager()
                backups = manager.list_backups(config.target_name)
            elif config.job_type == "sqlite":
                manager = self._get_sqlite_manager()
                backups = manager.list_backups(config.target_name)
            else:
                logger.error("Unknown job type: %s", config.job_type)
                return False

            if not backups:
                logger.warning("No backups found for %s", config.target_name)
                return False

            latest = backups[0]

            # Test restore to temp location
            with tempfile.TemporaryDirectory() as tmpdir:
                restore_path = Path(tmpdir) / "test_restore"

                if config.job_type == "faiss":
                    success = manager.restore(
                        latest.backup_id,
                        config.target_name,
                        restore_path,
                        verify=True,
                    )
                else:
                    success = manager.restore(
                        latest.backup_id,
                        config.target_name,
                        restore_path,
                        verify=True,
                    )

                if success:
                    logger.info(
                        "Restore test passed for %s (backup: %s)",
                        job_id,
                        latest.backup_id,
                    )
                else:
                    logger.error("Restore test failed for %s", job_id)

                return success

        except Exception as e:
            logger.error("Restore test failed for %s: %s", job_id, e)
            return False


# ─────────────────────────────────────────────────────────────────────────────
# Factory Function
# ─────────────────────────────────────────────────────────────────────────────

def create_backup_scheduler(
    storage_backend: str = "local",
    local_backup_path: Optional[str] = None,
    s3_bucket: Optional[str] = None,
    overdue_threshold_hours: int = 24,
) -> BackupScheduler:
    """Create a configured backup scheduler.

    Args:
        storage_backend: "local" or "s3"
        local_backup_path: Path for local backups
        s3_bucket: S3 bucket name
        overdue_threshold_hours: Overdue threshold

    Returns:
        Configured BackupScheduler
    """
    return BackupScheduler(
        storage_backend=storage_backend,
        local_backup_path=local_backup_path,
        s3_bucket=s3_bucket,
        overdue_threshold_hours=overdue_threshold_hours,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Default Job Configurations
# ─────────────────────────────────────────────────────────────────────────────

def get_default_backup_jobs() -> List[BackupJobConfig]:
    """Get default backup job configurations for Voice & Vision Assistant.

    Returns:
        List of default BackupJobConfig
    """
    return [
        # FAISS memory index - daily at 2 AM
        BackupJobConfig(
            job_id="faiss_memory",
            job_type="faiss",
            target_name="memory",
            target_path=Path("data/faiss/memory.index"),
            cron_expression="0 2 * * *",
            retention_days=30,
            extra_config={"incremental": True},
        ),
        # SQLite consent store - daily at 2:15 AM
        BackupJobConfig(
            job_id="sqlite_consent",
            job_type="sqlite",
            target_name="consent",
            target_path=Path("data/consent.db"),
            cron_expression="15 2 * * *",
            retention_days=30,
        ),
        # SQLite memory metadata - daily at 2:30 AM
        BackupJobConfig(
            job_id="sqlite_memory_meta",
            job_type="sqlite",
            target_name="memory_metadata",
            target_path=Path("data/memory_metadata.db"),
            cron_expression="30 2 * * *",
            retention_days=30,
        ),
        # SQLite cache - daily at 2:45 AM
        BackupJobConfig(
            job_id="sqlite_cache",
            job_type="sqlite",
            target_name="cache",
            target_path=Path("data/cache.db"),
            cron_expression="45 2 * * *",
            retention_days=7,  # Shorter retention for cache
        ),
    ]
