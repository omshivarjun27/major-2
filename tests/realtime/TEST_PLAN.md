# Spatial Perception Testing Methodology

## Overview

This document outlines the comprehensive testing methodology for validating the spatial perception pipeline's accuracy, reliability, and safety for blind navigation assistance.

---

## 1. Staged Testing Protocol

### Stage 1: Desk Testing (Controlled Environment)

**Environment Setup:**
- Controlled indoor space (desk/table area)
- Known objects at measured distances (0.3m - 2m)
- Consistent lighting conditions
- Static camera position

**Test Objects:**
| Object | Distance | Expected Detection |
|--------|----------|-------------------|
| Coffee mug | 0.5m | Person/Object |
| Laptop | 0.8m | Object |
| Chair | 1.5m | Chair |
| Person (standing) | 2.0m | Person |

**Acceptance Criteria:**
- [ ] Detection rate ≥ 90% for objects within 2m
- [ ] Distance estimation error < 30% at each distance
- [ ] Latency < 500ms per frame
- [ ] No crashes over 100 consecutive frames

**Commands:**
```bash
# Run desk test with mock detector
python tests/realtime/realtime_test.py --debug --benchmark --log-session

# Run desk test with YOLO
python tests/realtime/realtime_test.py --detector yolo --debug --benchmark
```

---

### Stage 2: Indoor Navigation Testing

**Environment Setup:**
- Hallway or room with obstacles
- Multiple object types at varying distances (0.5m - 5m)
- Normal indoor lighting with some shadows
- Moving camera (handheld or mounted)

**Test Scenarios:**
1. **Clear path**: Open hallway with no obstacles
2. **Single obstacle**: One object blocking path
3. **Multiple obstacles**: 2-3 objects at different depths
4. **Door approach**: Navigate toward doorway
5. **Corner navigation**: Turn around corners

**Measurements:**
| Metric | Target | Method |
|--------|--------|--------|
| Detection accuracy | ≥ 85% | Manual verification |
| False positive rate | < 15% | Count spurious detections |
| Distance accuracy | ±0.5m | Tape measure validation |
| Cue latency | < 500ms | Telemetry logging |
| Cue consistency | < 20% flicker | Count cue changes/second |

**Commands:**
```bash
# Full indoor test with logging
python tests/realtime/realtime_test.py --detector yolo --depth simple \
    --debug --log-session --log-dir logs/indoor_test

# Review session
python tests/realtime/replay_tool.py logs/indoor_test/SESSION_NAME
```

---

### Stage 3: Outdoor Testing

**Environment Setup:**
- Outdoor space (sidewalk, park, parking lot)
- Variable lighting conditions
- Weather considerations (sunny, cloudy, shade)
- Moving obstacles (pedestrians, vehicles)

**Test Scenarios:**
1. **Sunny conditions**: Bright light with shadows
2. **Overcast**: Diffuse lighting
3. **Shaded areas**: Transition between light/dark
4. **Pedestrian avoidance**: Moving people
5. **Urban obstacles**: Signs, poles, benches

**Special Considerations:**
- Higher false positive tolerance outdoors
- Larger distance ranges (up to 10m)
- Moving obstacle tracking

**Commands:**
```bash
# Outdoor test with full pipeline
python tests/realtime/realtime_test.py --detector yolo --depth midas \
    --debug --log-session --log-dir logs/outdoor_test
```

---

## 2. Metrics Collection Schema

### Frame-Level Metrics

```json
{
    "frame_id": 1234,
    "timestamp": 1699999999.123,
    "latency_ms": 45.2,
    "fps": 22.1,
    
    "detection": {
        "count": 3,
        "classes": ["person", "chair", "table"],
        "confidences": [0.92, 0.85, 0.78]
    },
    
    "depth": {
        "min_distance_m": 0.8,
        "mean_distance_m": 2.3,
        "estimator": "simple"
    },
    
    "navigation": {
        "cue": "Person ahead, 1 meter",
        "has_critical": true,
        "priority": "CRITICAL"
    },
    
    "system": {
        "memory_mb": 512.3,
        "cpu_percent": 45.0
    }
}
```

