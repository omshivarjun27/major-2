"""Static Dockerfile security analysis (no Docker daemon required)."""
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class TestDockerHardening:
    def test_root_dockerfile_has_user_directive(self):
        content = (PROJECT_ROOT / "Dockerfile").read_text()
        assert "USER appuser" in content, "Root Dockerfile must have USER directive"

    def test_canonical_dockerfile_has_user_directive(self):
        content = (PROJECT_ROOT / "deployments" / "docker" / "Dockerfile").read_text()
        assert "USER appuser" in content, "Canonical Dockerfile must have USER directive"

    def test_root_dockerfile_no_copy_env(self):
        content = (PROJECT_ROOT / "Dockerfile").read_text()
        # COPY . . is fine because .dockerignore excludes .env
        # But explicit COPY .env should not exist
        lines = content.strip().splitlines()
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("COPY") and ".env" in stripped and stripped != "COPY . .":
                pytest.fail(f"Dockerfile should not explicitly COPY .env: {stripped}")

    def test_dockerignore_excludes_env(self):
        content = (PROJECT_ROOT / ".dockerignore").read_text()
        assert ".env" in content, ".dockerignore must exclude .env"

    def test_user_directive_before_cmd(self):
        """USER must appear before CMD in both Dockerfiles."""
        for path in [PROJECT_ROOT / "Dockerfile", PROJECT_ROOT / "deployments" / "docker" / "Dockerfile"]:
            content = path.read_text()
            lines = content.strip().splitlines()
            user_line = None
            cmd_line = None
            for i, line in enumerate(lines):
                if line.strip().startswith("USER "):
                    user_line = i
                if line.strip().startswith("CMD "):
                    cmd_line = i
            assert user_line is not None, f"{path.name}: missing USER directive"
            assert cmd_line is not None, f"{path.name}: missing CMD directive"
            assert user_line < cmd_line, f"{path.name}: USER must come before CMD"

    def test_env_example_exists(self):
        path = PROJECT_ROOT / ".env.example"
        assert path.exists(), ".env.example template must exist"

    def test_env_example_has_all_secret_keys(self):
        content = (PROJECT_ROOT / ".env.example").read_text()
        required_keys = [
            "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "DEEPGRAM_API_KEY",
            "OLLAMA_API_KEY", "ELEVEN_API_KEY", "OLLAMA_VL_API_KEY", "TAVUS_API_KEY",
        ]
        for key in required_keys:
            assert key in content, f".env.example missing {key}"

    def test_env_example_has_no_real_keys(self):
        content = (PROJECT_ROOT / ".env.example").read_text()
        import re
        # Real keys are 20+ char alphanumeric strings (not placeholder text)
        for line in content.splitlines():
            if "=" in line and not line.strip().startswith("#"):
                key, _, value = line.partition("=")
                # Placeholder values like "your_xxx" or "true"/"false" are OK
                if re.match(r'^[a-zA-Z0-9]{20,}$', value.strip()):
                    pytest.fail(f".env.example may contain a real key: {key.strip()}")

    def test_compose_files_use_env_file(self):
        for compose_path in [
            PROJECT_ROOT / "docker-compose.test.yml",
            PROJECT_ROOT / "deployments" / "compose" / "docker-compose.test.yml",
        ]:
            if compose_path.exists():
                content = compose_path.read_text()
                assert "env_file" in content, f"{compose_path.name} should use env_file directive"
