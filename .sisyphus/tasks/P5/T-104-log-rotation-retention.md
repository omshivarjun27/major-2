# T-104: Log Rotation/Retention

## Status: completed

## Objective
Implement log rotation and retention policies with TimedRotatingFileHandler, gzip compression, configurable retention (30 days default), max file size (100MB), and PII scrubbing before archival.

## Deliverables

### 1. Log Rotation Module (`shared/logging/rotation.py`)
- **Size**: 537 lines
- **Features**:
  - `LogRotationConfig` - Dataclass for rotation configuration
  - `CompressedTimedRotatingFileHandler` - Daily rotation with gzip compression
  - `SizeAndTimeRotatingHandler` - Hybrid rotation (size + time)
  - `configure_file_logging()` - Easy setup function
  - `cleanup_old_logs()` - Manual cleanup utility
  - `get_log_stats()` - Log directory statistics

### 2. Key Features

#### Rotation Policies
- **Time-based**: Daily rotation at midnight
- **Size-based**: Rotate when file exceeds 100MB (configurable)
- **Hybrid**: Combined time + size rotation

#### Compression
- Automatic gzip compression of rotated files
- Background compression thread (non-blocking)
- Original files removed after successful compression

#### Retention
- Configurable retention period (default: 30 days)
- Automatic cleanup of expired files
- Manual cleanup utility function

#### PII Protection
- PII scrubbing filter applied to file handler
- Logs are sanitized before writing to disk
- Consistent with existing PIIScrubFilter from logging_config.py

### 3. Configuration Options
```python
@dataclass
class LogRotationConfig:
    log_dir: str = "logs"               # Log directory
    retention_days: int = 30            # Days to keep logs
    max_size_mb: int = 100              # Max file size in MB
    backup_count: int = 5               # Backup files per day
    compress_archives: bool = True      # Gzip old files
    pii_scrub: bool = True              # Enable PII scrubbing
    json_format: bool = True            # Use JSON formatter
    log_level: str = "INFO"             # Log level
    service_name: str = "voice-vision"  # Service name for files
```

### 4. Usage Examples
```python
# Simple setup
from shared.logging import configure_file_logging
configure_file_logging()

# Custom configuration
from shared.logging import LogRotationConfig, configure_file_logging
config = LogRotationConfig(
    log_dir="/var/log/voice-vision",
    retention_days=14,
    max_size_mb=50,
)
configure_file_logging(config)

# Manual cleanup
from shared.logging import cleanup_old_logs, get_log_stats
deleted = cleanup_old_logs(retention_days=7, dry_run=True)
stats = get_log_stats()
```

### 5. Module Exports Updated
- Updated `shared/logging/__init__.py` with rotation exports

## Integration
- Integrates with existing `StructuredJSONFormatter`
- Integrates with existing `PIIScrubFilter`
- Works alongside console logging
- Can be used independently or with `configure_logging()`

## Verification
- [x] Daily rotation at midnight
- [x] Size-based rotation at 100MB
- [x] Gzip compression of archives
- [x] 30-day retention policy
- [x] PII scrubbing applied
- [x] JSON format support
- [x] Module exports updated

## Completion Date
2026-02-28
