# Load Testing Guide

This directory contains Locust load tests for the Voice-Vision Assistant.

## Prerequisites

```bash
pip install locust>=2.20.0
# or
pip install -r requirements-extras.txt
```

## Quick Start

### 1. Start the API Server

```bash
uvicorn apps.api.server:app --host 0.0.0.0 --port 8000
```

### 2. Run Load Tests

**Web UI Mode (Interactive):**
```bash
locust -f tests/load/locustfile.py --host=http://localhost:8000
```
Then open http://localhost:8089 in your browser.

**Headless Mode (CI):**
```bash
locust -f tests/load/locustfile.py \
    --host=http://localhost:8000 \
    --headless \
    -u 10 \
    -r 2 \
    -t 60s \
    --csv=results/load_test
```

## User Types

| User Type | Weight | Description | Wait Time |
|-----------|--------|-------------|-----------|
| VoiceUser | 3 | Voice interaction (STT -> LLM -> TTS) | 1-3s |
| VisionUser | 2 | Vision queries (Image -> VQA -> TTS) | 2-5s |
| MixedUser | 1 | Combination of voice and vision | 1-4s |

## SLA Targets

| Metric | Target |
|--------|--------|
| Hot Path Latency | < 500ms |
| STT Latency | < 100ms |
| LLM Latency | < 300ms |
| TTS Latency | < 100ms |
| Concurrent Users | 10 |
| SLA Pass Rate | >= 95% |

## Test Scenarios

### Baseline Test
Single user, verify system works:
```bash
locust -f tests/load/locustfile.py --host=http://localhost:8000 \
    --headless -u 1 -r 1 -t 30s
```

### Target Load Test
10 concurrent users (RTX 4060 target):
```bash
locust -f tests/load/locustfile.py --host=http://localhost:8000 \
    --headless -u 10 -r 2 -t 120s --csv=results/target_load
```

### Stress Test
15+ concurrent users to find breaking point:
```bash
locust -f tests/load/locustfile.py --host=http://localhost:8000 \
    --headless -u 20 -r 3 -t 180s --csv=results/stress_test
```

### Custom Shape Test
Uses StagesShape for ramping pattern:
```bash
locust -f tests/load/locustfile.py --host=http://localhost:8000 \
    --headless --csv=results/shape_test
```

## Output Files

When using `--csv=results/prefix`:
- `results/prefix_stats.csv` - Request statistics
- `results/prefix_stats_history.csv` - Time series data
- `results/prefix_failures.csv` - Failed requests
- `results/prefix_exceptions.csv` - Exceptions

## Interpreting Results

### Key Metrics

1. **Response Time (P95)**: 95th percentile should be < 500ms
2. **Requests/s**: Throughput under load
3. **Failure Rate**: Should be < 1%
4. **SLA Violation Rate**: Custom metric for > 500ms responses

### Example Good Result
```
Total Requests: 1000
SLA Violation Rate: 2.3%
Total Latency:
  Avg: 380ms
  P50: 350ms
  P95: 480ms
  P99: 520ms
```

### Example Bad Result
```
Total Requests: 500
SLA Violation Rate: 35.0%
Total Latency:
  Avg: 650ms
  P50: 580ms
  P95: 1200ms
  P99: 2500ms
```

## Troubleshooting

### High Latency
- Check if GPU is being used (CUDA available)
- Verify model is loaded and warm
- Check for memory pressure (VRAM < 8GB target)

### Connection Errors
- Verify API server is running
- Check firewall/network settings
- Verify correct host URL

### Inconsistent Results
- Run warmup iterations first
- Ensure no other processes are using GPU
- Check for thermal throttling

## CI Integration

Add to GitHub Actions:
```yaml
- name: Run Load Tests
  run: |
    pip install locust
    locust -f tests/load/locustfile.py \
      --host=http://localhost:8000 \
      --headless -u 5 -r 1 -t 60s \
      --csv=results/ci_load_test
```

## Mock Test Mode

Run without Locust (for development):
```bash
python tests/load/locustfile.py
```

This runs a simplified mock test to verify the test infrastructure works.
