#!/usr/bin/env bash
# Load test runner script for Voice-Vision Assistant
#
# Usage:
#   ./scripts/run_load_test.sh [mode] [users] [duration]
#
# Modes:
#   baseline  - Single user test (default)
#   target    - 10 concurrent users (RTX 4060 target)
#   stress    - 20 concurrent users
#   custom    - Use provided users/duration

set -e

MODE="${1:-baseline}"
USERS="${2:-1}"
DURATION="${3:-30s}"
HOST="${HOST:-http://localhost:8000}"
OUTPUT_DIR="results/load_tests"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Set parameters based on mode
case "$MODE" in
    baseline)
        USERS=1
        SPAWN_RATE=1
        DURATION="30s"
        ;;
    target)
        USERS=10
        SPAWN_RATE=2
        DURATION="120s"
        ;;
    stress)
        USERS=20
        SPAWN_RATE=3
        DURATION="180s"
        ;;
    custom)
        SPAWN_RATE=2
        ;;
    *)
        echo "Unknown mode: $MODE"
        echo "Available modes: baseline, target, stress, custom"
        exit 1
        ;;
esac

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
CSV_PREFIX="$OUTPUT_DIR/${MODE}_${TIMESTAMP}"

echo "=================================================="
echo "LOAD TEST: $MODE"
echo "=================================================="
echo "Host:       $HOST"
echo "Users:      $USERS"
echo "Spawn Rate: $SPAWN_RATE"
echo "Duration:   $DURATION"
echo "Output:     $CSV_PREFIX"
echo "=================================================="

# Check if locust is installed
if ! command -v locust &> /dev/null; then
    echo "Locust not found. Installing..."
    pip install locust>=2.20.0
fi

# Run locust
locust -f tests/load/locustfile.py \
    --host="$HOST" \
    --headless \
    -u "$USERS" \
    -r "$SPAWN_RATE" \
    -t "$DURATION" \
    --csv="$CSV_PREFIX"

echo ""
echo "=================================================="
echo "LOAD TEST COMPLETE"
echo "=================================================="
echo "Results saved to: $CSV_PREFIX*.csv"

# Print summary if stats file exists
if [ -f "${CSV_PREFIX}_stats.csv" ]; then
    echo ""
    echo "Quick Summary:"
    tail -1 "${CSV_PREFIX}_stats.csv"
fi
