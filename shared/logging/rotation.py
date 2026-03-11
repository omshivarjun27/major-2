"""Log rotation and retention configuration for Voice & Vision Assistant.

Provides TimedRotatingFileHandler with daily rotation, gzip compression,
configurable retention policies, and PII scrubbing before archival.

Task: T-104 - Log Rotation/Retention

Usage::

    from shared.logging.rotation import configure_file_logging, LogRotationConfig

    config = LogRotationConfig(
        log_dir="logs",
        retention_days=30,
        max_size_mb=100,
        compress_archives=True,
    )
    configure_file_logging(config)
"""

from __future__ import annotations

import gzip
import logging
import os
import shutil
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Dict, List, Optional

from shared.logging.logging_config import (
    PIIScrubFilter,
    StructuredJSONFormatter,
)

logger = logging.getLogger(__name__)

# Default log directory
DEFAULT_LOG_DIR = "logs"

# Maximum log file size (100MB)
DEFAULT_MAX_SIZE_BYTES = 100 * 1024 * 1024

# Default retention period (30 days)
DEFAULT_RETENTION_DAYS = 30

# Backup count for size-based rotation
DEFAULT_BACKUP_COUNT = 5


@dataclass
class LogRotationConfig:
    """Configuration for log rotation and retention.

    Attributes:
        log_dir: Directory for log files
        retention_days: Number of days to retain logs
        max_size_mb: Maximum size per log file in MB
        backup_count: Number of backup files for size-based rotation
        compress_archives: Whether to gzip archived logs
        pii_scrub: Whether to scrub PII from logs
        json_format: Whether to use JSON format
        log_level: Logging level
        service_name: Service name for log files
    """
    log_dir: str = DEFAULT_LOG_DIR
    retention_days: int = DEFAULT_RETENTION_DAYS
    max_size_mb: int = 100
    backup_count: int = DEFAULT_BACKUP_COUNT
    compress_archives: bool = True
    pii_scrub: bool = True
    json_format: bool = True
    log_level: str = "INFO"
    service_name: str = "voice-vision"


