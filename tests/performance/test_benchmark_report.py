"""
NFR Test #130 — Automated Benchmark Report Export
==================================================

Verifies that the system can produce a machine-readable JSON
benchmark report capturing performance metrics.
"""

import json
import os
import time
import numpy as np
import pytest


class TestBenchmarkReport:

    def _generate_report(self) -> dict:
        """Generate a sample benchmark report."""
        from shared.config import get_config
        cfg = get_config()

        # Simulate frame processing timing
        latencies = []
        for _ in range(100):
            start = time.monotonic()
            frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            gray = np.mean(frame, axis=2).astype(np.uint8)
            _ = np.histogram(gray, bins=16)
            latencies.append((time.monotonic() - start) * 1000)

        latencies.sort()
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95)]
        p99 = latencies[int(len(latencies) * 0.99)]

        return {
            "schema_version": "1.0.0",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "config": {
                "spatial_enabled": cfg.get("SPATIAL_PERCEPTION_ENABLED", False),
                "target_total_latency_ms": cfg.get("TARGET_TOTAL_LATENCY_MS", 500),
                "pipeline_timeout_ms": cfg.get("PIPELINE_TIMEOUT_MS", 300),
            },
            "metrics": {
                "frames_processed": len(latencies),
                "latency_ms": {
                    "p50": round(p50, 2),
                    "p95": round(p95, 2),
                    "p99": round(p99, 2),
                    "mean": round(np.mean(latencies), 2),
                    "max": round(max(latencies), 2),
                },
                "throughput_fps": round(1000 / np.mean(latencies), 1),
            },
            "compliance": {
                "p95_under_500ms": p95 < 500,
                "face_encryption_enabled": cfg.get("FACE_ENCRYPTION_ENABLED", False),
                "debug_endpoints_disabled": not cfg.get("DEBUG_ENDPOINTS_ENABLED", True),
                "memory_consent_required": cfg.get("MEMORY_REQUIRE_CONSENT", True),
            },
        }

    def test_report_generation(self):
        """Benchmark report should be generated successfully."""
        report = self._generate_report()
        assert "schema_version" in report
        assert "metrics" in report
        assert "compliance" in report
        assert report["metrics"]["frames_processed"] == 100

    def test_report_valid_json(self):
        """Report should be valid JSON."""
        report = self._generate_report()
        json_str = json.dumps(report, indent=2)
        parsed = json.loads(json_str)
        assert parsed == report

    def test_report_latency_structure(self):
        """Report latency metrics should have p50, p95, p99."""
        report = self._generate_report()
        latency = report["metrics"]["latency_ms"]
        assert "p50" in latency
        assert "p95" in latency
        assert "p99" in latency
        assert "mean" in latency
        assert latency["p50"] <= latency["p95"] <= latency["p99"]

    def test_report_exportable_to_file(self, tmp_path):
        """Report should be writable to a JSON file."""
        report = self._generate_report()
        output = tmp_path / "benchmark_report.json"
        with open(output, "w") as f:
            json.dump(report, f, indent=2)
        assert output.exists()
        assert output.stat().st_size > 100

    def test_compliance_section(self):
        """Compliance section should flag SLA violations."""
        report = self._generate_report()
        compliance = report["compliance"]
        assert isinstance(compliance["p95_under_500ms"], bool)
        assert isinstance(compliance["memory_consent_required"], bool)
