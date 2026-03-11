"""
Startup Guards
==============

Enforces critical runtime constraints before any perception work begins:

1. **Venv enforcement** — refuse startup if not inside a Python venv.
2. **Device detection** — detect CPU/CUDA and log capability.
3. **Banned-module scanning** — reject loading of joke/undocumented modules.
4. **YAML config loading** — load config.yaml with env-var overrides.

Usage at entry-point::

    from shared.utils.startup_guards import run_startup_checks, load_yaml_config
    startup_info = run_startup_checks()   # exits if venv missing
    cfg = load_yaml_config()
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict, List, Optional

logger = logging.getLogger("startup-guards")

# ---------------------------------------------------------------------------
# YAML config loader
# ---------------------------------------------------------------------------

_YAML_AVAILABLE = False
try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:
    pass


_DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "config.yaml"
)


def load_yaml_config(path: Optional[str] = None) -> Dict[str, Any]:
    """Load config.yaml and return merged dict.

    Environment variables override YAML values using a flat key convention:
        ``PERCEPTION_<SECTION>_<KEY>`` → ``config[section][key]``

    Example: ``PERCEPTION_CONFIDENCE_DETECTED_THRESHOLD=0.70``
    """
    cfg_path = path or _DEFAULT_CONFIG_PATH
    if not _YAML_AVAILABLE:
        logger.warning("PyYAML not installed — using built-in defaults only")
        return _builtin_defaults()

    try:
        with open(cfg_path, "r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh) or {}
    except FileNotFoundError:
        logger.warning("config.yaml not found at %s — using defaults", cfg_path)
        cfg = _builtin_defaults()
    except Exception as exc:
        logger.error("Failed to parse config.yaml: %s — using defaults", exc)
        cfg = _builtin_defaults()

    # Apply env-var overrides
    _apply_env_overrides(cfg)
    return cfg


def _builtin_defaults() -> Dict[str, Any]:
    """Fallback defaults when config.yaml is missing."""
    return {
        "confidence": {
            "detected_threshold": 0.60,
            "low_confidence_threshold": 0.30,
            "face_verify_threshold": 0.85,
            "confusion_pair_penalty": 0.20,
        },
        "latency": {
            "frame_budget_ms": 250,
            "tts_first_chunk_ms": 300,
            "tts_remote_timeout_ms": 2000,
            "partial_response_window": 10,
        },
        "robustness": {
            "motion_stability_frames": 3,
            "small_crop_min_area": 1024,
            "small_crop_penalty": 0.15,
            "edge_density_min": 0.05,
            "edge_density_penalty": 0.10,
            "misclass_alert_count": 3,
            "misclass_window_seconds": 30,
        },
        "tts": {
            "chunk_max_seconds": 2.0,
            "gap_max_ms": 300,
            "cache_enabled": True,
            "cache_max_entries": 500,
        },
        "privacy": {
            "face_recognition_opt_in": False,
            "memory_consent_required": True,
        },
        "banned_modules": ["antigravity"],
        "confusion_pairs": [
            ["bottle", "smartphone"],
            ["cup", "bowl"],
            ["remote", "phone"],
            ["mouse", "remote"],
        ],
    }


def _apply_env_overrides(cfg: Dict[str, Any]) -> None:
    """Apply PERCEPTION_<SECTION>_<KEY> env vars as overrides."""
    prefix = "PERCEPTION_"
    for key, value in os.environ.items():
        if not key.startswith(prefix):
            continue
        parts = key[len(prefix):].lower().split("_", 1)
        if len(parts) != 2:
            continue
        section, sub_key = parts
        if section in cfg and isinstance(cfg[section], dict):
            # Coerce type to match existing value
            existing = cfg[section].get(sub_key)
            if existing is not None:
                try:
                    if isinstance(existing, bool):
                        cfg[section][sub_key] = value.lower() in ("true", "1", "yes")
                    elif isinstance(existing, int):
                        cfg[section][sub_key] = int(value)
                    elif isinstance(existing, float):
                        cfg[section][sub_key] = float(value)
                    else:
                        cfg[section][sub_key] = value
                except (ValueError, TypeError):
                    pass
            else:
                cfg[section][sub_key] = value


# ---------------------------------------------------------------------------
# Venv enforcement
# ---------------------------------------------------------------------------

def enforce_venv() -> bool:
    """Check that we are running inside a Python virtual environment.

    Returns True if in a venv. If not, prints a fatal message and exits.
    """
    in_venv = (
        hasattr(sys, "real_prefix")  # virtualenv
        or (sys.prefix != sys.base_prefix)  # stdlib venv
    )
    if not in_venv:
        msg = (
            "FATAL: Server must run inside a Python virtual environment.\n"
            "       Create one with: python -m venv .venv\n"
            "       Activate it and retry.\n"
            "VENV: false"
        )
        print(msg, file=sys.stderr)
        logger.critical("Startup blocked — not inside a venv")
        sys.exit(1)

    logger.info("VENV: true")
    print("VENV: true")
    return True


# ---------------------------------------------------------------------------
# Device capability detection
# ---------------------------------------------------------------------------

def detect_device() -> str:
    """Detect compute device (cpu or cuda) and log it.

    Returns 'cuda' if a CUDA-capable GPU is available, else 'cpu'.
    """
    device = "cpu"
    try:
        import torch
        if torch.cuda.is_available():
            device = "cuda"
            gpu_name = torch.cuda.get_device_name(0)
            logger.info("DEVICE: cuda (%s)", gpu_name)
        else:
            logger.info("DEVICE: cpu (CUDA not available)")
    except ImportError:
        logger.info("DEVICE: cpu (torch not installed)")
    except Exception as exc:
        logger.warning("DEVICE: cpu (detection error: %s)", exc)

    print(f"DEVICE: {device}")
    return device


# ---------------------------------------------------------------------------
# Banned-module scanning
# ---------------------------------------------------------------------------

def scan_banned_modules(banned_list: Optional[List[str]] = None) -> List[str]:
    """Scan sys.modules for banned imports.

    Returns list of detected banned modules. Logs each as a security event.
    """
    if banned_list is None:
        banned_list = ["antigravity"]

    found: List[str] = []
    for mod_name in banned_list:
        if mod_name in sys.modules:
            logger.critical("security: banned-module %s", mod_name)
            print(f"security: banned-module {mod_name}", file=sys.stderr)
            found.append(mod_name)

    if not found:
        logger.info("Banned-module scan passed (%d modules checked)", len(banned_list))

    return found


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

_STARTUP_INFO: Dict[str, Any] = {}


def run_startup_checks(
    config_path: Optional[str] = None,
    skip_venv_check: bool = False,
) -> Dict[str, Any]:
    """Run all startup checks and return info dict.

    Parameters
    ----------
    config_path : str, optional
        Path to config.yaml.  Defaults to project root.
    skip_venv_check : bool
        If True, skip venv enforcement (for testing only).

    Returns
    -------
    dict with keys: ``device``, ``venv``, ``banned_modules_found``, ``config``.
    """
    global _STARTUP_INFO

    # 1. Load config first (needed for banned-module list)
    cfg = load_yaml_config(config_path)

    # 2. Venv enforcement
    venv_ok = True
    if not skip_venv_check:
        enforce_venv()
    else:
        venv_ok = hasattr(sys, "real_prefix") or (sys.prefix != sys.base_prefix)
        logger.info("VENV: %s (check skipped)", venv_ok)

    # 3. Device detection
    device = detect_device()

    # 4. Banned-module scan
    banned = cfg.get("banned_modules", ["antigravity"])
    found_banned = scan_banned_modules(banned)

    info = {
        "device": device,
        "venv": venv_ok,
        "banned_modules_found": found_banned,
        "config": cfg,
    }
    _STARTUP_INFO = info
    return info


def get_startup_info() -> Dict[str, Any]:
    """Return cached startup info (empty dict if not yet run)."""
    return _STARTUP_INFO
