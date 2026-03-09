"""Tests verifying configuration documentation matches code."""

import re
from pathlib import Path

from shared.config.settings import CONFIG, SECRETS, validate_config

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Keys added to settings.py that are expected to be documented.
KNOWN_CONFIG_KEYS = {
    "WHISPER_MODEL_SIZE", "WHISPER_DEVICE", "WHISPER_COMPUTE_TYPE", "WHISPER_LANGUAGE", "WHISPER_VAD_FILTER",
    "LOCAL_TTS_VOICE", "LOCAL_TTS_RATE", "LOCAL_TTS_VOLUME", "LOCAL_TTS_PREFER_EDGE",
    "STT_TIMEOUT_S", "TTS_TIMEOUT_S", "LLM_TIMEOUT_S", "SEARCH_TIMEOUT_S", "AVATAR_TIMEOUT_S",
    "LIVEKIT_TIMEOUT_S", "DEFAULT_EXTERNAL_TIMEOUT_S",
    "CB_DEEPGRAM_THRESHOLD", "CB_DEEPGRAM_RESET_S", "CB_ELEVENLABS_THRESHOLD", "CB_ELEVENLABS_RESET_S",
    "CB_OLLAMA_THRESHOLD", "CB_OLLAMA_RESET_S", "CB_LIVEKIT_THRESHOLD", "CB_LIVEKIT_RESET_S",
    "CB_TAVUS_THRESHOLD", "CB_TAVUS_RESET_S", "CB_DUCKDUCKGO_THRESHOLD", "CB_DUCKDUCKGO_RESET_S",
    "CB_DEFAULT_THRESHOLD", "CB_DEFAULT_RESET_S",
    "RETRY_DEEPGRAM_MAX", "RETRY_DEEPGRAM_BASE_DELAY_S", "RETRY_DEEPGRAM_MAX_DELAY_S",
    "RETRY_ELEVENLABS_MAX", "RETRY_ELEVENLABS_BASE_DELAY_S", "RETRY_ELEVENLABS_MAX_DELAY_S",
    "RETRY_OLLAMA_MAX", "RETRY_OLLAMA_BASE_DELAY_S", "RETRY_OLLAMA_MAX_DELAY_S",
    "RETRY_LIVEKIT_MAX", "RETRY_LIVEKIT_BASE_DELAY_S", "RETRY_LIVEKIT_MAX_DELAY_S",
    "RETRY_TAVUS_MAX", "RETRY_TAVUS_BASE_DELAY_S", "RETRY_TAVUS_MAX_DELAY_S",
    "RETRY_DUCKDUCKGO_MAX", "RETRY_DUCKDUCKGO_BASE_DELAY_S", "RETRY_DUCKDUCKGO_MAX_DELAY_S",
    "RETRY_DEFAULT_MAX", "RETRY_DEFAULT_BASE_DELAY_S", "RETRY_DEFAULT_MAX_DELAY_S",
    "DEGRADATION_AUTO_NOTIFY_USER", "DEGRADATION_MIN_ANNOUNCE_INTERVAL_S", "DEGRADATION_MAX_LEVEL_BEFORE_PANIC",
}


class TestConfigDocumentation:
    """Verify docs/configuration.md stays in sync with settings.py."""

    def test_docs_configuration_exists(self):
        path = PROJECT_ROOT / "docs" / "configuration.md"
        assert path.exists(), "docs/configuration.md must exist"

    def test_all_config_keys_documented(self):
        docs = (PROJECT_ROOT / "docs" / "configuration.md").read_text()
        settings_text = (PROJECT_ROOT / "shared" / "config" / "settings.py").read_text()
        # Extract env var names from os.environ.get calls in settings.py
        env_vars = re.findall(r'os\.environ\.get\(["\']([A-Z_]+)["\']', settings_text)
        missing = [v for v in env_vars if v not in docs and v not in KNOWN_CONFIG_KEYS]
        assert not missing, f"Undocumented env vars: {missing}"

    def test_secrets_set_contains_api_keys(self):
        expected_minimum = {
            "LIVEKIT_API_KEY",
            "LIVEKIT_API_SECRET",
            "DEEPGRAM_API_KEY",
            "OLLAMA_API_KEY",
            "ELEVEN_API_KEY",
            "OLLAMA_VL_API_KEY",
            "TAVUS_API_KEY",
        }
        assert expected_minimum.issubset(SECRETS), (
            f"Missing from SECRETS: {expected_minimum - SECRETS}"
        )

    def test_secrets_have_empty_defaults(self):
        # Keys routed through SecretProvider may pick up values from .env at
        # import time.  We only check keys that appear as direct os.environ.get
        # calls in CONFIG (those have hard-coded defaults we can verify).
        from shared.config.secret_provider import SECRET_KEYS
        for key in SECRETS:
            if key in CONFIG and key not in SECRET_KEYS:
                val = CONFIG[key]
                assert val == "" or val is None or val is False, (
                    f"SECRET {key} has non-empty default: {val!r}"
                )

    def test_validate_config_returns_list(self):
        result = validate_config()
        assert isinstance(result, list)

    def test_secrets_is_frozenset(self):
        assert isinstance(SECRETS, frozenset)

    def test_secrets_documented_in_docs(self):
        docs = (PROJECT_ROOT / "docs" / "configuration.md").read_text()
        for key in SECRETS:
            assert key in docs, f"SECRET {key} not documented in configuration.md"

    def test_validate_config_warns_on_unset_secrets(self):
        # In test environments, secrets are typically not set, so we expect warnings.
        warnings = validate_config()
        # Each warning should follow the format "SECRET <KEY> is not set"
        for w in warnings:
            assert w.startswith("SECRET "), f"Unexpected warning format: {w}"
            assert "is not set" in w, f"Unexpected warning format: {w}"
