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
(default ``MEMORY_ENCRYPTION_KEY``), then URL-safe base64-encoded
for Fernet.  If no key is set the module gracefully degrades to
plain I/O so the assistant still works un-encrypted.

Usage::

    from shared.utils.encryption import EncryptionManager

    enc = EncryptionManager()          # reads key from env
    enc.save_encrypted(path, data)     # bytes → encrypted file
    data = enc.load_decrypted(path)    # encrypted file → bytes
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
    from cryptography.fernet import Fernet, InvalidToken  # type: ignore
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
        self._enabled = False

        raw_key = os.environ.get(key_env_var, "").strip()

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

        # Derive a 32-byte key via SHA-256 then base64-encode for Fernet
        derived = hashlib.sha256(raw_key.encode()).digest()
        fernet_key = base64.urlsafe_b64encode(derived)
        self._fernet = Fernet(fernet_key)
        self._enabled = True
        logger.info("Encryption enabled (AES-128-CBC via Fernet)")

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
        return self._fernet.encrypt(data)  # type: ignore[union-attr]

    def decrypt(self, token: bytes) -> bytes:
        """Decrypt a Fernet token.  Returns *token* unchanged if disabled."""
        if not self.active:
            return token
        try:
            return self._fernet.decrypt(token)  # type: ignore[union-attr]
        except Exception as exc:
            logger.error("Decryption failed – is the key correct? %s", exc)
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
