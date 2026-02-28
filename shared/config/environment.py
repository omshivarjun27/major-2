"""Environment-aware configuration management for Voice & Vision Assistant.

Provides configuration loading with environment-specific overrides, validation,
and a config diff utility for comparing environments.

Task: T-105 - Environment Configuration Management

Usage::

    from shared.config.environment import (
        get_environment,
        load_config,
        validate_config,
        config_diff,
        log_effective_config,
    )
    
    # Load configuration for current environment
    config = load_config()
    
    # Load specific environment config
    staging_config = load_config(environment="staging")
    
    # Compare environments
    diff = config_diff("development", "production")
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

logger = logging.getLogger(__name__)


class Environment(Enum):
    """Valid environment names."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


# Default config directory
DEFAULT_CONFIG_DIR = "configs"

# Required configuration keys for validation
REQUIRED_KEYS = {
    "confidence",
    "latency",
    "features",
}

# Keys that must not be empty in production
PRODUCTION_REQUIRED = {
    "confidence.detected_threshold",
    "latency.frame_budget_ms",
    "privacy.memory_consent_required",
}

# Keys containing secrets (should be redacted in logs)
SECRET_KEYS = {
    "api_key",
    "api_secret",
    "password",
    "token",
    "secret",
    "credential",
}


@dataclass
class ConfigValidationResult:
    """Result of configuration validation.
    
    Attributes:
        valid: Whether configuration is valid
        errors: List of validation errors
        warnings: List of validation warnings
        missing_keys: Keys that are missing
        invalid_values: Keys with invalid values
    """
    valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    missing_keys: Set[str] = field(default_factory=set)
    invalid_values: Dict[str, str] = field(default_factory=dict)
    
    def add_error(self, message: str) -> None:
        """Add validation error."""
        self.errors.append(message)
        self.valid = False
    
    def add_warning(self, message: str) -> None:
        """Add validation warning."""
        self.warnings.append(message)


def get_environment() -> Environment:
    """Get current environment from ENVIRONMENT env var.
    
    Returns:
        Environment enum value (defaults to DEVELOPMENT)
    """
    env_str = os.environ.get("ENVIRONMENT", "development").lower()
    
    try:
        return Environment(env_str)
    except ValueError:
        logger.warning("Unknown environment '%s', defaulting to development", env_str)
        return Environment.DEVELOPMENT


def get_config_path(
    environment: Optional[Union[str, Environment]] = None,
    config_dir: str = DEFAULT_CONFIG_DIR,
) -> Path:
    """Get path to configuration file for environment.
    
    Args:
        environment: Environment name or enum
        config_dir: Configuration directory path
    
    Returns:
        Path to configuration YAML file
    """
    if environment is None:
        environment = get_environment()
    elif isinstance(environment, str):
        try:
            environment = Environment(environment.lower())
        except ValueError:
            environment = Environment.DEVELOPMENT
    
    return Path(config_dir) / f"{environment.value}.yaml"


