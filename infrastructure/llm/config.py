"""LLM infrastructure configuration.

Delegates to shared.config.settings for base values and adds
LLM-specific timeout, connection-pool, and retry settings.
"""

import logging
import os
from typing import Any, Dict

from shared.config.settings import get_config as _get_shared_config

logger = logging.getLogger("llm-config")

# -- LLM-specific overrides (env → sensible defaults) -------------------------

LLM_CONNECT_TIMEOUT_S: float = float(os.environ.get("LLM_CONNECT_TIMEOUT_S", "5"))
LLM_READ_TIMEOUT_S: float = float(os.environ.get("LLM_READ_TIMEOUT_S", "30"))
LLM_TOTAL_TIMEOUT_S: float = float(os.environ.get("LLM_TOTAL_TIMEOUT_S", "60"))
LLM_MAX_CONNECTIONS: int = int(os.environ.get("LLM_MAX_CONNECTIONS", "20"))
LLM_MAX_KEEPALIVE: int = int(os.environ.get("LLM_MAX_KEEPALIVE", "10"))
LLM_MAX_RETRIES: int = int(os.environ.get("LLM_MAX_RETRIES", "3"))
LLM_BACKOFF_BASE: float = float(os.environ.get("LLM_BACKOFF_BASE", "0.5"))


def get_config() -> Dict[str, Any]:
    """Return merged LLM configuration.

    Includes all keys from shared CONFIG plus LLM-specific timeout/pool
    settings. Never raises — missing keys get sensible defaults.
    """
    cfg = dict(_get_shared_config())  # shallow copy so we don't mutate shared
    cfg.update({
        "LLM_CONNECT_TIMEOUT_S": LLM_CONNECT_TIMEOUT_S,
        "LLM_READ_TIMEOUT_S": LLM_READ_TIMEOUT_S,
        "LLM_TOTAL_TIMEOUT_S": LLM_TOTAL_TIMEOUT_S,
        "LLM_MAX_CONNECTIONS": LLM_MAX_CONNECTIONS,
        "LLM_MAX_KEEPALIVE": LLM_MAX_KEEPALIVE,
        "LLM_MAX_RETRIES": LLM_MAX_RETRIES,
        "LLM_BACKOFF_BASE": LLM_BACKOFF_BASE,
    })
    return cfg


def get_llm_timeout_config() -> Dict[str, float]:
    """Per-provider timeout configuration."""
    return {
        "connect": LLM_CONNECT_TIMEOUT_S,
        "read": LLM_READ_TIMEOUT_S,
        "total": LLM_TOTAL_TIMEOUT_S,
    }
