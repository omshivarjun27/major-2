"""Documentation accuracy tests for the agent decomposition (T-049).

Verifies that every Python module in apps/realtime/ is documented in
AGENTS.md and that the documented module names match actual files.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REALTIME_DIR = ROOT / "apps" / "realtime"
AGENTS_MD = REALTIME_DIR / "AGENTS.md"

# Modules that MUST be documented (the decomposed agent files)
REQUIRED_MODULES = [
    "agent.py",
    "session_manager.py",
    "vision_controller.py",
    "voice_controller.py",
    "tool_router.py",
    "user_data.py",
    "prompts.py",
    "entrypoint.py",
]


class TestAgentModulesDocumented:
    """Verify AGENTS.md covers all apps/realtime/ Python modules."""

    def test_agents_md_exists(self):
        assert AGENTS_MD.exists(), f"Missing: {AGENTS_MD}"

    def test_each_module_mentioned_in_agents_md(self):
        content = AGENTS_MD.read_text(encoding="utf-8").lower()
        missing = []
        for mod in REQUIRED_MODULES:
            # Check for the module name (with or without .py)
            stem = mod.replace(".py", "")
            if stem not in content and mod not in content:
                missing.append(mod)
        assert not missing, (
            f"Module(s) not documented in AGENTS.md: {', '.join(missing)}"
        )

    def test_no_phantom_modules_in_agents_md(self):
        """AGENTS.md should not reference .py files that don't exist."""
        content = AGENTS_MD.read_text(encoding="utf-8")
        actual_files = {f.name for f in REALTIME_DIR.glob("*.py")}
        # Extract any .py references from the markdown
        import re

        mentioned = set(re.findall(r"`?(\w+\.py)`?", content))
        phantoms = mentioned - actual_files
        # Filter out common false positives (e.g., references to files in other dirs)
        phantoms = {p for p in phantoms if not p.startswith("test_")}
        assert not phantoms, (
            f"AGENTS.md references non-existent files: {', '.join(sorted(phantoms))}"
        )

    def test_decomposition_guide_exists(self):
        """Migration guide should exist at docs/architecture/."""
        guide = ROOT / "docs" / "architecture" / "agent-decomposition.md"
        assert guide.exists(), f"Missing migration guide: {guide}"

    def test_agents_md_not_outdated_god_file_reference(self):
        """AGENTS.md should not describe agent.py as a current god-file."""
        content = AGENTS_MD.read_text(encoding="utf-8").lower()
        # The old AGENTS.md said 'agent.py: The god-file (approximately 1,900 LOC)'
        # as a current description. Historical mentions ("decomposed from") are fine.
        assert "approximately 1,900 loc" not in content, (
            "AGENTS.md still describes agent.py as 'approximately 1,900 LOC' (outdated)"
        )
        assert "the god-file" not in content, (
            "AGENTS.md still uses 'the god-file' terminology for agent.py"
        )
