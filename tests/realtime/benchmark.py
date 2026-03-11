"""
Benchmark Tool for Spatial Perception Pipeline
===============================================

Runs systematic benchmarks across different configurations to measure
performance characteristics and compare detector/depth combinations.

Usage:
    python benchmark.py                          # Run all benchmarks
    python benchmark.py --config mock-simple     # Specific config
    python benchmark.py --output results.json    # Save results
    python benchmark.py --frames 500             # Process N frames
    python benchmark.py --headless               # No display

Author: Ally Vision Team
"""

import argparse
import asyncio
import gc
import json
import logging
import os
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from PIL import Image

# Import spatial perception components
from core.vision.spatial import (
    create_spatial_processor,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("benchmark")


# =============================================================================
# BENCHMARK CONFIGURATIONS
# =============================================================================

@dataclass
class BenchmarkConfig:
    """Configuration for a benchmark run"""
    name: str
    detector: str  # mock, yolo
    depth: str     # simple, midas
    segmentation: bool
    depth_enabled: bool
    description: str = ""


PRESET_CONFIGS = {
    "mock-simple": BenchmarkConfig(
        name="mock-simple",
        detector="mock",
        depth="simple",
        segmentation=False,
        depth_enabled=True,
        description="Fastest config - Mock detector, Simple depth"
    ),
    "mock-simple-seg": BenchmarkConfig(
        name="mock-simple-seg",
        detector="mock",
        depth="simple",
        segmentation=True,
        depth_enabled=True,
        description="Mock detector with segmentation"
    ),
    "yolo-simple": BenchmarkConfig(
        name="yolo-simple",
        detector="yolo",
        depth="simple",
        segmentation=False,
        depth_enabled=True,
        description="YOLO detector, Simple depth"
    ),
    "yolo-simple-seg": BenchmarkConfig(
        name="yolo-simple-seg",
        detector="yolo",
        depth="simple",
        segmentation=True,
        depth_enabled=True,
        description="YOLO with segmentation"
    ),
    "mock-midas": BenchmarkConfig(
        name="mock-midas",
        detector="mock",
        depth="midas",
        segmentation=False,
        depth_enabled=True,
        description="Mock detector, MiDaS depth"
    ),
    "yolo-midas": BenchmarkConfig(
        name="yolo-midas",
        detector="yolo",
        depth="midas",
        segmentation=False,
        depth_enabled=True,
        description="YOLO detector, MiDaS depth - Full pipeline"
    ),
    "yolo-midas-full": BenchmarkConfig(
        name="yolo-midas-full",
        detector="yolo",
        depth="midas",
        segmentation=True,
        depth_enabled=True,
        description="Full pipeline with all features"
    ),
    "minimal": BenchmarkConfig(
        name="minimal",
        detector="mock",
        depth="simple",
        segmentation=False,
        depth_enabled=False,
        description="Minimal - detection only, no depth"
    ),
}


# =============================================================================
# BENCHMARK RESULTS
# =============================================================================

@dataclass
class FrameTiming:
    """Timing data for a single frame"""
    total_ms: float
    detection_ms: float = 0.0
    segmentation_ms: float = 0.0
    depth_ms: float = 0.0
    fusion_ms: float = 0.0


@dataclass
class BenchmarkResult:
    """Results from a benchmark run"""
    config_name: str
    config: BenchmarkConfig

    # Frame counts
    total_frames: int = 0
    warmup_frames: int = 0
    measured_frames: int = 0

    # Timing stats (ms)
    avg_latency_ms: float = 0.0
    min_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    std_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0

    # FPS stats
    avg_fps: float = 0.0
    min_fps: float = 0.0
    max_fps: float = 0.0

    # Memory stats (MB)
    peak_memory_mb: float = 0.0
    avg_memory_mb: float = 0.0

    # Detection stats
    avg_detections: float = 0.0

    # Pass/fail
    meets_latency_target: bool = False
    meets_fps_target: bool = False
    latency_target_ms: float = 500.0
    fps_target: float = 15.0

    # Timestamps
    start_time: str = ""
    end_time: str = ""
    duration_seconds: float = 0.0

    # Raw timings for analysis
    frame_timings: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['config'] = asdict(self.config)
        return result


# =============================================================================
# BENCHMARK RUNNER
# =============================================================================

class BenchmarkRunner:
    """Runs benchmarks on the spatial perception pipeline"""

    def __init__(
        self,
        camera_index: int = 0,
        warmup_frames: int = 30,
        benchmark_frames: int = 300,
        latency_target_ms: float = 500.0,
        fps_target: float = 15.0,
        headless: bool = False,
        use_synthetic: bool = False
    ):
        self.camera_index = camera_index
        self.warmup_frames = warmup_frames
        self.benchmark_frames = benchmark_frames
        self.latency_target_ms = latency_target_ms
        self.fps_target = fps_target
        self.headless = headless
        self.use_synthetic = use_synthetic

        self.results: List[BenchmarkResult] = []

    def _create_synthetic_frames(self, count: int, width: int = 640, height: int = 480) -> List[np.ndarray]:
        """Create synthetic test frames"""
        frames = []
        np.random.seed(42)  # Reproducibility

        for i in range(count):
            # Create gradient background
            frame = np.zeros((height, width, 3), dtype=np.uint8)

            # Add some objects (colored rectangles)
            num_objects = np.random.randint(1, 5)
            for _ in range(num_objects):
                x1 = np.random.randint(0, width - 100)
                y1 = np.random.randint(0, height - 100)
                x2 = x1 + np.random.randint(50, 150)
                y2 = y1 + np.random.randint(50, 150)
                color = tuple(np.random.randint(50, 255, 3).tolist())
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, -1)

            # Add some noise
            noise = np.random.randint(0, 30, frame.shape, dtype=np.uint8)
            frame = cv2.add(frame, noise)

            frames.append(frame)

        return frames

    def _get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / (1024 * 1024)
        except ImportError:
            return 0.0

    async def run_benchmark(self, config: BenchmarkConfig) -> BenchmarkResult:
        """Run benchmark for a specific configuration"""
        logger.info(f"\n{'='*60}")
        logger.info(f"Running benchmark: {config.name}")
        logger.info(f"Description: {config.description}")
        logger.info(f"{'='*60}")

        # Initialize result
        result = BenchmarkResult(
            config_name=config.name,
            config=config,
            latency_target_ms=self.latency_target_ms,
            fps_target=self.fps_target,
            start_time=datetime.now().isoformat()
        )

        # Create processor
        use_yolo = config.detector == "yolo"
        use_midas = config.depth == "midas"

        try:
            processor = create_spatial_processor(
                use_yolo=use_yolo,
                use_midas=use_midas,
                enable_segmentation=config.segmentation,
                enable_depth=config.depth_enabled
            )
        except Exception as e:
            logger.error(f"Failed to create processor: {e}")
            return result

        # Get frames (synthetic or camera)
        if self.use_synthetic:
            logger.info("Using synthetic frames")
            total_frames = self.warmup_frames + self.benchmark_frames
            frames = self._create_synthetic_frames(total_frames)
        else:
            logger.info(f"Opening camera {self.camera_index}")
            cap = cv2.VideoCapture(self.camera_index)
            if not cap.isOpened():
                logger.error("Failed to open camera")
                return result
            frames = None

        # Run benchmark
        frame_timings: List[float] = []
        detection_counts: List[int] = []
        memory_readings: List[float] = []
        frame_count = 0

        try:
            total_frames = self.warmup_frames + self.benchmark_frames

            for i in range(total_frames):
                # Get frame
                if self.use_synthetic:
                    frame = frames[i]
                else:
                    ret, frame = cap.read()
                    if not ret:
                        logger.warning("Failed to read frame")
                        continue

                # Convert to PIL
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(rgb_frame)

                # Time processing
                start_time = time.perf_counter()
                await processor.process_frame(pil_image)
                elapsed_ms = (time.perf_counter() - start_time) * 1000

                # Skip warmup frames
                if i >= self.warmup_frames:
                    frame_timings.append(elapsed_ms)
                    detection_counts.append(len(processor.last_obstacles))
                    memory_readings.append(self._get_memory_usage_mb())

                frame_count += 1

                # Progress
                if i % 50 == 0:
                    logger.info(f"  Processed {i}/{total_frames} frames")

                # Show frame if not headless
                if not self.headless:
                    cv2.imshow(f"Benchmark: {config.name}", frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break

                # Garbage collection every 100 frames
                if i % 100 == 0:
                    gc.collect()

        finally:
            if not self.use_synthetic:
                cap.release()
            if not self.headless:
                cv2.destroyAllWindows()

        # Calculate statistics
        if frame_timings:
            result.total_frames = frame_count
            result.warmup_frames = self.warmup_frames
            result.measured_frames = len(frame_timings)

            # Latency stats
            result.avg_latency_ms = statistics.mean(frame_timings)
            result.min_latency_ms = min(frame_timings)
            result.max_latency_ms = max(frame_timings)
            result.std_latency_ms = statistics.stdev(frame_timings) if len(frame_timings) > 1 else 0

            sorted_timings = sorted(frame_timings)
            result.p50_latency_ms = sorted_timings[len(sorted_timings) // 2]
            result.p95_latency_ms = sorted_timings[int(len(sorted_timings) * 0.95)]
            result.p99_latency_ms = sorted_timings[int(len(sorted_timings) * 0.99)]

            # FPS stats
            fps_values = [1000.0 / t for t in frame_timings if t > 0]
            result.avg_fps = statistics.mean(fps_values) if fps_values else 0
            result.min_fps = min(fps_values) if fps_values else 0
            result.max_fps = max(fps_values) if fps_values else 0

            # Memory stats
            if memory_readings:
                result.peak_memory_mb = max(memory_readings)
                result.avg_memory_mb = statistics.mean(memory_readings)

            # Detection stats
            result.avg_detections = statistics.mean(detection_counts) if detection_counts else 0

            # Pass/fail
            result.meets_latency_target = result.avg_latency_ms <= self.latency_target_ms
            result.meets_fps_target = result.avg_fps >= self.fps_target

            # Store raw timings
            result.frame_timings = frame_timings

        result.end_time = datetime.now().isoformat()
        result.duration_seconds = len(frame_timings) * result.avg_latency_ms / 1000 if frame_timings else 0

        self.results.append(result)
        self._print_result(result)

        return result

    def _print_result(self, result: BenchmarkResult):
        """Print benchmark result"""
        print(f"\n{'─'*50}")
        print(f"  {result.config_name}")
        print(f"{'─'*50}")
        print(f"  Frames Measured: {result.measured_frames}")
        print("  ")
        print("  Latency:")
        print(f"    Average: {result.avg_latency_ms:.2f} ms")
        print(f"    Min:     {result.min_latency_ms:.2f} ms")
        print(f"    Max:     {result.max_latency_ms:.2f} ms")
        print(f"    P50:     {result.p50_latency_ms:.2f} ms")
        print(f"    P95:     {result.p95_latency_ms:.2f} ms")
        print(f"    P99:     {result.p99_latency_ms:.2f} ms")
        print("  ")
        print("  FPS:")
        print(f"    Average: {result.avg_fps:.2f}")
        print(f"    Min:     {result.min_fps:.2f}")
        print(f"    Max:     {result.max_fps:.2f}")
        print("  ")
        print("  Memory:")
        print(f"    Peak:    {result.peak_memory_mb:.1f} MB")
        print(f"    Average: {result.avg_memory_mb:.1f} MB")
        print("  ")
        print(f"  Detections (avg): {result.avg_detections:.1f}")
        print("  ")

        latency_status = "✓ PASS" if result.meets_latency_target else "✗ FAIL"
        fps_status = "✓ PASS" if result.meets_fps_target else "✗ FAIL"

        print("  Targets:")
        print(f"    Latency < {result.latency_target_ms}ms: {latency_status}")
        print(f"    FPS >= {result.fps_target}: {fps_status}")
        print(f"{'─'*50}")

    async def run_all_benchmarks(self, configs: Optional[List[str]] = None):
        """Run benchmarks for all or specified configurations"""
        if configs is None:
            configs = list(PRESET_CONFIGS.keys())

        logger.info(f"Running {len(configs)} benchmark configurations")

        for config_name in configs:
            if config_name not in PRESET_CONFIGS:
                logger.warning(f"Unknown config: {config_name}")
                continue

            config = PRESET_CONFIGS[config_name]
            await self.run_benchmark(config)

            # Clear memory between benchmarks
            gc.collect()
            await asyncio.sleep(1)

        self._print_summary()

    def _print_summary(self):
        """Print summary of all benchmark results"""
        print("\n" + "=" * 70)
        print("BENCHMARK SUMMARY")
        print("=" * 70)
        print(f"\n{'Config':<25} {'Latency(ms)':<15} {'FPS':<10} {'Status':<15}")
        print("-" * 70)

        for result in self.results:
            latency_str = f"{result.avg_latency_ms:.1f}"
            fps_str = f"{result.avg_fps:.1f}"
            status = "✓✓" if (result.meets_latency_target and result.meets_fps_target) else "✗"

            print(f"{result.config_name:<25} {latency_str:<15} {fps_str:<10} {status:<15}")

        print("-" * 70)

        # Find best config
        if self.results:
            best_latency = min(self.results, key=lambda r: r.avg_latency_ms)
            best_fps = max(self.results, key=lambda r: r.avg_fps)

            print(f"\nBest Latency: {best_latency.config_name} ({best_latency.avg_latency_ms:.1f}ms)")
            print(f"Best FPS: {best_fps.config_name} ({best_fps.avg_fps:.1f} fps)")

        print("=" * 70)

    def save_results(self, output_path: str):
        """Save benchmark results to JSON"""
        results_dict = {
            "benchmark_date": datetime.now().isoformat(),
            "settings": {
                "warmup_frames": self.warmup_frames,
                "benchmark_frames": self.benchmark_frames,
                "latency_target_ms": self.latency_target_ms,
                "fps_target": self.fps_target,
                "use_synthetic": self.use_synthetic
            },
            "results": [r.to_dict() for r in self.results]
        }

        # Remove raw timings to reduce file size
        for r in results_dict["results"]:
            r["frame_timings"] = f"[{len(r['frame_timings'])} values - omitted]"

        with open(output_path, "w") as f:
            json.dump(results_dict, f, indent=2)

        logger.info(f"Results saved to: {output_path}")


# =============================================================================
# COMPARISON REPORT
# =============================================================================

def generate_comparison_report(results_path: str, output_path: str):
    """Generate HTML comparison report from benchmark results"""
    with open(results_path, "r") as f:
        data = json.load(f)

    html = """
<!DOCTYPE html>
<html>
<head>
    <title>Spatial Perception Benchmark Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #333; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        tr:nth-child(even) { background-color: #f2f2f2; }
        .pass { color: green; font-weight: bold; }
        .fail { color: red; font-weight: bold; }
        .metric { font-size: 24px; font-weight: bold; }
        .card { background: #f9f9f9; padding: 20px; margin: 10px; border-radius: 8px; display: inline-block; }
    </style>
</head>
<body>
    <h1>Spatial Perception Pipeline Benchmark Report</h1>
    <p>Generated: """ + data["benchmark_date"] + """</p>

    <h2>Settings</h2>
    <div>
        <div class="card">
            <div class="metric">""" + str(data["settings"]["benchmark_frames"]) + """</div>
            <div>Frames per config</div>
        </div>
        <div class="card">
            <div class="metric">""" + str(data["settings"]["latency_target_ms"]) + """ms</div>
            <div>Latency Target</div>
        </div>
        <div class="card">
            <div class="metric">""" + str(data["settings"]["fps_target"]) + """</div>
            <div>FPS Target</div>
        </div>
    </div>

    <h2>Results</h2>
    <table>
        <tr>
            <th>Configuration</th>
            <th>Avg Latency (ms)</th>
            <th>P95 Latency (ms)</th>
            <th>Avg FPS</th>
            <th>Peak Memory (MB)</th>
            <th>Latency</th>
            <th>FPS</th>
        </tr>
"""

    for result in data["results"]:
        latency_class = "pass" if result["meets_latency_target"] else "fail"
        fps_class = "pass" if result["meets_fps_target"] else "fail"
        latency_text = "PASS" if result["meets_latency_target"] else "FAIL"
        fps_text = "PASS" if result["meets_fps_target"] else "FAIL"

        html += f"""
        <tr>
            <td>{result["config_name"]}</td>
            <td>{result["avg_latency_ms"]:.1f}</td>
            <td>{result["p95_latency_ms"]:.1f}</td>
            <td>{result["avg_fps"]:.1f}</td>
            <td>{result["peak_memory_mb"]:.1f}</td>
            <td class="{latency_class}">{latency_text}</td>
            <td class="{fps_class}">{fps_text}</td>
        </tr>
"""

    html += """
    </table>
</body>
</html>
"""

    with open(output_path, "w") as f:
        f.write(html)

    logger.info(f"Report saved to: {output_path}")


# =============================================================================
# MAIN
# =============================================================================

def parse_args():
    parser = argparse.ArgumentParser(description="Benchmark Spatial Perception Pipeline")

    parser.add_argument("--config", type=str, nargs="+",
                        help="Specific config(s) to benchmark")
    parser.add_argument("--list-configs", action="store_true",
                        help="List available configurations")
    parser.add_argument("--frames", type=int, default=300,
                        help="Number of frames to benchmark (default: 300)")
    parser.add_argument("--warmup", type=int, default=30,
                        help="Warmup frames (default: 30)")
    parser.add_argument("--camera", type=int, default=0,
                        help="Camera index (default: 0)")
    parser.add_argument("--synthetic", action="store_true",
                        help="Use synthetic frames instead of camera")
    parser.add_argument("--headless", action="store_true",
                        help="Run without display")
    parser.add_argument("--output", type=str, default="benchmark_results.json",
                        help="Output file for results")
    parser.add_argument("--report", type=str,
                        help="Generate HTML report from results file")
    parser.add_argument("--latency-target", type=float, default=500.0,
                        help="Latency target in ms (default: 500)")
    parser.add_argument("--fps-target", type=float, default=15.0,
                        help="FPS target (default: 15)")

    return parser.parse_args()


async def main():
    args = parse_args()

    if args.list_configs:
        print("\nAvailable Benchmark Configurations:")
        print("-" * 60)
        for name, config in PRESET_CONFIGS.items():
            print(f"  {name:<20} - {config.description}")
        print("-" * 60)
        return

    if args.report:
        generate_comparison_report(args.report, args.report.replace(".json", ".html"))
        return

    runner = BenchmarkRunner(
        camera_index=args.camera,
        warmup_frames=args.warmup,
        benchmark_frames=args.frames,
        latency_target_ms=args.latency_target,
        fps_target=args.fps_target,
        headless=args.headless,
        use_synthetic=args.synthetic
    )

    await runner.run_all_benchmarks(args.config)
    runner.save_results(args.output)


if __name__ == "__main__":
    asyncio.run(main())
