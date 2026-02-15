#!/usr/bin/env python3
"""
Download ML models for spatial perception.

Usage:
    python scripts/download_models.py

Downloads:
    - YOLOv8n ONNX model (~12 MB) for object detection
      (exported from .pt via ultralytics; auto-installed if missing)
    - MiDaS v2.1 small ONNX model (~64 MB) for depth estimation

After download, set these environment variables:
    SPATIAL_USE_YOLO=true
    YOLO_MODEL_PATH=models/yolov8n.onnx
    SPATIAL_USE_MIDAS=true
    MIDAS_MODEL_PATH=models/midas_v21_small_256.onnx
"""

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models")

# ──────────────────────────────────────────────────────────────
# MiDaS v2.1 small — direct ONNX download from GitHub release
# ──────────────────────────────────────────────────────────────
MIDAS_URL = "https://github.com/isl-org/MiDaS/releases/download/v2_1/model-small.onnx"
MIDAS_DEST_NAME = "midas_v21_small_256.onnx"

# ──────────────────────────────────────────────────────────────
# YOLOv8n — no pre-built ONNX in ultralytics releases.
# We download the .pt weights and export to ONNX via ultralytics.
# ──────────────────────────────────────────────────────────────
YOLO_PT_URL = "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.pt"
YOLO_DEST_NAME = "yolov8n.onnx"

# ── SHA-256 checksums (None = skip verification — populate
#    after first successful download of known-good models) ────
MODEL_CHECKSUMS: dict[str, str | None] = {
    # Populated after first verified download; set to None to skip.
    MIDAS_DEST_NAME: None,
    YOLO_DEST_NAME: None,
}


def _sha256(path: str) -> str:
    """Compute SHA-256 hex digest of file at *path*."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _verify_checksum(path: str, name: str) -> bool:
    """Verify downloaded file against known checksum.

    Returns True if checksum matches or no checksum is registered.
    Prints the actual hash for future reference.
    """
    actual = _sha256(path)
    expected = MODEL_CHECKSUMS.get(name)
    print(f"    SHA-256: {actual}")
    if expected is None:
        print("    (no checksum registered — save the hash above for future verification)")
        return True
    if actual != expected:
        print(f"    CHECKSUM MISMATCH!  Expected: {expected}")
        print("    The downloaded file may be corrupted or tampered with.")
        os.remove(path)
        return False
    print("    Checksum verified ✓")
    return True


def _download(url: str, dest: str) -> None:
    """Download *url* to *dest* with progress indicator."""
    print(f"    URL : {url}")
    print(f"    Dest: {dest}")
    urllib.request.urlretrieve(url, dest)
    size_mb = os.path.getsize(dest) / (1024 * 1024)
    print(f"    OK ({size_mb:.1f} MB)")


def _ensure_package(pkg: str, pip_name: str | None = None) -> None:
    """Import *pkg*; if missing, pip-install *pip_name* into current env."""
    try:
        __import__(pkg)
    except ImportError:
        install = pip_name or pkg
        print(f"    Installing '{install}' (needed for ONNX export) ...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", install, "--quiet"],
        )


# ── MiDaS ────────────────────────────────────────────────────
def download_midas(model_dir: str) -> bool:
    dest = os.path.join(model_dir, MIDAS_DEST_NAME)
    if os.path.exists(dest):
        size_mb = os.path.getsize(dest) / (1024 * 1024)
        print(f"  [skip] {MIDAS_DEST_NAME} already exists ({size_mb:.1f} MB)")
        return True

    print(f"  Downloading {MIDAS_DEST_NAME} ...")
    print("    MiDaS v2.1 small — monocular depth estimation (~64 MB)")
    try:
        _download(MIDAS_URL, dest)
        if not _verify_checksum(dest, MIDAS_DEST_NAME):
            return False
        return True
    except Exception as e:
        print(f"    ERROR: {e}")
        return False


# ── YOLO ─────────────────────────────────────────────────────
def download_yolo(model_dir: str) -> bool:
    dest = os.path.join(model_dir, YOLO_DEST_NAME)
    if os.path.exists(dest):
        size_mb = os.path.getsize(dest) / (1024 * 1024)
        print(f"  [skip] {YOLO_DEST_NAME} already exists ({size_mb:.1f} MB)")
        return True

    print(f"  Preparing {YOLO_DEST_NAME} ...")
    print("    YOLOv8 nano — fast object detection (~12 MB ONNX)")
    print("    Step 1/2: downloading yolov8n.pt weights …")

    # -- download .pt -------------------------------------------------
    pt_path = os.path.join(model_dir, "yolov8n.pt")
    try:
        _download(YOLO_PT_URL, pt_path)
    except Exception as e:
        print(f"    ERROR downloading .pt: {e}")
        return False

    # -- export to ONNX via ultralytics --------------------------------
    print("    Step 2/2: exporting to ONNX …")
    try:
        _ensure_package("ultralytics")
        _ensure_package("onnx")
        from ultralytics import YOLO  # noqa: E402

        model = YOLO(pt_path)
        exported = model.export(format="onnx", imgsz=640, simplify=True)
        # ultralytics writes the onnx next to the .pt file
        exported_path = str(exported)
        if os.path.isfile(exported_path) and exported_path != dest:
            shutil.move(exported_path, dest)
        elif not os.path.isfile(dest):
            # fallback: look for yolov8n.onnx next to the .pt
            candidate = pt_path.replace(".pt", ".onnx")
            if os.path.isfile(candidate):
                shutil.move(candidate, dest)

        if os.path.isfile(dest):
            size_mb = os.path.getsize(dest) / (1024 * 1024)
            print(f"    Exported OK ({size_mb:.1f} MB)")
            if not _verify_checksum(dest, YOLO_DEST_NAME):
                return False
        else:
            print("    ERROR: ONNX file not created — check ultralytics output.")
            return False
    except Exception as e:
        print(f"    ERROR during ONNX export: {e}")
        print("    Tip: pip install ultralytics onnx")
        return False
    finally:
        # clean up .pt weights
        if os.path.isfile(pt_path):
            os.remove(pt_path)

    return True


# ── main ─────────────────────────────────────────────────────
def download_models():
    os.makedirs(MODEL_DIR, exist_ok=True)
    print(f"Model directory: {os.path.abspath(MODEL_DIR)}\n")

    ok_midas = download_midas(MODEL_DIR)
    ok_yolo = download_yolo(MODEL_DIR)

    print("\n" + "=" * 60)
    if ok_midas and ok_yolo:
        print("All models ready.  Add to .env:\n")
        print("SPATIAL_USE_YOLO=true")
        print("SPATIAL_USE_MIDAS=true")
        print(f"YOLO_MODEL_PATH=models/{YOLO_DEST_NAME}")
        print(f"MIDAS_MODEL_PATH=models/{MIDAS_DEST_NAME}")
    else:
        print("Some models FAILED — see errors above.")
        if not ok_yolo:
            print("  -> YOLO:  pip install ultralytics onnx  then re-run")
        if not ok_midas:
            print(f"  -> MiDaS: manually download {MIDAS_URL}")
    print("=" * 60)


if __name__ == "__main__":
    download_models()
