"""
Scenario Generator — Create synthetic test scenarios.

Generates JSON scenario files for the repro harness.
Supports multiple categories: spatial navigation, face recognition,
OCR, audio events, and VQA queries.

Usage::

    python repro/scenario_generator.py --count 100 --output scenarios/
"""

from __future__ import annotations

import json
import os
import random
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List

# Ensure project root importable
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


# ── Object categories for spatial scenarios ──────────────────────────
OBJECT_CATEGORIES = [
    "person", "bicycle", "car", "motorcycle", "bus", "truck",
    "traffic light", "stop sign", "bench", "chair", "table",
    "dog", "cat", "door", "stairs", "curb", "pole",
    "tree", "fire hydrant", "parking meter",
]

# ── Sound event categories ──────────────────────────────────────────
SOUND_EVENTS = [
    "car_horn", "siren", "dog_bark", "speech", "music",
    "construction", "traffic", "bird_song", "door_slam",
    "glass_break", "footsteps", "alarm",
]

# ── VQA question templates ──────────────────────────────────────────
VQA_TEMPLATES = [
    "What is in front of me?",
    "Is there a {object} nearby?",
    "How far is the closest obstacle?",
    "What color is the {object}?",
    "Can you read the sign?",
    "Is it safe to cross the street?",
    "What time does the clock show?",
    "Describe the scene around me.",
]


def generate_spatial_scenario(idx: int, seed: int) -> Dict[str, Any]:
    """Generate a spatial navigation scenario with random obstacles."""
    rng = random.Random(seed + idx)
    num_frames = rng.randint(3, 10)
    num_objects = rng.randint(1, 5)

    frames = []
    expected = []
    for fi in range(num_frames):
        frame_objects = []
        for _ in range(num_objects):
            obj = {
                "category": rng.choice(OBJECT_CATEGORIES),
                "confidence": round(rng.uniform(0.5, 0.99), 2),
                "bbox": [
                    rng.randint(0, 400), rng.randint(0, 300),
                    rng.randint(50, 200), rng.randint(50, 200),
                ],
                "distance_m": round(rng.uniform(0.5, 10.0), 1),
                "zone": rng.choice(["left", "center", "right"]),
            }
            frame_objects.append(obj)

        frames.append({
            "index": fi,
            "width": 640,
            "height": 480,
            "objects": frame_objects,
        })
        expected.append({
            "frame_idx": fi,
            "detection_count": len(frame_objects),
            "has_critical": any(o["distance_m"] < 1.0 for o in frame_objects),
        })

    return {
        "id": f"spatial_{idx:05d}",
        "name": f"Spatial Navigation #{idx}",
        "category": "spatial",
        "seed": seed + idx,
        "frame_count": num_frames,
        "frames": frames,
        "expected_detections": expected,
    }


def generate_face_scenario(idx: int, seed: int) -> Dict[str, Any]:
    """Generate a face recognition scenario."""
    rng = random.Random(seed + idx + 10000)
    num_faces = rng.randint(1, 3)

    frames = [{
        "index": 0,
        "width": 640,
        "height": 480,
        "faces": [
            {
                "bbox": [rng.randint(50, 400), rng.randint(50, 300), 100, 100],
                "confidence": round(rng.uniform(0.7, 0.99), 2),
                "name": f"Person_{rng.randint(1, 20)}",
                "consent": True,
            }
            for _ in range(num_faces)
        ],
    }]

    return {
        "id": f"face_{idx:05d}",
        "name": f"Face Recognition #{idx}",
        "category": "face",
        "seed": seed + idx + 10000,
        "frame_count": 1,
        "frames": frames,
        "expected_detections": [{"frame_idx": 0, "face_count": num_faces}],
    }


def generate_vqa_scenario(idx: int, seed: int) -> Dict[str, Any]:
    """Generate a VQA query scenario."""
    rng = random.Random(seed + idx + 20000)
    template = rng.choice(VQA_TEMPLATES)
    obj = rng.choice(OBJECT_CATEGORIES)
    question = template.replace("{object}", obj)

    return {
        "id": f"vqa_{idx:05d}",
        "name": f"VQA Query #{idx}",
        "category": "vqa",
        "seed": seed + idx + 20000,
        "frame_count": 1,
        "frames": [{"index": 0, "width": 640, "height": 480}],
        "question": question,
        "expected_detections": [{"frame_idx": 0, "question": question}],
    }


def generate_scenarios(
    count: int = 100,
    seed: int = 42,
    categories: List[str] | None = None,
) -> List[Dict[str, Any]]:
    """Generate a batch of synthetic scenarios.

    Args:
        count: Total number of scenarios to generate.
        seed: Random seed for reproducibility.
        categories: List of categories to include. Default: all.

    Returns:
        List of scenario dicts.
    """
    if categories is None:
        categories = ["spatial", "face", "vqa"]

    generators = {
        "spatial": generate_spatial_scenario,
        "face": generate_face_scenario,
        "vqa": generate_vqa_scenario,
    }

    rng = random.Random(seed)
    scenarios = []
    per_cat = count // len(categories)

    for cat in categories:
        gen = generators.get(cat)
        if gen is None:
            continue
        for i in range(per_cat):
            scenarios.append(gen(i, seed))

    # Fill remaining with random categories
    while len(scenarios) < count:
        cat = rng.choice(categories)
        gen = generators[cat]
        scenarios.append(gen(len(scenarios), seed))

    return scenarios


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate synthetic test scenarios")
    parser.add_argument("--count", type=int, default=100, help="Number of scenarios")
    parser.add_argument("--output", type=str, default="scenarios/", help="Output directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--single-file", action="store_true",
                        help="Write all scenarios to one file instead of individual files")
    args = parser.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    scenarios = generate_scenarios(count=args.count, seed=args.seed)

    if args.single_file:
        manifest_path = out / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump({"scenarios": scenarios, "count": len(scenarios)}, f, indent=2)
        print(f"Generated {len(scenarios)} scenarios → {manifest_path}")
    else:
        for scenario in scenarios:
            path = out / f"{scenario['id']}.json"
            with open(path, "w") as f:
                json.dump(scenario, f, indent=2)
        print(f"Generated {len(scenarios)} scenario files → {out}/")

    # Also write a manifest index
    manifest = {
        "total": len(scenarios),
        "seed": args.seed,
        "categories": {},
    }
    for s in scenarios:
        cat = s.get("category", "unknown")
        manifest["categories"][cat] = manifest["categories"].get(cat, 0) + 1

    with open(out / "manifest_index.json", "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Category breakdown: {manifest['categories']}")


if __name__ == "__main__":
    main()
