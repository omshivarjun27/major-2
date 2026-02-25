"""
Unit tests — Face Consent Integration (T-029)
===============================================

Tests consent audit trail, TTL expiry, and revocation cascade
for FaceEmbeddingStore.
"""

import time

import numpy as np
import pytest

from core.face.face_embeddings import EmbeddingConfig, FaceEmbeddingStore


@pytest.fixture
def face_config(tmp_path):
    """EmbeddingConfig pointing to tmp_path with encryption disabled."""
    return EmbeddingConfig(
        storage_dir=str(tmp_path / "face_store"),
        audit_dir=str(tmp_path / "consent"),
        encryption_enabled=False,
        consent_required=False,
        retention_ttl_days=90,
    )


@pytest.fixture
def store(face_config):
    """FaceEmbeddingStore with test config."""
    return FaceEmbeddingStore(config=face_config)


def _random_embedding(dim: int = 512) -> np.ndarray:
    vec = np.random.rand(dim).astype(np.float32)
    return vec / (np.linalg.norm(vec) + 1e-8)


class TestFaceConsentIntegration:
    """T-029: consent audit, TTL, revocation cascade."""

    def test_audit_log_writes_entry(self, store, face_config):
        """Grant consent via register, verify audit file contains entry."""
        embedding = _random_embedding()
        identity = store.register("Alice", embedding, consent=True)

        audit_path = store._audit_log._audit_path
        assert audit_path.exists(), "Audit JSONL file should exist after register"

        entries = store._audit_log.read_entries()
        assert len(entries) > 0, "Audit log should have at least one entry"

        # Find the consent_granted entry for Alice
        grant_entries = [e for e in entries if e.event_type == "consent_granted"]
        assert len(grant_entries) >= 1, "Should have a consent_granted entry"
        assert grant_entries[0].person_id == identity.identity_id

    def test_revocation_deletes_embeddings(self, store):
        """Register face, revoke consent, verify identity removed from store."""
        embedding = _random_embedding()
        identity = store.register("Bob", embedding, consent=True)
        identity_id = identity.identity_id

        assert store.count() == 1
        result = store.revoke_consent(identity_id, reason="test_revocation")
        assert result is True
        assert store.count() == 0, "Identity should be removed after consent revocation"

    def test_revocation_removes_disk_files(self, store, face_config):
        """Register + save, revoke, verify no leftover .npy files on disk."""
        from pathlib import Path

        embedding = _random_embedding()
        identity = store.register("Charlie", embedding, consent=True)
        identity_id = identity.identity_id

        storage = Path(face_config.storage_dir)

        # Revoke consent — should clean up disk
        store.revoke_consent(identity_id)

        # Check no .npy files remain for this identity
        for suffix in [".npy", ".npy.enc"]:
            p = storage / f"{identity_id}{suffix}"
            assert not p.exists(), f"File {p} should be deleted after revocation"

    def test_ttl_expiry_removes_old_identities(self, tmp_path):
        """Create identity with old timestamp, call cleanup, verify removed."""
        config = EmbeddingConfig(
            storage_dir=str(tmp_path / "face_store"),
            audit_dir=str(tmp_path / "consent"),
            encryption_enabled=False,
            consent_required=False,
            retention_ttl_days=1,  # 1 day TTL
        )
        s = FaceEmbeddingStore(config=config)
        embedding = _random_embedding()
        identity = s.register("OldPerson", embedding, consent=True)

        # Manually backdate the registration to 2 days ago
        identity.registered_at = time.time() - (2 * 24 * 60 * 60)

        assert s.count() == 1
        expired = s.cleanup_expired()
        assert len(expired) == 1, "Should expire the old identity"
        assert s.count() == 0, "Store should be empty after expiry"

    def test_ttl_preserves_recent_identities(self, store):
        """Create recent identity, call cleanup, verify preserved."""
        embedding = _random_embedding()
        store.register("RecentPerson", embedding, consent=True)

        assert store.count() == 1
        expired = store.cleanup_expired()
        assert len(expired) == 0, "Recent identity should not be expired"
        assert store.count() == 1, "Store should still have the identity"

    def test_identify_triggers_expiry_check(self, tmp_path):
        """Expired identity should not be returned by identify()."""
        config = EmbeddingConfig(
            storage_dir=str(tmp_path / "face_store"),
            audit_dir=str(tmp_path / "consent"),
            encryption_enabled=False,
            consent_required=False,
            retention_ttl_days=1,
            similarity_threshold=0.1,
        )
        s = FaceEmbeddingStore(config=config)
        embedding = _random_embedding()
        identity = s.register("ExpiredUser", embedding, consent=True)

        # Backdate to trigger expiry
        identity.registered_at = time.time() - (2 * 24 * 60 * 60)

        # identify() should trigger _check_expiry() and not find the expired user
        result = s.identify(embedding)
        assert result is None, "Expired identity should not be returned by identify()"
        assert s.count() == 0

    def test_audit_trail_records_cascade(self, store):
        """Revoke consent, verify audit trail has both revoke and delete events."""
        embedding = _random_embedding()
        identity = store.register("CascadeUser", embedding, consent=True)
        identity_id = identity.identity_id

        store.revoke_consent(identity_id)

        entries = store._audit_log.read_entries()
        event_types = [e.event_type for e in entries if e.person_id == identity_id]

        assert "consent_revoked" in event_types, "Audit should record consent_revoked"
        assert "data_deleted" in event_types, "Audit should record data_deleted cascade"
