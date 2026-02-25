"""Secret provider abstraction for credential management.

Decouples secret retrieval from direct os.environ access, enabling
future backend extensions (vault, KMS) without changing consumer code.
"""
from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

logger = logging.getLogger("secret-provider")


class SecretProvider(ABC):
    """Abstract base for secret retrieval backends."""

    @abstractmethod
    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret by key name. Returns None if not found."""
        ...

    def supports_rotation(self) -> bool:
        """Whether this provider supports key rotation."""
        return False

    def health_check(self) -> bool:
        """Verify the provider is operational."""
        return True


class EnvironmentProvider(SecretProvider):
    """Reads secrets from OS environment variables (Docker/CI)."""

    def get_secret(self, key: str) -> Optional[str]:
        value = os.environ.get(key, "").strip()
        return value if value else None

    def health_check(self) -> bool:
        return True


class EnvFileProvider(SecretProvider):
    """Reads secrets from .env files (local development).

    Parses KEY=VALUE format. Handles comments, blank lines,
    single/double quoted values, and inline comments.
    No python-dotenv dependency required.
    """

    def __init__(self, env_path: str = ".env"):
        self._secrets: dict[str, str] = {}
        self._path = env_path
        self._load(env_path)

    def _load(self, path: str) -> None:
        env_file = Path(path)
        if not env_file.is_file():
            logger.debug("No .env file at %s", path)
            return
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            # Strip surrounding quotes
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            # Strip inline comments (only for unquoted values)
            elif "#" in value:
                value = value.split("#", 1)[0].strip()
            if key:
                self._secrets[key] = value

    def get_secret(self, key: str) -> Optional[str]:
        return self._secrets.get(key)

    def health_check(self) -> bool:
        return len(self._secrets) > 0


# -- Secrets that should be routed through the provider --
SECRET_KEYS = frozenset({
    "LIVEKIT_API_KEY",
    "LIVEKIT_API_SECRET",
    "DEEPGRAM_API_KEY",
    "OLLAMA_API_KEY",
    "ELEVEN_API_KEY",
    "OLLAMA_VL_API_KEY",
    "TAVUS_API_KEY",
})


def _is_docker() -> bool:
    """Detect if running inside a Docker container."""
    return (
        os.path.exists("/.dockerenv")
        or os.environ.get("DOCKER", "").lower() == "true"
        or os.environ.get("CONTAINER", "").lower() == "true"
    )


def create_secret_provider() -> SecretProvider:
    """Auto-detect environment and return appropriate provider."""
    if _is_docker():
        logger.info("Docker detected — using EnvironmentProvider")
        return EnvironmentProvider()
    provider = EnvFileProvider()
    if provider.health_check():
        logger.info("Using EnvFileProvider (.env file found)")
    else:
        logger.info("No .env file — falling back to EnvironmentProvider")
        return EnvironmentProvider()
    return provider
