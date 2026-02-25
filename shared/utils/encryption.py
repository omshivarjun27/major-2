"""
On-device encryption helpers for at-rest data files.
=====================================================

Uses **Fernet** (AES-128-CBC + HMAC-SHA256) from the ``cryptography``
library for symmetric-key encryption of:

- FAISS index files
- JSON metadata files
- Face-embedding ``.npy`` files

Key Management
--------------
The 32-byte raw key is read from an environment variable
(default ``MEMORY_ENCRYPTION_KEY``), then derived via PBKDF2-HMAC-SHA256
(100 000 iterations) and URL-safe base64-encoded for Fernet.

A legacy SHA-256 fallback is maintained for files encrypted before
the PBKDF2 upgrade.  Salt is configurable via ``{KEY_ENV_VAR}_SALT``.

If no key is set the module gracefully degrades to
plain I/O so the assistant still works un-encrypted.

Usage::

    from shared.utils.encryption import EncryptionManager

    enc = EncryptionManager()          # reads key from env
    enc.save_encrypted(path, data)     # bytes -> encrypted file
    data = enc.load_decrypted(path)    # encrypted file -> bytes
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger("encryption")

_HAS_FERNET = False
try:
    from cryptography.fernet import Fernet  # type: ignore
    _HAS_FERNET = True
except ImportError:
    logger.debug("cryptography not installed – encryption unavailable")


class EncryptionManager:
    """Symmetric at-rest encryption with transparent fallback.

    Parameters
    ----------
    key_env_var : str
        Name of the env var holding the raw key string.
    enabled : bool | None
        * ``True``  – require encryption (fail if no key).
        * ``False`` – never encrypt.
        * ``None``  – auto: encrypt when a key is present.
    """

    def __init__(
        self,
        key_env_var: str = "MEMORY_ENCRYPTION_KEY",
        enabled: Optional[bool] = None,
    ):
        self._key_env_var = key_env_var
        self._fernet: Optional["Fernet"] = None  # type: ignore[name-defined]
        self._legacy_fernet: Optional["Fernet"] = None  # type: ignore[name-defined]
        self._enabled = False

        raw_key = os.environ.get(key_env_var, "").strip()

        # Try SecretProvider if env var is empty
        if not raw_key:
            try:
                from shared.config.secret_provider import create_secret_provider
                provider = create_secret_provider()
                raw_key = provider.get_secret(key_env_var) or ""
            except Exception:
                pass  # Fall back to empty key (no encryption)

        if enabled is False:
            return

        if not raw_key:
            if enabled is True:
                raise RuntimeError(
                    f"Encryption required but env var {key_env_var} is not set"
                )
            return  # auto mode – no key → plain IO

        if not _HAS_FERNET:
            if enabled is True:
                raise RuntimeError(
                    "Encryption required but 'cryptography' package is not installed"
                )
            logger.warning("Key found but cryptography not installed – skipping encryption")
            return

        # Hardened KDF: PBKDF2 with configurable salt and 100k iterations
        salt = os.environ.get(f"{key_env_var}_SALT", "voice-vision-default-salt").encode()
        derived = hashlib.pbkdf2_hmac("sha256", raw_key.encode(), salt, iterations=100_000)
        fernet_key = base64.urlsafe_b64encode(derived)
        self._fernet = Fernet(fernet_key)
        self._enabled = True

        # Keep legacy Fernet for migration (old files encrypted with SHA-256-derived key)
        legacy_derived = hashlib.sha256(raw_key.encode()).digest()
        legacy_fernet_key = base64.urlsafe_b64encode(legacy_derived)
        self._legacy_fernet = Fernet(legacy_fernet_key)

        logger.info("Encryption enabled (AES-128-CBC via Fernet, PBKDF2 KDF)")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def active(self) -> bool:
        """Return whether encryption is actually in use."""
        return self._enabled and self._fernet is not None

    def encrypt(self, data: bytes) -> bytes:
        """Encrypt raw bytes.  Returns *data* unchanged if disabled."""
        if not self.active:
            return data
        logger.debug("encrypt: %d bytes", len(data))
        return self._fernet.encrypt(data)  # type: ignore[union-attr]

    def decrypt(self, token: bytes) -> bytes:
        """Decrypt a Fernet token. Falls back to legacy key if PBKDF2 key fails."""
        if not self.active:
            return token
        logger.debug("decrypt: %d bytes", len(token))
        try:
            return self._fernet.decrypt(token)  # type: ignore[union-attr]
        except Exception:
            if self._legacy_fernet:
                logger.warning("Decrypting with legacy SHA-256 key derivation - re-encrypt recommended")
                try:
                    return self._legacy_fernet.decrypt(token)
                except Exception as exc:
                    logger.error("Decryption failed with both PBKDF2 and legacy keys: %s", exc)
                    raise
            raise

    def save_encrypted(self, path: str | Path, data: bytes) -> None:
        """Write *data* to *path*, encrypting if enabled."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.encrypt(data))

    def load_decrypted(self, path: str | Path) -> bytes:
        """Read *path* and return decrypted bytes."""
        return self.decrypt(Path(path).read_bytes())

    # ------------------------------------------------------------------
    # Convenience: NumPy arrays (face embeddings, etc.)
    # ------------------------------------------------------------------

    def save_npy_encrypted(self, path: str | Path, arr) -> None:
        """Serialize a numpy array and encrypt it on disk."""
        import io, numpy as np  # noqa: E401
        buf = io.BytesIO()
        np.save(buf, arr)
        self.save_encrypted(path, buf.getvalue())

    def load_npy_decrypted(self, path: str | Path):
        """Load an encrypted ``.npy`` file and return the numpy array."""
        import io, numpy as np  # noqa: E401
        raw = self.load_decrypted(path)
        return np.load(io.BytesIO(raw))

    # ------------------------------------------------------------------
    # Convenience: JSON
    # ------------------------------------------------------------------

    def save_json_encrypted(self, path: str | Path, obj) -> None:
        """Serialize *obj* to JSON and encrypt."""
        import json
        self.save_encrypted(path, json.dumps(obj, indent=2).encode())

    def load_json_decrypted(self, path: str | Path):
        """Load an encrypted JSON file."""
        import json
        return json.loads(self.load_decrypted(path).decode())


# ── Singleton (shared across modules) ────────────────────────────────

_instance: Optional[EncryptionManager] = None


def get_encryption_manager(
    key_env_var: str = "MEMORY_ENCRYPTION_KEY",
    enabled: Optional[bool] = None,
) -> EncryptionManager:
    """Return the process-wide ``EncryptionManager`` singleton."""
    global _instance
    if _instance is None:
        _instance = EncryptionManager(key_env_var=key_env_var, enabled=enabled)
    return _instance


def reset_encryption_manager() -> None:
    """Reset singleton (testing only)."""
    global _instance
    _instance = None
