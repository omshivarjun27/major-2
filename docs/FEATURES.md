# Features

Voice & Vision Assistant feature reference and troubleshooting guide.

---

## 1. QR / AR Tag Scanning

Scan QR codes and AR markers (AprilTag / ArUco) from the camera feed.

### How it works
1. **Frame capture** → LiveKit VideoFrame converted to PIL Image.
2. **Pre-processing** → grayscale → sharpen → scan; fallback to original colour.
3. **QR decode** → pyzbar (primary) or OpenCV QRCodeDetector (fallback).
4. **Multi-scale retry** → preprocessed + 75%/50% scale for distant codes.
5. **Content classification** → URL, location, transport, WiFi, contact, product, text.
6. **Cache** → offline-first `CacheManager` stores decoded results with TTL.

### Trigger
Ask the agent: *"scan QR"*, *"read this code"*, *"what does this QR say"*.

### API Endpoint
`POST /qr/scan` — accepts base64 image, returns decoded result JSON.

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "QR scanning is not available" | `pyzbar` or `libzbar0` not installed | `pip install pyzbar` + `apt install libzbar0` (Linux) |
| Repeated "No QR code detected" | Low contrast / blur / distance | Hold camera closer, steady; check debug frames in `data/debug_frames/` |
| Silent failure, no logs | QR engine not enabled | Set `ENABLE_QR=true` in `.env` |

---

## 2. OCR (Text Reading)

Read printed or handwritten text from the camera.

**Backends (priority order):** EasyOCR → pytesseract → OpenCV heuristic.

Pre-processing includes **deskew** (Hough-line rotation correction) before OCR.

### Trigger
*"read this text"*, *"what does this sign say"*.

---

## 3. Spatial Perception

YOLO object detection + MiDaS depth estimation + scene-graph construction.

- Model files: `models/yolov8n.onnx`, `models/midas_v21_small_256.onnx`
- Auto-detected on startup; logged with path and existence status.

---

## 4. Visual Question Answering (VQA)

Combines perception pipeline + LLM reasoning for visual questions.

### Trigger
*"What colour is the door?"*, *"How many people are in the room?"*.

---

## 5. Navigation

Real-time obstacle detection and navigation cues for safe movement.

### Trigger
*"Help me cross the street"*, *"Is the path clear?"*.

---

## 6. Face Recognition

Detect and identify known faces in the camera feed.

---

## 7. Internet Search

Search the web for real-time information.

---

## Debug Mode

Set `DEBUG_ENDPOINTS_ENABLED=true` to:
- Save failed QR scan frames to `data/debug_frames/`
- Enable `/debug/*` API endpoints
- Emit verbose structured JSON logs
