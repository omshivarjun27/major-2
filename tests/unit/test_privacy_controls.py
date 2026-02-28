"""
Unit tests for Cloud Sync Privacy Controls (T-115).
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from core.memory.privacy_controls import (
    DataCategory,
    DataResidency,
    ErasureRequest,
    PrivacyControlsManager,
    SyncAuditEntry,
    SyncConsent,
)


class TestDataCategory:
    """Tests for DataCategory enum."""

    def test_all_categories(self):
        """Test all expected categories exist."""
        assert DataCategory.MEMORY.value == "memory"
        assert DataCategory.PREFERENCES.value == "preferences"
        assert DataCategory.FACE_EMBEDDINGS.value == "face_embeddings"


class TestDataResidency:
    """Tests for DataResidency enum."""

    def test_all_residencies(self):
        """Test all expected residencies exist."""
        assert DataResidency.DEFAULT.value == "default"
        assert DataResidency.EU.value == "eu"
        assert DataResidency.LOCAL_ONLY.value == "local_only"


class TestSyncConsent:
    """Tests for SyncConsent."""

    def test_allows_sync_enabled_category(self):
        """Test allows_sync for enabled category."""
        consent = SyncConsent(
            user_id="user1",
            enabled_categories={DataCategory.MEMORY, DataCategory.PREFERENCES},
        )

        assert consent.allows_sync(DataCategory.MEMORY) is True
        assert consent.allows_sync(DataCategory.PREFERENCES) is True
        assert consent.allows_sync(DataCategory.FACE_EMBEDDINGS) is False

    def test_allows_sync_opt_out_all(self):
        """Test allows_sync when opt_out_all is True."""
        consent = SyncConsent(
            user_id="user1",
            enabled_categories={DataCategory.MEMORY},
            opt_out_all=True,
        )

        assert consent.allows_sync(DataCategory.MEMORY) is False

    def test_allows_sync_local_only(self):
        """Test allows_sync with LOCAL_ONLY residency."""
        consent = SyncConsent(
            user_id="user1",
            enabled_categories={DataCategory.MEMORY},
            data_residency=DataResidency.LOCAL_ONLY,
        )

        assert consent.allows_sync(DataCategory.MEMORY) is False

    def test_to_dict_and_from_dict(self):
        """Test serialization round-trip."""
        consent = SyncConsent(
            user_id="user1",
            enabled_categories={DataCategory.MEMORY, DataCategory.PREFERENCES},
            data_residency=DataResidency.EU,
        )

        data = consent.to_dict()
        restored = SyncConsent.from_dict(data)

        assert restored.user_id == "user1"
        assert DataCategory.MEMORY in restored.enabled_categories
        assert restored.data_residency == DataResidency.EU


class TestErasureRequest:
    """Tests for ErasureRequest."""

    def test_is_overdue_false(self):
        """Test is_overdue when deadline not passed."""
        import time

        request = ErasureRequest(
            request_id="req1",
            user_id="user1",
            requested_at_ms=time.time() * 1000,
            deadline_ms=(time.time() + 3600) * 1000,  # 1 hour from now
            categories={DataCategory.MEMORY},
        )

        assert request.is_overdue() is False

    def test_is_overdue_true(self):
        """Test is_overdue when deadline passed."""
        import time

        request = ErasureRequest(
            request_id="req1",
            user_id="user1",
            requested_at_ms=(time.time() - 7200) * 1000,  # 2 hours ago
            deadline_ms=(time.time() - 3600) * 1000,  # 1 hour ago
            categories={DataCategory.MEMORY},
        )

        assert request.is_overdue() is True

    def test_to_dict(self):
        """Test serialization."""
        request = ErasureRequest(
            request_id="req1",
            user_id="user1",
            requested_at_ms=1000.0,
            deadline_ms=2000.0,
            categories={DataCategory.MEMORY},
        )

        data = request.to_dict()

        assert data["request_id"] == "req1"
        assert "memory" in data["categories"]


class TestSyncAuditEntry:
    """Tests for SyncAuditEntry."""

    def test_to_dict(self):
        """Test serialization."""
        entry = SyncAuditEntry(
            entry_id="e1",
            user_id="user1",
            timestamp_ms=1000.0,
            operation="push",
            data_category=DataCategory.MEMORY,
            source_location="local",
            destination_location="cloud",
            record_count=10,
            success=True,
        )

        data = entry.to_dict()

        assert data["entry_id"] == "e1"
        assert data["data_category"] == "memory"
        assert data["success"] is True


class TestPrivacyControlsManager:
    """Tests for PrivacyControlsManager."""

    @pytest.fixture
    def manager(self, tmp_path):
        return PrivacyControlsManager(
            consent_path=str(tmp_path / "consent"),
            audit_path=str(tmp_path / "audit"),
        )

    async def test_set_consent(self, manager):
        """Test setting consent."""
        consent = await manager.set_consent(
            user_id="user1",
            categories={DataCategory.MEMORY, DataCategory.PREFERENCES},
            data_residency=DataResidency.EU,
        )

        assert consent.user_id == "user1"
        assert DataCategory.MEMORY in consent.enabled_categories

    async def test_get_consent(self, manager):
        """Test getting consent."""
        await manager.set_consent(
            user_id="user1",
            categories={DataCategory.MEMORY},
        )

        consent = await manager.get_consent("user1")

        assert consent is not None
        assert consent.user_id == "user1"

    async def test_get_consent_nonexistent(self, manager):
        """Test getting consent for nonexistent user."""
        consent = await manager.get_consent("unknown")
        assert consent is None

    async def test_revoke_consent(self, manager):
        """Test revoking consent."""
        await manager.set_consent(
            user_id="user1",
            categories={DataCategory.MEMORY},
        )

        result = await manager.revoke_consent("user1")
        assert result is True

        consent = await manager.get_consent("user1")
        assert consent.opt_out_all is True

    async def test_check_sync_allowed(self, manager):
        """Test checking if sync is allowed."""
        await manager.set_consent(
            user_id="user1",
            categories={DataCategory.MEMORY},
            data_residency=DataResidency.EU,
        )

        # Allowed
        assert await manager.check_sync_allowed("user1", DataCategory.MEMORY) is True

        # Not allowed (category not enabled)
        assert await manager.check_sync_allowed("user1", DataCategory.FACE_EMBEDDINGS) is False

    async def test_check_sync_allowed_data_residency(self, manager):
        """Test data residency enforcement."""
        await manager.set_consent(
            user_id="user1",
            categories={DataCategory.MEMORY},
            data_residency=DataResidency.EU,
        )

        # Allowed in EU
        assert await manager.check_sync_allowed(
            "user1", DataCategory.MEMORY, "eu-west-1"
        ) is True

        # Not allowed in US
        assert await manager.check_sync_allowed(
            "user1", DataCategory.MEMORY, "us-east-1"
        ) is False

    async def test_request_erasure(self, manager):
        """Test requesting erasure."""
        request = await manager.request_erasure(
            user_id="user1",
            categories={DataCategory.MEMORY},
        )

        assert request.user_id == "user1"
        assert request.deadline_ms > request.requested_at_ms
        assert not request.completed

    async def test_complete_erasure(self, manager):
        """Test completing erasure."""
        request = await manager.request_erasure(
            user_id="user1",
            categories={DataCategory.MEMORY},
        )

        completed = await manager.complete_erasure(
            request.request_id,
            locations_cleared=["local", "cloud"],
        )

        assert completed.completed is True
        assert "local" in completed.locations_cleared

    async def test_get_pending_erasures(self, manager):
        """Test getting pending erasures."""
        await manager.request_erasure("user1")
        await manager.request_erasure("user2")

        pending = await manager.get_pending_erasures()
        assert len(pending) == 2

    async def test_log_sync_operation(self, manager):
        """Test logging sync operations."""
        entry = await manager.log_sync_operation(
            user_id="user1",
            operation="push",
            category=DataCategory.MEMORY,
            source="local",
            destination="cloud",
            record_count=10,
            success=True,
        )

        assert entry.user_id == "user1"
        assert entry.success is True

    async def test_get_audit_log(self, manager):
        """Test getting audit log."""
        await manager.log_sync_operation(
            user_id="user1",
            operation="push",
            category=DataCategory.MEMORY,
            source="local",
            destination="cloud",
            record_count=10,
            success=True,
        )

        log = manager.get_audit_log(user_id="user1")
        assert len(log) == 1
        assert log[0]["user_id"] == "user1"

    def test_health(self, manager):
        """Test health status."""
        health = manager.health()

        assert "total_users_with_consent" in health
        assert "pending_erasure_requests" in health
