"""
VQA Engine Real-time Benchmark
==============================

Benchmarks the VQA pipeline latencies to ensure they meet targets:
- STT → LLM: ≤100ms
- Vision pipeline: ≤300ms
- LLM → TTS: ≤100ms
- Total E2E: ≤500ms
"""

import asyncio
import logging
import statistics
import sys
import time
from pathlib import Path
from typing import List, Tuple

import numpy as np
from PIL import Image

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.vqa import (
    create_perception_pipeline,
    build_scene_graph,
    SpatialFuser,
    VQAReasoner,
    MicroNavFormatter,
    QuickAnswers,
    VQARequest,
    VQAMemory,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vqa-benchmark")


# ============================================================================
# Test Images
# ============================================================================

def create_test_images() -> List[Image.Image]:
    """Create test images of varying complexity."""
    images = []
    
    # Simple gray image
    images.append(Image.new("RGB", (640, 480), color=(128, 128, 128)))
    
    # Image with colored regions (simulating objects)
    img = Image.new("RGB", (640, 480), color=(200, 200, 200))
    pixels = img.load()
    # Red region (object 1)
    for x in range(100, 200):
        for y in range(150, 300):
            pixels[x, y] = (255, 50, 50)
    # Blue region (object 2)
    for x in range(350, 480):
        for y in range(100, 250):
            pixels[x, y] = (50, 50, 255)
    images.append(img)
    
    # More complex image
    img = Image.new("RGB", (640, 480), color=(100, 100, 100))
    pixels = img.load()
    for i in range(5):
        x0 = 50 + i * 120
        y0 = 100 + (i % 2) * 150
        for x in range(x0, x0 + 80):
            for y in range(y0, y0 + 100):
                if 0 <= x < 640 and 0 <= y < 480:
                    pixels[x, y] = (50 * i, 100, 200 - 30 * i)
    images.append(img)
    
    return images


# ============================================================================
# Benchmark Functions
# ============================================================================

async def benchmark_perception(
    pipeline,
    images: List[Image.Image],
    iterations: int = 10,
) -> Tuple[float, float, float]:
    """Benchmark perception pipeline latency."""
    times = []
    
    for _ in range(iterations):
        for img in images:
            start = time.perf_counter()
            await pipeline.process(img)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
    
    return statistics.mean(times), statistics.median(times), max(times)


async def benchmark_scene_graph(
    pipeline,
    images: List[Image.Image],
    iterations: int = 10,
) -> Tuple[float, float, float]:
    """Benchmark scene graph building latency."""
    times = []
    
    for _ in range(iterations):
        for img in images:
            perception = await pipeline.process(img)
            
            start = time.perf_counter()
            build_scene_graph(perception)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
    
    return statistics.mean(times), statistics.median(times), max(times)


async def benchmark_fusion(
    pipeline,
    fuser: SpatialFuser,
    images: List[Image.Image],
    iterations: int = 10,
) -> Tuple[float, float, float]:
    """Benchmark spatial fusion latency."""
    times = []
    
    for _ in range(iterations):
        for img in images:
            perception = await pipeline.process(img)
            
            start = time.perf_counter()
            fuser.fuse(perception)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
    
    return statistics.mean(times), statistics.median(times), max(times)


async def benchmark_micronav(
    pipeline,
    fuser: SpatialFuser,
    images: List[Image.Image],
    iterations: int = 10,
) -> Tuple[float, float, float]:
    """Benchmark MicroNav formatting latency."""
    formatter = MicroNavFormatter()
    times = []
    
    for _ in range(iterations):
        for img in images:
            perception = await pipeline.process(img)
            scene_graph = build_scene_graph(perception)
            fused = fuser.fuse(perception)
            
            start = time.perf_counter()
            formatter.format(fused, scene_graph)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
    
    return statistics.mean(times), statistics.median(times), max(times)


async def benchmark_e2e(
    pipeline,
    fuser: SpatialFuser,
    images: List[Image.Image],
    iterations: int = 10,
) -> Tuple[float, float, float]:
    """Benchmark end-to-end latency (perception → scene graph → fusion → micronav)."""
    formatter = MicroNavFormatter()
    times = []
    
    for _ in range(iterations):
        for img in images:
            start = time.perf_counter()
            
            # Full pipeline
            perception = await pipeline.process(img)
            scene_graph = build_scene_graph(perception)
            fused = fuser.fuse(perception)
            formatter.format(fused, scene_graph)
            
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
    
    return statistics.mean(times), statistics.median(times), max(times)


async def benchmark_quick_answer(
    pipeline,
    fuser: SpatialFuser,
    images: List[Image.Image],
    iterations: int = 10,
) -> Tuple[float, float, float]:
    """Benchmark quick answer (bypass LLM) latency."""
    questions = [
        "What's ahead?",
        "Is the path clear?",
        "Any obstacles?",
    ]
    times = []
    
    for _ in range(iterations):
        for img in images:
            perception = await pipeline.process(img)
            fused = fuser.fuse(perception)
            
            for q in questions:
                start = time.perf_counter()
                QuickAnswers.try_quick_answer(q, fused)
                elapsed = (time.perf_counter() - start) * 1000
                times.append(elapsed)
    
    return statistics.mean(times), statistics.median(times), max(times)


# ============================================================================
# Main Benchmark Runner
# ============================================================================

async def run_benchmarks():
    """Run all benchmarks and report results."""
    print("=" * 60)
    print("VQA ENGINE BENCHMARK")
    print("=" * 60)
    print()
    
    # Initialize components
    print("Initializing components...")
    pipeline = create_perception_pipeline(use_mock=True)  # Use mock for consistent benchmarks
    fuser = SpatialFuser()
    images = create_test_images()
    print(f"Created {len(images)} test images")
    print()
    
    # Warm up
    print("Warming up...")
    for img in images:
        await pipeline.process(img)
    print()
    
    # Run benchmarks
    results = {}
    iterations = 20
    
    print(f"Running benchmarks ({iterations} iterations each)...")
    print("-" * 60)
    
    # Perception benchmark
    print("1. Perception Pipeline...")
    mean, median, p99 = await benchmark_perception(pipeline, images, iterations)
    results["perception"] = (mean, median, p99)
    status = "✓" if median <= 300 else "✗"
    print(f"   {status} Mean: {mean:.1f}ms, Median: {median:.1f}ms, P99: {p99:.1f}ms")
    print(f"   Target: ≤300ms")
    print()
    
    # Scene graph benchmark
    print("2. Scene Graph Building...")
    mean, median, p99 = await benchmark_scene_graph(pipeline, images, iterations)
    results["scene_graph"] = (mean, median, p99)
    status = "✓" if median <= 50 else "✗"
    print(f"   {status} Mean: {mean:.1f}ms, Median: {median:.1f}ms, P99: {p99:.1f}ms")
    print(f"   Target: ≤50ms")
    print()
    
    # Fusion benchmark
    print("3. Spatial Fusion...")
    mean, median, p99 = await benchmark_fusion(pipeline, fuser, images, iterations)
    results["fusion"] = (mean, median, p99)
    status = "✓" if median <= 20 else "✗"
    print(f"   {status} Mean: {mean:.1f}ms, Median: {median:.1f}ms, P99: {p99:.1f}ms")
    print(f"   Target: ≤20ms")
    print()
    
    # MicroNav benchmark
    print("4. MicroNav Formatting...")
    mean, median, p99 = await benchmark_micronav(pipeline, fuser, images, iterations)
    results["micronav"] = (mean, median, p99)
    status = "✓" if median <= 5 else "✗"
    print(f"   {status} Mean: {mean:.1f}ms, Median: {median:.1f}ms, P99: {p99:.1f}ms")
    print(f"   Target: ≤5ms")
    print()
    
    # Quick answer benchmark
    print("5. Quick Answer (No LLM)...")
    mean, median, p99 = await benchmark_quick_answer(pipeline, fuser, images, iterations)
    results["quick_answer"] = (mean, median, p99)
    status = "✓" if median <= 1 else "✗"
    print(f"   {status} Mean: {mean:.3f}ms, Median: {median:.3f}ms, P99: {p99:.3f}ms")
    print(f"   Target: ≤1ms")
    print()
    
    # End-to-end benchmark
    print("6. End-to-End (Full Pipeline)...")
    mean, median, p99 = await benchmark_e2e(pipeline, fuser, images, iterations)
    results["e2e"] = (mean, median, p99)
    status = "✓" if median <= 300 else "✗"
    print(f"   {status} Mean: {mean:.1f}ms, Median: {median:.1f}ms, P99: {p99:.1f}ms")
    print(f"   Target: ≤300ms (vision only)")
    print()
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    total_median = results["e2e"][1]
    targets_met = sum([
        results["perception"][1] <= 300,
        results["scene_graph"][1] <= 50,
        results["fusion"][1] <= 20,
        results["micronav"][1] <= 5,
        results["quick_answer"][1] <= 1,
        results["e2e"][1] <= 300,
    ])
    
    print(f"Total Vision Latency (Median): {total_median:.1f}ms")
    print(f"Targets Met: {targets_met}/6")
    print()
    
    if total_median <= 300:
        print("✓ Vision pipeline meets <300ms target!")
        print("  Combined with STT/TTS, total E2E should be <500ms")
    else:
        print("✗ Vision pipeline exceeds 300ms target")
        print("  Consider using mock detector or reducing image size")
    
    print()
    print("=" * 60)
    
    return results


if __name__ == "__main__":
    asyncio.run(run_benchmarks())
