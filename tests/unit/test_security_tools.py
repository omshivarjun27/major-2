"""
Tests for security scanning tools: SAST, DAST, dependency scan, and security audit.

Covers argument parsing, config loading/validation, report generation,
pass/fail exit code behavior, and individual audit checks with mocked filesystems.
"""
from __future__ import annotations

import json
import os
import textwrap
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

# ── SAST imports ──────────────────────────────────────────────────────
from scripts.run_sast import (
    build_arg_parser as sast_build_parser,
    classify_findings,
    filter_baseline,
    format_text_report,
    load_baseline,
    main as sast_main,
    should_block as sast_should_block,
)

# ── DAST imports ──────────────────────────────────────────────────────
from scripts.run_dast import (
    ZAP_CHECK_CATEGORIES,
    build_arg_parser as dast_build_parser,
    build_zap_config,
    generate_mock_html,
    generate_mock_report,
    main as dast_main,
    validate_config,
)

# ── Dependency scan imports ───────────────────────────────────────────
from scripts.run_dep_scan import (
    build_arg_parser as dep_build_parser,
    classify_vulnerabilities,
    generate_sbom,
    main as dep_main,
    parse_requirements,
    should_block as dep_should_block,
)

# ── Security audit imports ────────────────────────────────────────────
from scripts.security_audit import (
    AuditCheck,
    build_arg_parser as audit_build_parser,
    check_cors_configured,
    check_docker_nonroot,
    check_encryption_present,
    check_https_enforced,
    check_input_validation,
    check_no_plaintext_keys,
    check_pii_scrubbing,
    check_rate_limiting,
    generate_report,
    main as audit_main,
    run_all_checks,
)


