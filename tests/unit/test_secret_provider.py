"""Tests for SecretProvider abstraction."""
import os
from pathlib import Path

import pytest

from shared.config.secret_provider import (
    SECRET_KEYS,
    EnvFileProvider,
    EnvironmentProvider,
    SecretProvider,
    _is_docker,
    create_secret_provider,
)


class TestEnvironmentProvider:
    def test_returns_set_env_var(self, monkeypatch):
        monkeypatch.setenv("TEST_KEY", "test_value")
        provider = EnvironmentProvider()
        assert os.environ.get("TEST_KEY") == "test_value"
        assert isinstance(monkeypatch, pytest.MonkeyPatch)
        assert provider.get_secret("TEST_KEY") == "test_value"

    def test_returns_none_for_missing(self):
        provider = EnvironmentProvider()
        assert provider.get_secret("NONEXISTENT_KEY_XYZ_123") is None

    def test_returns_none_for_empty(self, monkeypatch):
        monkeypatch.setenv("TEST_KEY", "")
        provider = EnvironmentProvider()
        assert provider.get_secret("TEST_KEY") is None

    def test_strips_whitespace(self, monkeypatch):
        monkeypatch.setenv("TEST_KEY", "  value_with_spaces  ")
        provider = EnvironmentProvider()
        assert provider.get_secret("TEST_KEY") == "value_with_spaces"

    def test_health_check_always_true(self):
        assert EnvironmentProvider().health_check() is True

    def test_supports_rotation_false(self):
        provider = EnvironmentProvider()
        assert provider.supports_rotation() is False
        assert isinstance(provider, SecretProvider)


class TestEnvFileProvider:
    def test_reads_env_file(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("MY_KEY=my_value\nOTHER=123\n")
        provider = EnvFileProvider(str(env_file))
        assert isinstance(env_file, Path)
        assert provider.get_secret("MY_KEY") == "my_value"
        assert provider.get_secret("OTHER") == "123"

    def test_ignores_comments(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("# This is a comment\nKEY=value\n# Another comment\n")
        provider = EnvFileProvider(str(env_file))
        assert provider.get_secret("KEY") == "value"
        assert provider.get_secret("# This is a comment") is None

    def test_ignores_blank_lines(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("\n\nKEY=value\n\n")
        provider = EnvFileProvider(str(env_file))
        assert provider.get_secret("KEY") == "value"

    def test_handles_quoted_values(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("SINGLE='single_val'\nDOUBLE=\"double_val\"\n")
        provider = EnvFileProvider(str(env_file))
        assert provider.get_secret("SINGLE") == "single_val"
        assert provider.get_secret("DOUBLE") == "double_val"

    def test_handles_inline_comments(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=value # this is inline\n")
        provider = EnvFileProvider(str(env_file))
        assert provider.get_secret("KEY") == "value"

    def test_handles_values_with_equals(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("URL=http://host:8080/path?key=val\n")
        provider = EnvFileProvider(str(env_file))
        assert provider.get_secret("URL") == "http://host:8080/path?key=val"

    def test_returns_none_for_missing_key(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=value\n")
        provider = EnvFileProvider(str(env_file))
        assert provider.get_secret("MISSING") is None

    def test_health_check_true_when_loaded(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=value\n")
        provider = EnvFileProvider(str(env_file))
        assert provider.health_check() is True

    def test_health_check_false_when_no_file(self, tmp_path):
        provider = EnvFileProvider(str(tmp_path / "nonexistent.env"))
        assert provider.health_check() is False

    def test_supports_rotation_false(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=value\n")
        assert EnvFileProvider(str(env_file)).supports_rotation() is False


class TestDockerDetection:
    def test_not_docker_by_default(self, monkeypatch):
        monkeypatch.delenv("DOCKER", raising=False)
        monkeypatch.delenv("CONTAINER", raising=False)
        # Note: /.dockerenv won't exist in test environment
        assert _is_docker() is False

    def test_docker_env_var(self, monkeypatch):
        monkeypatch.setenv("DOCKER", "true")
        assert _is_docker() is True

    def test_container_env_var(self, monkeypatch):
        monkeypatch.setenv("CONTAINER", "true")
        assert _is_docker() is True


class TestFactory:
    def test_returns_env_file_provider_locally(self, monkeypatch):
        monkeypatch.delenv("DOCKER", raising=False)
        monkeypatch.delenv("CONTAINER", raising=False)
        # The factory should return EnvFileProvider if .env exists,
        # or EnvironmentProvider if it doesn't
        provider = create_secret_provider()
        assert isinstance(provider, (EnvFileProvider, EnvironmentProvider))

    def test_returns_environment_provider_in_docker(self, monkeypatch):
        monkeypatch.setenv("DOCKER", "true")
        provider = create_secret_provider()
        assert isinstance(provider, EnvironmentProvider)


class TestSecretKeys:
    def test_secret_keys_contains_expected(self):
        expected = {
            "LIVEKIT_API_KEY",
            "LIVEKIT_API_SECRET",
            "DEEPGRAM_API_KEY",
            "OLLAMA_API_KEY",
            "ELEVEN_API_KEY",
            "OLLAMA_VL_API_KEY",
            "TAVUS_API_KEY",
        }
        assert SECRET_KEYS == expected

    def test_secret_keys_is_frozenset(self):
        assert isinstance(SECRET_KEYS, frozenset)
