# T-100: Backup Scheduler Orchestrator

## Metadata
- **Phase**: P5
- **Cluster**: CL-INF
- **Risk Tier**: Medium
- **Upstream Deps**: [T-098, T-099]
- **Downstream Impact**: [T-108]
- **Current State**: completed

## Objective

Create a unified backup scheduler that orchestrates FAISS and SQLite backup jobs. Implement `infrastructure/backup/scheduler.py` using APScheduler with configurable cron expressions. Add backup health monitoring: track last successful backup time, backup size, duration. Alert if any backup is overdue by more than 24 hours. Implement backup verification by performing a test restore to a temporary location and validating data integrity.

## Acceptance Criteria

1. ✅ BackupScheduler class with job registration/management
2. ✅ Configurable cron expressions per job
3. ✅ Health monitoring with overdue detection
4. ✅ Backup success/failure callbacks
5. ✅ Automatic cleanup of old backups
6. ✅ Backup verification after completion
7. ✅ Test restore capability
8. ✅ Prometheus metrics integration
9. ✅ Default job configurations for Voice & Vision Assistant
10. ✅ Unit tests (22 tests)

## Implementation Notes

Created `infrastructure/backup/scheduler.py` with:

**Data Classes:**
- `BackupStatus`: Enum (PENDING, RUNNING, SUCCESS, FAILED, SKIPPED)
- `BackupJobResult`: Execution result with timing and metadata
- `BackupHealth`: System health status with overdue detection
- `BackupJobConfig`: Job configuration with cron expression

**BackupScheduler methods:**
- `register_job()`: Add a backup job
- `unregister_job()`: Remove a backup job
- `run_backup()`: Execute a job immediately
- `run_all_now()`: Execute all jobs
- `get_health()`: Get system health status
- `get_job_status()`: Get last result for a job
- `test_restore()`: Verify restore capability
- `start()`: Start APScheduler
- `stop()`: Stop scheduler

**Default Jobs:**
- `faiss_memory`: Daily at 2:00 AM
- `sqlite_consent`: Daily at 2:15 AM
- `sqlite_memory_meta`: Daily at 2:30 AM
- `sqlite_cache`: Daily at 2:45 AM (7 day retention)

## Test Requirements

- ✅ Unit: tests/unit/test_backup_scheduler.py with 22 tests
