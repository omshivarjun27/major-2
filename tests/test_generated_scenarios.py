"""
Parametrized pytest test suite driven by the 1000+ generated scenarios.

Run::

    # Generate scenarios first (one-time or after template changes)
    python scripts/generate_scenarios.py

    # Run all generated scenario tests
    pytest tests/test_generated_scenarios.py -v --tb=short

    # Run a specific bucket
    pytest tests/test_generated_scenarios.py -v -k "detection"
"""

from __future__ import annotations

import json
import pathlib
from typing import Any, Dict, List

import pytest

SCENARIOS_FILE = pathlib.Path(__file__).parent / "generated_scenarios.json"

# ---------------------------------------------------------------------------
# Load generated scenarios
# ---------------------------------------------------------------------------


def _load_scenarios() -> List[Dict[str, Any]]:
    if not SCENARIOS_FILE.exists():
        pytest.skip("Run 'python scripts/generate_scenarios.py' first")
    with open(SCENARIOS_FILE) as f:
        data = json.load(f)
    return data.get("scenarios", [])


_ALL_SCENARIOS = _load_scenarios() if SCENARIOS_FILE.exists() else []


def _ids():
    return [s["id"] for s in _ALL_SCENARIOS]


def _by_bucket(bucket_substr: str) -> List[Dict[str, Any]]:
    return [s for s in _ALL_SCENARIOS if bucket_substr.lower() in s["bucket"].lower()]


# ═══════════════════════════════════════════════════════════════════════
# Bucket: Object Detection (T-DETECT)
# ═══════════════════════════════════════════════════════════════════════

_DET = _by_bucket("Object Detection")


@pytest.mark.parametrize(
    "scenario",
    _DET,
    ids=[s["id"] for s in _DET],
)
def test_detection_scenario(scenario):
    """Validate detection scenario can be instantiated and has valid fields."""
    v = scenario["variables"]
    assert "object" in v
    assert isinstance(v["distance"], (int, float)) and v["distance"] > 0
    assert v["lighting"] in [
        "bright-sun", "overcast", "indoor-fluorescent",
        "dim-indoor", "nighttime", "backlit",
    ]
    assert "none" in v["occlusion"] or "pct" in v["occlusion"] or "partial" in v["occlusion"] or "heavy" in v["occlusion"]
    # Structural: acceptance criterion must mention confidence or latency
    ac = scenario["acceptance_criterion"]
    assert "confidence" in ac.lower() or "latency" in ac.lower() or "distance" in ac.lower()


# ═══════════════════════════════════════════════════════════════════════
# Bucket: Depth Estimation (T-DEPTH)
# ═══════════════════════════════════════════════════════════════════════

_DEP = _by_bucket("Depth Estimation")


@pytest.mark.parametrize(
    "scenario",
    _DEP,
    ids=[s["id"] for s in _DEP],
)
def test_depth_scenario(scenario):
    v = scenario["variables"]
    assert isinstance(v["true_depth"], (int, float)) and v["true_depth"] > 0
    assert v["surface"] in ["matte", "reflective", "transparent", "textured"]


# ═══════════════════════════════════════════════════════════════════════
# Bucket: OCR (T-OCR)
# ═══════════════════════════════════════════════════════════════════════

_OCR = _by_bucket("OCR")


@pytest.mark.parametrize(
    "scenario",
    _OCR,
    ids=[s["id"] for s in _OCR],
)
def test_ocr_scenario(scenario):
    v = scenario["variables"]
    assert v["language"] in ["en", "es", "fr", "zh", "ar", "hi"]
    assert v["text_type"] in ["printed", "handwritten", "digital-display", "embossed", "engraved"]


# ═══════════════════════════════════════════════════════════════════════
# Bucket: Failure Modes (T-FAILURE)
# ═══════════════════════════════════════════════════════════════════════

_FAIL = _by_bucket("Failure")


@pytest.mark.parametrize(
    "scenario",
    _FAIL,
    ids=[s["id"] for s in _FAIL],
)
def test_failure_scenario(scenario):
    v = scenario["variables"]
    assert v["module"] in [
        "camera", "STT", "TTS", "LLM", "detection", "depth",
        "OCR", "QR", "face", "memory",
    ]
    assert v["failure_type"] in [
        "timeout", "crash", "OOM", "network-error",
        "corrupted-input", "permission-denied",
    ]
    # Must have a safe fallback acceptance
    assert "crash" in scenario["acceptance_criterion"].lower() or "fallback" in scenario["acceptance_criterion"].lower()


# ═══════════════════════════════════════════════════════════════════════
# Bucket: Privacy (T-PRIVACY)
# ═══════════════════════════════════════════════════════════════════════

_PRV = _by_bucket("Privacy")