### Session Summary Metrics

```json
{
    "session_id": "test_20241201_143022",
    "duration_seconds": 300.0,
    "total_frames": 4500,
    
    "performance": {
        "avg_latency_ms": 42.5,
        "p95_latency_ms": 68.2,
        "avg_fps": 23.5,
        "min_fps": 18.2
    },
    
    "detection": {
        "total_detections": 12500,
        "unique_classes": 8,
        "avg_per_frame": 2.8
    },
    
    "navigation": {
        "critical_frames": 156,
        "critical_ratio": 0.035,
        "cue_changes_per_second": 0.8
    },
    
    "quality": {
        "meets_latency_target": true,
        "meets_fps_target": true,
        "pass": true
    }
}
```

---

## 3. Human Evaluation Protocol

### Evaluator Setup
- Sighted evaluator observing pipeline output
- Comparison with actual scene
- Standardized evaluation form

### Evaluation Form

**Session Information:**
- Session ID: _______________
- Evaluator: _______________
- Date: _______________
- Environment: [ ] Desk [ ] Indoor [ ] Outdoor

**Detection Accuracy (per 5-minute segment):**

| Metric | Count | Notes |
|--------|-------|-------|
| True Positives | ___ | Correct detections |
| False Positives | ___ | Ghost detections |
| False Negatives | ___ | Missed objects |
| Distance Accuracy | [ ] Good [ ] Fair [ ] Poor | |

**Navigation Cue Quality:**

| Criterion | Rating (1-5) | Notes |
|-----------|--------------|-------|
| Cue clarity | ___ | Easy to understand? |
| Cue timing | ___ | Appropriately early? |
| Cue accuracy | ___ | Matches scene? |
| Cue consistency | ___ | Stable, not flickering? |
| Priority correctness | ___ | Critical = actually dangerous? |

**Safety Assessment:**

| Question | Yes/No | Notes |
|----------|--------|-------|
| Would user avoid obstacles? | | |
| Any dangerous false negatives? | | |
| Clear path correctly identified? | | |
| Critical alerts appropriate? | | |

**Overall Score:** ___ / 5

**Comments:**
_______________________________________________

---

## 4. Edge Case Testing

### Lighting Conditions

| Condition | Test Method | Expected Behavior |
|-----------|-------------|-------------------|
| Very bright | Point at window | Graceful degradation |
| Very dark | Cover camera | "Low visibility" warning |
| Backlighting | Person against window | Detect silhouette |
| Flickering | Near fluorescent | Stable output |

### Object Challenges

| Challenge | Test Method | Expected Behavior |
|-----------|-------------|-------------------|
| Glass door | Approach glass | Detect frame/reflections |
| Mirror | Face mirror | Handle reflection |
| Transparent objects | Glass table | Warn if detected |
| Small obstacles | Step/curb | Detect if possible |
| Moving objects | Walking person | Track movement |
| Occluded objects | Partial view | Partial detection |

### System Stress

| Condition | Test Method | Expected Behavior |
|-----------|-------------|-------------------|
| Memory pressure | Run other apps | Graceful degradation |
| CPU throttling | Thermal stress | Reduce features |
| Camera disconnect | Unplug camera | Error message |
| Model failure | Invalid model | Fallback to mock |

**Commands for stress testing:**
```bash
# Memory stress test
python tests/realtime/benchmark.py --config yolo-midas-full --frames 1000

# Compare all configurations
python tests/realtime/benchmark.py --frames 500 --output stress_test.json
python tests/realtime/benchmark.py --report stress_test.json
```

---

## 5. Performance Benchmarks

### Target Metrics

