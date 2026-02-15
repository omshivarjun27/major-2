#!/usr/bin/env python3
"""
Deterministic 1000+ Scenario Test Generator
============================================

Generates concrete test cases from parametric templates using a deterministic
SHA-256 sampling strategy.  Each generated scenario has:

- A unique ID (e.g., ``DET-0042``)
- A human-readable title
- Acceptance criteria
- Reproduction steps
- Expected behaviour
- Required synthetic data spec

Usage::

    # Generate all scenarios (writes tests/generated_scenarios.json)
    python scripts/generate_scenarios.py

    # Generate a specific bucket only
    python scripts/generate_scenarios.py --bucket detection

    # Print stats only
    python scripts/generate_scenarios.py --stats
"""

from __future__ import annotations

import hashlib
import itertools
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

SEED = 42
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "tests", "generated_scenarios.json")

# ═══════════════════════════════════════════════════════════════════════
# Template Definitions (mirrors REMEDIATION_PLAN.json generator_algorithm)
# ═══════════════════════════════════════════════════════════════════════

TEMPLATES = [
    # ----------------------------------------------------------------
    # T-DETECT: Object detection under varying conditions
    # ----------------------------------------------------------------
    {
        "id": "T-DETECT",
        "prefix": "DET",
        "bucket": "Perception - Object Detection",
        "pattern": "Detect {object} at {distance}m in {lighting} with {occlusion} at {angle}°",
        "variables": {
            "object": [
                "person", "chair", "table", "car", "bicycle", "dog",
                "stroller", "bollard", "curb", "stairs", "door", "wall",
                "tree", "sign", "trash-bin", "fire-hydrant", "bench",
                "wheelchair", "scooter", "pole",
            ],
            "distance": [0.3, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 8.0],
            "lighting": [
                "bright-sun", "overcast", "indoor-fluorescent",
                "dim-indoor", "nighttime", "backlit",
            ],
            "occlusion": ["none", "partial-25pct", "partial-50pct", "heavy-75pct"],
            "angle": [0, 15, 30, 45, 60],
        },
        "target": 200,
        "acceptance": (
            "Detection confidence > 0.3 for {occlusion} != heavy-75pct, "
            "distance error < 0.5m, latency < 200ms"
        ),
        "data_spec": (
            "Synthetic: OpenCV-rendered scene, {object} at calibrated depth={distance}m, "
            "gamma adjusted for {lighting}, mask-based {occlusion}"
        ),
    },
    # ----------------------------------------------------------------
    # T-DEPTH: Depth estimation accuracy
    # ----------------------------------------------------------------
    {
        "id": "T-DEPTH",
        "prefix": "DEP",
        "bucket": "Perception - Depth Estimation",
        "pattern": "Estimate depth of {object} at {true_depth}m in {lighting} on {surface}",
        "variables": {
            "object": [
                "person", "car", "wall", "door", "stairs", "table",
                "bollard", "bench", "sign", "pole",
            ],
            "true_depth": [0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 8.0, 10.0],
            "lighting": ["bright", "dim", "backlit", "nighttime"],
            "surface": ["matte", "reflective", "transparent", "textured"],
        },
        "target": 90,
        "acceptance": "Depth error < 15% of true_depth for matte/textured, < 30% for reflective/transparent",
        "data_spec": "Synthetic: known-depth scene with {surface} material under {lighting}",
    },
    # ----------------------------------------------------------------
    # T-OCR: Text reading under varying conditions
    # ----------------------------------------------------------------
    {
        "id": "T-OCR",
        "prefix": "OCR",
        "bucket": "Text Reading (OCR)",
        "pattern": "Read {text_type} text in {language} on {surface} under {lighting} at {distance}m",
        "variables": {
            "text_type": ["printed", "handwritten", "digital-display", "embossed", "engraved"],
            "language": ["en", "es", "fr", "zh", "ar", "hi"],
            "surface": ["flat-paper", "curved-bottle", "metal-sign", "fabric", "screen", "braille-plate"],
            "lighting": ["bright", "dim", "glare", "shadow"],
            "distance": [0.2, 0.3, 0.5, 1.0],
        },
        "target": 110,
        "acceptance": "Character accuracy > 80% for printed, > 60% for handwritten; latency < 1500ms",
        "data_spec": "Synthetic: rendered text image with known content in {language} on {surface}",
    },
    # ----------------------------------------------------------------
    # T-STT: Speech-to-text under varying conditions
    # ----------------------------------------------------------------
    {
        "id": "T-STT",
        "prefix": "STT",
        "bucket": "Audio - STT/TTS",
        "pattern": "Recognize '{command}' spoken with {accent} accent in {noise} at {distance}m from mic",
        "variables": {
            "command": [
                "what is in front of me", "read this", "describe the scene",
                "where am I", "help me cross the street", "scan barcode",
            ],
            "accent": ["neutral-US", "British", "Indian", "Chinese", "Spanish", "African"],
            "noise": ["quiet", "moderate-street", "loud-crowd", "wind", "echo-indoor"],
            "distance": [0.3, 0.5, 1.0],
        },
        "target": 90,
        "acceptance": "WER < 20% for quiet/moderate, < 40% for loud; latency < 200ms",
        "data_spec": "Synthetic TTS audio + noise overlay at specified SNR",
    },
    # ----------------------------------------------------------------
    # T-FAILURE: Module failure modes
    # ----------------------------------------------------------------
    {
        "id": "T-FAILURE",
        "prefix": "MFM",
        "bucket": "Multimodal Failure Modes",
        "pattern": "{module} fails with {failure_type} while user is {activity}",
        "variables": {
            "module": [
                "camera", "STT", "TTS", "LLM", "detection", "depth",
                "OCR", "QR", "face", "memory",
            ],
            "failure_type": [
                "timeout", "crash", "OOM", "network-error",
                "corrupted-input", "permission-denied",
            ],
            "activity": [
                "walking", "standing", "crossing-street",
                "on-stairs", "in-elevator", "in-meeting",
            ],
        },
        "target": 100,
        "acceptance": "No process crash; user gets spoken safe fallback within 3s",
        "data_spec": "Simulated failure via mock/patch",
    },
    # ----------------------------------------------------------------
    # T-PRIVACY: Consent & data handling
    # ----------------------------------------------------------------
    {
        "id": "T-PRIVACY",
        "prefix": "PRV",
        "bucket": "Privacy & Consent",
        "pattern": "{feature} with consent={consent} and {data_action}",
        "variables": {
            "feature": ["face-detection", "memory-store", "raw-media-save", "embedding-persist", "cloud-sync"],
            "consent": ["granted", "not-granted", "revoked"],
            "data_action": ["store", "retrieve", "delete", "export"],
        },
        "target": 60,
        "acceptance": (
            "If consent=not-granted|revoked: no data stored, 403 or skip returned. "
            "If consent=granted: operation succeeds normally."
        ),
        "data_spec": "Unit test with mocked consent store",
    },
    # ----------------------------------------------------------------
    # T-NETWORK: Offline / partitioned scenarios
    # ----------------------------------------------------------------
    {
        "id": "T-NETWORK",
        "prefix": "NET",
        "bucket": "Network Partitioning / Offline Mode",
        "pattern": "{service} unreachable while user requests {action}",
        "variables": {
            "service": [
                "Deepgram-STT", "ElevenLabs-TTS", "Ollama-LLM",
                "LiveKit-server", "DuckDuckGo-search",
            ],
            "action": [
                "scene-describe", "read-text", "navigate",
                "search-internet", "remember",
            ],
        },
        "target": 80,
        "acceptance": "Failsafe spoken response within 3s; no hang or crash",
        "data_spec": "Mock: set service URL to down host",
    },
    # ----------------------------------------------------------------
    # T-HARDWARE: Resource constrained environments
    # ----------------------------------------------------------------
    {
        "id": "T-HARDWARE",
        "prefix": "HW",
        "bucket": "Hardware Constraints",
        "pattern": "Run {pipeline} on {device} with {memory}MB RAM and {cpu} cores",
        "variables": {
            "pipeline": ["detection-only", "detection+depth", "full-pipeline", "OCR-only", "STT+TTS-only"],
            "device": ["x86-desktop", "Raspberry-Pi-4", "Jetson-Nano", "Android-phone"],
            "memory": [512, 1024, 2048, 4096],
            "cpu": [1, 2, 4, 8],
        },
        "target": 60,
        "acceptance": "No OOM kill; latency < 2x baseline on reference hardware",
        "data_spec": "Docker container with cgroup memory + CPU limits",
    },
    # ----------------------------------------------------------------
    # T-MOBILITY: Real-world movement scenarios
    # ----------------------------------------------------------------
    {
        "id": "T-MOBILITY",
        "prefix": "MOB",
        "bucket": "Mobility Scenarios",
        "pattern": "User {action} in {environment} with {obstacle_density} obstacles",
        "variables": {
            "action": [
                "walking-forward", "descending-stairs", "ascending-stairs",
                "crossing-street", "entering-elevator", "boarding-bus",
                "navigating-crowd", "passing-doorway",
            ],
            "environment": [
                "indoor-office", "indoor-mall", "outdoor-sidewalk",
                "outdoor-park", "subway-station", "parking-lot",
            ],
            "obstacle_density": ["none", "sparse", "moderate", "dense"],
        },
        "target": 80,
        "acceptance": "Critical obstacles detected and announced before user reaches them",
        "data_spec": "Video sequence of scripted mobility scenario",
    },
    # ----------------------------------------------------------------
    # T-ACCESSIBLE: Accessibility-specific scenarios
    # ----------------------------------------------------------------
    {
        "id": "T-ACCESSIBLE",
        "prefix": "ACC",
        "bucket": "Accessibility-Specific",
        "pattern": "Identify {item} at {distance}m in {condition}",
        "variables": {
            "item": [
                "braille-sign", "tactile-paving", "low-contrast-sign",
                "traffic-light-color", "pedestrian-signal",
                "elevator-button", "currency-note", "medicine-label",
            ],
            "distance": [0.2, 0.5, 1.0, 2.0],
            "condition": ["good-lighting", "dim", "glare", "motion-blur", "partial-occlusion"],
        },
        "target": 60,
        "acceptance": "Correct identification or safe 'cannot determine' fallback",
        "data_spec": "Real or synthetic accessibility test images",
    },
    # ----------------------------------------------------------------
    # T-QR: QR/AR scanning scenarios
    # ----------------------------------------------------------------
    {
        "id": "T-QR",
        "prefix": "QR",
        "bucket": "QR/AR Scanning",
        "pattern": "Scan {code_type} containing {content_type} at {angle}° in {lighting}",
        "variables": {
            "code_type": ["QR-v1", "QR-v2", "DataMatrix", "AR-marker", "barcode-EAN13"],
            "content_type": ["URL", "WiFi-config", "vCard", "plain-text", "product-ID"],
            "angle": [0, 15, 30, 45],
            "lighting": ["bright", "dim", "glare"],
        },
        "target": 60,
        "acceptance": "Decode success rate > 90% at 0-30°; graceful error at 45°+",
        "data_spec": "Printed QR codes photographed at calibrated angles",
    },
    # ----------------------------------------------------------------
    # T-API: Integration / API scenarios
    # ----------------------------------------------------------------
    {
        "id": "T-API",
        "prefix": "API",
        "bucket": "Integration & API",
        "pattern": "{method} {endpoint} with {payload_state} while {system_state}",
        "variables": {
            "method": ["GET", "POST", "DELETE"],
            "endpoint": ["/health", "/vqa/analyze", "/memory/store", "/face/detect", "/qr/scan"],
            "payload_state": ["valid", "malformed", "oversized", "empty"],
            "system_state": ["healthy", "degraded-no-LLM", "degraded-no-OCR", "cold-start"],
        },
        "target": 60,
        "acceptance": "Correct HTTP status code, valid JSON body, no crash",
        "data_spec": "httpx client with crafted payloads",
    },
]