class CompressedTimedRotatingFileHandler(TimedRotatingFileHandler):
    """TimedRotatingFileHandler with gzip compression support.

    Automatically compresses rotated log files to save disk space.
    Supports daily rotation with configurable retention.
    """

    def __init__(
        self,
        filename: str,
        when: str = "midnight",
        interval: int = 1,
        backupCount: int = DEFAULT_RETENTION_DAYS,
        encoding: Optional[str] = "utf-8",
        compress: bool = True,
        pii_scrub: bool = True,
    ):
        """Initialize the handler.

        Args:
            filename: Log file path
            when: Rotation interval type (midnight, H, D, etc.)
            interval: Rotation interval count
            backupCount: Number of backups to keep
            encoding: File encoding
            compress: Whether to gzip rotated files
            pii_scrub: Whether to apply PII scrubbing
        """
        super().__init__(
            filename,
            when=when,
            interval=interval,
            backupCount=backupCount,
            encoding=encoding,
        )
        self._compress = compress
        self._pii_scrub = pii_scrub
        self._compression_thread: Optional[threading.Thread] = None

    def doRollover(self) -> None:
        """Perform rollover with optional compression."""
        # Get the name of the file being rotated before super().doRollover()
        if self.stream:
            self.stream.close()
            self.stream = None  # type: ignore

        # Compute rotated file name
        current_time = int(time.time())
        dst_now = time.localtime(current_time)[-1]
        t = self.rolloverAt - self.interval
        if self.utc:
            time_tuple = time.gmtime(t)
        else:
            time_tuple = time.localtime(t)
            dst_then = time_tuple[-1]
            if dst_now != dst_then:
                if dst_now:
                    addend = 3600
                else:
                    addend = -3600
                time_tuple = time.localtime(t + addend)

        dfn = self.rotation_filename(self.baseFilename + "." + time.strftime(self.suffix, time_tuple))

        # Remove existing rotated file if present
        if os.path.exists(dfn):
            os.remove(dfn)

        # Rotate the file
        self.rotate(self.baseFilename, dfn)

        # Delete old files
        if self.backupCount > 0:
            for s in self.getFilesToDelete():
                os.remove(s)

        # Reopen stream
        self.stream = self._open()

        # Calculate next rollover
        newRolloverAt = self.computeRollover(current_time)
        while newRolloverAt <= current_time:
            newRolloverAt = newRolloverAt + self.interval

        # Handle DST
        if (self.when == "MIDNIGHT" or self.when.startswith("W")) and not self.utc:
            dst_at_rollover = time.localtime(newRolloverAt)[-1]
            if dst_now != dst_at_rollover:
                if not dst_now:
                    addend = -3600
                else:
                    addend = 3600
                newRolloverAt += addend

        self.rolloverAt = newRolloverAt

        # Compress in background thread
        if self._compress and os.path.exists(dfn):
            self._compression_thread = threading.Thread(
                target=self._compress_file,
                args=(dfn,),
                daemon=True,
            )
            self._compression_thread.start()

    def _compress_file(self, filepath: str) -> None:
        """Compress a file using gzip.

        Args:
            filepath: Path to file to compress
        """
        try:
            compressed_path = filepath + ".gz"

            with open(filepath, "rb") as f_in:
                with gzip.open(compressed_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # Remove original after successful compression
            os.remove(filepath)

            logger.debug("Compressed log file: %s -> %s", filepath, compressed_path)
        except Exception as e:
            logger.error("Failed to compress log file %s: %s", filepath, e)

    def getFilesToDelete(self) -> List[str]:
        """Get list of files to delete, including .gz files.

        Returns:
            List of file paths to delete
        """
        dir_name, base_name = os.path.split(self.baseFilename)
        file_names = os.listdir(dir_name)
        result = []
        prefix = base_name + "."
        plen = len(prefix)

        for file_name in file_names:
            if file_name[:plen] == prefix:
                # Include both regular and .gz files
                suffix = file_name[plen:]
                # Check if it matches date pattern or date pattern.gz
                if self.extMatch.match(suffix) or (
                    suffix.endswith(".gz") and self.extMatch.match(suffix[:-3])
                ):
                    result.append(os.path.join(dir_name, file_name))

        # Sort and return files to delete (keep backupCount newest)
        if len(result) <= self.backupCount:
            result = []
        else:
            result.sort()
            result = result[:len(result) - self.backupCount]

        return result


class SizeAndTimeRotatingHandler(logging.Handler):
    """Handler that rotates based on both size and time.

    Combines TimedRotatingFileHandler and RotatingFileHandler behavior:
    - Rotates daily at midnight
    - Also rotates if file exceeds max size
    - Compresses old files
    - Enforces retention policy
    """

    def __init__(
        self,
        filename: str,
        max_bytes: int = DEFAULT_MAX_SIZE_BYTES,
        backup_count: int = DEFAULT_BACKUP_COUNT,
        retention_days: int = DEFAULT_RETENTION_DAYS,
        encoding: str = "utf-8",
        compress: bool = True,
    ):
        """Initialize the handler.

        Args:
            filename: Base log file path
            max_bytes: Maximum file size before rotation
            backup_count: Number of size-based backups per day
            retention_days: Days to retain logs
            encoding: File encoding
            compress: Whether to compress rotated files
        """
        super().__init__()
        self._filename = filename
        self._max_bytes = max_bytes
        self._backup_count = backup_count
        self._retention_days = retention_days
        self._encoding = encoding
        self._compress = compress
        self._lock = threading.RLock()

        # Ensure directory exists
        dir_name = os.path.dirname(filename)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        # Initialize internal handlers
        self._setup_handlers()

        # Track current date for time-based rotation
        self._current_date = datetime.now(timezone.utc).date()

    def _setup_handlers(self) -> None:
        """Set up internal file handler."""
        self._file_handler = RotatingFileHandler(
            self._filename,
            maxBytes=self._max_bytes,
            backupCount=self._backup_count,
            encoding=self._encoding,
        )

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record, rotating if necessary."""
        with self._lock:
            # Check for date change (daily rotation)
            current_date = datetime.now(timezone.utc).date()
            if current_date != self._current_date:
                self._rotate_daily()
                self._current_date = current_date

            # Emit to internal handler
            self._file_handler.emit(record)

    def _rotate_daily(self) -> None:
        """Perform daily rotation."""
        # Close current handler
        self._file_handler.close()

        # Archive yesterday's logs
        yesterday = self._current_date.isoformat()
        archive_name = f"{self._filename}.{yesterday}"

        if os.path.exists(self._filename):
            try:
                os.rename(self._filename, archive_name)

                # Compress if enabled
                if self._compress:
                    self._compress_file(archive_name)
            except Exception as e:
                logger.error("Failed to rotate log file: %s", e)

        # Clean up old files
        self._cleanup_old_files()

        # Reopen handler
        self._setup_handlers()
        if self.formatter:
            self._file_handler.setFormatter(self.formatter)
        for filter_ in self.filters:
            self._file_handler.addFilter(filter_)

    def _compress_file(self, filepath: str) -> None:
        """Compress file in background."""
        def compress():
            try:
                compressed = filepath + ".gz"
                with open(filepath, "rb") as f_in:
                    with gzip.open(compressed, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
                os.remove(filepath)
            except Exception as e:
                logger.error("Compression failed: %s", e)

        thread = threading.Thread(target=compress, daemon=True)
        thread.start()

    def _cleanup_old_files(self) -> None:
        """Remove files older than retention period."""
        dir_name = os.path.dirname(self._filename) or "."
        base_name = os.path.basename(self._filename)
        cutoff_date = datetime.now(timezone.utc).date()

        try:
            for file_name in os.listdir(dir_name):
                if not file_name.startswith(base_name + "."):
                    continue

                file_path = os.path.join(dir_name, file_name)

                # Check file age
                try:
                    file_stat = os.stat(file_path)
                    file_date = datetime.fromtimestamp(
                        file_stat.st_mtime, timezone.utc
                    ).date()

                    age_days = (cutoff_date - file_date).days
                    if age_days > self._retention_days:
                        os.remove(file_path)
                        logger.debug("Removed old log file: %s", file_path)
                except Exception as e:
                    logger.warning("Failed to check/remove %s: %s", file_path, e)
        except Exception as e:
            logger.error("Failed to cleanup old files: %s", e)

    def setFormatter(self, fmt: logging.Formatter) -> None:
        """Set formatter on internal handler."""
        super().setFormatter(fmt)
        self._file_handler.setFormatter(fmt)

    def addFilter(self, filter: logging.Filter) -> None:
        """Add filter to internal handler."""
        super().addFilter(filter)
        self._file_handler.addFilter(filter)

    def close(self) -> None:
        """Close the handler."""
        with self._lock:
            self._file_handler.close()
        super().close()


def configure_file_logging(
    config: Optional[LogRotationConfig] = None,
    *,
    log_dir: Optional[str] = None,
    retention_days: Optional[int] = None,
    max_size_mb: Optional[int] = None,
    service_name: Optional[str] = None,
) -> logging.Handler:
    """Configure file-based logging with rotation.

    Args:
        config: Full configuration object
        log_dir: Override log directory
        retention_days: Override retention days
        max_size_mb: Override max file size
        service_name: Override service name

    Returns:
        Configured file handler
    """
    if config is None:
        config = LogRotationConfig()

    # Apply overrides
    if log_dir is not None:
        config.log_dir = log_dir
    if retention_days is not None:
        config.retention_days = retention_days
    if max_size_mb is not None:
        config.max_size_mb = max_size_mb
    if service_name is not None:
        config.service_name = service_name

    # Ensure log directory exists
    log_path = Path(config.log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Create log file path
    log_file = log_path / f"{config.service_name}.log"

    # Create handler
    handler = SizeAndTimeRotatingHandler(
        filename=str(log_file),
        max_bytes=config.max_size_mb * 1024 * 1024,
        backup_count=config.backup_count,
        retention_days=config.retention_days,
        compress=config.compress_archives,
    )

    # Set formatter
    if config.json_format:
        handler.setFormatter(StructuredJSONFormatter())

    # Add PII scrubbing filter
    if config.pii_scrub:
        handler.addFilter(PIIScrubFilter(enabled=True))

    # Set level
    handler.setLevel(getattr(logging, config.log_level.upper(), logging.INFO))

    # Add to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    logger.info(
        "Configured file logging: dir=%s, retention=%d days, max_size=%d MB",
        config.log_dir,
        config.retention_days,
        config.max_size_mb,
    )

    return handler


def cleanup_old_logs(
    log_dir: str = DEFAULT_LOG_DIR,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    dry_run: bool = False,
) -> List[str]:
    """Manually clean up old log files.

    Args:
        log_dir: Log directory path
        retention_days: Days to retain
        dry_run: If True, only report files that would be deleted

    Returns:
        List of deleted (or would-be-deleted) file paths
    """
    log_path = Path(log_dir)
    if not log_path.exists():
        return []

    cutoff = datetime.now(timezone.utc).timestamp() - (retention_days * 86400)
    deleted = []

    for file_path in log_path.glob("*.log*"):
        try:
            if file_path.stat().st_mtime < cutoff:
                if not dry_run:
                    file_path.unlink()
                deleted.append(str(file_path))
        except Exception as e:
            logger.warning("Failed to process %s: %s", file_path, e)

    return deleted


def get_log_stats(log_dir: str = DEFAULT_LOG_DIR) -> Dict[str, Any]:
    """Get statistics about log files.

    Args:
        log_dir: Log directory path

    Returns:
        Dictionary with log statistics
    """
    log_path = Path(log_dir)
    if not log_path.exists():
        return {"exists": False, "file_count": 0, "total_size_bytes": 0}

    files = list(log_path.glob("*.log*"))
    total_size = sum(f.stat().st_size for f in files if f.exists())

    # Find oldest and newest
    mtimes = [(f, f.stat().st_mtime) for f in files if f.exists()]
    oldest = min(mtimes, key=lambda x: x[1], default=(None, 0))
    newest = max(mtimes, key=lambda x: x[1], default=(None, 0))

    return {
        "exists": True,
        "file_count": len(files),
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "oldest_file": str(oldest[0]) if oldest[0] else None,
        "oldest_mtime": datetime.fromtimestamp(oldest[1], timezone.utc).isoformat() if oldest[1] else None,
        "newest_file": str(newest[0]) if newest[0] else None,
        "newest_mtime": datetime.fromtimestamp(newest[1], timezone.utc).isoformat() if newest[1] else None,
    }
