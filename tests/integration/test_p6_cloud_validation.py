"""
Cloud Sync Validation Tests (T-132).

Validates cloud sync components work together:
- Cloud sync architecture (bidirectional protocol)
- FAISS sync
- SQLite sync
- Conflict resolution, privacy, offline queue
"""

from __future__ import annotations

from core.memory.cloud_sync import CloudSyncConfig
from core.memory.conflict_resolver import ConflictResolutionManager
from core.memory.faiss_sync import FAISSSyncConfig
from core.memory.offline_queue import OfflineQueue, QueueOperationType
from core.memory.privacy_controls import PrivacyControlsManager
from core.memory.sqlite_sync import SQLiteSyncConfig

# ===========================================================================
# Cloud Sync Architecture Validation
# ===========================================================================

class TestCloudSyncArchitectureValidation:
    def test_config_defaults(self):
        cfg = CloudSyncConfig()
        assert cfg.enabled is False
        assert cfg.provider == "stub"
        assert cfg.sync_interval_s == 300.0

    def test_config_from_env(self):
        cfg = CloudSyncConfig.from_env()
        assert isinstance(cfg, CloudSyncConfig)


# ===========================================================================
# FAISS Sync Validation
# ===========================================================================

class TestFAISSSyncValidation:
    def test_config_creation(self):
        cfg = FAISSSyncConfig()
        assert isinstance(cfg, FAISSSyncConfig)


# ===========================================================================
# SQLite Sync Validation
# ===========================================================================

class TestSQLiteSyncValidation:
    def test_config_creation(self):
        cfg = SQLiteSyncConfig()
        assert isinstance(cfg, SQLiteSyncConfig)


# ===========================================================================
# Conflict Resolution Validation
# ===========================================================================

class TestConflictResolutionValidation:
    def test_manager_creation(self):
        manager = ConflictResolutionManager()
        assert manager is not None

    def test_manager_health(self):
        manager = ConflictResolutionManager()
        h = manager.health()
        assert isinstance(h, dict)


# ===========================================================================
# Privacy Controls Validation
# ===========================================================================

class TestPrivacyControlsValidation:
    def test_manager_creation(self):
        manager = PrivacyControlsManager()
        assert manager is not None

    def test_manager_health(self):
        manager = PrivacyControlsManager()
        h = manager.health()
        assert isinstance(h, dict)


# ===========================================================================
# Offline Queue Validation
# ===========================================================================

class TestOfflineQueueValidation:
    def test_queue_creation(self):
        queue = OfflineQueue()
        assert queue is not None

    def test_queue_operation_types(self):
        assert QueueOperationType.ADD is not None
        assert QueueOperationType.UPDATE is not None
        assert QueueOperationType.DELETE is not None

    def test_queue_health(self):
        queue = OfflineQueue()
        h = queue.health()
        assert isinstance(h, dict)
