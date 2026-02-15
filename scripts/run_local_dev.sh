#!/usr/bin/env bash
# ================================================================
# run_local_dev.sh — Start development server
# ================================================================
set -euo pipefail

echo "=== Voice-Vision Assistant — Local Dev ==="

# Activate venv if present
if [ -d ".venv" ]; then
  echo "Activating .venv..."
  source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate 2>/dev/null || true
fi

# Run dependency check (non-fatal)
echo "Running dependency check..."
python scripts/check_deps.py || echo "WARNING: Some dependencies missing (see above)"

echo ""
echo "Starting API server on :8000..."
uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

echo "Starting LiveKit agent..."
python app.py start &
AGENT_PID=$!

echo ""
echo "API server PID: $API_PID  (http://localhost:8000)"
echo "Agent PID: $AGENT_PID"
echo ""
echo "Press Ctrl+C to stop both."

trap "kill $API_PID $AGENT_PID 2>/dev/null; exit" INT TERM
wait
