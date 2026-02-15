#!/usr/bin/env bash
# ================================================================
# check_deps.sh  —  Verify all project dependencies
# ================================================================
# Returns non-zero exit code if critical dependencies are missing.
# Run: bash scripts/check_deps.sh
# ================================================================
set -uo pipefail

EXIT_CODE=0
WARNINGS=0

echo "=== Voice-Vision Assistant — Dependency Check ==="
echo ""

# ── Python version ───────────────────────────────────────────────
echo "--- Python ---"
if command -v python3 &>/dev/null; then
  PY_VER=$(python3 --version 2>&1)
  echo "  $PY_VER"
elif command -v python &>/dev/null; then
  PY_VER=$(python --version 2>&1)
  echo "  $PY_VER"
else
  echo "  ERROR: Python not found!"
  EXIT_CODE=1
fi

# ── Python packages from requirements.txt ────────────────────────
echo ""
echo "--- Python Packages (requirements.txt) ---"
PYTHON_CMD="python"
command -v python3 &>/dev/null && PYTHON_CMD="python3"

$PYTHON_CMD -c "
import sys, importlib, re

missing = []
with open('requirements.txt') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        # Extract package name
        pkg = re.split(r'[>=<\[!;]', line)[0].strip()
        if not pkg:
            continue
        # Normalise package name for import
        mod = pkg.replace('-', '_').lower()
        # Some packages have different import names
        aliases = {
            'python_dotenv': 'dotenv',
            'opencv_python': 'cv2',
            'pillow': 'PIL',
            'scikit_image': 'skimage',
            'pyzbar': 'pyzbar',
            'faiss_cpu': 'faiss',
            'livekit_agents': 'livekit.agents',
            'livekit_plugins_deepgram': 'livekit.plugins.deepgram',
            'livekit_plugins_openai': 'livekit.plugins.openai',
            'livekit_plugins_silero': 'livekit.plugins.silero',
            'livekit_plugins_elevenlabs': 'livekit.plugins.elevenlabs',
            'livekit_plugins_tavus': 'livekit.plugins.tavus',
            'livekit_api': 'livekit.api',
            'duckduckgo_search': 'duckduckgo_search',
            'langchain_community': 'langchain_community',
            'sentence_transformers': 'sentence_transformers',
            'qrcode': 'qrcode',
        }
        mod = aliases.get(mod, mod)
        try:
            importlib.import_module(mod.split('.')[0])
            print(f'  OK: {pkg}')
        except ImportError:
            print(f'  MISSING: {pkg}')
            missing.append(pkg)

if missing:
    print(f'\n  {len(missing)} package(s) missing. Run: pip install -r requirements.txt')
    sys.exit(1)
else:
    print('\n  All Python packages OK.')
" || { EXIT_CODE=1; }

# ── System binaries ──────────────────────────────────────────────
echo ""
echo "--- System Binaries ---"

check_binary() {
  local name="$1"
  local install_hint="$2"
  if command -v "$name" &>/dev/null; then
    echo "  OK: $name"
  else
    echo "  MISSING: $name — $install_hint"
    WARNINGS=$((WARNINGS + 1))
  fi
}

check_binary "tesseract" "apt install tesseract-ocr / brew install tesseract / choco install tesseract"
check_binary "ffmpeg" "apt install ffmpeg / brew install ffmpeg / choco install ffmpeg (optional, for audio)"

# ── OCR-specific checks ─────────────────────────────────────────
echo ""
echo "--- OCR Backends ---"
$PYTHON_CMD -c "
try:
    import easyocr
    print('  EasyOCR: OK')
except ImportError:
    print('  EasyOCR: NOT INSTALLED (pip install easyocr)')

try:
    import pytesseract
    pytesseract.get_tesseract_version()
    print('  pytesseract: OK (binary found)')
except Exception as e:
    print(f'  pytesseract: ISSUE ({e})')

try:
    import cv2
    print(f'  OpenCV: OK (v{cv2.__version__})')
except ImportError:
    print('  OpenCV: NOT INSTALLED (pip install opencv-python)')
"

# ── Summary ──────────────────────────────────────────────────────
echo ""
echo "=== Summary ==="
if [ $EXIT_CODE -ne 0 ]; then
  echo "FAIL: Critical dependencies missing. Fix the issues above."
elif [ $WARNINGS -gt 0 ]; then
  echo "WARN: $WARNINGS optional dependencies missing. Core features may work."
else
  echo "PASS: All dependencies satisfied."
fi

exit $EXIT_CODE
