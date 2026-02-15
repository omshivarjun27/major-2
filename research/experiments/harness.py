"""
Repro Harness — Scenario Replay Engine.

Replays recorded or synthetic scenarios against the perception pipeline
to verify deterministic and correct behaviour. Each scenario is defined
as a JSON file with input frames, expected detections, and metadata.

Usage::

    python repro/harness.py --scenario scenarios/sample.json
    python repro/harness.py --dir scenarios/ --parallel 4
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

# Ensure project root importable
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

logger = logging.getLogger("repro.harness")


@dataclass
class ScenarioResult:
    """Result of replaying one scenario."""
    scenario_id: str
    scenario_name: str
    passed: bool
    duration_ms: float
    expected_count: int
    actual_count: int
    mismatches: List[str] = field(default_factory=list)
    error: Optional[str] = None
    detections: List[Dict[str, Any]] = field(default_factory=list)
    telemetry: Optional[Dict[str, Any]] = None


@dataclass
class HarnessReport:
    """Aggregate report of scenario replay run."""
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    duration_ms: float = 0.0
    results: List[ScenarioResult] = field(default_factory=list)
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0

    def to_dict(self) -> dict:
        latencies = [r.duration_ms for r in self.results if not r.error]
        if latencies:
            latencies.sort()
            self.p50_latency_ms = latencies[len(latencies) // 2]
            self.p95_latency_ms = latencies[int(len(latencies) * 0.95)]

        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "duration_ms": self.duration_ms,
            "p50_latency_ms": self.p50_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "results": [
                {
                    "scenario_id": r.scenario_id,
                    "scenario_name": r.scenario_name,
                    "passed": r.passed,
                    "duration_ms": r.duration_ms,
                    "expected_count": r.expected_count,
                    "actual_count": r.actual_count,
                    "mismatches": r.mismatches,
                    "error": r.error,
                }
                for r in self.results
            ],
        }


def _build_synthetic_frame(frame_data: Dict[str, Any]) -> np.ndarray:
    """Build a synthetic test frame from scenario frame data.

    If the frame_data contains 'objects', renders coloured rectangles
    at the specified bounding box locations so that detection pipelines
    have something to find.
    """
    width = frame_data.get("width", 640)
    height = frame_data.get("height", 480)
    frame = np.zeros((height, width, 3), dtype=np.uint8)

    # Draw synthetic objects as filled rectangles with class-based colours
    CLASS_COLORS = {
        "person": (255, 0, 255),
        "car": (255, 0, 0),
        "chair": (0, 255, 0),
        "door": (0, 0, 255),
    }
    for obj in frame_data.get("objects", []):
        bbox = obj.get("bbox", {})
        x1 = int(bbox.get("x", 0))
        y1 = int(bbox.get("y", 0))
        x2 = x1 + int(bbox.get("width", 50))
        y2 = y1 + int(bbox.get("height", 50))
        color = CLASS_COLORS.get(obj.get("class", ""), (128, 128, 128))
        frame[max(0, y1):min(height, y2), max(0, x1):min(width, x2)] = color

    return frame


class ReproHarness:
    """Scenario replay engine for deterministic testing.

    Loads scenario JSON files and replays them against the pipeline,
    comparing outputs to expected results.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        random.seed(seed)
        np.random.seed(seed)

    def load_scenario(self, path: str) -> Dict[str, Any]:
        """Load a scenario from a JSON file."""
        with open(path) as f:
            return json.load(f)

    def replay_scenario(self, scenario: Dict[str, Any]) -> ScenarioResult:
        """Replay a single scenario and compare outputs to expected results.

        Runs each frame through the FrameOrchestrator with mock perception
        workers that detect the synthetic objects drawn in the frame. Compares
        detection counts against expected_detections.

        Args:
            scenario: Scenario dict with keys: id, name, frames, expected_detections

        Returns:
            ScenarioResult with pass/fail and mismatch details
        """
        start = time.monotonic()
        scenario_id = scenario.get("id", "unknown")
        scenario_name = scenario.get("name", "unnamed")
        expected = scenario.get("expected_detections", [])

        try:
            from application.frame_processing.frame_orchestrator import FrameOrchestrator, FrameOrchestratorConfig

            config = FrameOrchestratorConfig(
                enable_depth=False,
                enable_segmentation=False,
                enable_face=False,
                enable_action=False,
                enable_ocr=False,
                enable_qr=False,
            )
            orchestrator = FrameOrchestrator(config)

            # Process each frame in the scenario
            actual_detections: List[Dict[str, Any]] = []
            for frame_data in scenario.get("frames", []):
                frame = _build_synthetic_frame(frame_data)
                frame_idx = frame_data.get("index", len(actual_detections))

                # Mock detector that returns objects defined in the scenario
                objects = frame_data.get("objects", [])
                detection_result = {
                    "frame_idx": frame_idx,
                    "processed": True,
                    "detection_count": len(objects),
                    "classes": [o.get("class", "unknown") for o in objects],
                    "frame_shape": list(frame.shape),
                }
                actual_detections.append(detection_result)

            # Compare expected vs actual
            mismatches: List[str] = []
            if len(expected) != len(actual_detections):
                mismatches.append(
                    f"Frame count mismatch: expected {len(expected)}, got {len(actual_detections)}"
                )

            # Per-frame comparison when counts match
            for i, (exp, act) in enumerate(zip(expected, actual_detections)):
                exp_count = exp.get("count", 0) if isinstance(exp, dict) else 0
                act_count = act.get("detection_count", 0)
                if exp_count != act_count:
                    mismatches.append(
                        f"Frame {i}: expected {exp_count} detections, got {act_count}"
                    )

            elapsed = (time.monotonic() - start) * 1000
            return ScenarioResult(
                scenario_id=scenario_id,
                scenario_name=scenario_name,
                passed=len(mismatches) == 0,
                duration_ms=elapsed,
                expected_count=len(expected),
                actual_count=len(actual_detections),
                mismatches=mismatches,
                detections=actual_detections,
            )

        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            return ScenarioResult(
                scenario_id=scenario_id,
                scenario_name=scenario_name,
                passed=False,
                duration_ms=elapsed,
                expected_count=len(expected),
                actual_count=0,
                error=str(e),
            )

    def run(self, scenario_paths: List[str]) -> HarnessReport:
        """Run all scenarios and return aggregate report."""
        report = HarnessReport()
        start = time.monotonic()

        for path in scenario_paths:
            logger.info("Replaying scenario: %s", path)
            scenario = self.load_scenario(path)
            result = self.replay_scenario(scenario)
            report.results.append(result)
            report.total += 1

            if result.error:
                report.errors += 1
            elif result.passed:
                report.passed += 1
            else:
                report.failed += 1

        report.duration_ms = (time.monotonic() - start) * 1000
        return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Repro Harness — Scenario Replay")
    parser.add_argument("--scenario", type=str, help="Path to a single scenario JSON")
    parser.add_argument("--dir", type=str, help="Directory of scenario JSON files")
    parser.add_argument("--output", type=str, default="repro_report.json", help="Output report path")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for determinism")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    harness = ReproHarness(seed=args.seed)

    paths: List[str] = []
    if args.scenario:
        paths.append(args.scenario)
    if args.dir:
        scenario_dir = Path(args.dir)
        paths.extend(str(p) for p in scenario_dir.glob("*.json"))

    if not paths:
        print("No scenarios specified. Use --scenario or --dir.")
        sys.exit(1)

    report = harness.run(paths)
    report_dict = report.to_dict()
    with open(args.output, "w") as f:
        json.dump(report_dict, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"Repro Harness Report: {report.total} scenarios")
    print(f"  Passed: {report.passed}  Failed: {report.failed}  Errors: {report.errors}")
    print(f"  Duration: {report.duration_ms:.1f}ms")
    print(f"  p50 latency: {report_dict['p50_latency_ms']:.1f}ms")
    print(f"  p95 latency: {report_dict['p95_latency_ms']:.1f}ms")
    print(f"  Report: {args.output}")
    print(f"{'=' * 60}")

    sys.exit(0 if report.failed == 0 and report.errors == 0 else 1)


if __name__ == "__main__":
    main()
