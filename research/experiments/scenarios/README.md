# Scenarios Directory

This directory holds synthetic and recorded test scenarios
for the Repro Harness.

## Scenario Format

Each scenario is a JSON file with this structure:

```json
{
  "id": "spatial_00001",
  "name": "Spatial Navigation #1",
  "category": "spatial|face|vqa|audio|ocr",
  "seed": 42,
  "frame_count": 5,
  "frames": [
    {
      "index": 0,
      "width": 640,
      "height": 480,
      "objects": [...],
      "faces": [...]
    }
  ],
  "expected_detections": [
    {
      "frame_idx": 0,
      "detection_count": 3,
      "has_critical": true
    }
  ]
}
```

## Generating Scenarios

```bash
# Generate 100 synthetic scenarios
python repro/scenario_generator.py --count 100 --output scenarios/

# Generate 10,000 scenarios as single manifest
python repro/scenario_generator.py --count 10000 --output scenarios/ --single-file
```

## Running Scenarios

```bash
# Replay one scenario
python repro/harness.py --scenario scenarios/spatial_00001.json

# Replay all scenarios in directory
python repro/harness.py --dir scenarios/ --output repro_report.json
```

## Categories

| Category | Description |
|----------|-------------|
| spatial  | Obstacle detection + distance estimation |
| face     | Face detection + identity matching |
| vqa      | Visual Q&A with expected answers |
| audio    | Sound event classification + localization |
| ocr      | Text detection + recognition |