# ═══════════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Scenario:
    id: str
    title: str
    bucket: str
    template_id: str
    variables: Dict[str, Any]
    acceptance_criterion: str
    data_spec: str
    expected_behavior: str = ""
    reproduction_steps: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════
# Deterministic Sampler
# ═══════════════════════════════════════════════════════════════════════

def _hash_combo(template_id: str, combo_index: int, seed: int = SEED) -> int:
    """Deterministic hash for selecting combos."""
    raw = f"{template_id}:{combo_index}:{seed}".encode()
    return int(hashlib.sha256(raw).hexdigest(), 16)


def _sample_combos(template: dict) -> List[Dict[str, Any]]:
    """Deterministically sample exactly `target` combos from full cartesian product."""
    var_names = list(template["variables"].keys())
    var_values = [template["variables"][k] for k in var_names]

    all_combos = list(itertools.product(*var_values))
    target = template["target"]

    if len(all_combos) <= target:
        chosen = all_combos
    else:
        # Sort by deterministic hash, take first `target`
        scored = [
            (_hash_combo(template["id"], idx), combo)
            for idx, combo in enumerate(all_combos)
        ]
        scored.sort(key=lambda x: x[0])
        chosen = [combo for _, combo in scored[:target]]

    return [dict(zip(var_names, c)) for c in chosen]


