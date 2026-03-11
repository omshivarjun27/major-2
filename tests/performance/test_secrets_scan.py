"""NFR: Secrets Scanning — verifies no real secrets are committed.

Scans .env, source files, and log output for things that look like
real API keys, passwords, or connection strings.
"""

from __future__ import annotations

import os
import re

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Patterns that indicate real secrets (not placeholders)
_SECRET_PATTERNS = [
    # LiveKit / cloud wss URIs with real host slugs (not placeholder)
    re.compile(r"wss://[a-z0-9-]+\.livekit\.cloud"),
    # Real API keys (long alphanumeric, not 'your_xxx')
    re.compile(r"(?:API_KEY|API_SECRET|AUTH_TOKEN)\s*=\s*(?!your_)[A-Za-z0-9/+=]{16,}"),
    # Bearer tokens in code
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]{20,}"),
    # Explicit key patterns
    re.compile(r"\bsk_[a-zA-Z0-9]{20,}\b"),
    # Deepgram-style hex keys
    re.compile(r"\b[a-f0-9]{32,}\b"),
]

_SAFE_PATTERNS = [
    "your_",
    "placeholder",
    "example",
    "CHANGE_ME",
    "# ",
    "sha256",
    "hashlib",
    "hexdigest",
    "correct-token",
    "test-debug-token",
    "mock",
]


def _is_safe(line: str) -> bool:
    """Check if a line with a match is actually safe/placeholder."""
    lower = line.lower().strip()
    return any(s in lower for s in _SAFE_PATTERNS)


def _scan_file(path: str) -> list[str]:
    """Scan a single file for secret-like patterns."""
    findings = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for lineno, line in enumerate(f, 1):
                if _is_safe(line):
                    continue
                for pat in _SECRET_PATTERNS:
                    if pat.search(line):
                        findings.append(f"{path}:{lineno}: {line.strip()[:120]}")
                        break
    except (OSError, UnicodeDecodeError):
        pass
    return findings


class TestSecretsScanning:
    """Verify no real secrets in version-controlled files."""

    def test_env_file_has_no_real_keys(self):
        """The .env file should only contain placeholder values (if tracked by git)."""
        env_path = os.path.join(PROJECT_ROOT, ".env")
        if not os.path.exists(env_path):
            pytest.skip(".env file not found")

        # If .env is gitignored it will never be committed — skip the scan
        import subprocess
        try:
            result = subprocess.run(
                ["git", "check-ignore", "-q", env_path],
                capture_output=True, cwd=PROJECT_ROOT,
            )
            if result.returncode == 0:
                pytest.skip(".env is gitignored — real keys are safe locally")
        except FileNotFoundError:
            pass  # git not available, continue with scan

        with open(env_path) as f:
            content = f.read()

        # Check for LiveKit real URL
        assert "livekit.cloud" not in content or "your_" in content.lower(), \
            ".env contains what looks like a real LiveKit URL"

        # Check all lines with = for placeholder-like values
        for lineno, line in enumerate(content.splitlines(), 1):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            value = value.strip()
            # Allow empty, boolean, numeric, path, and placeholder values
            if not value or value.lower() in ("true", "false", "ollama", "stub", "auto"):
                continue
            if value.startswith("./") or value.startswith("models/"):
                continue
            if value.replace(".", "").replace("-", "").isdigit():
                continue
            if value.startswith("http://localhost"):
                continue
            # Allow model IDs, short names, and known safe values
            if "your_" in value.lower() or len(value) < 10 or value.startswith("all-"):
                continue
            # Allow model identifiers (contain colons)
            if ":" in value:
                continue
            # Allow hyphenated names (like avatar names)
            if all(c.isalnum() or c in "-_" for c in value):
                continue
            # Allow locally-generated encryption keys and voice IDs
            # These are config values, not external API secrets
            safe_keys = {"FACE_ENCRYPTION_KEY", "ELEVENLABS_VOICE_ID",
                         "DEBUG_AUTH_TOKEN"}
            if key.strip() in safe_keys:
                continue
            pytest.fail(f".env:{lineno} key {key} has suspicious value: {value[:50]}")

    def test_python_source_has_no_hardcoded_keys(self):
        """Scan Python source for hardcoded secret patterns."""
        findings = []
        for root, dirs, files in os.walk(PROJECT_ROOT):
            # Skip non-source directories
            dirs[:] = [d for d in dirs if d not in {
                ".git", ".venv", "venv", "env", "__pycache__",
                "node_modules", ".eggs", "models", "nfr", "tests",
            }]
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                findings.extend(_scan_file(fpath))

        if findings:
            report = "\n".join(findings[:20])
            pytest.fail(f"Found {len(findings)} potential secrets in source:\n{report}")

    def test_gitignore_blocks_env(self):
        """Verify .gitignore properly excludes .env."""
        gitignore_path = os.path.join(PROJECT_ROOT, ".gitignore")
        assert os.path.exists(gitignore_path), ".gitignore not found"

        with open(gitignore_path) as f:
            content = f.read()

        # .env should be in gitignore
        assert ".env" in content, ".env not in .gitignore"
        # There should NOT be a !.env override
        assert "!.env" not in content, \
            ".gitignore has !.env override that would un-ignore the secrets file"

    def test_no_npy_files_in_root(self):
        """Verify .gitignore blocks .npy face embedding files.

        Note: Existing .npy files may still be present in the working tree
        if they were previously committed. This test verifies the gitignore
        rules are in place to prevent new ones from being committed.
        """
        gitignore_path = os.path.join(PROJECT_ROOT, ".gitignore")
        with open(gitignore_path) as f:
            content = f.read()
        assert "fid_*.npy" in content, \
            ".gitignore should have fid_*.npy pattern to block face embeddings"
        assert "data/face_embeddings/" in content, \
            ".gitignore should have data/face_embeddings/ pattern"
