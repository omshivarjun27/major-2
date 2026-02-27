"""Tests for the async audit sweep script (T-046).

Validates the audit tool finds blocking patterns and correctly classifies
hot-path vs startup-only vs non-hot-path findings.
"""

from pathlib import Path
from unittest.mock import patch

from scripts.async_audit import (
    AuditReport,
    Finding,
    HOT_PATH_DIRS,
    STARTUP_ONLY_FILES,
    _is_hot_path,
    _should_skip,
    run_audit,
    scan_file,
)


class TestIsHotPath:
    """Test hot-path classification logic."""

    def test_core_vision_spatial_is_hot(self):
        assert _is_hot_path("core/vision/spatial.py") is True

    def test_core_vqa_is_hot(self):
        assert _is_hot_path("core/vqa/perception.py") is True

    def test_core_memory_is_hot(self):
        assert _is_hot_path("core/memory/indexer.py") is True

    def test_application_frame_processing_is_hot(self):
        assert _is_hot_path("application/frame_processing/freshness.py") is True

    def test_application_pipelines_is_hot(self):
        assert _is_hot_path("application/pipelines/worker.py") is True

    def test_infrastructure_is_not_hot(self):
        assert _is_hot_path("infrastructure/llm/handler.py") is False

    def test_model_download_is_startup_only(self):
        assert _is_hot_path("core/vision/model_download.py") is False

    def test_init_is_startup_only(self):
        assert _is_hot_path("core/vision/__init__.py") is False

    def test_backslash_normalization(self):
        assert _is_hot_path("core\\vision\\spatial.py") is True

    def test_core_ocr_is_not_hot(self):
        assert _is_hot_path("core/ocr/engine.py") is False


class TestShouldSkip:
    """Test file skip logic."""

    def test_skips_pycache(self):
        assert _should_skip("core/__pycache__/foo.py") is True

    def test_skips_test_files(self):
        assert _should_skip("tests/unit/test_foo.py") is True

    def test_skips_conftest(self):
        assert _should_skip("tests/conftest.py") is True

    def test_does_not_skip_normal_file(self):
        assert _should_skip("core/vision/spatial.py") is False


class TestScanFile:
    """Test single-file scanning."""

    def test_detects_requests_get(self, tmp_path):
        f = tmp_path / "code.py"
        f.write_text("import requests\nresult = requests.get(url)\n", encoding="utf-8")
        findings = scan_file(f, tmp_path)
        names = [fi.pattern_name for fi in findings]
        assert "import_requests" in names
        assert "requests_call" in names

    def test_detects_urllib_urlopen(self, tmp_path):
        f = tmp_path / "dl.py"
        f.write_text("import urllib.request\nurllib.request.urlopen(url)\n", encoding="utf-8")
        findings = scan_file(f, tmp_path)
        assert any(fi.pattern_name == "urllib_urlopen" for fi in findings)

    def test_detects_time_sleep(self, tmp_path):
        f = tmp_path / "wait.py"
        f.write_text("import time\ntime.sleep(1)\n", encoding="utf-8")
        findings = scan_file(f, tmp_path)
        assert any(fi.pattern_name == "time_sleep" for fi in findings)

    def test_detects_subprocess_run(self, tmp_path):
        f = tmp_path / "cmd.py"
        f.write_text("import subprocess\nsubprocess.run(['ls'])\n", encoding="utf-8")
        findings = scan_file(f, tmp_path)
        assert any(fi.pattern_name == "subprocess_sync" for fi in findings)

    def test_ignores_comments(self, tmp_path):
        f = tmp_path / "safe.py"
        f.write_text("# requests.get(url)\n", encoding="utf-8")
        findings = scan_file(f, tmp_path)
        assert len(findings) == 0

    def test_clean_file_returns_empty(self, tmp_path):
        f = tmp_path / "clean.py"
        f.write_text("import asyncio\nasync def foo(): pass\n", encoding="utf-8")
        findings = scan_file(f, tmp_path)
        assert len(findings) == 0

    def test_skips_test_files(self, tmp_path):
        f = tmp_path / "test_something.py"
        f.write_text("import requests\nrequests.get(url)\n", encoding="utf-8")
        findings = scan_file(f, tmp_path)
        assert len(findings) == 0


class TestFinding:
    """Test Finding dataclass behavior."""

    def test_hot_path_severity_is_error(self):
        f = Finding(file="core/vision/spatial.py", line_no=10, pattern_name="time_sleep",
                    line_text="time.sleep(1)", hot_path=True)
        assert f.severity == "ERROR"

    def test_non_hot_path_severity_is_warning(self):
        f = Finding(file="infrastructure/llm/handler.py", line_no=10, pattern_name="time_sleep",
                    line_text="time.sleep(1)", hot_path=False)
        assert f.severity == "WARNING"


class TestAuditReport:
    """Test AuditReport summary and properties."""

    def test_clean_when_no_hot_path_violations(self):
        report = AuditReport(findings=[], files_scanned=50, hot_path_violations=0, warnings=1)
        assert report.clean is True

    def test_not_clean_when_hot_path_violations(self):
        report = AuditReport(findings=[], files_scanned=50, hot_path_violations=1)
        assert report.clean is False

    def test_summary_contains_pass(self):
        report = AuditReport(files_scanned=10, hot_path_violations=0)
        assert "PASS" in report.summary()

    def test_summary_contains_fail(self):
        report = AuditReport(files_scanned=10, hot_path_violations=1,
                             findings=[Finding("f.py", 1, "test", "x", True)])
        assert "FAIL" in report.summary()

    def test_summary_includes_finding_details(self):
        f = Finding("core/vision/spatial.py", 42, "time_sleep", "  time.sleep(1)", True)
        report = AuditReport(findings=[f], files_scanned=1, hot_path_violations=1)
        s = report.summary()
        assert "core/vision/spatial.py:42" in s
        assert "time_sleep" in s


class TestRunAudit:
    """Integration test for the full audit on the real project."""

    def test_audit_passes_on_project(self):
        """The project should have zero hot-path violations after T-046."""
        report = run_audit()
        assert report.files_scanned > 50, f"Expected >50 files, got {report.files_scanned}"
        assert report.hot_path_violations == 0, (
            f"Hot-path violations found:\n"
            + "\n".join(f"  {f.file}:{f.line_no} ({f.pattern_name})" for f in report.findings if f.hot_path)
        )

    def test_audit_finds_model_download_warning(self):
        """model_download.py should be flagged as a non-hot-path warning."""
        report = run_audit()
        model_dl = [f for f in report.findings if "model_download" in f.file]
        assert len(model_dl) >= 1
        assert all(f.severity == "WARNING" for f in model_dl)

    def test_hot_path_dirs_are_defined(self):
        assert len(HOT_PATH_DIRS) >= 4

    def test_startup_only_files_defined(self):
        assert "model_download.py" in STARTUP_ONLY_FILES


class TestConstants:
    """Verify audit constants are sensible."""

    def test_hot_path_dirs_nonempty(self):
        assert len(HOT_PATH_DIRS) > 0

    def test_startup_only_contains_model_download(self):
        assert "model_download.py" in STARTUP_ONLY_FILES
