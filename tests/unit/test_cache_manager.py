"""
Unit tests for the QR/AR Cache Manager.
"""

import time

import pytest

from core.qr.cache_manager import CacheEntry, CacheManager


@pytest.fixture
def tmp_cache_dir(tmp_path):
    """Provide a temporary cache directory."""
    return str(tmp_path / "qr_cache_test")


@pytest.fixture
def cache(tmp_cache_dir):
    """Provide a fresh CacheManager instance."""
    return CacheManager(cache_dir=tmp_cache_dir, ttl=3600, max_entries=100)


class TestCacheEntry:
    def test_entry_fields(self):
        e = CacheEntry(
            key="abc123",
            raw_data="https://example.com",
            content_type="url",
            contextual_message="Link to example.com.",
        )
        assert e.key == "abc123"
        assert e.raw_data == "https://example.com"
        assert not e.is_expired

    def test_entry_expired(self):
        e = CacheEntry(
            key="x",
            raw_data="old",
            content_type="text",
            contextual_message="old data",
            expires_at=time.time() - 10,
        )
        assert e.is_expired

    def test_entry_no_expiry(self):
        e = CacheEntry(
            key="x",
            raw_data="data",
            content_type="text",
            contextual_message="data",
            expires_at=0,
        )
        assert not e.is_expired

    def test_to_dict(self):
        e = CacheEntry(
            key="k", raw_data="r", content_type="text", contextual_message="m"
        )
        d = e.to_dict()
        assert d["key"] == "k"
        assert "created_at" in d


class TestCacheManager:
    def test_make_key_deterministic(self):
        k1 = CacheManager.make_key("hello")
        k2 = CacheManager.make_key("hello")
        assert k1 == k2

    def test_make_key_different(self):
        k1 = CacheManager.make_key("abc")
        k2 = CacheManager.make_key("xyz")
        assert k1 != k2

    def test_put_and_get(self, cache):
        cache.put(
            raw_data="test_data",
            content_type="text",
            contextual_message="Test message.",
        )
        entry = cache.get("test_data")
        assert entry is not None
        assert entry.contextual_message == "Test message."
        assert entry.content_type == "text"

    def test_get_miss(self, cache):
        assert cache.get("nonexistent") is None

    def test_put_overwrites(self, cache):
        cache.put(raw_data="data", content_type="text", contextual_message="v1")
        cache.put(raw_data="data", content_type="text", contextual_message="v2")
        entry = cache.get("data")
        assert entry.contextual_message == "v2"

    def test_delete(self, cache):
        cache.put(raw_data="del_me", content_type="text", contextual_message="bye")
        assert cache.delete("del_me") is True
        assert cache.get("del_me") is None

    def test_delete_nonexistent(self, cache):
        assert cache.delete("no_such") is False

    def test_clear(self, cache):
        for i in range(5):
            cache.put(raw_data=f"item_{i}", content_type="text", contextual_message=f"m{i}")
        count = cache.clear()
        assert count == 5
        assert cache.size == 0

    def test_history(self, cache):
        for i in range(3):
            cache.put(raw_data=f"h_{i}", content_type="text", contextual_message=f"hist {i}")
        history = cache.history(limit=10)
        assert len(history) == 3
        # Newest first
        assert history[0].raw_data == "h_2"

    def test_expiry(self, tmp_cache_dir):
        cache = CacheManager(cache_dir=tmp_cache_dir, ttl=1, max_entries=100)
        cache.put(raw_data="expire_me", content_type="text", contextual_message="short lived")
        # Should be present immediately
        assert cache.get("expire_me") is not None
        # Sleep to exceed TTL
        time.sleep(1.5)
        assert cache.get("expire_me") is None

    def test_max_entries_eviction(self, tmp_cache_dir):
        cache = CacheManager(cache_dir=tmp_cache_dir, ttl=3600, max_entries=3)
        for i in range(5):
            cache.put(raw_data=f"evict_{i}", content_type="text", contextual_message=f"m{i}")
        assert cache.size <= 3

    def test_refresh(self, cache):
        cache.put(raw_data="refresh_me", content_type="text", contextual_message="old")
        assert cache.refresh("refresh_me") is True
        assert cache.get("refresh_me") is None

    def test_navigation_and_coords(self, cache):
        cache.put(
            raw_data="nav_test",
            content_type="location",
            contextual_message="A location.",
            navigation_available=True,
            lat=37.77,
            lon=-122.42,
        )
        entry = cache.get("nav_test")
        assert entry.navigation_available is True
        assert entry.lat == pytest.approx(37.77)
        assert entry.lon == pytest.approx(-122.42)

    def test_persistence(self, tmp_cache_dir):
        """Entries survive re-instantiation."""
        c1 = CacheManager(cache_dir=tmp_cache_dir, ttl=3600)
        c1.put(raw_data="persist", content_type="text", contextual_message="saved")

        c2 = CacheManager(cache_dir=tmp_cache_dir, ttl=3600)
        entry = c2.get("persist")
        assert entry is not None
        assert entry.contextual_message == "saved"
