# core/AGENTS.md
Domain engines implementing pure perception/NLP/audio logic.
**Constraint**: Import from `shared/` only — never from `application/`, `infrastructure/`, or `apps/`.

## WHERE TO LOOK
| Module | Purpose | Deep Dive |
|--------|---------|-----------|
| `vqa/` | Low-latency Visual Q&A (detection→segmentation→depth→LLM) | [AGENTS.md](vqa/AGENTS.md) |
| `memory/` | Privacy-first local RAG engine (FAISS + embeddings) | [AGENTS.md](memory/AGENTS.md) |
| `vision/` | Ultra-low-latency spatial perception (YOLO/ONNX) | [AGENTS.md](vision/AGENTS.md) |
| `ocr/` | 3-tier fallback OCR (EasyOCR → Tesseract) | [AGENTS.md](ocr/AGENTS.md) |
| `braille/` | Braille capture, segmentation, and Grade 1 classification | - |
| `qr/` | QR/AR scanning, decoding, and offline TTL cache | - |
| `face/` | Face detection, tracking, and recognition (RetinaFace/MTCNN) | - |
| `speech/` | Voice pipeline, TTS bridge, voice router | - |
| `audio/` | Audio event detection and sound source localization | - |
| `action/` | Clip-based action/intent recognition (16-frame clips) | - |
| `reasoning/` | Central reasoning engine (placeholder) | - |

## Module Highlights
- **braille/**: `BrailleOCR`, `BrailleSegmenter`, `BrailleClassifier`, `EmbossingGuide`. Pipeline: deskew → segment → classify.
- **qr/**: `QRScanner` (pyzbar > OpenCV), `QRDecoder` (content classification), `ARTagHandler`, `CacheManager`. Factory: `build_qr_router()`.
- **face/**: `FaceDetector`, `FaceEmbeddingStore`, `FaceTracker`, `SocialCueAnalyzer`. **ALL OPT-IN + consent required**.
- **speech/**: `VoiceAskPipeline` (STT → VQA → TTS, ≤500ms); `VoiceRouter` (IntentType: visual/search/qr/general).
- **audio/**: `SoundSourceLocalizer` (mic-array or mono degraded), `AudioEventDetector`, `AudioVisionFuser`.
- **action/**: `ActionRecognizer`, `ClipBuffer` (16-frame clips, stride 4, min_confidence 0.3).

## CONVENTIONS
- **Factories**: Use `create_*/build_*/make_*` for all major engine components.
- **Async Executor**: Offload CPU-bound work (torch, cv2, OCR) to `run_in_executor()`.
- **Graceful Degradation**: Never raise from engine methods; return `HealthStatus.DEGRADED` or empty results with error strings.
- **Optional Imports**: Guard heavy dependencies (torch, EasyOCR) to allow partial system startup.

## ANTI-PATTERNS
- **No Layer Violations**: Never import from `application/`, `infrastructure/`, or `apps/`.
- **No Type Redefinitions**: Always use `shared.schemas` for data structures.
- **No Silent Failures**: Log errors at `ERROR` level but return gracefully.