@pytest.mark.parametrize(
    "scenario",
    _PRV,
    ids=[s["id"] for s in _PRV],
)
def test_privacy_scenario(scenario):
    v = scenario["variables"]
    assert v["consent"] in ["granted", "not-granted", "revoked"]
    assert v["data_action"] in ["store", "retrieve", "delete", "export"]
    if v["consent"] in ("not-granted", "revoked"):
        assert "403" in scenario["acceptance_criterion"] or "skip" in scenario["acceptance_criterion"]


# ═══════════════════════════════════════════════════════════════════════
# Bucket: Network (T-NETWORK)
# ═══════════════════════════════════════════════════════════════════════

_NET = _by_bucket("Network")


@pytest.mark.parametrize(
    "scenario",
    _NET,
    ids=[s["id"] for s in _NET],
)
def test_network_scenario(scenario):
    v = scenario["variables"]
    assert isinstance(v["service"], str)
    assert isinstance(v["action"], str)
    assert "fallback" in scenario["acceptance_criterion"].lower() or "crash" in scenario["acceptance_criterion"].lower()


# ═══════════════════════════════════════════════════════════════════════
# Bucket: Hardware (T-HARDWARE)
# ═══════════════════════════════════════════════════════════════════════

_HW = _by_bucket("Hardware")


@pytest.mark.parametrize(
    "scenario",
    _HW,
    ids=[s["id"] for s in _HW],
)
def test_hardware_scenario(scenario):
    v = scenario["variables"]
    assert isinstance(v["memory"], (int, float)) and v["memory"] >= 512
    assert isinstance(v["cpu"], int) and v["cpu"] >= 1


# ═══════════════════════════════════════════════════════════════════════
# Bucket: Mobility (T-MOBILITY)
# ═══════════════════════════════════════════════════════════════════════

_MOB = _by_bucket("Mobility")


@pytest.mark.parametrize(
    "scenario",
    _MOB,
    ids=[s["id"] for s in _MOB],
)
def test_mobility_scenario(scenario):
    v = scenario["variables"]
    assert v["obstacle_density"] in ["none", "sparse", "moderate", "dense"]
    assert isinstance(v["environment"], str)


# ═══════════════════════════════════════════════════════════════════════
# Bucket: Accessibility (T-ACCESSIBLE)
# ═══════════════════════════════════════════════════════════════════════

_ACC = _by_bucket("Accessibility")


@pytest.mark.parametrize(
    "scenario",
    _ACC,
    ids=[s["id"] for s in _ACC],
)
def test_accessibility_scenario(scenario):
    v = scenario["variables"]
    assert isinstance(v["item"], str)
    assert isinstance(v["distance"], (int, float))


# ═══════════════════════════════════════════════════════════════════════
# Bucket: QR (T-QR)
# ═══════════════════════════════════════════════════════════════════════

_QR = _by_bucket("QR")


@pytest.mark.parametrize(
    "scenario",
    _QR,
    ids=[s["id"] for s in _QR],
)
def test_qr_scenario(scenario):
    v = scenario["variables"]
    assert v["code_type"] in ["QR-v1", "QR-v2", "DataMatrix", "AR-marker", "barcode-EAN13"]
    assert isinstance(v["angle"], (int, float))


# ═══════════════════════════════════════════════════════════════════════
# Bucket: API (T-API)
# ═══════════════════════════════════════════════════════════════════════

_API = _by_bucket("API")


@pytest.mark.parametrize(
    "scenario",
    _API,
    ids=[s["id"] for s in _API],
)
def test_api_scenario(scenario):
    v = scenario["variables"]
    assert v["method"] in ["GET", "POST", "DELETE"]
    assert v["endpoint"].startswith("/")
    assert v["payload_state"] in ["valid", "malformed", "oversized", "empty"]
    assert "status" in scenario["acceptance_criterion"].lower() or "json" in scenario["acceptance_criterion"].lower() or "crash" in scenario["acceptance_criterion"].lower()


# ═══════════════════════════════════════════════════════════════════════
# Bucket: STT (T-STT)
# ═══════════════════════════════════════════════════════════════════════

_STT = _by_bucket("STT")


@pytest.mark.parametrize(
    "scenario",
    _STT,
    ids=[s["id"] for s in _STT],
)
def test_stt_scenario(scenario):
    v = scenario["variables"]
    assert isinstance(v["command"], str)
    assert isinstance(v["accent"], str)
    assert isinstance(v["noise"], str)


# ═══════════════════════════════════════════════════════════════════════
# Meta-test: minimum scenario count
# ═══════════════════════════════════════════════════════════════════════


def test_minimum_scenario_count():
    """Guarantee we have at least 990 synthesised scenarios."""
    assert len(_ALL_SCENARIOS) >= 990, (
        f"Expected >=990 scenarios, got {len(_ALL_SCENARIOS)}. "
        f"Run 'python scripts/generate_scenarios.py' to regenerate."
    )
