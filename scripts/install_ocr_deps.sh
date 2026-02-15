#!/usr/bin/env bash
# ================================================================
# install_ocr_deps.sh  —  Install OCR dependencies
# ================================================================
# Run: bash scripts/install_ocr_deps.sh
#
# Installs:
#   1. Python packages: easyocr, pytesseract, Pillow, opencv-python
#   2. System binary: tesseract-ocr (platform-detected)
#   3. Optional: torch (CPU by default, GPU if --gpu flag)
# ================================================================
set -euo pipefail

echo "=== OCR Dependency Installer ==="

# ── Detect OS ────────────────────────────────────────────────────
OS="$(uname -s)"
case "$OS" in
  Linux*)   PLATFORM="linux" ;;
  Darwin*)  PLATFORM="macos" ;;
  MINGW*|MSYS*|CYGWIN*) PLATFORM="windows" ;;
  *)        PLATFORM="unknown" ;;
esac
echo "Detected platform: $PLATFORM"

# ── Install system Tesseract binary ──────────────────────────────
install_tesseract() {
  echo "--- Installing Tesseract OCR binary ---"
  case "$PLATFORM" in
    linux)
      if command -v apt-get &>/dev/null; then
        sudo apt-get update && sudo apt-get install -y tesseract-ocr libtesseract-dev
      elif command -v yum &>/dev/null; then
        sudo yum install -y tesseract
      elif command -v pacman &>/dev/null; then
        sudo pacman -S tesseract
      else
        echo "WARNING: Cannot detect package manager. Install tesseract manually."
      fi
      ;;
    macos)
      if command -v brew &>/dev/null; then
        brew install tesseract
      else
        echo "WARNING: Homebrew not found. Install with: brew install tesseract"
      fi
      ;;
    windows)
      if command -v choco &>/dev/null; then
        choco install tesseract -y
      else
        echo "WARNING: Chocolatey not found."
        echo "Download Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki"
        echo "After install, add tesseract to your PATH."
      fi
      ;;
    *)
      echo "WARNING: Unknown platform. Install tesseract manually."
      ;;
  esac
}

# ── Check if tesseract is already installed ──────────────────────
if command -v tesseract &>/dev/null; then
  echo "Tesseract already installed: $(tesseract --version 2>&1 | head -1)"
else
  install_tesseract
fi

# ── Install Python packages ──────────────────────────────────────
echo ""
echo "--- Installing Python OCR packages ---"
pip install --upgrade pip

# Core OCR packages
pip install pytesseract Pillow opencv-python

# EasyOCR (larger download, includes torch dependency)
GPU_FLAG="${1:-}"
if [ "$GPU_FLAG" = "--gpu" ]; then
  echo "Installing EasyOCR with GPU (CUDA) support..."
  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
  pip install easyocr
else
  echo "Installing EasyOCR with CPU support..."
  pip install easyocr
fi

# ── Verify ───────────────────────────────────────────────────────
echo ""
echo "=== Verification ==="
python -c "import pytesseract; print('pytesseract: OK')" 2>/dev/null || echo "pytesseract: FAILED"
python -c "import easyocr; print('easyocr: OK')" 2>/dev/null || echo "easyocr: FAILED"
python -c "import cv2; print('opencv: OK')" 2>/dev/null || echo "opencv: FAILED"
python -c "import PIL; print('Pillow: OK')" 2>/dev/null || echo "Pillow: FAILED"

if command -v tesseract &>/dev/null; then
  echo "tesseract binary: OK ($(tesseract --version 2>&1 | head -1))"
else
  echo "tesseract binary: NOT FOUND — some OCR features will be unavailable"
fi

echo ""
echo "=== Done ==="
