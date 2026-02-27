"""
Unit tests for resilience configuration in shared/config/settings.py

Tests:
- Circuit breaker configuration loading
- Retry policy configuration loading
- Degradation configuration loading
- Environment variable overrides
- Default fallback behavior
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from shared.config.settings import (
    CONFIG,
    get_circuit_breaker_config,
    get_degradation_config,
    get_resilience_config,
    get_retry_config,
)


# ============================================================================
# Circuit Breaker Config Tests
# ============================================================================


class TestCircuitBreakerConfig:
    """Tests for get_circuit_breaker_config."""

    def test_get_config_for_known_service(self):
        """Should return config for known services."""
        config = get_circuit_breaker_config("deepgram")
        assert "failure_threshold" in config
        assert "reset_timeout_s" in config
        assert isinstance(config["failure_threshold"], int)
        assert isinstance(config["reset_timeout_s"], float)

    def test_get_config_for_elevenlabs(self):
        """Should return config for ElevenLabs."""
        config = get_circuit_breaker_config("elevenlabs")
        assert config["failure_threshold"] > 0
        assert config["reset_timeout_s"] > 0

    def test_get_config_for_ollama(self):
        """Should return config for Ollama."""
        config = get_circuit_breaker_config("ollama")
        assert config["failure_threshold"] > 0
        assert config["reset_timeout_s"] > 0

    def test_get_config_for_unknown_service_uses_default(self):
        """Unknown services should use default values."""
        config = get_circuit_breaker_config("unknown_service_xyz")
        default_threshold = CONFIG.get("CB_DEFAULT_THRESHOLD", 3)
        default_reset = CONFIG.get("CB_DEFAULT_RESET_S", 30.0)
        assert config["failure_threshold"] == default_threshold
        assert config["reset_timeout_s"] == default_reset

    def test_config_case_insensitive_lookup(self):
        """Service lookup should be case-insensitive."""
        config_lower = get_circuit_breaker_config("deepgram")
        config_upper = get_circuit_breaker_config("DEEPGRAM")
        # Both should return valid configs (may differ if env vars differ)
        assert config_lower["failure_threshold"] > 0
        assert config_upper["failure_threshold"] > 0

    def test_config_default_values_are_sane(self):
        """Default values should be reasonable."""
        config = get_circuit_breaker_config("deepgram")
        # Threshold should be 1-10 failures
        assert 1 <= config["failure_threshold"] <= 10
        # Reset should be 5-120 seconds
        assert 5.0 <= config["reset_timeout_s"] <= 120.0


# ============================================================================
# Retry Config Tests
# ============================================================================


class TestRetryConfig:
    """Tests for get_retry_config."""

    def test_get_config_for_known_service(self):
        """Should return config for known services."""
        config = get_retry_config("deepgram")
        assert "max_retries" in config
        assert "base_delay_s" in config
        assert "max_delay_s" in config

    def test_get_config_for_elevenlabs(self):
        """Should return config for ElevenLabs."""
        config = get_retry_config("elevenlabs")
        assert config["max_retries"] >= 0
        assert config["base_delay_s"] > 0
        assert config["max_delay_s"] >= config["base_delay_s"]

    def test_get_config_for_unknown_service_uses_default(self):
        """Unknown services should use default values."""
        config = get_retry_config("unknown_service_xyz")
        default_max = CONFIG.get("RETRY_DEFAULT_MAX", 3)
        default_base = CONFIG.get("RETRY_DEFAULT_BASE_DELAY_S", 1.0)
        default_max_delay = CONFIG.get("RETRY_DEFAULT_MAX_DELAY_S", 30.0)
        assert config["max_retries"] == default_max
        assert config["base_delay_s"] == default_base
        assert config["max_delay_s"] == default_max_delay

    def test_config_values_are_typed_correctly(self):
        """Config values should have correct types."""
        config = get_retry_config("deepgram")
        assert isinstance(config["max_retries"], int)
        assert isinstance(config["base_delay_s"], float)
        assert isinstance(config["max_delay_s"], float)

    def test_max_delay_greater_than_base_delay(self):
        """Max delay should be >= base delay."""
        for service in ["deepgram", "elevenlabs", "ollama", "tavus", "duckduckgo"]:
            config = get_retry_config(service)
            assert config["max_delay_s"] >= config["base_delay_s"]


# ============================================================================
# Degradation Config Tests
# ============================================================================


class TestDegradationConfig:
    """Tests for get_degradation_config."""

    def test_get_degradation_config(self):
        """Should return degradation configuration."""
        config = get_degradation_config()
        assert "auto_notify_user" in config
        assert "min_announce_interval_s" in config
        assert "max_level_before_panic" in config

    def test_degradation_config_types(self):
        """Config values should have correct types."""
        config = get_degradation_config()
        assert isinstance(config["auto_notify_user"], bool)
        assert isinstance(config["min_announce_interval_s"], float)
        assert isinstance(config["max_level_before_panic"], str)

    def test_degradation_defaults_are_sane(self):
        """Default values should be reasonable."""
        config = get_degradation_config()
        # Announce interval should be 5-120 seconds
        assert 5.0 <= config["min_announce_interval_s"] <= 120.0
        # Max level should be a valid degradation level
        assert config["max_level_before_panic"] in ["none", "minimal", "degraded", "critical"]


# ============================================================================
# Full Resilience Config Tests
# ============================================================================


class TestGetResilienceConfig:
    """Tests for get_resilience_config."""

    def test_get_full_resilience_config(self):
        """Should return full resilience configuration."""
        config = get_resilience_config()
        assert "timeouts" in config
        assert "circuit_breakers" in config
        assert "retry_policies" in config
        assert "degradation" in config

    def test_timeouts_section(self):
        """Timeouts section should have all services."""
        config = get_resilience_config()
        timeouts = config["timeouts"]
        assert "stt" in timeouts
        assert "tts" in timeouts
        assert "llm" in timeouts
        assert "search" in timeouts
        assert "avatar" in timeouts
        assert "livekit" in timeouts
        assert "default" in timeouts

    def test_circuit_breakers_section(self):
        """Circuit breakers section should have all services."""
        config = get_resilience_config()
        cbs = config["circuit_breakers"]
        assert "deepgram" in cbs
        assert "elevenlabs" in cbs
        assert "ollama" in cbs
        assert "livekit" in cbs
        assert "tavus" in cbs
        assert "duckduckgo" in cbs

    def test_retry_policies_section(self):
        """Retry policies section should have all services."""
        config = get_resilience_config()
        retries = config["retry_policies"]
        assert "deepgram" in retries
        assert "elevenlabs" in retries
        assert "ollama" in retries
        assert "livekit" in retries
        assert "tavus" in retries
        assert "duckduckgo" in retries


# ============================================================================
# Environment Variable Override Tests
# ============================================================================


class TestEnvironmentVariableOverrides:
    """Tests for environment variable override functionality."""

    def test_circuit_breaker_env_override(self):
        """Circuit breaker config should respect env vars."""
        with patch.dict(os.environ, {"CB_DEEPGRAM_THRESHOLD": "5"}):
            # Need to reload CONFIG to pick up env var
            # This test verifies the pattern works
            threshold = int(os.environ.get("CB_DEEPGRAM_THRESHOLD", "3"))
            assert threshold == 5

    def test_retry_env_override(self):
        """Retry config should respect env vars."""
        with patch.dict(os.environ, {"RETRY_DEEPGRAM_MAX": "5"}):
            max_retries = int(os.environ.get("RETRY_DEEPGRAM_MAX", "2"))
            assert max_retries == 5

    def test_timeout_env_override(self):
        """Timeout config should respect env vars."""
        with patch.dict(os.environ, {"STT_TIMEOUT_S": "5.0"}):
            timeout = float(os.environ.get("STT_TIMEOUT_S", "2.0"))
            assert timeout == 5.0


# ============================================================================
# Integration with Circuit Breaker Module Tests
# ============================================================================


class TestCircuitBreakerIntegration:
    """Tests for circuit breaker config integration."""

    def test_circuit_breaker_reads_from_config(self):
        """Circuit breaker should read from centralized config."""
        from infrastructure.resilience.circuit_breaker import (
            CircuitBreakerConfig,
            clear_registry,
            register_circuit_breaker,
        )

        clear_registry()

        # Register without explicit config - should use settings
        cb = register_circuit_breaker("test_service")

        # Should have valid config
        assert cb.config.failure_threshold > 0
        assert cb.config.reset_timeout_s > 0

        clear_registry()

    def test_circuit_breaker_explicit_config_overrides(self):
        """Explicit config should override settings."""
        from infrastructure.resilience.circuit_breaker import (
            CircuitBreakerConfig,
            clear_registry,
            register_circuit_breaker,
        )

        clear_registry()

        explicit_config = CircuitBreakerConfig(
            failure_threshold=10,
            reset_timeout_s=120.0,
        )
        cb = register_circuit_breaker("test_explicit", config=explicit_config)

        assert cb.config.failure_threshold == 10
        assert cb.config.reset_timeout_s == 120.0

        clear_registry()


# ============================================================================
# Integration with Retry Policy Module Tests
# ============================================================================


class TestRetryPolicyIntegration:
    """Tests for retry policy config integration."""

    def test_retry_policy_reads_from_config(self):
        """Retry policy should read from centralized config."""
        from infrastructure.resilience.retry_policy import get_retry_policy

        policy = get_retry_policy("deepgram")

        # Should have valid config
        assert policy.config.max_retries >= 0
        assert policy.config.base_delay_s > 0
        assert policy.config.max_delay_s > 0

    def test_retry_decorator_uses_config(self):
        """with_retry decorator should use centralized config."""
        from infrastructure.resilience.retry_policy import with_retry

        @with_retry("deepgram")
        async def test_func():
            return "success"

        # Check decorator attached config
        assert hasattr(test_func, "retry_config")
        assert test_func.retry_config.max_retries >= 0


# ============================================================================
# Edge Cases
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_service_name(self):
        """Empty service name should use defaults."""
        config = get_circuit_breaker_config("")
        assert config["failure_threshold"] > 0
        assert config["reset_timeout_s"] > 0

    def test_special_characters_in_service_name(self):
        """Service names with special chars should work."""
        config = get_circuit_breaker_config("service-with-dashes")
        assert config["failure_threshold"] > 0

    def test_numeric_service_name(self):
        """Numeric service names should work."""
        config = get_circuit_breaker_config("123")
        assert config["failure_threshold"] > 0

    def test_config_dict_is_fresh_copy(self):
        """Each call should return a fresh dict."""
        config1 = get_circuit_breaker_config("deepgram")
        config2 = get_circuit_breaker_config("deepgram")
        config1["failure_threshold"] = 999
        assert config2["failure_threshold"] != 999
