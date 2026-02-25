"""Storage adapters for local persistence."""

# pyright: reportImplicitOverride=false, reportAny=false, reportDeprecated=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

from __future__ import annotations

import asyncio
import json
import logging
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, Mapping, TypeVar

logger = logging.getLogger("storage-adapter")

_KEY_PATTERN = re.compile(r"^[A-Za-z0-9/_-]+$")
_DEFAULT_IO_TIMEOUT_S = 2.0

T = TypeVar("T")


JsonValue = object
JsonDict = dict[str, JsonValue]
JsonMapping = Mapping[str, JsonValue]


class StorageAdapter(ABC):
    """Abstract storage adapter for JSON and binary blobs."""

    @abstractmethod
    async def save_json(self, key: str, data: JsonMapping) -> None:
        """Persist JSON-serializable data under key."""

    @abstractmethod
    async def load_json(self, key: str) -> JsonDict | None:
        """Load JSON data for key, or None if missing."""

    @abstractmethod
    async def save_binary(self, key: str, data: bytes) -> None:
        """Persist binary data under key."""

    @abstractmethod
    async def load_binary(self, key: str) -> bytes | None:
        """Load binary data for key, or None if missing."""

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete stored data for key. Returns True if anything removed."""

    @abstractmethod
    async def list_keys(self, prefix: str = "") -> list[str]:
        """List stored keys, optionally filtered by prefix."""

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Return True if key exists in storage."""

    @abstractmethod
    async def health(self) -> dict[str, object]:
        """Return storage health metadata."""


class LocalFileStorage(StorageAdapter):
    """Local filesystem-backed storage adapter."""

    def __init__(self, base_dir: str | Path = "data/storage") -> None:
        """Initialize storage with a base directory."""
        self._base_dir: Path = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._io_timeout_s: float = _DEFAULT_IO_TIMEOUT_S

    def _validate_key(self, key: str) -> Path:
        """Validate a storage key and return its base path."""
        if not key:
            raise ValueError("Storage key must be a non-empty string")
        if key.startswith(("/", "\\")) or ".." in key or "\\" in key:
            raise ValueError(f"Invalid storage key: {key}")
        if key.endswith("/"):
            raise ValueError(f"Invalid storage key: {key}")
        if not _KEY_PATTERN.fullmatch(key):
            raise ValueError(f"Invalid storage key: {key}")
        return self._base_dir / key

    def _validate_prefix(self, prefix: str) -> None:
        """Validate prefix filter for list_keys."""
        if not prefix:
            return
        if prefix.startswith(("/", "\\")) or ".." in prefix or "\\" in prefix:
            raise ValueError(f"Invalid storage prefix: {prefix}")
        trimmed = prefix.rstrip("/")
        if trimmed and not _KEY_PATTERN.fullmatch(trimmed):
            raise ValueError(f"Invalid storage prefix: {prefix}")

    def _json_path(self, key: str) -> Path:
        return self._validate_key(key).with_suffix(".json")

    def _binary_path(self, key: str) -> Path:
        return self._validate_key(key).with_suffix(".bin")

    async def _run_io(
        self,
        func: Callable[..., T],
        *args: object,
        **kwargs: object,
    ) -> T:
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(func, *args, **kwargs),
                timeout=self._io_timeout_s,
            )
        except asyncio.TimeoutError as exc:
            logger.error("Storage IO timed out after %.1fs", self._io_timeout_s)
            raise exc

    async def save_json(self, key: str, data: JsonMapping) -> None:
        path = self._json_path(key)
        payload = json.dumps(data)

        def _write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            _ = path.write_text(payload, encoding="utf-8")

        try:
            await self._run_io(_write)
        except Exception as exc:
            logger.error("Failed to save json for key %s: %s", key, exc)
            raise

    async def load_json(self, key: str) -> JsonDict | None:
        path = self._json_path(key)

        def _read() -> str | None:
            if not path.exists():
                return None
            return path.read_text(encoding="utf-8")

        try:
            payload = await self._run_io(_read)
        except Exception as exc:
            logger.error("Failed to load json for key %s: %s", key, exc)
            return None

        if payload is None:
            return None

        try:
            data = json.loads(payload)
            if isinstance(data, dict):
                normalized: JsonDict = {str(key): value for key, value in data.items()}
                return normalized
            logger.error("JSON payload for key %s is not a dict", key)
            return None
        except json.JSONDecodeError as exc:
            logger.error("Failed to decode json for key %s: %s", key, exc)
            return None

    async def save_binary(self, key: str, data: bytes) -> None:
        path = self._binary_path(key)

        def _write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            _ = path.write_bytes(data)

        try:
            await self._run_io(_write)
        except Exception as exc:
            logger.error("Failed to save binary for key %s: %s", key, exc)
            raise

    async def load_binary(self, key: str) -> bytes | None:
        path = self._binary_path(key)

        def _read() -> bytes | None:
            if not path.exists():
                return None
            return path.read_bytes()

        try:
            return await self._run_io(_read)
        except Exception as exc:
            logger.error("Failed to load binary for key %s: %s", key, exc)
            return None

    async def delete(self, key: str) -> bool:
        json_path = self._json_path(key)
        bin_path = self._binary_path(key)

        def _delete() -> bool:
            removed = False
            if json_path.exists():
                json_path.unlink()
                removed = True
            if bin_path.exists():
                bin_path.unlink()
                removed = True
            return removed

        try:
            return await self._run_io(_delete)
        except Exception as exc:
            logger.error("Failed to delete key %s: %s", key, exc)
            return False

    async def list_keys(self, prefix: str = "") -> list[str]:
        self._validate_prefix(prefix)

        def _scan() -> list[str]:
            if not self._base_dir.exists():
                return []
            keys: set[str] = set()
            for path in self._base_dir.rglob("*"):
                if path.is_file() and path.suffix in {".json", ".bin"}:
                    rel_path = path.relative_to(self._base_dir)
                    key = rel_path.with_suffix("").as_posix()
                    keys.add(key)
            results = sorted(keys)
            if prefix:
                results = [key for key in results if key.startswith(prefix)]
            return results

        try:
            return await self._run_io(_scan)
        except Exception as exc:
            logger.error("Failed to list keys: %s", exc)
            return []

    async def exists(self, key: str) -> bool:
        json_path = self._json_path(key)
        bin_path = self._binary_path(key)

        def _exists() -> bool:
            return json_path.exists() or bin_path.exists()

        try:
            return await self._run_io(_exists)
        except Exception as exc:
            logger.error("Failed to check exists for key %s: %s", key, exc)
            return False

    async def health(self) -> dict[str, object]:
        try:
            base_exists = await self._run_io(self._base_dir.exists)
        except Exception as exc:
            logger.error("Failed to check base directory: %s", exc)
            base_exists = False
        keys = await self.list_keys()
        return {
            "base_dir": str(self._base_dir),
            "exists": bool(base_exists),
            "item_count": len(keys),
        }


def create_storage_adapter(storage_type: str = "local", **kwargs: object) -> StorageAdapter:
    """Factory for storage adapters."""
    if storage_type == "local":
        base_dir = kwargs.get("base_dir", "data/storage")
        if not isinstance(base_dir, (str, Path)):
            raise ValueError("base_dir must be a str or Path")
        return LocalFileStorage(base_dir=base_dir)
    raise ValueError(f"Unknown storage type: {storage_type}")