def _format_pattern(pattern: str, variables: Dict[str, Any]) -> str:
    """Substitute variables into pattern string."""
    result = pattern
    for k, v in variables.items():
        result = result.replace(f"{{{k}}}", str(v))
    return result


def generate_all() -> List[Scenario]:
    """Generate all scenarios from all templates."""
    scenarios: List[Scenario] = []
    global_idx = 0

    for tmpl in TEMPLATES:
        combos = _sample_combos(tmpl)
        for combo in combos:
            global_idx += 1
            sid = f"{tmpl['prefix']}-{global_idx:04d}"
            title = _format_pattern(tmpl["pattern"], combo)

            acceptance = tmpl["acceptance"]
            if isinstance(acceptance, str):
                acceptance = _format_pattern(acceptance, combo)

            data_spec = _format_pattern(tmpl.get("data_spec", ""), combo)

            scenario = Scenario(
                id=sid,
                title=title,
                bucket=tmpl["bucket"],
                template_id=tmpl["id"],
                variables=combo,
                acceptance_criterion=acceptance,
                data_spec=data_spec,
                expected_behavior=f"System handles: {title}",
                reproduction_steps=[
                    f"Configure test with {json.dumps(combo)}",
                    "Submit synthetic input matching data_spec",
                    f"Assert acceptance: {acceptance}",
                ],
            )
            scenarios.append(scenario)

    return scenarios


# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate 1000+ test scenarios")
    parser.add_argument("--bucket", help="Generate only this bucket")
    parser.add_argument("--stats", action="store_true", help="Print stats only")
    parser.add_argument("--output", default=OUTPUT_PATH, help="Output file path")
    args = parser.parse_args()

    scenarios = generate_all()

    if args.bucket:
        scenarios = [s for s in scenarios if args.bucket.lower() in s.bucket.lower()]

    if args.stats:
        buckets: Dict[str, int] = {}
        for s in scenarios:
            buckets[s.bucket] = buckets.get(s.bucket, 0) + 1
        print(f"Total scenarios: {len(scenarios)}")
        print(f"Buckets ({len(buckets)}):")
        for b, c in sorted(buckets.items(), key=lambda x: -x[1]):
            print(f"  {c:>5d}  {b}")
        return

    # Serialize
    data = {
        "generated_at": "deterministic_seed_42",
        "total": len(scenarios),
        "scenarios": [asdict(s) for s in scenarios],
    }

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(data, f, indent=2, default=str)

    # Stats
    buckets: Dict[str, int] = {}
    for s in scenarios:
        buckets[s.bucket] = buckets.get(s.bucket, 0) + 1
    print(f"Generated {len(scenarios)} scenarios → {args.output}")
    for b, c in sorted(buckets.items(), key=lambda x: -x[1]):
        print(f"  {c:>5d}  {b}")


if __name__ == "__main__":
    main()
