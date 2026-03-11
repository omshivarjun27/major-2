"""VRAM profiling script for Voice-Vision Assistant.

Profiles GPU memory usage across all components to identify
optimization opportunities and validate VRAM budget (<8GB).

Usage:
    python scripts/profile_vram.py
    python scripts/profile_vram.py --detailed
    python scripts/profile_vram.py --output docs/performance/vram-analysis.md
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.utils.vram_profiler import (
    empty_cuda_cache,
    get_cuda_device_info,
    get_current_vram_usage,
    get_vram_profiler,
    is_cuda_available,
)

# ---------------------------------------------------------------------------
# Component Profiling
# ---------------------------------------------------------------------------

@dataclass
class ComponentProfile:
    """Profile results for a single component."""
    name: str
    load_time_ms: float
    idle_vram_mb: float
    active_vram_mb: float
    peak_vram_mb: float
    inference_time_ms: float
    available: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def profile_yolo_detector() -> ComponentProfile:
    """Profile YOLO object detector VRAM usage."""
    profiler = get_vram_profiler()

    try:
        from core.vision.object_detector import create_detector

        empty_cuda_cache()
        start_vram, _, _ = get_current_vram_usage()

        # Load model
        load_start = time.perf_counter()
        with profiler.track("yolo_load"):
            detector = create_detector()
        load_time = (time.perf_counter() - load_start) * 1000

        idle_vram, _, _ = get_current_vram_usage()

        # Run inference
        import numpy as np
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)

        infer_start = time.perf_counter()
        with profiler.track("yolo_inference"):
            import asyncio
            asyncio.run(detector.detect(test_image))
        infer_time = (time.perf_counter() - infer_start) * 1000

        active_vram, _, peak_vram = get_current_vram_usage()

        return ComponentProfile(
            name="YOLO Detector",
            load_time_ms=load_time,
            idle_vram_mb=idle_vram - start_vram,
            active_vram_mb=active_vram - start_vram,
            peak_vram_mb=peak_vram,
            inference_time_ms=infer_time,
        )

    except Exception as e:
        return ComponentProfile(
            name="YOLO Detector",
            load_time_ms=0,
            idle_vram_mb=0,
            active_vram_mb=0,
            peak_vram_mb=0,
            inference_time_ms=0,
            available=False,
            error=str(e),
        )


def profile_depth_estimator() -> ComponentProfile:
    """Profile MiDaS depth estimator VRAM usage."""
    profiler = get_vram_profiler()

    try:
        from core.vision.depth_estimator import create_depth_estimator

        empty_cuda_cache()
        start_vram, _, _ = get_current_vram_usage()

        load_start = time.perf_counter()
        with profiler.track("midas_load"):
            estimator = create_depth_estimator()
        load_time = (time.perf_counter() - load_start) * 1000

        idle_vram, _, _ = get_current_vram_usage()

        import numpy as np
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)

        infer_start = time.perf_counter()
        with profiler.track("midas_inference"):
            import asyncio
            asyncio.run(estimator.estimate(test_image))
        infer_time = (time.perf_counter() - infer_start) * 1000

        active_vram, _, peak_vram = get_current_vram_usage()

        return ComponentProfile(
            name="MiDaS Depth",
            load_time_ms=load_time,
            idle_vram_mb=idle_vram - start_vram,
            active_vram_mb=active_vram - start_vram,
            peak_vram_mb=peak_vram,
            inference_time_ms=infer_time,
        )

    except Exception as e:
        return ComponentProfile(
            name="MiDaS Depth",
            load_time_ms=0,
            idle_vram_mb=0,
            active_vram_mb=0,
            peak_vram_mb=0,
            inference_time_ms=0,
            available=False,
            error=str(e),
        )


def profile_faiss_index() -> ComponentProfile:
    """Profile FAISS index VRAM usage (if GPU-backed)."""
    profiler = get_vram_profiler()

    try:
        import faiss
        import numpy as np

        empty_cuda_cache()
        start_vram, _, _ = get_current_vram_usage()

        # Create a test index with 5000 vectors
        dim = 384  # Common embedding dimension
        n_vectors = 5000

        load_start = time.perf_counter()
        with profiler.track("faiss_create"):
            index = faiss.IndexFlatL2(dim)
            vectors = np.random.random((n_vectors, dim)).astype('float32')
            index.add(vectors)
        load_time = (time.perf_counter() - load_start) * 1000

        idle_vram, _, _ = get_current_vram_usage()

        # Query
        query = np.random.random((1, dim)).astype('float32')
        infer_start = time.perf_counter()
        with profiler.track("faiss_query"):
            index.search(query, k=10)
        infer_time = (time.perf_counter() - infer_start) * 1000

        active_vram, _, peak_vram = get_current_vram_usage()

        return ComponentProfile(
            name="FAISS Index (5K vectors)",
            load_time_ms=load_time,
            idle_vram_mb=idle_vram - start_vram,
            active_vram_mb=active_vram - start_vram,
            peak_vram_mb=peak_vram,
            inference_time_ms=infer_time,
        )

    except Exception as e:
        return ComponentProfile(
            name="FAISS Index",
            load_time_ms=0,
            idle_vram_mb=0,
            active_vram_mb=0,
            peak_vram_mb=0,
            inference_time_ms=0,
            available=False,
            error=str(e),
        )


def profile_pytorch_baseline() -> ComponentProfile:
    """Profile baseline PyTorch VRAM usage."""
    profiler = get_vram_profiler()

    try:
        import torch

        empty_cuda_cache()
        start_vram, _, _ = get_current_vram_usage()

        if not torch.cuda.is_available():
            return ComponentProfile(
                name="PyTorch Baseline",
                load_time_ms=0,
                idle_vram_mb=0,
                active_vram_mb=0,
                peak_vram_mb=0,
                inference_time_ms=0,
                available=False,
                error="CUDA not available",
            )

        load_start = time.perf_counter()
        with profiler.track("pytorch_init"):
            # Simple tensor operation to initialize CUDA context
            x = torch.zeros(1, device="cuda")
            del x
        load_time = (time.perf_counter() - load_start) * 1000

        idle_vram, _, _ = get_current_vram_usage()

        # Simple compute
        infer_start = time.perf_counter()
        with profiler.track("pytorch_compute"):
            x = torch.randn(1000, 1000, device="cuda")
            y = torch.mm(x, x)
            del x, y
        infer_time = (time.perf_counter() - infer_start) * 1000

        active_vram, _, peak_vram = get_current_vram_usage()

        return ComponentProfile(
            name="PyTorch Baseline",
            load_time_ms=load_time,
            idle_vram_mb=idle_vram - start_vram,
            active_vram_mb=active_vram - start_vram,
            peak_vram_mb=peak_vram,
            inference_time_ms=infer_time,
        )

    except Exception as e:
        return ComponentProfile(
            name="PyTorch Baseline",
            load_time_ms=0,
            idle_vram_mb=0,
            active_vram_mb=0,
            peak_vram_mb=0,
            inference_time_ms=0,
            available=False,
            error=str(e),
        )


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------

def generate_vram_report(profiles: List[ComponentProfile], detailed: bool = False) -> Dict[str, Any]:
    """Generate VRAM profiling report."""
    get_vram_profiler()
    device_info = get_cuda_device_info()

    total_vram = device_info.get("total_memory_mb", 8192) if device_info else 8192

    # Calculate totals
    available_profiles = [p for p in profiles if p.available]
    total_idle = sum(p.idle_vram_mb for p in available_profiles)
    total_peak = max((p.peak_vram_mb for p in available_profiles), default=0)

    report = {
        "timestamp": datetime.now().isoformat(),
        "device": device_info,
        "budget_mb": 8192,  # 8GB target
        "total_vram_mb": total_vram,
        "summary": {
            "components_profiled": len(profiles),
            "components_available": len(available_profiles),
            "total_idle_vram_mb": round(total_idle, 2),
            "estimated_peak_mb": round(total_peak, 2),
            "budget_remaining_mb": round(8192 - total_peak, 2),
            "within_budget": total_peak < 8192,
        },
        "components": [p.to_dict() for p in profiles],
        "top_consumers": sorted(
            [(p.name, p.peak_vram_mb) for p in available_profiles],
            key=lambda x: x[1],
            reverse=True,
        )[:5],
        "recommendations": [],
    }

    # Generate recommendations
    if total_peak > 6000:
        report["recommendations"].append(
            "Consider INT8 quantization to reduce VRAM usage"
        )

    for p in profiles:
        if p.available and p.peak_vram_mb > 2000:
            report["recommendations"].append(
                f"{p.name}: Large VRAM consumer ({p.peak_vram_mb:.0f}MB) - consider optimization"
            )

    return report


def generate_markdown_report(report: Dict[str, Any]) -> str:
    """Generate markdown formatted VRAM analysis report."""
    lines = [
        "# VRAM Profiling Analysis",
        "",
        f"**Generated:** {report['timestamp']}",
        "",
        "## Device Information",
        "",
    ]

    device = report.get("device")
    if device:
        lines.extend([
            f"- **GPU:** {device.get('name', 'Unknown')}",
            f"- **Total VRAM:** {device.get('total_memory_mb', 0):.0f} MB",
            f"- **Compute Capability:** {device.get('compute_capability', 'N/A')}",
        ])
    else:
        lines.append("- **GPU:** Not available (CPU mode)")

    lines.extend([
        "",
        "## Summary",
        "",
        "| Metric | Value | Budget | Status |",
        "|--------|-------|--------|--------|",
        f"| Components Profiled | {report['summary']['components_profiled']} | - | - |",
        f"| Estimated Peak VRAM | {report['summary']['estimated_peak_mb']:.0f} MB | 8192 MB | {'OK' if report['summary']['within_budget'] else 'OVER'} |",
        f"| Budget Remaining | {report['summary']['budget_remaining_mb']:.0f} MB | - | - |",
        "",
        "## Component Breakdown",
        "",
        "| Component | Idle (MB) | Active (MB) | Peak (MB) | Load (ms) | Status |",
        "|-----------|-----------|-------------|-----------|-----------|--------|",
    ])

    for comp in report["components"]:
        status = "OK" if comp["available"] else f"N/A ({comp.get('error', 'unavailable')})"
        if comp["available"]:
            lines.append(
                f"| {comp['name']} | {comp['idle_vram_mb']:.1f} | {comp['active_vram_mb']:.1f} | {comp['peak_vram_mb']:.1f} | {comp['load_time_ms']:.0f} | {status} |"
            )
        else:
            lines.append(f"| {comp['name']} | - | - | - | - | {status} |")

    lines.extend([
        "",
        "## Top VRAM Consumers",
        "",
    ])

    for i, (name, peak) in enumerate(report["top_consumers"], 1):
        pct = (peak / report["budget_mb"]) * 100
        lines.append(f"{i}. **{name}**: {peak:.0f} MB ({pct:.1f}% of budget)")

    if report["recommendations"]:
        lines.extend([
            "",
            "## Recommendations",
            "",
        ])
        for rec in report["recommendations"]:
            lines.append(f"- {rec}")

    lines.extend([
        "",
        "## Notes",
        "",
        "- VRAM measurements are approximate and may vary based on GPU driver and CUDA version.",
        "- Peak VRAM includes PyTorch workspace and CUDA context overhead.",
        "- Budget target of 8GB allows headroom for RTX 4060 (8GB VRAM).",
    ])

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Profile VRAM usage")
    parser.add_argument("--detailed", action="store_true", help="Include detailed breakdown")
    parser.add_argument("--output", type=str, help="Output markdown file path")
    parser.add_argument("--json", type=str, help="Output JSON file path")
    args = parser.parse_args()

    print("=" * 60)
    print("VRAM PROFILER")
    print("=" * 60)

    # Check CUDA availability
    if not is_cuda_available():
        print("\nCUDA not available - running in simulation mode")
        print("Actual VRAM measurements require GPU hardware")
    else:
        device_info = get_cuda_device_info()
        if device_info:
            print(f"\nDevice: {device_info['name']}")
            print(f"Total VRAM: {device_info['total_memory_mb']:.0f} MB")

    print("\nProfiling components...\n")

    # Profile each component
    profiles = []

    print("[1/4] PyTorch baseline...")
    profiles.append(profile_pytorch_baseline())

    print("[2/4] FAISS index...")
    profiles.append(profile_faiss_index())

    print("[3/4] YOLO detector...")
    profiles.append(profile_yolo_detector())

    print("[4/4] MiDaS depth estimator...")
    profiles.append(profile_depth_estimator())

    # Generate report
    report = generate_vram_report(profiles, detailed=args.detailed)

    # Print summary
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Estimated Peak VRAM: {report['summary']['estimated_peak_mb']:.0f} MB")
    print("Budget: 8192 MB")
    print(f"Status: {'WITHIN BUDGET' if report['summary']['within_budget'] else 'OVER BUDGET'}")

    print("\nTop Consumers:")
    for i, (name, peak) in enumerate(report["top_consumers"], 1):
        print(f"  {i}. {name}: {peak:.0f} MB")

    # Save outputs
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(generate_markdown_report(report))
        print(f"\nMarkdown report: {output_path}")

    if args.json:
        json_path = Path(args.json)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"JSON report: {json_path}")

    # Default output to docs
    if not args.output and not args.json:
        default_output = Path("docs/performance/vram-analysis.md")
        default_output.parent.mkdir(parents=True, exist_ok=True)
        with open(default_output, "w", encoding="utf-8") as f:
            f.write(generate_markdown_report(report))
        print(f"\nReport saved to: {default_output}")

    return report


if __name__ == "__main__":
    main()