def load_yaml(filepath: Path) -> Dict[str, Any]:
    """Load YAML file.
    
    Args:
        filepath: Path to YAML file
    
    Returns:
        Parsed YAML content as dictionary
    """
    if not YAML_AVAILABLE:
        logger.warning("PyYAML not available, returning empty config")
        return {}
    
    if not filepath.exists():
        logger.warning("Config file not found: %s", filepath)
        return {}
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error("Failed to load config %s: %s", filepath, e)
        return {}


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries.
    
    Args:
        base: Base dictionary
        override: Override dictionary (takes precedence)
    
    Returns:
        Merged dictionary
    """
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


def flatten_dict(
    d: Dict[str, Any],
    parent_key: str = "",
    sep: str = ".",
) -> Dict[str, Any]:
    """Flatten nested dictionary.
    
    Args:
        d: Dictionary to flatten
        parent_key: Parent key prefix
        sep: Key separator
    
    Returns:
        Flattened dictionary with dotted keys
    """
    items: List[Tuple[str, Any]] = []
    
    for key, value in d.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key
        
        if isinstance(value, dict):
            items.extend(flatten_dict(value, new_key, sep).items())
        else:
            items.append((new_key, value))
    
    return dict(items)


def load_config(
    environment: Optional[Union[str, Environment]] = None,
    config_dir: str = DEFAULT_CONFIG_DIR,
    include_base: bool = True,
) -> Dict[str, Any]:
    """Load configuration for specified environment.
    
    Configuration loading order:
    1. Base config (config.yaml)
    2. Environment-specific config (development.yaml, etc.)
    3. Environment variables (override everything)
    
    Args:
        environment: Environment to load (defaults to current)
        config_dir: Configuration directory path
        include_base: Whether to include base config.yaml
    
    Returns:
        Merged configuration dictionary
    """
    config: Dict[str, Any] = {}
    
    # Load base config
    if include_base:
        base_path = Path(config_dir) / "config.yaml"
        config = load_yaml(base_path)
    
    # Load environment-specific config
    env_path = get_config_path(environment, config_dir)
    env_config = load_yaml(env_path)
    
    # Merge configs
    config = deep_merge(config, env_config)
    
    # Add environment marker
    if environment is None:
        environment = get_environment()
    elif isinstance(environment, str):
        try:
            environment = Environment(environment.lower())
        except ValueError:
            environment = Environment.DEVELOPMENT
    
    config["_environment"] = environment.value
    config["_config_file"] = str(env_path)
    
    logger.info("Loaded configuration for environment: %s", environment.value)
    
    return config


def validate_config(
    config: Dict[str, Any],
    environment: Optional[Environment] = None,
) -> ConfigValidationResult:
    """Validate configuration.
    
    Args:
        config: Configuration dictionary to validate
        environment: Environment for context-specific validation
    
    Returns:
        ConfigValidationResult with validation status and messages
    """
    result = ConfigValidationResult()
    
    if environment is None:
        env_str = config.get("_environment", "development")
        try:
            environment = Environment(env_str)
        except ValueError:
            environment = Environment.DEVELOPMENT
    
    # Check required keys
    for key in REQUIRED_KEYS:
        if key not in config:
            result.missing_keys.add(key)
            result.add_error(f"Missing required key: {key}")
    
    # Production-specific validation
    if environment == Environment.PRODUCTION:
        flat = flatten_dict(config)
        
        for key in PRODUCTION_REQUIRED:
            if key not in flat or flat[key] is None:
                result.add_error(f"Production requires: {key}")
        
        # Validate specific production requirements
        if config.get("debug", False):
            result.add_warning("Debug mode should be disabled in production")
        
        if config.get("privacy", {}).get("memory_consent_required") is False:
            result.add_error("Memory consent must be required in production")
        
        log_level = config.get("log_level", "INFO")
        if log_level == "DEBUG":
            result.add_warning("Log level DEBUG not recommended for production")
    
    # Validate latency thresholds
    latency = config.get("latency", {})
    if latency:
        frame_budget = latency.get("frame_budget_ms", 0)
        if frame_budget <= 0:
            result.add_error("latency.frame_budget_ms must be positive")
        elif frame_budget > 1000:
            result.add_warning("latency.frame_budget_ms > 1000ms may cause poor UX")
    
    # Validate confidence thresholds
    confidence = config.get("confidence", {})
    if confidence:
        detected = confidence.get("detected_threshold", 0)
        low_conf = confidence.get("low_confidence_threshold", 0)
        
        if detected <= low_conf:
            result.add_error(
                "detected_threshold must be > low_confidence_threshold"
            )
        
        if detected < 0 or detected > 1:
            result.add_error("detected_threshold must be between 0 and 1")
    
    return result


def config_diff(
    env1: Union[str, Environment],
    env2: Union[str, Environment],
    config_dir: str = DEFAULT_CONFIG_DIR,
) -> Dict[str, Dict[str, Any]]:
    """Compare configurations between two environments.
    
    Args:
        env1: First environment
        env2: Second environment
        config_dir: Configuration directory
    
    Returns:
        Dictionary with keys:
        - only_in_env1: Keys only in first env
        - only_in_env2: Keys only in second env
        - different: Keys with different values
    """
    config1 = load_config(env1, config_dir)
    config2 = load_config(env2, config_dir)
    
    flat1 = flatten_dict(config1)
    flat2 = flatten_dict(config2)
    
    # Remove metadata keys
    for key in list(flat1.keys()):
        if key.startswith("_"):
            del flat1[key]
    for key in list(flat2.keys()):
        if key.startswith("_"):
            del flat2[key]
    
    keys1 = set(flat1.keys())
    keys2 = set(flat2.keys())
    
    only_in_1 = {k: flat1[k] for k in keys1 - keys2}
    only_in_2 = {k: flat2[k] for k in keys2 - keys1}
    
    different = {}
    for key in keys1 & keys2:
        if flat1[key] != flat2[key]:
            different[key] = {
                env1 if isinstance(env1, str) else env1.value: flat1[key],
                env2 if isinstance(env2, str) else env2.value: flat2[key],
            }
    
    return {
        "only_in_env1": only_in_1,
        "only_in_env2": only_in_2,
        "different": different,
    }


def scrub_secrets(config: Dict[str, Any]) -> Dict[str, Any]:
    """Scrub secret values from configuration.
    
    Args:
        config: Configuration dictionary
    
    Returns:
        Configuration with secrets redacted
    """
    flat = flatten_dict(config)
    scrubbed = {}
    
    for key, value in flat.items():
        key_lower = key.lower()
        is_secret = any(s in key_lower for s in SECRET_KEYS)
        
        if is_secret and value:
            scrubbed[key] = "[REDACTED]"
        else:
            scrubbed[key] = value
    
    return scrubbed


def log_effective_config(
    config: Dict[str, Any],
    scrub: bool = True,
) -> None:
    """Log effective configuration at startup.
    
    Args:
        config: Configuration dictionary
        scrub: Whether to redact secrets
    """
    if scrub:
        flat = scrub_secrets(config)
    else:
        flat = flatten_dict(config)
    
    # Log key configuration values
    env = config.get("_environment", "unknown")
    logger.info("=== Effective Configuration (%s) ===", env)
    
    # Log critical settings
    critical_keys = [
        "environment",
        "debug",
        "log_level",
        "confidence.detected_threshold",
        "latency.frame_budget_ms",
        "privacy.memory_consent_required",
    ]
    
    for key in critical_keys:
        if key in flat:
            logger.info("  %s = %s", key, flat[key])
    
    # Log feature flags
    features = config.get("features", {})
    if features:
        logger.info("  Feature flags:")
        for feature, enabled in features.items():
            logger.info("    %s = %s", feature, "enabled" if enabled else "disabled")
    
    logger.info("=== End Configuration ===")


def get_config_value(
    config: Dict[str, Any],
    key: str,
    default: Any = None,
) -> Any:
    """Get configuration value by dotted key path.
    
    Args:
        config: Configuration dictionary
        key: Dotted key path (e.g., "confidence.detected_threshold")
        default: Default value if key not found
    
    Returns:
        Configuration value or default
    """
    keys = key.split(".")
    value = config
    
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default
    
    return value
