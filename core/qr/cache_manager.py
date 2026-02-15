"""
Offline Cache Manager for QR/AR scan results.

Design: offline-first.
- Every scan result is stored locally (JSON file).
- Subsequent scans for the same payload return the cached result
  instantly when the network is unavailable.
- Entries have configurable TTL (time-to-live) and support manual refresh.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("qr-cache")

DEFAULT_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "qr_cache")
DEFAULT_TTL_SECONDS = 86400  # 24 hours


@dataclass
class CacheEntry:
    """Single cached QR scan result."""

    key: str  # SHA-256 of raw_data
    raw_data: str
    content_type: str
    contextual_message: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = "online"  # "online" or "offline"
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0  # 0 = never
    navigation_available: bool = False
    lat: Optional[float] = None
    lon: Optional[float] = None

    @property
    def is_expired(self) -> bool:
        if self.expires_at <= 0:
            return False
        return time.time() > self.expires_at

    def to_dict(self) -> dict:
        return asdict(self)


class CacheManager:
    """
    JSON-file-backed offline cache for QR scan results.

    - ``cache_dir``: directory for persistence (auto-created).
    - ``ttl``: default time-to-live per entry in seconds.
    - ``max_entries``: evict oldest when exceeded (0 = unlimited).
    """

    def __init__(
        self,
        cache_dir: str = DEFAULT_CACHE_DIR,
        ttl: int = DEFAULT_TTL_SECONDS,
        max_entries: int = 5000,
    ) -> None:
        self._cache_dir = Path(cache_dir)
        self._ttl = ttl
        self._max_entries = max_entries
        self._index_path = self._cache_dir / "_index.json"
        self._index: Dict[str, Dict[str, Any]] = {}

        self._ensure_dir()
        self._load_index()
        logger.info(
            f"QR cache initialised: {len(self._index)} entries, dir={self._cache_dir}"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def make_key(raw_data: str) -> str:
        """Deterministic key from raw QR content."""
        return hashlib.sha256(raw_data.encode("utf-8")).hexdigest()[:32]

    def get(self, raw_data: str) -> Optional[CacheEntry]:
        """Return cached entry or ``None``."""
        key = self.make_key(raw_data)
        meta = self._index.get(key)
        if meta is None:
            return None

        entry = self._load_entry(key)
        if entry is None:
            return None

        if entry.is_expired:
            logger.debug(f"Cache EXPIRED for key={key[:8]}…")
            self._delete_entry(key)
            return None

        logger.debug(f"Cache HIT for key={key[:8]}…")
        return entry

    def put(
        self,
        raw_data: str,
        content_type: str,
        contextual_message: str,
        metadata: Optional[Dict[str, Any]] = None,
        source: str = "online",
        ttl: Optional[int] = None,
        navigation_available: bool = False,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
    ) -> CacheEntry:
        """Store or update a cache entry."""
        key = self.make_key(raw_data)
        now = time.time()
        effective_ttl = ttl if ttl is not None else self._ttl
        expires = now + effective_ttl if effective_ttl > 0 else 0.0

        entry = CacheEntry(
            key=key,
            raw_data=raw_data,
            content_type=content_type,
            contextual_message=contextual_message,
            metadata=metadata or {},
            source=source,
            created_at=now,
            expires_at=expires,
            navigation_available=navigation_available,
            lat=lat,
            lon=lon,
        )

        self._save_entry(entry)
        self._evict_if_needed()
        logger.debug(f"Cache PUT key={key[:8]}… source={source}")
        return entry

    def delete(self, raw_data: str) -> bool:
        """Remove a single entry. Returns True if found."""
        key = self.make_key(raw_data)
        return self._delete_entry(key)

    def clear(self) -> int:
        """Remove all cached entries. Returns count deleted."""
        count = len(self._index)
        for key in list(self._index):
            self._delete_entry(key)
        return count

    def history(self, limit: int = 50) -> List[CacheEntry]:
        """Return the most recent entries (newest first)."""
        entries: List[CacheEntry] = []
        sorted_keys = sorted(
            self._index.keys(),
            key=lambda k: self._index[k].get("created_at", 0),
            reverse=True,
        )
        for key in sorted_keys[:limit]:
            e = self._load_entry(key)
            if e:
                entries.append(e)
        return entries

    def refresh(self, raw_data: str) -> bool:
        """Mark entry for refresh (delete so next scan re-fetches)."""
        return self.delete(raw_data)

    @property
    def size(self) -> int:
        return len(self._index)

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _ensure_dir(self) -> None:
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _load_index(self) -> None:
        if self._index_path.exists():
            try:
                with open(self._index_path, "r", encoding="utf-8") as f:
                    self._index = json.load(f)
            except Exception:
                self._index = {}

    def _save_index(self) -> None:
        try:
            with open(self._index_path, "w", encoding="utf-8") as f:
                json.dump(self._index, f, indent=1)
        except Exception as exc:
            logger.error(f"Failed to write cache index: {exc}")

    def _entry_path(self, key: str) -> Path:
        return self._cache_dir / f"{key}.json"

    def _load_entry(self, key: str) -> Optional[CacheEntry]:
        p = self._entry_path(key)
        if not p.exists():
            return None
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            return CacheEntry(**data)
        except Exception as exc:
            logger.debug(f"Failed to load cache entry {key[:8]}…: {exc}")
            return None

    def _save_entry(self, entry: CacheEntry) -> None:
        p = self._entry_path(entry.key)
        try:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(entry.to_dict(), f, indent=1)
            # Update index
            self._index[entry.key] = {
                "created_at": entry.created_at,
                "content_type": entry.content_type,
                "raw_data_preview": entry.raw_data[:60],
            }
            self._save_index()
        except Exception as exc:
            logger.error(f"Failed to save cache entry: {exc}")

    def _delete_entry(self, key: str) -> bool:
        if key not in self._index:
            return False
        p = self._entry_path(key)
        try:
            p.unlink(missing_ok=True)
        except Exception:
            pass
        self._index.pop(key, None)
        self._save_index()
        return True

    def _evict_if_needed(self) -> None:
        if self._max_entries <= 0:
            return
        while len(self._index) > self._max_entries:
            oldest_key = min(
                self._index, key=lambda k: self._index[k].get("created_at", 0)
            )
            self._delete_entry(oldest_key)
