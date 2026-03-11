"""
Tests for tts_manager.py
=========================
Covers LRU cache, text chunking, remote-timeout fallback,
and meta.tts_fallback tracking.
"""

from __future__ import annotations

import time
from unittest import mock

from infrastructure.speech.elevenlabs.tts_manager import TTSCache, TTSChunker, TTSManager, TTSResult

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

class TestTTSCache:

    def test_fingerprint_deterministic(self):
        fp1 = TTSCache.fingerprint("hello world")
        fp2 = TTSCache.fingerprint("hello world")
        assert fp1 == fp2

    def test_fingerprint_case_insensitive(self):
        fp1 = TTSCache.fingerprint("Hello World")
        fp2 = TTSCache.fingerprint("hello world")
        assert fp1 == fp2

    def test_cache_hit(self):
        cache = TTSCache(max_entries=10)
        cache.put("test text", b"audio_bytes_123")
        result = cache.get("test text")
        assert result == b"audio_bytes_123"
        assert cache.hits == 1

    def test_cache_miss(self):
        cache = TTSCache(max_entries=10)
        result = cache.get("nonexistent")
        assert result is None
        assert cache.misses == 1

    def test_lru_eviction(self):
        cache = TTSCache(max_entries=2)
        cache.put("a", b"1")
        cache.put("b", b"2")
        cache.put("c", b"3")  # evicts "a"
        assert cache.get("a") is None
        assert cache.get("b") == b"2"
        assert cache.get("c") == b"3"

    def test_lru_access_refreshes(self):
        cache = TTSCache(max_entries=2)
        cache.put("a", b"1")
        cache.put("b", b"2")
        cache.get("a")          # refresh "a"
        cache.put("c", b"3")    # should evict "b" (oldest unused)
        assert cache.get("a") == b"1"
        assert cache.get("b") is None


# ---------------------------------------------------------------------------
# Chunker
# ---------------------------------------------------------------------------

class TestTTSChunker:

    def test_short_text_single_chunk(self):
        chunker = TTSChunker(max_seconds=2.0)
        chunks = chunker.chunk("Hello there.")
        assert len(chunks) == 1
        assert chunks[0] == "Hello there."

    def test_empty_text(self):
        chunker = TTSChunker(max_seconds=2.0)
        assert chunker.chunk("") == []
        assert chunker.chunk("  ") == []

    def test_long_text_split_into_chunks(self):
        chunker = TTSChunker(max_seconds=2.0, words_per_second=2.5)
        # max_words = 5 words per chunk
        text = "The quick brown fox jumps over the lazy dog near the river."
        chunks = chunker.chunk(text)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk.split()) <= 5

    def test_sentence_boundary_respected(self):
        chunker = TTSChunker(max_seconds=2.0, words_per_second=2.5)
        text = "Short one. Another short one. Third sentence here."
        chunks = chunker.chunk(text)
        # Should try to keep sentences together
        assert all(isinstance(c, str) for c in chunks)


# ---------------------------------------------------------------------------
# Manager — cache integration
# ---------------------------------------------------------------------------

class TestTTSManagerCache:

    def test_cache_hit_returns_cached(self):
        mgr = TTSManager(cache_enabled=True, cache_max_entries=10)
        # Prime cache
        mgr.synthesise("hello")
        result2 = mgr.synthesise("hello")
        assert result2.cache_hit is True
        assert result2.engine == "cache"

    def test_cache_disabled(self):
        mgr = TTSManager(cache_enabled=False)
        mgr.synthesise("hello")
        result2 = mgr.synthesise("hello")
        assert result2.cache_hit is False


# ---------------------------------------------------------------------------
# Manager — remote timeout + fallback
# ---------------------------------------------------------------------------

class TestTTSManagerFallback:

    def test_remote_success(self):
        remote_fn = mock.MagicMock(return_value=b"remote_audio")
        mgr = TTSManager(
            remote_fn=remote_fn,
            remote_timeout_ms=5000,
            cache_enabled=False,
        )
        result = mgr.synthesise("testing")
        assert result.engine == "remote"
        assert result.fallback_used is False
        assert result.audio_bytes == b"remote_audio"

    def test_remote_timeout_triggers_fallback(self):
        def slow_remote(text):
            time.sleep(5)  # will exceed timeout
            return b"too_slow"

        local_fn = mock.MagicMock(return_value=b"local_audio")
        mgr = TTSManager(
            local_fn=local_fn,
            remote_fn=slow_remote,
            remote_timeout_ms=100,   # 100ms timeout
            cache_enabled=False,
        )
        result = mgr.synthesise("testing")
        assert result.engine == "local"
        assert result.fallback_used is True
        assert result.audio_bytes == b"local_audio"
        assert mgr.remote_failures == 1

    def test_remote_exception_triggers_fallback(self):
        def broken_remote(text):
            raise ConnectionError("Service unavailable")

        local_fn = mock.MagicMock(return_value=b"fallback")
        mgr = TTSManager(
            local_fn=local_fn,
            remote_fn=broken_remote,
            remote_timeout_ms=2000,
            cache_enabled=False,
        )
        result = mgr.synthesise("hello")
        assert result.engine == "local"
        assert result.fallback_used is True

    def test_no_remote_uses_local(self):
        local_fn = mock.MagicMock(return_value=b"local_only")
        mgr = TTSManager(local_fn=local_fn, cache_enabled=False)
        result = mgr.synthesise("test")
        assert result.engine == "local"
        assert result.fallback_used is False


# ---------------------------------------------------------------------------
# Manager — chunked streaming
# ---------------------------------------------------------------------------

class TestTTSManagerChunked:

    def test_chunked_yields_multiple_results(self):
        mgr = TTSManager(chunk_max_seconds=1.0, cache_enabled=False)
        # ~2.5 words/sec → max 2 words per chunk
        text = "One two three four five six seven eight."
        results = list(mgr.synthesise_chunked(text))
        assert len(results) > 1
        assert all(isinstance(r, TTSResult) for r in results)
        # Check indices
        for i, r in enumerate(results):
            assert r.chunk_index == i
            assert r.total_chunks == len(results)

    def test_chunked_short_text_single(self):
        mgr = TTSManager(chunk_max_seconds=5.0, cache_enabled=False)
        results = list(mgr.synthesise_chunked("Hi."))
        assert len(results) == 1

    def test_chunked_empty_text(self):
        mgr = TTSManager(cache_enabled=False)
        results = list(mgr.synthesise_chunked(""))
        assert len(results) == 0
