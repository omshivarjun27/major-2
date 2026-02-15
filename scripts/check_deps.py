#!/usr/bin/env python3
"""
check_deps.py — Python dependency checker
==========================================

Verifies Python packages and system binaries.
Returns non-zero exit code on critical failures.

Usage:  python scripts/check_deps.py
"""

import importlib
import os
import platform
import re
import shutil
import sys
from pathlib import Path


def check_python_packages(req_path: str = "requirements.txt") -> list:
    """Check all packages from requirements.txt."""
    missing = []
    if not Path(req_path).exists():
        print(f"  WARNING: {req_path} not found")
        return missing

    IMPORT_ALIASES = {
        "python-dotenv": "dotenv",
        "opencv-python": "cv2",
        "pillow": "PIL",
        "scikit-image": "skimage",
        "faiss-cpu": "faiss",
        "livekit-agents": "livekit.agents",
        "livekit-plugins-deepgram": "livekit.plugins.deepgram",
        "livekit-plugins-openai": "livekit.plugins.openai",
        "livekit-plugins-silero": "livekit.plugins.silero",
        "livekit-plugins-elevenlabs": "livekit.plugins.elevenlabs",
        "livekit-plugins-tavus": "livekit.plugins.tavus",
        "livekit-api": "livekit.api",
        "livekit": "livekit",
        "duckduckgo-search": "duckduckgo_search",
        "langchain-community": "langchain_community",
        "sentence-transformers": "sentence_transformers",
        "qrcode": "qrcode",
    }

    with open(req_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            pkg = re.split(r"[>=<\[!;]", line)[0].strip()
            if not pkg:
                continue
            mod = IMPORT_ALIASES.get(pkg, pkg.replace("-", "_"))
            try:
                importlib.import_module(mod.split(".")[0])
                print(f"  OK: {pkg}")
            except ImportError:
                print(f"  MISSING: {pkg}")
                missing.append(pkg)

    return missing


def check_system_binaries() -> list:
    """Check for required system binaries."""
    missing = []
    os_name = platform.system().lower()

    binaries = {
        "tesseract": {
            "linux": "sudo apt install tesseract-ocr",
            "darwin": "brew install tesseract",
            "windows": "choco install tesseract",
        },
    }

    for name, hints in binaries.items():
        if shutil.which(name):
            print(f"  OK: {name}")
        else:
            hint = hints.get(os_name, f"Install {name} for your platform")
            print(f"  MISSING: {name} — {hint}")
            missing.append(name)

    return missing


def check_ocr_backends() -> dict:
    """Check OCR backend availability."""
    status = {}

    try:
        import easyocr
        status["easyocr"] = True
        print("  EasyOCR: OK")
    except ImportError:
        status["easyocr"] = False
        print("  EasyOCR: NOT INSTALLED")

    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        status["pytesseract"] = True
        print("  pytesseract: OK")
    except Exception as e:
        status["pytesseract"] = False
        print(f"  pytesseract: ISSUE ({e})")

    try:
        import cv2
        status["opencv"] = True
        print(f"  OpenCV: OK (v{cv2.__version__})")
    except ImportError:
        status["opencv"] = False
        print("  OpenCV: NOT INSTALLED")

    return status


def main():
    exit_code = 0

    print("=== Voice-Vision Assistant — Dependency Check (Python) ===\n")

    print(f"Python: {sys.version}")
    print(f"Platform: {platform.system()} {platform.release()}\n")

    print("--- Python Packages ---")
    missing_pkgs = check_python_packages()
    if missing_pkgs:
        print(f"\n  {len(missing_pkgs)} package(s) missing: {', '.join(missing_pkgs)}")
        print("  Run: pip install -r requirements.txt")
        exit_code = 1
    else:
        print("\n  All packages OK.")

    print("\n--- System Binaries ---")
    missing_bins = check_system_binaries()
    if missing_bins:
        print(f"\n  {len(missing_bins)} binary(ies) missing")

    print("\n--- OCR Backends ---")
    ocr = check_ocr_backends()

    print("\n=== Summary ===")
    if exit_code:
        print("FAIL: Critical dependencies missing.")
    elif missing_bins:
        print(f"WARN: {len(missing_bins)} optional binary(ies) missing.")
    else:
        print("PASS: All dependencies satisfied.")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