# =====================================================================
# Fixtures
# =====================================================================


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a minimal project structure for audit checks."""
    # Create shared/logging with PIIScrubFilter
    log_dir = tmp_path / "shared" / "logging"
    log_dir.mkdir(parents=True)
    (log_dir / "rotation.py").write_text(
        textwrap.dedent("""\
        from shared.logging.logging_config import PIIScrubFilter
        handler = logging.StreamHandler()
        handler.addFilter(PIIScrubFilter(enabled=True))
        """),
        encoding="utf-8",
    )
    (log_dir / "logging_config.py").write_text(
        textwrap.dedent("""\
        import logging
        class PIIScrubFilter(logging.Filter):
            def __init__(self, enabled=True):
                self.enabled = enabled
        """),
        encoding="utf-8",
    )

    # Create encryption utility
    utils_dir = tmp_path / "shared" / "utils"
    utils_dir.mkdir(parents=True)
    (utils_dir / "encryption.py").write_text(
        "from cryptography.fernet import Fernet\ndef encrypt(data): pass\n",
        encoding="utf-8",
    )

    # Create a safe Python file (no secrets)
    core_dir = tmp_path / "core"
    core_dir.mkdir()
    (core_dir / "engine.py").write_text(
        "import os\nAPI_KEY = os.environ.get('API_KEY', '')\n",
        encoding="utf-8",
    )

    # Create Dockerfile with non-root user
    deploy_dir = tmp_path / "deployments" / "docker"
    deploy_dir.mkdir(parents=True)
    (deploy_dir / "Dockerfile").write_text(
        "FROM python:3.11-slim\nRUN useradd -r appuser\nUSER appuser\n",
        encoding="utf-8",
    )

    # Create API server with validation
    api_dir = tmp_path / "apps" / "api"
    api_dir.mkdir(parents=True)
    (api_dir / "server.py").write_text(
        textwrap.dedent("""\
        from fastapi import FastAPI, Query, Depends, HTTPException
        from pydantic import BaseModel
        app = FastAPI()
        """),
        encoding="utf-8",
    )

    # Requirements file
    (tmp_path / "requirements.txt").write_text(
        "fastapi>=0.109.0\nuvicorn>=0.27.0\nhttpx>=0.26.0\n",
        encoding="utf-8",
    )

    return tmp_path


@pytest.fixture
def tmp_reports(tmp_path: Path) -> Path:
    """Return a temp path for report output."""
    reports = tmp_path / "reports"
    reports.mkdir()
    return reports


# =====================================================================
# SAST Tests
# =====================================================================


class TestSASTArgParser:
    """Test SAST script argument parsing."""

    def test_default_args(self) -> None:
        parser = sast_build_parser()
        args = parser.parse_args([])
        assert args.config == ".bandit"
        assert args.baseline == ".bandit-baseline.json"
        assert args.targets is None
        assert args.output is None
        assert args.format == "text"

    def test_custom_args(self) -> None:
        parser = sast_build_parser()
        args = parser.parse_args(["--config", "custom.bandit", "--format", "json"])
        assert args.config == "custom.bandit"
        assert args.format == "json"

    def test_targets_arg(self) -> None:
        parser = sast_build_parser()
        args = parser.parse_args(["--targets", "core", "shared"])
        assert args.targets == ["core", "shared"]


class TestSASTBaseline:
    """Test baseline loading and filtering."""

    def test_load_baseline_empty_file(self, tmp_path: Path) -> None:
        baseline_file = tmp_path / "baseline.json"
        baseline_file.write_text('{"results": []}', encoding="utf-8")
        result = load_baseline(str(baseline_file))
        assert result == []

    def test_load_baseline_missing_file(self) -> None:
        result = load_baseline("/nonexistent/baseline.json")
        assert result == []

    def test_load_baseline_malformed(self, tmp_path: Path) -> None:
        baseline_file = tmp_path / "bad.json"
        baseline_file.write_text("not json", encoding="utf-8")
        result = load_baseline(str(baseline_file))
        assert result == []

    def test_filter_baseline_removes_known(self) -> None:
        results = [
            {"filename": "a.py", "line_number": 10, "test_id": "B101", "issue_severity": "LOW"},
            {"filename": "b.py", "line_number": 20, "test_id": "B102", "issue_severity": "HIGH"},
        ]
        baseline = [
            {"filename": "a.py", "line_number": 10, "test_id": "B101"},
        ]
        filtered = filter_baseline(results, baseline)
        assert len(filtered) == 1
        assert filtered[0]["filename"] == "b.py"


class TestSASTClassification:
    """Test finding classification and blocking."""

    def test_classify_findings(self) -> None:
        findings = [
            {"issue_severity": "HIGH"},
            {"issue_severity": "LOW"},
            {"issue_severity": "MEDIUM"},
            {"issue_severity": "HIGH"},
        ]
        classified = classify_findings(findings)
        assert len(classified["HIGH"]) == 2
        assert len(classified["LOW"]) == 1
        assert len(classified["MEDIUM"]) == 1

    def test_should_block_on_high(self) -> None:
        classified = {"HIGH": [{"issue": "test"}], "MEDIUM": [], "LOW": []}
        assert sast_should_block(classified) is True

    def test_should_not_block_on_low(self) -> None:
        classified = {"HIGH": [], "MEDIUM": [{"issue": "test"}], "LOW": [{"issue": "test"}]}
        assert sast_should_block(classified) is False

    def test_format_text_report_pass(self) -> None:
        classified = {"HIGH": [], "MEDIUM": [], "LOW": []}
        report = format_text_report(classified, block=False)
        assert "PASS" in report
        assert "Total findings: 0" in report

    def test_format_text_report_fail(self) -> None:
        classified = {"HIGH": [{"test_id": "B105", "issue_text": "hardcoded password", "filename": "a.py", "line_number": 1}], "MEDIUM": [], "LOW": []}
        report = format_text_report(classified, block=True)
        assert "FAIL" in report


class TestSASTMain:
    """Test SAST main entry point."""

    @patch("scripts.run_sast.run_bandit")
    def test_main_pass_no_findings(self, mock_bandit: MagicMock, tmp_path: Path) -> None:
        mock_bandit.return_value = {"results": [], "errors": [], "metrics": {}}
        baseline = tmp_path / "baseline.json"
        baseline.write_text('{"results": []}', encoding="utf-8")
        rc = sast_main(["--config", ".bandit", "--baseline", str(baseline)])
        assert rc == 0

    @patch("scripts.run_sast.run_bandit")
    def test_main_fail_high_finding(self, mock_bandit: MagicMock, tmp_path: Path) -> None:
        mock_bandit.return_value = {
            "results": [{"issue_severity": "HIGH", "filename": "x.py", "line_number": 1, "test_id": "B105"}],
            "errors": [],
            "metrics": {},
        }
        baseline = tmp_path / "baseline.json"
        baseline.write_text('{"results": []}', encoding="utf-8")
        rc = sast_main(["--config", ".bandit", "--baseline", str(baseline)])
        assert rc == 1


# =====================================================================
# DAST Tests
# =====================================================================


class TestDASTConfig:
    """Test DAST config building and validation."""

    def test_build_zap_config(self) -> None:
        config = build_zap_config("http://localhost:8000", "/openapi.json")
        assert config["target"] == "http://localhost:8000"
        assert config["openapi_url"] == "http://localhost:8000/openapi.json"
        assert len(config["checks"]) == len(ZAP_CHECK_CATEGORIES)

    def test_validate_config_valid(self) -> None:
        config = build_zap_config("http://localhost:8000", "/openapi.json")
        errors = validate_config(config)
        assert errors == []

    def test_validate_config_missing_target(self) -> None:
        config = {"target": "", "openapi_url": "http://x/api", "checks": ["xss-reflected"]}
        errors = validate_config(config)
        assert any("target" in e for e in errors)

    def test_validate_config_bad_scheme(self) -> None:
        config = {"target": "ftp://bad", "openapi_url": "ftp://bad/api", "checks": ["xss-reflected"]}
        errors = validate_config(config)
        assert any("http" in e for e in errors)

    def test_validate_config_unknown_check(self) -> None:
        config = {"target": "http://ok", "openapi_url": "http://ok/api", "checks": ["unknown-check"]}
        errors = validate_config(config)
        assert any("unknown" in e for e in errors)


class TestDASTReports:
    """Test DAST report generation."""

    def test_generate_mock_report(self) -> None:
        config = build_zap_config("http://localhost:8000", "/openapi.json")
        report = generate_mock_report(config)
        assert report["status"] == "PASS"
        assert report["mode"] == "mock"
        assert report["summary"]["high"] == 0

    def test_generate_mock_html(self) -> None:
        config = build_zap_config("http://localhost:8000", "/openapi.json")
        report = generate_mock_report(config)
        html = generate_mock_html(report)
        assert "<html>" in html
        assert "DAST" in html

    def test_dast_main_mock_mode(self, tmp_path: Path) -> None:
        report_dir = str(tmp_path / "reports" / "dast")
        rc = dast_main(["--mock", "--report-dir", report_dir])
        assert rc == 0
        assert (tmp_path / "reports" / "dast" / "dast_report.json").exists()
        assert (tmp_path / "reports" / "dast" / "dast_report.html").exists()


class TestDASTArgParser:
    """Test DAST argument parsing."""

    def test_default_args(self) -> None:
        parser = dast_build_parser()
        args = parser.parse_args([])
        assert args.target == "http://localhost:8000"
        assert args.mock is False

    def test_mock_flag(self) -> None:
        parser = dast_build_parser()
        args = parser.parse_args(["--mock"])
        assert args.mock is True


# =====================================================================
# Dependency Scan Tests
# =====================================================================


class TestDepScanRequirements:
    """Test requirements parsing."""

    def test_parse_requirements_basic(self, tmp_path: Path) -> None:
        req = tmp_path / "requirements.txt"
        req.write_text("fastapi>=0.109.0\nuvicorn>=0.27.0\n# comment\n", encoding="utf-8")
        components = parse_requirements(str(req))
        assert len(components) == 2
        assert components[0]["name"] == "fastapi"
        assert components[0]["version"] == "0.109.0"

    def test_parse_requirements_with_extras(self, tmp_path: Path) -> None:
        req = tmp_path / "requirements.txt"
        req.write_text("livekit-agents[deepgram,elevenlabs]>=1.0.0\n", encoding="utf-8")
        components = parse_requirements(str(req))
        assert components[0]["name"] == "livekit-agents"

    def test_parse_requirements_missing_file(self) -> None:
        components = parse_requirements("/nonexistent/requirements.txt")
        assert components == []


class TestDepScanSBOM:
    """Test SBOM generation."""

    def test_generate_sbom_format(self, tmp_path: Path) -> None:
        req = tmp_path / "requirements.txt"
        req.write_text("fastapi>=0.109.0\nhttpx>=0.26.0\n", encoding="utf-8")
        sbom_path = str(tmp_path / "sbom.json")

        sbom = generate_sbom([str(req)], sbom_path)

        assert sbom["bomFormat"] == "CycloneDX"
        assert sbom["specVersion"] == "1.4"
        assert len(sbom["components"]) == 2
        assert sbom["components"][0]["type"] == "library"
        assert "purl" in sbom["components"][0]

        # Verify file written
        with open(sbom_path, "r", encoding="utf-8") as f:
            written = json.load(f)
        assert written["bomFormat"] == "CycloneDX"

    def test_sbom_deduplicates(self, tmp_path: Path) -> None:
        req1 = tmp_path / "req1.txt"
        req1.write_text("fastapi>=0.109.0\n", encoding="utf-8")
        req2 = tmp_path / "req2.txt"
        req2.write_text("fastapi>=0.110.0\n", encoding="utf-8")
        sbom_path = str(tmp_path / "sbom.json")

        sbom = generate_sbom([str(req1), str(req2)], sbom_path)
        assert len(sbom["components"]) == 1


class TestDepScanClassification:
    """Test vulnerability classification."""

    def test_classify_vulnerabilities(self) -> None:
        result = {"vulnerabilities": [{"severity": "HIGH"}, {"severity": "LOW"}, {"severity": "CRITICAL"}]}
        counts = classify_vulnerabilities(result)
        assert counts["HIGH"] == 1
        assert counts["CRITICAL"] == 1
        assert counts["LOW"] == 1

    def test_should_block_critical(self) -> None:
        assert dep_should_block({"CRITICAL": 1, "HIGH": 0, "MEDIUM": 0, "LOW": 0}) is True

    def test_should_not_block_medium(self) -> None:
        assert dep_should_block({"CRITICAL": 0, "HIGH": 0, "MEDIUM": 5, "LOW": 10}) is False


class TestDepScanMain:
    """Test dependency scan main."""

    def test_main_generates_sbom(self, tmp_path: Path) -> None:
        req = tmp_path / "requirements.txt"
        req.write_text("fastapi>=0.109.0\n", encoding="utf-8")
        sbom = str(tmp_path / "sbom.json")
        report = str(tmp_path / "report.json")

        rc = dep_main([
            "--requirements", str(req),
            "--sbom-output", sbom,
            "--report-output", report,
        ])
        # Should succeed even without pip-audit/safety installed
        assert rc == 0
        assert Path(sbom).exists()


# =====================================================================
# Security Audit Tests
# =====================================================================


class TestAuditCheck:
    """Test AuditCheck model."""

    def test_pass_check(self) -> None:
        check = AuditCheck("test", "test desc")
        check.pass_check("all good")
        assert check.passed is True
        assert "all good" in check.evidence

    def test_fail_check(self) -> None:
        check = AuditCheck("test", "test desc", severity="CRITICAL")
        check.fail_check("bad thing")
        assert check.passed is False
        assert check.severity == "CRITICAL"

    def test_to_dict(self) -> None:
        check = AuditCheck("test", "desc", severity="HIGH")
        check.pass_check()
        d = check.to_dict()
        assert d["name"] == "test"
        assert d["passed"] is True


class TestAuditChecks:
    """Test individual audit checks against mock filesystem."""

    def test_no_plaintext_keys_pass(self, tmp_project: Path) -> None:
        check = check_no_plaintext_keys(tmp_project)
        assert check.passed is True

    def test_no_plaintext_keys_fail(self, tmp_project: Path) -> None:
        bad_file = tmp_project / "core" / "bad.py"
        bad_file.write_text('API_KEY = "sk-abcdefghijklmnopqrstuvwxyz1234567890"\n', encoding="utf-8")
        check = check_no_plaintext_keys(tmp_project)
        assert check.passed is False

    def test_docker_nonroot_pass(self, tmp_project: Path) -> None:
        check = check_docker_nonroot(tmp_project)
        assert check.passed is True

    def test_docker_nonroot_fail(self, tmp_project: Path) -> None:
        df = tmp_project / "deployments" / "docker" / "Dockerfile"
        df.write_text("FROM python:3.11\nCMD python app.py\n", encoding="utf-8")
        check = check_docker_nonroot(tmp_project)
        assert check.passed is False

    def test_pii_scrubbing_pass(self, tmp_project: Path) -> None:
        check = check_pii_scrubbing(tmp_project)
        assert check.passed is True

    def test_encryption_present_pass(self, tmp_project: Path) -> None:
        check = check_encryption_present(tmp_project)
        assert check.passed is True

    def test_https_enforced_pass(self, tmp_project: Path) -> None:
        check = check_https_enforced(tmp_project)
        assert check.passed is True

    def test_input_validation_pass(self, tmp_project: Path) -> None:
        check = check_input_validation(tmp_project)
        assert check.passed is True

    def test_rate_limiting_fail(self, tmp_project: Path) -> None:
        # Default fixture has no rate limiting
        check = check_rate_limiting(tmp_project)
        assert check.passed is False

    def test_cors_no_middleware(self, tmp_project: Path) -> None:
        # No CORS is acceptable (API-only)
        check = check_cors_configured(tmp_project)
        assert check.passed is True


class TestAuditReport:
    """Test audit report generation."""

    def test_generate_report_all_pass(self) -> None:
        checks = [AuditCheck("a", "desc a"), AuditCheck("b", "desc b")]
        checks[0].pass_check()
        checks[1].pass_check()
        report = generate_report(checks)
        assert report["status"] == "PASS"
        assert report["summary"]["passed"] == 2
        assert report["summary"]["failed"] == 0

    def test_generate_report_critical_fail(self) -> None:
        checks = [AuditCheck("a", "desc", severity="CRITICAL")]
        checks[0].fail_check("oops")
        report = generate_report(checks)
        assert report["status"] == "FAIL"
        assert report["summary"]["critical_failures"] == 1

    def test_generate_report_non_critical_fail(self) -> None:
        checks = [AuditCheck("a", "desc", severity="MEDIUM")]
        checks[0].fail_check("minor issue")
        report = generate_report(checks)
        assert report["status"] == "PASS"  # Only CRITICAL triggers FAIL


class TestAuditMain:
    """Test audit main entry point."""

    def test_main_writes_report(self, tmp_project: Path, tmp_path: Path) -> None:
        report_path = str(tmp_path / "audit.json")
        rc = audit_main(["--project-root", str(tmp_project), "--report-output", report_path])
        assert Path(report_path).exists()
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
        assert "checks" in report
        assert report["summary"]["total_checks"] == 8


class TestAuditArgParser:
    """Test audit argument parsing."""

    def test_default_args(self) -> None:
        parser = audit_build_parser()
        args = parser.parse_args([])
        assert args.project_root == "."
        assert args.report_output == "reports/security_audit.json"

    def test_custom_root(self) -> None:
        parser = audit_build_parser()
        args = parser.parse_args(["--project-root", "/tmp/project"])
        assert args.project_root == "/tmp/project"
