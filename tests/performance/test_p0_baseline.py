"""Verify P0 baseline metrics are capturable and within expected ranges."""
import json


class TestP0BaselineMetrics:
    """Validate baseline metric capture functions."""

    def test_import_latency_under_limits(self):
        """Key module imports complete within acceptable time."""
        from scripts.capture_baseline import measure_import_latency

        results = measure_import_latency()
        # Config should import in < 2000ms (generous for CI)
        assert results["Config"]["status"] == "ok"
        assert results["Config"]["ms"] < 2000, f"Config import took {results['Config']['ms']}ms"

        # At least 3 of 5 modules should import successfully
        ok_count = sum(1 for v in results.values() if v["status"] == "ok")
        assert ok_count >= 3, f"Only {ok_count}/5 modules imported successfully"

    def test_loc_counts_nonzero(self):
        """All source modules have nonzero LOC."""
        from scripts.capture_baseline import count_loc

        results = count_loc()
        for module in ["shared", "core", "application", "infrastructure", "apps"]:
            assert results[module] > 0, f"{module} has 0 lines of code"

    def test_config_var_count_matches_expected(self):
        """settings.py has approximately 82 env var lookups."""
        from scripts.capture_baseline import count_config_vars

        count = count_config_vars()
        # Allow +-15 variance from the known ~82 count
        assert 65 <= count <= 100, f"Expected ~82 config vars, got {count}"

    def test_dependency_count_reasonable(self):
        """Requirements files have a reasonable number of packages."""
        from scripts.capture_baseline import count_dependencies

        results = count_dependencies()
        assert "requirements.txt" in results
        assert results["requirements.txt"] > 5, "Too few dependencies in requirements.txt"

    def test_baseline_json_schema(self, tmp_path, monkeypatch):
        """Generated baseline JSON matches expected schema."""
        from scripts.capture_baseline import main

        # Redirect output to tmp_path
        monkeypatch.chdir(tmp_path)
        (tmp_path / "shared" / "config").mkdir(parents=True)
        (tmp_path / "shared" / "config" / "settings.py").write_text("# stub")

        # Create minimal requirements
        (tmp_path / "requirements.txt").write_text("pytest>=7.0\n")
        (tmp_path / "requirements-extras.txt").write_text("# extras\n")
        (tmp_path / "tests").mkdir()

        main()

        output_path = tmp_path / "docs" / "baselines" / "p0_metrics.json"
        assert output_path.exists(), "Baseline JSON was not created"

        data = json.loads(output_path.read_text())

        # Verify top-level schema
        assert data["schema_version"] == "1.0.0"
        assert "captured_at" in data
        assert data["phase"] == "P0_baseline"
        assert "git_commit" in data

        # Verify metrics section
        metrics = data["metrics"]
        assert "import_latency" in metrics
        assert "loc_per_module" in metrics
        assert "stub_inventory" in metrics
        assert "config_var_count" in metrics
        assert "dependency_count" in metrics
        assert "test_stats" in metrics

        # Verify VRAM section
        assert data["vram_usage"]["value_mb"] is None

    def test_stub_inventory_capturable(self):
        """Stub counting works and returns per-module results."""
        from scripts.capture_baseline import count_stubs

        results = count_stubs()
        assert isinstance(results, dict)
        assert "shared" in results
        assert "core" in results
        # Values should be non-negative integers
        for module, count in results.items():
            assert isinstance(count, int)
            assert count >= 0

    def test_test_stats_capturable(self):
        """Test stat collection returns valid structure."""
        from scripts.capture_baseline import capture_test_stats

        results = capture_test_stats()
        assert "collected" in results
        # Should collect at least 400 tests (we have 840+)
        assert results["collected"] >= 400, f"Only {results['collected']} tests collected (expected 400+)"
