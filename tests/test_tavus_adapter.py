"""
Tests for tavus_adapter — TavusAdapter, TavusConfig, TavusMessage.
"""

from __future__ import annotations

import os
import pytest

from infrastructure.tavus.adapter import TavusAdapter, TavusConfig, TavusMessage


class TestTavusConfig:
    def test_defaults(self):
        cfg = TavusConfig()
        assert cfg.enabled is False
        assert cfg.api_key == ""
        assert cfg.replica_id == ""
        assert cfg.base_url == "https://api.tavus.io/v2"

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("TAVUS_ENABLED", "false")
        monkeypatch.setenv("TAVUS_API_KEY", "")
        cfg = TavusConfig.from_env()
        assert cfg.enabled is False

    def test_from_env_enabled(self, monkeypatch):
        monkeypatch.setenv("TAVUS_ENABLED", "true")
        monkeypatch.setenv("TAVUS_API_KEY", "test-key")
        monkeypatch.setenv("TAVUS_REPLICA_ID", "r123")
        cfg = TavusConfig.from_env()
        assert cfg.enabled is True
        assert cfg.api_key == "test-key"
        assert cfg.replica_id == "r123"


class TestTavusAdapter:
    def test_init_disabled(self):
        adapter = TavusAdapter(TavusConfig(enabled=False))
        assert adapter.enabled is False

    def test_enabled_requires_key_and_replica(self):
        adapter = TavusAdapter(TavusConfig(enabled=True, api_key="", replica_id=""))
        assert adapter.enabled is False

    def test_enabled_with_credentials(self):
        adapter = TavusAdapter(TavusConfig(enabled=True, api_key="key", replica_id="rep"))
        assert adapter.enabled is True

    @pytest.mark.asyncio
    async def test_connect_disabled(self):
        adapter = TavusAdapter(TavusConfig(enabled=False))
        result = await adapter.connect()
        assert result is False

    @pytest.mark.asyncio
    async def test_send_narration_disabled(self):
        adapter = TavusAdapter(TavusConfig(enabled=False))
        result = await adapter.send_narration("test")
        assert result is False

    @pytest.mark.asyncio
    async def test_disconnect_disabled(self):
        adapter = TavusAdapter(TavusConfig(enabled=False))
        await adapter.disconnect()  # should not raise

    def test_health(self):
        adapter = TavusAdapter(TavusConfig(enabled=False))
        h = adapter.health()
        assert h["enabled"] is False
        assert h["connected"] is False

    def test_get_history_empty(self):
        adapter = TavusAdapter()
        assert adapter.get_history() == []


class TestTavusMessage:
    def test_to_dict(self):
        msg = TavusMessage(role="user", text="Hello", timestamp_ms=1000)
        d = msg.to_dict()
        assert d["role"] == "user"
        assert d["text"] == "Hello"