| Metric | Target | Minimum Acceptable |
|--------|--------|-------------------|
| Latency (avg) | < 300ms | < 500ms |
| Latency (p95) | < 500ms | < 800ms |
| FPS | ≥ 20 | ≥ 15 |
| Memory | < 500MB | < 1GB |

### Configuration Comparison

Run benchmarks for each configuration:

```bash
# Benchmark all configurations
python tests/realtime/benchmark.py --list-configs
python tests/realtime/benchmark.py --frames 500 --output benchmarks.json

# Quick comparison
python tests/realtime/benchmark.py --config mock-simple yolo-simple --frames 200
```

### Benchmark Results Template

| Config | Latency | FPS | Memory | Pass |
|--------|---------|-----|--------|------|
| mock-simple | ___ ms | ___ | ___ MB | |
| mock-midas | ___ ms | ___ | ___ MB | |
| yolo-simple | ___ ms | ___ | ___ MB | |
| yolo-midas | ___ ms | ___ | ___ MB | |

---

## 6. Regression Testing

### Pre-Commit Checklist

Before any code changes:

1. [ ] Run benchmark on current code
2. [ ] Save baseline results
3. [ ] Make code changes
4. [ ] Run benchmark again
5. [ ] Compare results (latency should not increase >10%)
6. [ ] Run 100-frame stability test

### Automated Regression Script

```bash
#!/bin/bash
# regression_test.sh

echo "Running regression tests..."

# Quick benchmark
python tests/realtime/benchmark.py \
    --config mock-simple yolo-simple \
    --frames 100 \
    --synthetic \
    --headless \
    --output regression_results.json

# Check results
python -c "
import json
with open('regression_results.json') as f:
    data = json.load(f)
    
for r in data['results']:
    if not r['meets_latency_target'] or not r['meets_fps_target']:
        print(f'FAIL: {r[\"config_name\"]}')
        exit(1)
        
print('PASS: All regression tests passed')
"
```

---

## 7. Test Session Workflow

### Before Testing

1. Charge devices, ensure camera works
2. Clear previous logs if needed
3. Note environmental conditions
4. Prepare evaluation forms

### During Testing

1. Start with desk tests (warm-up)
2. Run each test scenario 3x minimum
3. Note any anomalies immediately
4. Use hotkeys to save interesting frames

### After Testing

1. Review session recordings
2. Complete evaluation forms
3. Export metrics to spreadsheet
4. Compare against baselines
5. Document issues found

### Quick Start Commands

```bash
# 1. Start testing session
cd c:\Voice-Vision-Assistant-for-Blind
python tests/realtime/realtime_test.py --debug --benchmark --log-session

# 2. Review session
python tests/realtime/replay_tool.py logs/realtime_sessions/[SESSION]

# 3. Analyze metrics
python tests/realtime/session_logger.py info logs/realtime_sessions/[SESSION]
python tests/realtime/session_logger.py export logs/realtime_sessions/[SESSION] -o results.csv

# 4. Run full benchmark
python tests/realtime/benchmark.py --output benchmark_results.json
```

---

## Appendix A: Test Environment Specifications

### Hardware Requirements
- Camera: USB webcam, 720p minimum
- CPU: Modern multi-core (i5/Ryzen 5 or better)
- RAM: 8GB minimum, 16GB recommended
- GPU: Optional (for YOLO/MiDaS acceleration)

### Software Requirements
- Python 3.11+
- OpenCV 4.x
- NumPy
- PIL/Pillow

### Recommended Test Setup
```
Camera → USB 3.0 port
        ↓
    Test Script
        ↓
    Debug Display + Log Files
```

---

## Appendix B: Troubleshooting

| Issue | Likely Cause | Solution |
|-------|--------------|----------|
| No camera | Permissions/driver | Check device manager |
| Low FPS | CPU overload | Use lighter config |
| Memory error | Image size | Reduce resolution |
| Crashes | Model loading | Check model paths |
| Flickering cues | Threshold too tight | Adjust stability params |

---

*Last updated: 2024*
