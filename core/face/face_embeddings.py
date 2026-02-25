"""
Face Embeddings — Consent-based on-device embedding storage.

Embeddings are stored locally with optional AES encryption at rest.
All operations require explicit consent check.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .consent_audit import AuditEntry, ConsentAuditLog

logger = logging.getLogger("face-embeddings")

# Optional at-rest encryption (shared with memory engine)
try:
    from shared.utils.encryption import get_encryption_manager as _get_enc
except ImportError:
    _get_enc = None  # type: ignore[assignment]


@dataclass
class EmbeddingConfig:
    """Configuration for face embedding storage."""
    storage_dir: str = "data/face_embeddings"
    audit_dir: str = "data/consent"
    encryption_enabled: bool = True
    encryption_key_env: str = "FACE_ENCRYPTION_KEY"
    embedding_dim: int = 512
    similarity_threshold: float = 0.6
    max_identities: int = 100
    consent_required: bool = True
    retention_ttl_days: int = 90


@dataclass
class FaceIdentity:
    """A registered face identity."""
    identity_id: str
    name: str
    embedding: np.ndarray
    registered_at: float  # epoch seconds
    consent_given: bool = True
    consent_timestamp: float = 0.0
    last_seen: float = 0.0
    times_seen: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "identity_id": self.identity_id,
            "name": self.name,
            "registered_at": self.registered_at,
            "consent_given": self.consent_given,
            "consent_timestamp": self.consent_timestamp,
            "last_seen": self.last_seen,
            "times_seen": self.times_seen,
            "metadata": self.metadata,
        }


class FaceEmbeddingStore:
    """On-device face embedding storage with consent management.

    Usage::

        store = FaceEmbeddingStore()
        store.register("Alice", embedding_vector, consent=True)
        match = store.identify(query_embedding)
    """

    def __init__(self, config: Optional[EmbeddingConfig] = None):
        self.config = config or EmbeddingConfig()
        self._identities: Dict[str, FaceIdentity] = {}
        self._consent_log: List[Dict[str, Any]] = []
        self._encryption_key: Optional[bytes] = None
        self._audit_log: Optional[ConsentAuditLog] = ConsentAuditLog(self.config.audit_dir)

        if self.config.encryption_enabled:
            self._init_encryption()

        self._load_from_disk()

    def _init_encryption(self) -> None:
        key_str = os.environ.get(self.config.encryption_key_env, "")
        if key_str:
            self._encryption_key = hashlib.sha256(key_str.encode()).digest()
            logger.info("Face embedding encryption enabled")
        else:
            logger.warning("FACE_ENCRYPTION_KEY not set; encryption disabled")
            self.config.encryption_enabled = False

    def _load_from_disk(self) -> None:
        storage = Path(self.config.storage_dir)
        meta_path = storage / "identities.json"
        if not meta_path.exists():
            return
        try:
            enc = _get_enc() if _get_enc is not None else None

            # Load metadata JSON (may be encrypted)
            if enc and enc.active:
                try:
                    data = enc.load_json_decrypted(meta_path)
                except Exception:
                    # Fallback: maybe stored before encryption was enabled
                    with open(meta_path, "r") as f:
                        data = json.load(f)
            else:
                with open(meta_path, "r") as f:
                    data = json.load(f)

            for entry in data.get("identities", []):
                emb_path = storage / f"{entry['identity_id']}.npy"
                if emb_path.exists():
                    # Load embedding (may be encrypted)
                    if enc and enc.active:
                        try:
                            embedding = enc.load_npy_decrypted(emb_path)
                        except Exception:
                            embedding = np.load(str(emb_path))
                    else:
                        embedding = np.load(str(emb_path))
                    self._identities[entry["identity_id"]] = FaceIdentity(
                        identity_id=entry["identity_id"],
                        name=entry["name"],
                        embedding=embedding,
                        registered_at=entry.get("registered_at", 0),
                        consent_given=entry.get("consent_given", True),
                        consent_timestamp=entry.get("consent_timestamp", 0),
                        last_seen=entry.get("last_seen", 0),
                        times_seen=entry.get("times_seen", 0),
                        metadata=entry.get("metadata", {}),
                    )
            logger.info("Loaded %d face identities from disk", len(self._identities))
        except Exception as exc:
            logger.warning("Failed to load face identities: %s", exc)

    def _save_to_disk(self) -> None:
        storage = Path(self.config.storage_dir)
        storage.mkdir(parents=True, exist_ok=True)
        enc = _get_enc() if _get_enc is not None else None

        entries = []
        for ident in self._identities.values():
            entries.append(ident.to_dict())
            emb_path = storage / f"{ident.identity_id}.npy"
            if enc and enc.active:
                enc.save_npy_encrypted(emb_path, ident.embedding)
            else:
                np.save(str(emb_path), ident.embedding)

        meta = {"identities": entries, "updated_at": time.time()}
        if enc and enc.active:
            enc.save_json_encrypted(storage / "identities.json", meta)
        else:
            with open(storage / "identities.json", "w") as f:
                json.dump(meta, f, indent=2)

    def _log_audit(self, event_type: str, identity_id: str, details: Optional[Dict[str, Any]] = None) -> None:
        if not self._audit_log:
            return
        entry = AuditEntry(
            timestamp=f"{datetime.utcnow().isoformat()}Z",
            event_type=event_type,
            person_id=identity_id,
            details=details or {},
        )
        self._audit_log.log(entry)

    def _check_expiry(self) -> List[str]:
        if self.config.retention_ttl_days <= 0:
            return []
        now = time.time()
        ttl_seconds = self.config.retention_ttl_days * 24 * 60 * 60
        expired_ids: List[str] = []
        storage = Path(self.config.storage_dir)
        for identity_id, ident in list(self._identities.items()):
            if ident.registered_at <= 0:
                continue
            if now - ident.registered_at <= ttl_seconds:
                continue
            expired_ids.append(identity_id)
            del self._identities[identity_id]
            for suffix in [".npy", ".npy.enc"]:
                p = storage / f"{identity_id}{suffix}"
                if p.exists():
                    p.unlink()
            self._log_audit(
                "data_expired",
                identity_id,
                {"name": ident.name, "ttl_days": self.config.retention_ttl_days},
            )
        if expired_ids:
            self._save_to_disk()
        return expired_ids

    def cleanup_expired(self) -> List[str]:
        return self._check_expiry()

    # ── Consent Management ──

    def check_consent(self, identity_id: Optional[str] = None) -> bool:
        if not self.config.consent_required:
            return True
        if identity_id and identity_id in self._identities:
            return self._identities[identity_id].consent_given
        return False

    def record_consent(self, name: str, consent: bool, reason: str = "") -> Dict[str, Any]:
        entry = {
            "name": name,
            "consent": consent,
            "reason": reason,
            "timestamp": time.time(),
            "action": "grant" if consent else "revoke",
        }
        self._consent_log.append(entry)
        logger.info("Face consent %s for '%s': %s", entry["action"], name, reason)
        return entry

    def get_consent_log(self) -> List[Dict[str, Any]]:
        return list(self._consent_log)

    # ── Registration ──

    def register(
        self,
        name: str,
        embedding: np.ndarray,
        consent: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FaceIdentity:
        if not consent and self.config.consent_required:
            raise ValueError("Consent is required for face registration")

        if len(self._identities) >= self.config.max_identities:
            raise ValueError(f"Maximum identities ({self.config.max_identities}) reached")

        identity_id = f"fid_{uuid.uuid4().hex[:12]}"
        now = time.time()

        identity = FaceIdentity(
            identity_id=identity_id,
            name=name,
            embedding=embedding.copy(),
            registered_at=now,
            consent_given=consent,
            consent_timestamp=now,
            last_seen=now,
            times_seen=1,
            metadata=metadata or {},
        )
        self._identities[identity_id] = identity
        self.record_consent(name, consent, "initial_registration")
        self._log_audit(
            "consent_granted" if consent else "consent_revoked",
            identity_id,
            {"name": name, "reason": "initial_registration"},
        )
        self._save_to_disk()
        logger.info("Registered face identity: %s (%s)", name, identity_id)
        return identity

    def delete(self, identity_id: str) -> bool:
        if identity_id in self._identities:
            name = self._identities[identity_id].name
            del self._identities[identity_id]
            self.record_consent(name, False, "identity_deleted")
            self._log_audit("data_deleted", identity_id, {"name": name, "reason": "identity_deleted"})
            self._save_to_disk()
            # Delete embedding file (check both plain and encrypted forms)
            storage = Path(self.config.storage_dir)
            for suffix in [".npy", ".npy.enc"]:
                p = storage / f"{identity_id}{suffix}"
                if p.exists():
                    p.unlink()
            logger.info("Deleted face identity: %s (%s)", name, identity_id)
            return True
        return False

    def grant_consent(self, identity_id: str, reason: str = "manual") -> bool:
        identity = self._identities.get(identity_id)
        if not identity:
            return False
        identity.consent_given = True
        identity.consent_timestamp = time.time()
        self.record_consent(identity.name, True, reason)
        self._log_audit("consent_granted", identity_id, {"name": identity.name, "reason": reason})
        self._save_to_disk()
        return True

    def revoke_consent(self, identity_id: str, reason: str = "manual") -> bool:
        identity = self._identities.get(identity_id)
        if not identity:
            return False
        self.record_consent(identity.name, False, reason)
        self._log_audit("consent_revoked", identity_id, {"name": identity.name, "reason": reason})
        del self._identities[identity_id]
        storage = Path(self.config.storage_dir)
        for suffix in [".npy", ".npy.enc"]:
            p = storage / f"{identity_id}{suffix}"
            if p.exists():
                p.unlink()
        self._log_audit("data_deleted", identity_id, {"name": identity.name, "reason": "consent_revoked"})
        self._save_to_disk()
        return True

    def forget_all(self) -> int:
        count = len(self._identities)
        storage = Path(self.config.storage_dir)
        for ident in list(self._identities.values()):
            self.record_consent(ident.name, False, "forget_all")
            self._log_audit("data_deleted", ident.identity_id, {"name": ident.name, "reason": "forget_all"})
            # Delete embedding files (both plain and encrypted)
            for suffix in [".npy", ".npy.enc"]:
                p = storage / f"{ident.identity_id}{suffix}"
                if p.exists():
                    p.unlink()
        self._identities.clear()
        self._save_to_disk()
        return count

    # ── Identification ──

    def identify(self, query_embedding: np.ndarray) -> Optional[Tuple[FaceIdentity, float]]:
        self._check_expiry()
        if not self._identities:
            return None

        best_match = None
        best_sim = -1.0

        for ident in self._identities.values():
            if not ident.consent_given:
                continue
            sim = self._cosine_similarity(query_embedding, ident.embedding)
            if sim > best_sim:
                best_sim = sim
                best_match = ident

        if best_match and best_sim >= self.config.similarity_threshold:
            best_match.last_seen = time.time()
            best_match.times_seen += 1
            self._log_audit(
                "data_accessed",
                best_match.identity_id,
                {"name": best_match.name, "similarity": best_sim},
            )
            return (best_match, best_sim)
        return None

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        a_flat = a.flatten().astype(np.float32)
        b_flat = b.flatten().astype(np.float32)
        dot = np.dot(a_flat, b_flat)
        norm_a = np.linalg.norm(a_flat)
        norm_b = np.linalg.norm(b_flat)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot / (norm_a * norm_b))

    # ── Queries ──

    def list_identities(self) -> List[Dict[str, Any]]:
        return [ident.to_dict() for ident in self._identities.values()]

    def get_identity(self, identity_id: str) -> Optional[FaceIdentity]:
        return self._identities.get(identity_id)

    def count(self) -> int:
        return len(self._identities)

    def health(self) -> Dict[str, Any]:
        return {
            "identities_registered": self.count(),
            "max_identities": self.config.max_identities,
            "encryption_enabled": self.config.encryption_enabled,
            "consent_required": self.config.consent_required,
            "storage_dir": self.config.storage_dir,
        }
