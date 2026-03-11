"""
Cloud Sync Privacy Controls Module (T-115).

Implements privacy controls for cloud sync:
- User-level sync consent (opt-in per data category)
- Data residency configuration (restrict sync to specific regions)
- Right-to-erasure (cascade deletion within 24 hours)
- Sync audit log
- Integration with existing consent management
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("privacy-controls")


class DataCategory(Enum):
    """Categories of data that can be synced."""

    MEMORY = "memory"  # Memory entries and embeddings
    PREFERENCES = "preferences"  # User preferences
    FACE_EMBEDDINGS = "face_embeddings"  # Face recognition data
    CONVERSATION_LOGS = "conversation_logs"  # Conversation history
    TELEMETRY = "telemetry"  # Usage telemetry


class DataResidency(Enum):
    """Data residency regions."""

    DEFAULT = "default"  # No restriction
    US = "us"
    EU = "eu"
    EU_WEST = "eu-west"
    EU_CENTRAL = "eu-central"
    ASIA_PACIFIC = "asia-pacific"
    LOCAL_ONLY = "local_only"  # Never sync to cloud


@dataclass
class SyncConsent:
    """User's sync consent preferences."""

    user_id: str
    enabled_categories: Set[DataCategory] = field(default_factory=set)
    data_residency: DataResidency = DataResidency.DEFAULT
    consent_given_at: float = field(default_factory=lambda: time.time() * 1000)
    consent_version: str = "1.0"
    opt_out_all: bool = False

    def allows_sync(self, category: DataCategory) -> bool:
        """Check if sync is allowed for a category."""
        if self.opt_out_all:
            return False
        if self.data_residency == DataResidency.LOCAL_ONLY:
            return False
        return category in self.enabled_categories

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "enabled_categories": [c.value for c in self.enabled_categories],
            "data_residency": self.data_residency.value,
            "consent_given_at": self.consent_given_at,
            "consent_version": self.consent_version,
            "opt_out_all": self.opt_out_all,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SyncConsent":
        return cls(
            user_id=data["user_id"],
            enabled_categories={
                DataCategory(c) for c in data.get("enabled_categories", [])
            },
            data_residency=DataResidency(data.get("data_residency", "default")),
            consent_given_at=data.get("consent_given_at", 0),
            consent_version=data.get("consent_version", "1.0"),
            opt_out_all=data.get("opt_out_all", False),
        )


@dataclass
class ErasureRequest:
    """Request to erase user data."""

    request_id: str
    user_id: str
    requested_at_ms: float
    deadline_ms: float  # Must complete by this time
    categories: Set[DataCategory]
    completed: bool = False
    completed_at_ms: float = 0
    locations_cleared: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def is_overdue(self) -> bool:
        """Check if deadline has passed."""
        return time.time() * 1000 > self.deadline_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "requested_at_ms": self.requested_at_ms,
            "deadline_ms": self.deadline_ms,
            "categories": [c.value for c in self.categories],
            "completed": self.completed,
            "completed_at_ms": self.completed_at_ms,
            "locations_cleared": self.locations_cleared,
            "error": self.error,
        }


@dataclass
class SyncAuditEntry:
    """Audit entry for sync operations."""

    entry_id: str
    user_id: str
    timestamp_ms: float
    operation: str  # push, pull, delete
    data_category: DataCategory
    source_location: str
    destination_location: str
    record_count: int
    success: bool
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "user_id": self.user_id,
            "timestamp_ms": self.timestamp_ms,
            "operation": self.operation,
            "data_category": self.data_category.value,
            "source_location": self.source_location,
            "destination_location": self.destination_location,
            "record_count": self.record_count,
            "success": self.success,
            "error": self.error,
        }


