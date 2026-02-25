"""Unit tests for infrastructure.storage adapter."""

# pyright: reportUnknownParameterType=false, reportMissingParameterType=false

from __future__ import annotations

from pathlib import Path

import pytest

from infrastructure.storage.adapter import LocalFileStorage


async def test_save_and_load_json(tmp_path: Path) -> None:
    storage = LocalFileStorage(base_dir=tmp_path)
    payload = {"name": "ally", "count": 3}

    await storage.save_json("profiles/user_1", payload)
    loaded = await storage.load_json("profiles/user_1")

    assert loaded == payload


async def test_save_and_load_binary(tmp_path: Path) -> None:
    storage = LocalFileStorage(base_dir=tmp_path)
    payload = b"\x00\x01\x02\xff"

    await storage.save_binary("blobs/item_1", payload)
    loaded = await storage.load_binary("blobs/item_1")

    assert loaded == payload


async def test_delete_removes_file(tmp_path: Path) -> None:
    storage = LocalFileStorage(base_dir=tmp_path)
    await storage.save_json("sessions/abc", {"ok": True})

    _ = await storage.delete("sessions/abc")

    assert await storage.exists("sessions/abc") is False


async def test_list_keys_returns_stored(tmp_path: Path) -> None:
    storage = LocalFileStorage(base_dir=tmp_path)
    keys = {"alpha/one", "alpha/two", "beta/one"}

    await storage.save_json("alpha/one", {"id": 1})
    await storage.save_binary("alpha/two", b"data")
    await storage.save_json("beta/one", {"id": 2})

    listed = await storage.list_keys()

    assert set(listed) == keys


async def test_list_keys_with_prefix(tmp_path: Path) -> None:
    storage = LocalFileStorage(base_dir=tmp_path)
    await storage.save_json("alpha/one", {"id": 1})
    await storage.save_json("alpha/two", {"id": 2})
    await storage.save_binary("beta/one", b"data")

    listed = await storage.list_keys(prefix="alpha/")

    assert set(listed) == {"alpha/one", "alpha/two"}


async def test_load_missing_returns_none(tmp_path: Path) -> None:
    storage = LocalFileStorage(base_dir=tmp_path)

    assert await storage.load_json("missing/key") is None


async def test_path_traversal_rejected(tmp_path: Path) -> None:
    storage = LocalFileStorage(base_dir=tmp_path)

    with pytest.raises(ValueError):
        await storage.save_json("../escape", {"no": "thanks"})


async def test_health_reports_base_dir(tmp_path: Path) -> None:
    storage = LocalFileStorage(base_dir=tmp_path)
    await storage.save_json("health/check", {"ok": True})

    health = await storage.health()

    assert health["base_dir"] == str(tmp_path)
    assert health["item_count"] == 1
