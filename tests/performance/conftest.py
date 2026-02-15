"""Shared fixtures for NFR tests."""

from __future__ import annotations

import os
import sys
import pytest

# Ensure project root is importable
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture
def project_root() -> str:
    """Absolute path to the project root directory."""
    return PROJECT_ROOT


@pytest.fixture
def env_overrides(monkeypatch):
    """Helper to temporarily override env vars during a test."""
    def _set(**kwargs):
        for key, val in kwargs.items():
            monkeypatch.setenv(key, str(val))
    return _set