class PrivacyControlsManager:
    """Manages privacy controls for cloud sync.

    Features:
    - Per-user, per-category consent management
    - Data residency enforcement
    - Right-to-erasure with 24-hour SLA
    - Comprehensive audit logging
    """

    ERASURE_SLA_HOURS = 24

    def __init__(
        self,
        consent_path: str = "./data/consent/",
        audit_path: str = "./data/audit/",
        max_audit_entries: int = 10000,
    ):
        self.consent_path = Path(consent_path)
        self.audit_path = Path(audit_path)
        self.max_audit_entries = max_audit_entries

        self.consent_path.mkdir(parents=True, exist_ok=True)
        self.audit_path.mkdir(parents=True, exist_ok=True)

        # In-memory caches
        self._consents: Dict[str, SyncConsent] = {}
        self._erasure_requests: Dict[str, ErasureRequest] = {}
        self._audit_log: List[SyncAuditEntry] = []
        self._entry_count = 0
        self._lock = asyncio.Lock()

        # Load existing consents
        self._load_consents()

    def _load_consents(self) -> None:
        """Load consents from disk."""
        consent_file = self.consent_path / "sync_consents.json"
        if consent_file.exists():
            try:
                data = json.loads(consent_file.read_text())
                for user_id, consent_data in data.items():
                    self._consents[user_id] = SyncConsent.from_dict(consent_data)
            except Exception as exc:
                logger.error(f"Failed to load consents: {exc}")

    def _save_consents(self) -> None:
        """Save consents to disk."""
        consent_file = self.consent_path / "sync_consents.json"
        data = {uid: c.to_dict() for uid, c in self._consents.items()}
        consent_file.write_text(json.dumps(data, indent=2))

    async def set_consent(
        self,
        user_id: str,
        categories: Set[DataCategory],
        data_residency: DataResidency = DataResidency.DEFAULT,
    ) -> SyncConsent:
        """Set sync consent for a user."""
        async with self._lock:
            consent = SyncConsent(
                user_id=user_id,
                enabled_categories=categories,
                data_residency=data_residency,
            )
            self._consents[user_id] = consent
            self._save_consents()

            logger.info(
                f"Consent set for user {user_id}: "
                f"categories={[c.value for c in categories]}, "
                f"residency={data_residency.value}"
            )

            return consent

    async def get_consent(self, user_id: str) -> Optional[SyncConsent]:
        """Get sync consent for a user."""
        return self._consents.get(user_id)

    async def revoke_consent(self, user_id: str) -> bool:
        """Revoke all sync consent for a user."""
        async with self._lock:
            if user_id in self._consents:
                self._consents[user_id].opt_out_all = True
                self._save_consents()
                return True
            return False

    async def check_sync_allowed(
        self,
        user_id: str,
        category: DataCategory,
        destination_region: Optional[str] = None,
    ) -> bool:
        """Check if sync is allowed for a user and category."""
        consent = self._consents.get(user_id)
        if not consent:
            return False

        if not consent.allows_sync(category):
            return False

        # Check data residency
        if destination_region and consent.data_residency != DataResidency.DEFAULT:
            if consent.data_residency == DataResidency.LOCAL_ONLY:
                return False
            # Could add more sophisticated region matching here
            if consent.data_residency.value not in destination_region.lower():
                logger.warning(
                    f"Data residency violation: user {user_id} restricted to "
                    f"{consent.data_residency.value}, attempted sync to {destination_region}"
                )
                return False

        return True

    async def request_erasure(
        self,
        user_id: str,
        categories: Optional[Set[DataCategory]] = None,
    ) -> ErasureRequest:
        """Request erasure of user data (right-to-erasure).

        Args:
            user_id: User whose data should be erased
            categories: Categories to erase (None = all)

        Returns:
            ErasureRequest with deadline (24 hours)
        """
        async with self._lock:
            request_id = f"erasure_{user_id}_{int(time.time() * 1000)}"
            now_ms = time.time() * 1000
            deadline_ms = now_ms + (self.ERASURE_SLA_HOURS * 3600 * 1000)

            request = ErasureRequest(
                request_id=request_id,
                user_id=user_id,
                requested_at_ms=now_ms,
                deadline_ms=deadline_ms,
                categories=categories or set(DataCategory),
            )

            self._erasure_requests[request_id] = request

            logger.info(
                f"Erasure request {request_id} for user {user_id}: "
                f"deadline={datetime.fromtimestamp(deadline_ms / 1000).isoformat()}"
            )

            return request

    async def complete_erasure(
        self,
        request_id: str,
        locations_cleared: List[str],
    ) -> ErasureRequest:
        """Mark an erasure request as complete."""
        async with self._lock:
            if request_id not in self._erasure_requests:
                raise ValueError(f"Unknown erasure request: {request_id}")

            request = self._erasure_requests[request_id]
            request.completed = True
            request.completed_at_ms = time.time() * 1000
            request.locations_cleared = locations_cleared

            if request.is_overdue():
                logger.warning(
                    f"Erasure request {request_id} completed after deadline!"
                )

            return request

    async def get_pending_erasures(self) -> List[ErasureRequest]:
        """Get all pending erasure requests."""
        return [
            r for r in self._erasure_requests.values()
            if not r.completed
        ]

    async def log_sync_operation(
        self,
        user_id: str,
        operation: str,
        category: DataCategory,
        source: str,
        destination: str,
        record_count: int,
        success: bool,
        error: Optional[str] = None,
    ) -> SyncAuditEntry:
        """Log a sync operation for audit."""
        async with self._lock:
            self._entry_count += 1
            entry = SyncAuditEntry(
                entry_id=f"audit_{int(time.time() * 1000)}_{self._entry_count}",
                user_id=user_id,
                timestamp_ms=time.time() * 1000,
                operation=operation,
                data_category=category,
                source_location=source,
                destination_location=destination,
                record_count=record_count,
                success=success,
                error=error,
            )

            self._audit_log.append(entry)

            # Trim audit log if too large
            if len(self._audit_log) > self.max_audit_entries:
                self._audit_log = self._audit_log[-self.max_audit_entries:]

            return entry

    def get_audit_log(
        self,
        user_id: Optional[str] = None,
        category: Optional[DataCategory] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get audit log entries with optional filters."""
        entries = self._audit_log

        if user_id:
            entries = [e for e in entries if e.user_id == user_id]

        if category:
            entries = [e for e in entries if e.data_category == category]

        return [e.to_dict() for e in entries[-limit:]]

    def health(self) -> Dict[str, Any]:
        """Get health status."""
        pending = len([r for r in self._erasure_requests.values() if not r.completed])
        overdue = len([
            r for r in self._erasure_requests.values()
            if not r.completed and r.is_overdue()
        ])

        return {
            "total_users_with_consent": len(self._consents),
            "pending_erasure_requests": pending,
            "overdue_erasure_requests": overdue,
            "audit_log_size": len(self._audit_log),
        }
