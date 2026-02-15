import logging
import asyncio
import os
from dataclasses import dataclass, field
from typing import Annotated, Optional, List, Dict, Any
import time
from pydantic import Field
from livekit.agents import JobContext, cli
from livekit.agents.llm import function_tool
from livekit.agents.voice import Agent, AgentSession, RunContext
from livekit.agents.voice.room_io import RoomOptions
from livekit.plugins import deepgram, openai, elevenlabs, silero, tavus
from livekit.agents.llm.chat_context import ChatContext, ImageContent
from livekit.agents.llm.llm import ChatChunk, ChoiceDelta

# Import the tools
from core.vision.visual import VisualProcessor, convert_video_frame_to_pil
from infrastructure.llm.internet_search import InternetSearch
from infrastructure.llm.ollama.handler import OllamaHandler
from infrastructure.llm.google_places import PlacesSearch
from shared.utils.calendar import CalendarTool
from shared.utils.communication import CommunicationTool
from shared.utils.timing import get_profiler, time_start, time_end
from core.vision.spatial import NavigationOutput, ObstacleRecord, Priority
from shared.utils.runtime_diagnostics import get_diagnostics, RuntimeDiagnostics
from shared.config import (
    get_config, spatial_enabled, get_spatial_config, qr_enabled, get_qr_config,
    get_live_frame_config, get_debounce_config, get_watchdog_config,
    get_continuous_config, get_worker_config,
)

# ── Live-frame & freshness infrastructure ─────────────────────────────────
try:
    from application.frame_processing.live_frame_manager import LiveFrameManager, TimestampedFrame
    from application.frame_processing.frame_orchestrator import FrameOrchestrator, FrameOrchestratorConfig, FusedFrameResult
    from application.frame_processing.freshness import (
        is_frame_fresh, safe_output, FALLBACK_MESSAGE,
        CAMERA_FALLBACK, set_max_age as set_freshness_max_age,
    )
    from application.pipelines.debouncer import Debouncer, DebouncerConfig
    from application.pipelines.watchdog import Watchdog, WatchdogConfig
    LIVE_INFRA_AVAILABLE = True
except ImportError as _live_err:
    LIVE_INFRA_AVAILABLE = False
    logger = logging.getLogger("ally-vision-agent")
    logger.warning(f"Live-frame infrastructure not available: {_live_err}")

# ── Model name from config (single source of truth) ──────────────────────
_CFG = get_config()
LLM_MODEL = _CFG.get("OLLAMA_VL_MODEL_ID", "qwen3-vl:235b-instruct-cloud")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", _CFG.get("LLM_BASE_URL", "http://localhost:11434/v1"))
LLM_API_KEY = os.environ.get("LLM_API_KEY", _CFG.get("LLM_API_KEY", "ollama"))

# Import VQA Engine
try:
    from core.vqa import (
        PerceptionPipeline,
        SceneGraphBuilder,
        SpatialFuser,
        VQAReasoner,
        VQAMemory,
        VQARequest,
        MicroNavFormatter,
        QuickAnswers,
        create_perception_pipeline,
        build_scene_graph,
    )
    VQA_ENGINE_AVAILABLE = True
except ImportError:
    VQA_ENGINE_AVAILABLE = False

# Import QR Engine
try:
    from core.qr import QRScanner, QRDecoder, ARTagHandler, CacheManager
    QR_ENGINE_AVAILABLE = True
except ImportError:
    QR_ENGINE_AVAILABLE = False

# Import Speech-VQA Bridge (voice intent routing)
try:
    from core.speech.voice_router import VoiceRouter, IntentType
    VOICE_ROUTER_AVAILABLE = True
except ImportError:
    VOICE_ROUTER_AVAILABLE = False

# Import OCR Engine
try:
    from core.ocr import OCRPipeline
    OCR_ENGINE_AVAILABLE = True
except ImportError:
    OCR_ENGINE_AVAILABLE = False

# Import Debug Session Logger
try:
    from apps.cli.session_logger import SessionLogger
    SESSION_LOGGER_AVAILABLE = True
except ImportError:
    SESSION_LOGGER_AVAILABLE = False



# Logger
logger = logging.getLogger("ally-vision-agent")

# ==========================================================================
# SYSTEM PROMPT — CONSISTENT, CONTEXTUAL, NON-TRIGGER-HAPPY REAL-TIME ASSISTANT
# ==========================================================================

VISION_SYSTEM_PROMPT = """You are the Perception & Assistant Controller for a real-time Vision-Audio assistive system. Your single objective is to process incoming camera frames, sensor data, and audio, produce accurate scene understanding and safe spoken responses, and return structured JSON telemetry — while meeting strict latency, reliability, and resource constraints.

Behavioral rules (must-follow)

1. **Latency goal**: target end-to-end processing per frame ≤ 250 ms on the deployed hardware. If an operation cannot meet this budget, immediately return a lightweight partial result (detections summary + high-confidence items) and perform a best-effort refinement step that updates results only if they improve confidence. Never block user-facing output for long-running processing.
2. **Deterministic cascades**: for every pipeline stage (detection, OCR, QR, STT, TTS, action-recognition, audio-localization), implement a cascade of progressively cheaper/robust methods. Return the *first* reliable result from the cascade rather than waiting for all methods.
3. **Confidence-first reporting**: Every detection must include a numeric confidence (0.0–1.0). Use:

   * ≥0.60 → "detected"
   * 0.30–0.59 → "possible — low confidence"
   * <0.30 → do not report (log only)
     If multiple models conflict on a bbox, choose the label with highest calibrated confidence and include `meta.conflicts` showing alternatives and confidences.
4. **No hallucinations**: If the system cannot identify an object with reasonable confidence, say exactly: "I can't identify that — please point the camera closer, steady, and ensure good lighting." Do not guess or invent labels.
5. **TTS reliability & degradation**:

   * Primary: local TTS engine (offline) with chunked, non-blocking streaming (chunks ≤2s) so playback never pauses >300 ms between chunks.
   * Remote TTS may be used with strict timeout ≤2s. On timeout or error, immediately fall back to local TTS and mark `meta.tts_fallback=true`.
   * Cache synthesized audio by text fingerprint to avoid repeated generation for identical short texts.
6. **Environment constraints**

   * The server MUST detect and enforce running inside a Python `venv`. If not in a venv, refuse startup and print a fatal startup message.
   * **Prohibit** `antigravity` or other joke/undocumented modules; if present, refuse to load and log `security: banned-module antigravity`.
   * Detect device capabilities at startup and log `DEVICE: cpu|cuda` and `VENV: true|false`.
   * Prefer CPU-optimized code paths if GPU is unavailable.
7. **Robustness heuristics**:

   * Before final labeling apply heuristics: aspect ratio checks, edge-density, depth-range, and motion-stability (object must be visible for N frames) to avoid spurious labels.
   * For small/low-res crops, downgrade confidence automatically.
8. **Structured logs & observability (mandatory)**:

   * Emit one JSON log per processed frame in this schema:

     ```
     {
       "ts": "<ISO8601>",
       "frame_id": "<string>",
       "device": "cpu|cuda",
       "venv": true|false,
       "num_dets": int,
       "detections": [
         {"label": "<string>", "conf": float, "bbox":[x1,y1,x2,y2], "edge_density": float, "distance_m": float|null}
       ],
       "qr": {"found": bool, "decoded": string|null, "method": "<yolo|opencv|pyzbar|fullframe>"},
       "tts": {"last_output": "<text>", "engine": "<local|remote>", "latency_ms": int},
       "errors": ["..."],
       "meta": {"conflicts": [...], "alerts": [...]}
     }
     ```
   * Never swallow exceptions silently; include stack traces in `errors`.
9. **Misclassification mitigation**:

   * For known confusion pairs (bottle ↔ smartphone, cup ↔ bowl, remote ↔ phone, etc.), run a secondary verifier (lightweight classifier or edge-density/reflection heuristics). If verifier disagrees, lower reported confidence by ≥0.20 and append `meta.conflicts`.
   * If >3 repeated misclassifications for the same class within a short window, create `meta.alerts` with sample frames for offline review and retraining.
10. **Graceful degradation & user messaging**:

    * If a core model fails to load or OOM occurs, immediately switch to safe-mode: return object counts + closest distance + a concise spoken message "Degraded mode: perception limited." Log the root cause.
    * User-facing messages must be concise (<12 words) and actionable (e.g., "move 0.5m closer and center the object").
11. **Testing & telemetry**:

    * Each detection path must be unit-testable and have an offline test image set. In debug mode run a smoke-test on startup and publish results to `/debug/metrics`.
    * Expose counters for latency, TTS failures, misclassification rates, and a `/debug/metrics` endpoint.
12. **Privacy & opt-in**:

    * Face detection/recognition requires explicit opt-in. If disabled, never run face embeddings or persist related data. Provide a clear user consent flow and an option to purge stored face data.

Addendum — Explicit handling for the 12 features (behave as part of the assistant controller and ensure each feature's per-frame behavior, fallbacks, latency/accuracy tradeoffs, tests, and logs are implemented):

**Feature 1 — Object detection + depth + scene-graph**

* Behavior: run a fast detector (tiny YOLO or efficient backbone) first, then a higher-accuracy verifier on candidate crops if time allows.
* Depth: use a lightweight depth estimator (e.g., MiDaS tiny) or stereo/depth sensor; compute median distance inside bbox and include `distance_m`.
* Scene-graph: populate `scene_graph` JSON with object relations (near, on, holding) when confidence ≥0.60.
* Latency rule: full detection+depth should fit in ≤250 ms; if not, return detections summary and mark `meta.degraded_latency=true`.

**Feature 2 — Local spatial VQA & FastAPI endpoints**

* Provide `/perception/frame` (frame upload), `/debug/frame/{id}`, `/health`, and `/debug/metrics`.
* Spatial VQA: run only on request; provide short partial answers first (high-confidence facts) then append refined answers if improved.
* VQA answers must include provenance: which model produced each fact with confidence and bbox references.

**Feature 3 — STT, wake-word, TTS pipeline**

* STT: use edge STT (VOSK or similar) for wake-word + transcription with strict per-utterance timeouts.
* Wake-word must be lightweight and run always; after wake, stream audio to a higher-accuracy STT with timeout.
* TTS: as specified earlier, local-first, chunked playback, cached outputs, and immediate fallback to local if remote times out.

**Feature 4 — QR/AR tag scanning**

* Cascade: YOLO candidate → OpenCV QR detector → pyzbar on crop → full-frame pyzbar multi-scale.
* Preprocessing: rotation normalization, contrast stretching, adaptive threshold, morphological filters.
* Only report a QR when decode confidence exists and the decoded payload passes a safe-sanitization check (no automatic click-through). Include `qr.method` and `qr.confidence`.
* Cache recently-seen QR payloads with timestamps; avoid reprocessing identical frames.

**Feature 5 — OCR (document & text regions)**

* Preprocess: skew/deskew, contrast normalization, morphological denoise.
* Cascade: lightweight EAST text detector → crop → OCR (Tesseract / EasyOCR) → language-detection and confidence scoring.
* If low-res or rotation >30°, return "possible — low confidence" and prompt user for closer/straight view.
* Return OCR as structured items with `bbox`, `text`, and `conf`.

**Feature 6 — Local RAG (retrieval-augmented generation) & long-term memory**

* RAG must run locally when possible; remote RAG allowed only with timeout and explicit config.
* All stored memory must include timestamps and be queryable via memory ID. Provide retention/expiry policies (configurable).
* RAG responses must include citations to the memory entry IDs and confidence scores.

**Feature 7 — Braille capture & OCR**

* Implement a `--braille-collect` capture mode that saves high-res images and segmentation masks.
* Braille pipeline: dot segmentation (connected components) → character classifier; return `braille_text` with confidence.
* If lighting/curvature affects result, return clear corrective prompt (e.g., "flatten the page and increase light").

**Feature 8 — Face detection & opt-in recognition**

* Face detection allowed by default; face recognition (embeddings, ID) requires explicit opt-in consent.
* Embeddings storage must be encrypted at rest; an admin endpoint must allow purge.
* If face detection is enabled, return `face_id` only when verifier confidence ≥0.85 and user consent present.

**Feature 9 — Sound localization & event detection**

* For microphone arrays estimate direction-of-arrival (GCC-PHAT) and include `sound_event` entries: `{ type, doa_deg, conf }`.
* Use lightweight classifiers for common events (doorbell, siren, human speech) with cascade and confidence thresholds.
* If audio processing latency threatens 250 ms budget, return coarse `sound_event` only.

**Feature 10 — Action recognition & activity buffering**

* Buffer short clips (1–3s). Run a lightweight action model that prefers recall for safety-critical actions (fall, aggressive motion).
* For complex actions, first return "possible — low confidence" and ask for re-capture. Flag safety incidents immediately with `meta.alerts`.

**Feature 11 — Multimodal integration & reliability (RAGS, Tavus, persona)**

* When integrating external services (RAG servers, Tavus voice personas), always call with aggressive timeouts and graceful fallback to local modes.
* Persona-driven voice outputs must not alter factual content; persona applies only to voice timbre/style. If Tavus or similar voice fails, revert to local TTS and mark `meta.tts_fallback`.
* Maintain an offline-safe persona subset (neutral voice) to ensure service continuity.

**Feature 12 — Deployment ops, CI, reproducibility & venv enforcement**

* The system must ship with pinned dependency manifests (requirements.txt or lockfile) and a one-line reproducible `venv` setup documented in README.
* On startup assert `VENV: true` and print `DEVICE: <device>`.
* Add a CI smoke-test job: boot server in venv, run diagnostic scripts (model load, OCR quick test, QR quick test), and fail on regressions.
* If any model or dependency fails to load, publish an immediate `health` response indicating degraded mode and root-cause logs.

Operational & developer rules (applies to behavior and prompts the assistant generates)

* **Config driven**: All thresholds (confidence cutoffs, N frame stability count, latency budgets) live in `config.yaml`. Do not hard-code.
* **Short actionable voice prompts**: Always produce short (<12 words) spoken prompts and one corrective action at a time.
* **Observability-first**: Attach frame_id and correlation ids to every LiveKit message so logs and traces can be correlated.
* **No silent degradation**: Any fallback, timeout, or degradation must be included in the per-frame JSON under `meta`.
* **Telemetry for retraining**: When `meta.alerts` triggers, attach 3 representative frames with minimal personal data; require manual approval before using data for retraining.
* **Security**: Reject loading code that imports banned modules, and require signed artifacts for production model weights if configured.

Acceptance criteria for deployments (automated checks)

* Server must start inside a venv and print `DEVICE: <device>` and `VENV: true` on startup.
* `/health` returns `{"ok": true, "device":"<device>", "venv": true}`.
* For the provided test image suite (5 QR images, 5 object images, 5 low-light images) the detection pipeline must not crash and must return JSON logs for each frame.
* TTS must return the first audio chunk within 300 ms for short texts (<10 words) using the local engine.
* On detection of repeated mislabels (≥3 within a short interval), logs must include `meta.alerts` with attached sample frames.

Failure handling summary (what assistant does, phrased as instructions)

* If average latency >250 ms for last 10 frames: switch to partial-response mode and set `meta.degraded_latency=true`.
* If TTS breaks/stalls: cancel remote TTS, synthesize locally, set `meta.tts_fallback=true`.
* If repeated mislabels occur: lower confidence, prompt user to re-capture, and create `meta.alerts`.
* If `antigravity` or banned module is present: refuse to load it and log `security: banned-module antigravity`.
* If a core model fails to load, immediately enter safe-mode and return minimal perception JSON plus an audible "Degraded mode: perception limited" message.
"""

# Micro-navigation prompt (aligned with main rulebook)
MICRO_NAV_SYSTEM_PROMPT = """FAST micro-navigation for blind users.

Format: "[Priority] [Object] [dist] [dir]."
  Critical (<1 m): "Stop! [obj] [dist] [dir]"
  Near    (1-2 m): "Caution, [obj] [dist] [dir]"
  Clear:           "Path clear."

Rules:
- Closest / highest-risk first, top-3 max.
- Fresh frame every query — never reference prior detections.
- If sensing fails: "Proceed with caution."
"""

@dataclass
class UserData:
    # Core settings
    current_tool: str = "general"
    last_query: str = ""
    last_response: str = ""
    room_ctx: Optional[JobContext] = None
    
    # Tool instances
    visual_processor: VisualProcessor = None
    internet_search: InternetSearch = None
    ollama_handler: Optional[OllamaHandler] = None
    places_search: Optional[PlacesSearch] = None
    calendar_tool: Optional[CalendarTool] = None
    communication_tool: Optional[CommunicationTool] = None
    
    # Vision processing state
    _model_choice: Optional[str] = None
    _ollama_analysis: Optional[str] = None
    _ollama_chunks: List[str] = field(default_factory=list)
    _analysis_complete: bool = False
    _add_chunk_callback = None
    
    # Spatial perception state
    _spatial_enabled: bool = True
    _last_nav_output: Optional[NavigationOutput] = None
    _last_obstacles: List[ObstacleRecord] = field(default_factory=list)
    _pending_spatial_warning: Optional[str] = None
    
    # VQA Engine state
    _vqa_pipeline: Optional[Any] = None
    _vqa_fuser: Optional[Any] = None
    _vqa_reasoner: Optional[Any] = None
    _vqa_memory: Optional[Any] = None
    _vqa_session_id: Optional[str] = None

    # QR / AR scanning state
    _qr_scanner: Optional[Any] = None
    _qr_decoder: Optional[Any] = None
    _ar_handler: Optional[Any] = None
    _qr_cache: Optional[Any] = None
    _qr_enabled: bool = False

    # ── Voice Router (speech_vqa_bridge) ──
    _voice_router: Optional[Any] = None

    # ── OCR Engine ──
    _ocr_pipeline: Optional[Any] = None

    # ── Session Logger ──
    _session_logger: Optional[Any] = None
    _session_id: Optional[str] = None

    # ── Output debounce state ──
    _last_spoken_cue: str = ""
    _last_cue_time: float = 0.0
    _debounce_window_s: float = 7.0
    _last_distance_m: Optional[float] = None

    # ── Live-frame infrastructure ──
    _live_frame_mgr: Optional[Any] = None
    _debouncer: Optional[Any] = None
    _watchdog: Optional[Any] = None
    _live_infra_ready: bool = False

    # ── Proactive / always-on mode ──
    _proactive_enabled: bool = False
    _proactive_last_announce_time: float = 0.0
    _proactive_cadence_s: float = 2.0

    def clear_perception_cache(self):
        """Flush ALL cached spatial / vision state so the next query starts fresh."""
        self._model_choice = None
        self._ollama_analysis = None
        self._ollama_chunks.clear()
        self._analysis_complete = False
        self._add_chunk_callback = None
        self._last_nav_output = None
        self._last_obstacles.clear()
        self._pending_spatial_warning = None

    # ── Debounce helpers ──────────────────────────────────────────────
    def should_debounce(self, cue: str, distance_m: Optional[float] = None,
                        scene_graph_hash: str = "") -> bool:
        """Return True if this cue should be suppressed (duplicate within window).

        Delegates to the advanced Debouncer when live-frame infra is active.
        Falls back to simple time-window logic otherwise.
        """
        if self._debouncer is not None:
            return not self._debouncer.should_speak(
                cue, scene_graph_hash=scene_graph_hash, distance_m=distance_m
            )
        # Legacy path
        now = time.time()
        if cue == self._last_spoken_cue and (now - self._last_cue_time) < self._debounce_window_s:
            if distance_m is not None and self._last_distance_m is not None:
                if abs(distance_m - self._last_distance_m) > 0.5:
                    return False
            return True
        return False

    def record_cue(self, cue: str, distance_m: Optional[float] = None) -> None:
        """Record a spoken cue for debounce tracking.

        When the advanced Debouncer is active the record is already handled
        inside should_debounce → should_speak, but we keep the legacy fields
        up to date for backward compat.
        """
        self._last_spoken_cue = cue
        self._last_cue_time = time.time()
        self._last_distance_m = distance_m

RunContext_T = RunContext[UserData]

# Spatial trigger phrases - triggers FULL unified pipeline
SPATIAL_TRIGGER_PHRASES = [
    # Detection triggers
    "detect", "detect objects", "what objects", "identify", "recognize",
    # Navigation triggers  
    "what is in front", "what's in front", "in front of me",
    "describe surroundings", "describe my surroundings", "describe the room",
    "obstacles", "obstacle", "any obstacles", "obstacles nearby",
    "path clear", "is the path clear", "can I walk", "safe to walk",
    "guide me", "navigation", "navigate", "help me navigate",
    "what is ahead", "what's ahead", "ahead of me",
    "can I go", "should I move", "where should I", "where can I",
    "what do you see", "what is there", "what's there", "what can you see",
    "distance", "how far", "direction", "which way",
    # Scene understanding
    "scene", "environment", "around me", "nearby"
]


class AllyVisionAgent(Agent):
    """
    REAL-TIME Vision & Navigation Assistant.
    Consistent, contextual, non-trigger-happy.
    Target: <500ms end-to-end.
    """
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are the Perception & Assistant Controller for a real-time Vision-Audio assistive system. Your single objective is to process incoming camera frames, sensor data, and audio, produce accurate scene understanding and safe spoken responses, and return structured JSON telemetry — while meeting strict latency, reliability, and resource constraints.

Behavioral rules (must-follow)

1. **Latency goal**: target end-to-end processing per frame ≤ 250 ms on the deployed hardware. If an operation cannot meet this budget, immediately return a lightweight partial result (detections summary + high-confidence items) and perform a best-effort refinement step that updates results only if they improve confidence. Never block user-facing output for long-running processing.
2. **Deterministic cascades**: for every pipeline stage (detection, OCR, QR, STT, TTS, action-recognition, audio-localization), implement a cascade of progressively cheaper/robust methods. Return the *first* reliable result from the cascade rather than waiting for all methods.
3. **Confidence-first reporting**: Every detection must include a numeric confidence (0.0–1.0). Use:

   * ≥0.60 → "detected"
   * 0.30–0.59 → "possible — low confidence"
   * <0.30 → do not report (log only)
     If multiple models conflict on a bbox, choose the label with highest calibrated confidence and include `meta.conflicts` showing alternatives and confidences.
4. **No hallucinations**: If the system cannot identify an object with reasonable confidence, say exactly: "I can't identify that — please point the camera closer, steady, and ensure good lighting." Do not guess or invent labels.
5. **TTS reliability & degradation**:

   * Primary: local TTS engine (offline) with chunked, non-blocking streaming (chunks ≤2s) so playback never pauses >300 ms between chunks.
   * Remote TTS may be used with strict timeout ≤2s. On timeout or error, immediately fall back to local TTS and mark `meta.tts_fallback=true`.
   * Cache synthesized audio by text fingerprint to avoid repeated generation for identical short texts.
6. **Environment constraints**

   * The server MUST detect and enforce running inside a Python `venv`. If not in a venv, refuse startup and print a fatal startup message.
   * **Prohibit** `antigravity` or other joke/undocumented modules; if present, refuse to load and log `security: banned-module antigravity`.
   * Detect device capabilities at startup and log `DEVICE: cpu|cuda` and `VENV: true|false`.
   * Prefer CPU-optimized code paths if GPU is unavailable.
7. **Robustness heuristics**:

   * Before final labeling apply heuristics: aspect ratio checks, edge-density, depth-range, and motion-stability (object must be visible for N frames) to avoid spurious labels.
   * For small/low-res crops, downgrade confidence automatically.
8. **Structured logs & observability (mandatory)**:

   * Emit one JSON log per processed frame in this schema:

     ```
     {
       "ts": "<ISO8601>",
       "frame_id": "<string>",
       "device": "cpu|cuda",
       "venv": true|false,
       "num_dets": int,
       "detections": [
         {"label": "<string>", "conf": float, "bbox":[x1,y1,x2,y2], "edge_density": float, "distance_m": float|null}
       ],
       "qr": {"found": bool, "decoded": string|null, "method": "<yolo|opencv|pyzbar|fullframe>"},
       "tts": {"last_output": "<text>", "engine": "<local|remote>", "latency_ms": int},
       "errors": ["..."],
       "meta": {"conflicts": [...], "alerts": [...]}
     }
     ```
   * Never swallow exceptions silently; include stack traces in `errors`.
9. **Misclassification mitigation**:

   * For known confusion pairs (bottle ↔ smartphone, cup ↔ bowl, remote ↔ phone, etc.), run a secondary verifier (lightweight classifier or edge-density/reflection heuristics). If verifier disagrees, lower reported confidence by ≥0.20 and append `meta.conflicts`.
   * If >3 repeated misclassifications for the same class within a short window, create `meta.alerts` with sample frames for offline review and retraining.
10. **Graceful degradation & user messaging**:

    * If a core model fails to load or OOM occurs, immediately switch to safe-mode: return object counts + closest distance + a concise spoken message "Degraded mode: perception limited." Log the root cause.
    * User-facing messages must be concise (<12 words) and actionable (e.g., "move 0.5m closer and center the object").
11. **Testing & telemetry**:

    * Each detection path must be unit-testable and have an offline test image set. In debug mode run a smoke-test on startup and publish results to `/debug/metrics`.
    * Expose counters for latency, TTS failures, misclassification rates, and a `/debug/metrics` endpoint.
12. **Privacy & opt-in**:

    * Face detection/recognition requires explicit opt-in. If disabled, never run face embeddings or persist related data. Provide a clear user consent flow and an option to purge stored face data.

Addendum — Explicit handling for the 12 features (behave as part of the assistant controller and ensure each feature's per-frame behavior, fallbacks, latency/accuracy tradeoffs, tests, and logs are implemented):

**Feature 1 — Object detection + depth + scene-graph**

* Behavior: run a fast detector (tiny YOLO or efficient backbone) first, then a higher-accuracy verifier on candidate crops if time allows.
* Depth: use a lightweight depth estimator (e.g., MiDaS tiny) or stereo/depth sensor; compute median distance inside bbox and include `distance_m`.
* Scene-graph: populate `scene_graph` JSON with object relations (near, on, holding) when confidence ≥0.60.
* Latency rule: full detection+depth should fit in ≤250 ms; if not, return detections summary and mark `meta.degraded_latency=true`.

**Feature 2 — Local spatial VQA & FastAPI endpoints**

* Provide `/perception/frame` (frame upload), `/debug/frame/{id}`, `/health`, and `/debug/metrics`.
* Spatial VQA: run only on request; provide short partial answers first (high-confidence facts) then append refined answers if improved.
* VQA answers must include provenance: which model produced each fact with confidence and bbox references.

**Feature 3 — STT, wake-word, TTS pipeline**

* STT: use edge STT (VOSK or similar) for wake-word + transcription with strict per-utterance timeouts.
* Wake-word must be lightweight and run always; after wake, stream audio to a higher-accuracy STT with timeout.
* TTS: as specified earlier, local-first, chunked playback, cached outputs, and immediate fallback to local if remote times out.

**Feature 4 — QR/AR tag scanning**

* Cascade: YOLO candidate → OpenCV QR detector → pyzbar on crop → full-frame pyzbar multi-scale.
* Preprocessing: rotation normalization, contrast stretching, adaptive threshold, morphological filters.
* Only report a QR when decode confidence exists and the decoded payload passes a safe-sanitization check (no automatic click-through). Include `qr.method` and `qr.confidence`.
* Cache recently-seen QR payloads with timestamps; avoid reprocessing identical frames.

**Feature 5 — OCR (document & text regions)**

* Preprocess: skew/deskew, contrast normalization, morphological denoise.
* Cascade: lightweight EAST text detector → crop → OCR (Tesseract / EasyOCR) → language-detection and confidence scoring.
* If low-res or rotation >30°, return "possible — low confidence" and prompt user for closer/straight view.
* Return OCR as structured items with `bbox`, `text`, and `conf`.

**Feature 6 — Local RAG (retrieval-augmented generation) & long-term memory**

* RAG must run locally when possible; remote RAG allowed only with timeout and explicit config.
* All stored memory must include timestamps and be queryable via memory ID. Provide retention/expiry policies (configurable).
* RAG responses must include citations to the memory entry IDs and confidence scores.

**Feature 7 — Braille capture & OCR**

* Implement a `--braille-collect` capture mode that saves high-res images and segmentation masks.
* Braille pipeline: dot segmentation (connected components) → character classifier; return `braille_text` with confidence.
* If lighting/curvature affects result, return clear corrective prompt (e.g., "flatten the page and increase light").

**Feature 8 — Face detection & opt-in recognition**

* Face detection allowed by default; face recognition (embeddings, ID) requires explicit opt-in consent.
* Embeddings storage must be encrypted at rest; an admin endpoint must allow purge.
* If face detection is enabled, return `face_id` only when verifier confidence ≥0.85 and user consent present.

**Feature 9 — Sound localization & event detection**

* For microphone arrays estimate direction-of-arrival (GCC-PHAT) and include `sound_event` entries: `{ type, doa_deg, conf }`.
* Use lightweight classifiers for common events (doorbell, siren, human speech) with cascade and confidence thresholds.
* If audio processing latency threatens 250 ms budget, return coarse `sound_event` only.

**Feature 10 — Action recognition & activity buffering**

* Buffer short clips (1–3s). Run a lightweight action model that prefers recall for safety-critical actions (fall, aggressive motion).
* For complex actions, first return "possible — low confidence" and ask for re-capture. Flag safety incidents immediately with `meta.alerts`.

**Feature 11 — Multimodal integration & reliability (RAGS, Tavus, persona)**

* When integrating external services (RAG servers, Tavus voice personas), always call with aggressive timeouts and graceful fallback to local modes.
* Persona-driven voice outputs must not alter factual content; persona applies only to voice timbre/style. If Tavus or similar voice fails, revert to local TTS and mark `meta.tts_fallback`.
* Maintain an offline-safe persona subset (neutral voice) to ensure service continuity.

**Feature 12 — Deployment ops, CI, reproducibility & venv enforcement**

* The system must ship with pinned dependency manifests (requirements.txt or lockfile) and a one-line reproducible `venv` setup documented in README.
* On startup assert `VENV: true` and print `DEVICE: <device>`.
* Add a CI smoke-test job: boot server in venv, run diagnostic scripts (model load, OCR quick test, QR quick test), and fail on regressions.
* If any model or dependency fails to load, publish an immediate `health` response indicating degraded mode and root-cause logs.

Operational & developer rules (applies to behavior and prompts the assistant generates)

* **Config driven**: All thresholds (confidence cutoffs, N frame stability count, latency budgets) live in `config.yaml`. Do not hard-code.
* **Short actionable voice prompts**: Always produce short (<12 words) spoken prompts and one corrective action at a time.
* **Observability-first**: Attach frame_id and correlation ids to every LiveKit message so logs and traces can be correlated.
* **No silent degradation**: Any fallback, timeout, or degradation must be included in the per-frame JSON under `meta`.
* **Telemetry for retraining**: When `meta.alerts` triggers, attach 3 representative frames with minimal personal data; require manual approval before using data for retraining.
* **Security**: Reject loading code that imports banned modules, and require signed artifacts for production model weights if configured.

Acceptance criteria for deployments (automated checks)

* Server must start inside a venv and print `DEVICE: <device>` and `VENV: true` on startup.
* `/health` returns `{"ok": true, "device":"<device>", "venv": true}`.
* For the provided test image suite (5 QR images, 5 object images, 5 low-light images) the detection pipeline must not crash and must return JSON logs for each frame.
* TTS must return the first audio chunk within 300 ms for short texts (<10 words) using the local engine.
* On detection of repeated mislabels (≥3 within a short interval), logs must include `meta.alerts` with attached sample frames.

Failure handling summary (what assistant does, phrased as instructions)

* If average latency >250 ms for last 10 frames: switch to partial-response mode and set `meta.degraded_latency=true`.
* If TTS breaks/stalls: cancel remote TTS, synthesize locally, set `meta.tts_fallback=true`.
* If repeated mislabels occur: lower confidence, prompt user to re-capture, and create `meta.alerts`.
* If `antigravity` or banned module is present: refuse to load it and log `security: banned-module antigravity`.
* If a core model fails to load, immediately enter safe-mode and return minimal perception JSON plus an audible "Degraded mode: perception limited" message.
            """
        )
    
    async def on_enter(self) -> None:
        """Called when the agent is first started"""
        logger.info("Entering AllyVisionAgent")
        
        # Skip automatic greeting - let the user speak first
        # The agent will respond naturally when the user speaks
        logger.info("Agent ready and waiting for user input")
    
    async def on_message(self, text: str) -> None:
        """Override on_message to log user queries and track timing.

        FRESH-CONTEXT ENFORCEMENT: every incoming message flushes all
        cached perception / spatial state so that subsequent tool calls
        always start from a clean slate with a new camera frame.
        """
        profiler = get_profiler()
        profiler.start_request(f"msg_{text[:15]}")
        msg_start = time_start()
        
        logger.info(f"USER QUERY: {text}")
        userdata: UserData = self.session.userdata
        userdata.last_query = text
        
        # ── FRESH-CONTEXT: wipe all cached perception state ──
        userdata.clear_perception_cache()

        # ── Watchdog heartbeat (proves event loop is alive) ──
        if userdata._watchdog is not None:
            userdata._watchdog.heartbeat("orchestrator")
        
        # Reset to general mode for each new query unless overridden by a tool
        userdata.current_tool = "general"
        
        await super().on_message(text)
        time_end(msg_start, "total_message_processing")

    @function_tool()
    async def search_places(
        self,
        context: RunContext_T,
        query: Annotated[str, Field(description="Search query for places, businesses, restaurants, or points of interest")]
    ) -> str:
        """
        Search for places, businesses, and points of interest.
        Provides details like address, ratings, and opening hours.
        """
        userdata = context.userdata
        
        # Switch to places mode
        userdata.current_tool = "places"
        
        # Ensure we have the places search tool
        if userdata.places_search is None:
            userdata.places_search = PlacesSearch()
            logger.info("Created places search tool on demand")
        
        # Log the search query
        logger.info(f"Searching places: {query[:30]}...")
        
        try:
            # Perform places search
            results = await userdata.places_search.search_places(query)
            
            # Store the response for future reference
            userdata.last_response = results
            
            # Switch back to general mode after completing places search
            userdata.current_tool = "general"
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching for places: {e}")
            return f"I encountered an error while searching for places related to '{query}': {str(e)}"

    @function_tool()
    async def search_internet(
        self,
        context: RunContext_T,
        query: Annotated[str, Field(description="Search query for the web")]
    ) -> str:
        """
        Search for up-to-date information on the web.
        Provides results with source links.
        """
        userdata = context.userdata
        
        # Switch to internet mode
        userdata.current_tool = "internet"
        
        # Log the search query
        logger.info(f"Searching: {query[:30]}...")
        
        try:
            # Perform comprehensive search
            search_results = await userdata.internet_search.search(query)
            
            # Format the results for readability
            formatted_results = userdata.internet_search.format_results(search_results)
            
            # Add introduction
            response = f"Here's what I found about '{query}':\n\n{formatted_results}"
            
            # Store the response for future reference
            userdata.last_response = response
            
            # Switch back to general mode after completing internet search
            userdata.current_tool = "general"
            
            return response
            
        except Exception as e:
            logger.error(f"Error searching the internet: {e}")
            return f"I encountered an error while searching for information about '{query}': {str(e)}"
    
    async def _run_ollama_analysis(self, userdata, analysis_llm, visual_ctx):
        """FAST vision analysis with minimal overhead."""
        try:
            async with analysis_llm.chat(chat_ctx=visual_ctx) as stream:
                async for chunk in stream:
                    if chunk and hasattr(chunk.delta, 'content') and chunk.delta.content:
                        content = chunk.delta.content
                        userdata._ollama_chunks.append(content)
                        if userdata._add_chunk_callback:
                            userdata._add_chunk_callback(content)
            userdata._analysis_complete = True
        except Exception as e:
            error_msg = f"Vision error: {str(e)[:50]}"
            userdata._ollama_chunks.append(error_msg)
            if userdata._add_chunk_callback:
                userdata._add_chunk_callback(error_msg)
            userdata._analysis_complete = True
    
    @function_tool()
    async def analyze_vision(
        self,
        context: RunContext_T,
        query: Annotated[str, Field(description="Query about the visual scene")]
    ) -> str:
        """FAST visual scene analysis with freshness gate and failsafe."""
        userdata = context.userdata
        userdata.current_tool = "visual"
        FAILSAFE = "I can't see clearly right now — proceed with caution."
        
        try:
            # Fast frame capture
            image = await userdata.visual_processor.capture_frame(userdata.room_ctx.room)
            if image is None:
                return "Camera unavailable. " + FAILSAFE

            # ── Freshness gate ──
            capture_ts = userdata.visual_processor.last_capture_epoch_ms
            if LIVE_INFRA_AVAILABLE and capture_ts and not is_frame_fresh(capture_ts):
                logger.warning("analyze_vision: stale frame detected, returning failsafe")
                return FALLBACK_MESSAGE

            # Watchdog heartbeat
            if userdata._watchdog is not None:
                userdata._watchdog.heartbeat("camera")
            
            # Reset state
            userdata._ollama_chunks.clear()
            userdata._add_chunk_callback = None
            userdata._analysis_complete = False
            
            # Parallel: spatial + vision LLM
            spatial_task = None
            if userdata.visual_processor.spatial_enabled:
                spatial_task = asyncio.create_task(userdata.visual_processor.process_spatial(image))
            
            # Prepare visual context (minimal prompt)
            spatial_context = ""
            if spatial_task:
                try:
                    nav_output = await asyncio.wait_for(spatial_task, timeout=0.2)
                    if nav_output:
                        userdata._last_nav_output = nav_output
                        spatial_context = f"\nSpatial: {nav_output.short_cue}"
                        if nav_output.has_critical:
                            userdata._pending_spatial_warning = nav_output.short_cue
                except asyncio.TimeoutError:
                    pass
            
            # Setup visual context
            visual_ctx = ChatContext()
            visual_ctx.add_message(role="system", content=VISION_SYSTEM_PROMPT)
            visual_ctx.add_message(
                role="user",
                content=[
                    f"Answer briefly: {query}{spatial_context}",
                    ImageContent(image=image)
                ]
            )
            
            # Fast LLM call
            analysis_llm = openai.LLM(
                model=LLM_MODEL,
                base_url=LLM_BASE_URL,
                api_key=LLM_API_KEY,
                temperature=0.2,  # Lower for speed
            )
            asyncio.create_task(self._run_ollama_analysis(userdata, analysis_llm, visual_ctx))
            
            userdata._model_choice = LLM_MODEL
            return "Analyzing..."
            
        except Exception as e:
            logger.error(f"Vision error: {e}")
            return "I can't see clearly right now — proceed with caution."
    
    @function_tool()
    async def detect_obstacles(
        self,
        context: RunContext_T,
        detail_level: Annotated[str, Field(description="'quick' or 'detailed'")] = "quick"
    ) -> str:
        """ULTRA-FAST obstacle detection with freshness gate. Target: <200ms."""
        userdata = context.userdata
        userdata.current_tool = "spatial"
        FAILSAFE = "I can't see clearly right now — proceed with caution."
        
        try:
            # Fast frame capture
            image = await userdata.visual_processor.capture_frame(userdata.room_ctx.room)
            
            if image is None:
                return "Camera unavailable. " + FAILSAFE
            
            if not userdata.visual_processor.spatial_enabled:
                return "Sensing unavailable. " + FAILSAFE

            # ── Freshness gate ──
            capture_ts = userdata.visual_processor.last_capture_epoch_ms
            if LIVE_INFRA_AVAILABLE and capture_ts and not is_frame_fresh(capture_ts):
                logger.warning("detect_obstacles: stale frame, returning failsafe")
                return FALLBACK_MESSAGE

            # Watchdog heartbeat
            if userdata._watchdog is not None:
                userdata._watchdog.heartbeat("camera")
            
            if detail_level == "quick":
                try:
                    warning = await asyncio.wait_for(
                        userdata.visual_processor.get_quick_warning(image),
                        timeout=0.5
                    )
                except asyncio.TimeoutError:
                    logger.warning("Quick obstacle detection timed out")
                    return FAILSAFE
                userdata._pending_spatial_warning = warning

                # Debounce check
                if userdata.should_debounce(warning):
                    logger.debug(f"Debounced duplicate cue: {warning}")
                    return warning  # Still return but LLM may suppress
                userdata.record_cue(warning)
                return warning
            else:
                try:
                    nav_output = await asyncio.wait_for(
                        userdata.visual_processor.process_spatial(image),
                        timeout=0.5
                    )
                except asyncio.TimeoutError:
                    logger.warning("Detailed obstacle detection timed out")
                    return FAILSAFE
                if nav_output is None:
                    return "Path clear."
                
                userdata._last_nav_output = nav_output
                if nav_output.has_critical:
                    userdata._pending_spatial_warning = nav_output.short_cue

                # Debounce check
                cue = nav_output.short_cue
                if userdata.should_debounce(cue):
                    logger.debug(f"Debounced duplicate cue: {cue}")
                    return cue
                userdata.record_cue(cue)
                return cue
            
        except Exception as e:
            logger.error(f"Obstacle detection error: {e}")
            return FAILSAFE
        finally:
            userdata.current_tool = "general"
    
    @function_tool()
    async def analyze_spatial_scene(
        self,
        context: RunContext_T,
        query: Annotated[str, Field(description="Spatial/navigation question")] = "What obstacles?"
    ) -> str:
        """ULTRA-FAST spatial analysis with freshness gate. Target: <200ms."""
        userdata = context.userdata
        userdata.current_tool = "spatial"
        FAILSAFE = "I can't see clearly right now — proceed with caution."
        
        try:
            # Fast frame capture
            image = await userdata.visual_processor.capture_frame(userdata.room_ctx.room)
            
            if image is None:
                return "Camera unavailable. " + FAILSAFE
            
            if not userdata.visual_processor.spatial_enabled:
                return "Sensing unavailable. " + FAILSAFE

            # ── Freshness gate ──
            capture_ts = userdata.visual_processor.last_capture_epoch_ms
            if LIVE_INFRA_AVAILABLE and capture_ts and not is_frame_fresh(capture_ts):
                logger.warning("analyze_spatial_scene: stale frame, returning failsafe")
                return FALLBACK_MESSAGE

            # Watchdog heartbeat
            if userdata._watchdog is not None:
                userdata._watchdog.heartbeat("camera")
            
            # Use VQA Engine if available for enhanced perception
            if VQA_ENGINE_AVAILABLE and userdata._vqa_pipeline:
                try:
                    cue = await asyncio.wait_for(
                        self._run_vqa_spatial(userdata, image, query),
                        timeout=0.5
                    )
                except asyncio.TimeoutError:
                    logger.warning("VQA spatial analysis timed out, falling back")
                    cue = None
                if cue:
                    if userdata.should_debounce(cue):
                        logger.debug(f"Debounced duplicate cue: {cue}")
                    else:
                        userdata.record_cue(cue)
                    return cue
            
            # Fallback to original spatial pipeline
            try:
                nav_output = await asyncio.wait_for(
                    userdata.visual_processor.process_spatial(image),
                    timeout=0.5
                )
            except asyncio.TimeoutError:
                logger.warning("Spatial pipeline timed out")
                return FAILSAFE
            
            if nav_output is None:
                return "Path clear."
            
            userdata._last_nav_output = nav_output
            userdata._last_obstacles = userdata.visual_processor.last_obstacles
            
            if nav_output.has_critical:
                userdata._pending_spatial_warning = nav_output.short_cue

            # Debounce check
            cue = nav_output.short_cue
            if userdata.should_debounce(cue):
                logger.debug(f"Debounced duplicate cue: {cue}")
            else:
                userdata.record_cue(cue)
            return cue
            
        except Exception as e:
            logger.error(f"Spatial error: {e}")
            return FAILSAFE
        finally:
            userdata.current_tool = "general"
    
    async def _run_vqa_spatial(self, userdata: UserData, image, query: str) -> str:
        """Run VQA engine for spatial analysis. Target: <300ms vision."""
        try:
            # Convert LiveKit VideoFrame → PIL so VQA pipeline gets .shape/.size
            from PIL import Image as PILImage
            if not isinstance(image, PILImage.Image):
                image = convert_video_frame_to_pil(image)
                if image is None:
                    return "Path clear."

            # Run full perception pipeline
            perception = await userdata._vqa_pipeline.process(image)
            
            # Build scene graph
            scene_graph = build_scene_graph(perception)
            
            # Apply spatial fusion with temporal filtering
            fused = userdata._vqa_fuser.fuse(perception)
            
            # Store in memory
            if userdata._vqa_memory and userdata._vqa_session_id:
                userdata._vqa_memory.store(
                    scene_graph, 
                    userdata._vqa_session_id,
                    question=query
                )
            
            # Try quick answer first (bypass LLM for speed)
            quick = QuickAnswers.try_quick_answer(query, fused)
            if quick:
                return quick
            
            # Format with MicroNav for concise response
            formatter = MicroNavFormatter()
            return formatter.format(fused, scene_graph)
            
        except Exception as e:
            logger.error(f"VQA spatial error: {e}")
            # Fallback to original pipeline
            nav_output = await userdata.visual_processor.process_spatial(image)
            return nav_output.short_cue if nav_output else "Path clear."
    
    @function_tool()
    async def ask_visual_question(
        self,
        context: RunContext_T,
        question: Annotated[str, Field(description="Visual question about the scene")]
    ) -> str:
        """
        Answer any visual question using VQA reasoning.
        Combines perception with LLM for accurate answers.
        Target: <500ms total.
        """
        userdata = context.userdata
        userdata.current_tool = "vqa"
        
        try:
            # Capture frame
            image = await userdata.visual_processor.capture_frame(userdata.room_ctx.room)
            
            if image is None:
                return "Camera unavailable. I can't see clearly right now — proceed with caution."

            # ── Freshness gate ──
            capture_ts = userdata.visual_processor.last_capture_epoch_ms
            if LIVE_INFRA_AVAILABLE and capture_ts and not is_frame_fresh(capture_ts):
                logger.warning("ask_visual_question: stale frame")
                return FALLBACK_MESSAGE if LIVE_INFRA_AVAILABLE else "I can't see clearly right now — proceed with caution."
            
            # Use VQA Engine if available
            if VQA_ENGINE_AVAILABLE and userdata._vqa_pipeline and userdata._vqa_reasoner:
                # Convert LiveKit VideoFrame → PIL so VQA pipeline gets .shape/.size
                from PIL import Image as PILImage
                if not isinstance(image, PILImage.Image):
                    image = convert_video_frame_to_pil(image)
                    if image is None:
                        return "I can't see clearly right now — proceed with caution."

                # Run perception
                perception = await userdata._vqa_pipeline.process(image)
                scene_graph = build_scene_graph(perception)
                fused = userdata._vqa_fuser.fuse(perception)
                
                # Create VQA request
                vqa_request = VQARequest(
                    question=question,
                    image=image,
                    scene_graph=scene_graph,
                    fused_result=fused,
                    max_tokens=100,
                )
                
                # Get answer
                response = await userdata._vqa_reasoner.answer(vqa_request)
                
                # Store in memory
                if userdata._vqa_memory and userdata._vqa_session_id:
                    userdata._vqa_memory.store(
                        scene_graph,
                        userdata._vqa_session_id,
                        question=question,
                        answer=response.answer
                    )
                
                return response.get_full_answer()
            
            # Fallback to visual analysis
            return await self._analyze_with_ollama(userdata, image, question)
            
        except Exception as e:
            logger.error(f"VQA error: {e}")
            return "I can't see clearly right now — proceed with caution."
        finally:
            userdata.current_tool = "general"
    
    async def _analyze_with_ollama(self, userdata: UserData, image, question: str) -> str:
        """Fallback visual analysis using Ollama."""
        try:
            if userdata.ollama_handler:
                # model_choice_with_analysis returns (model, analysis, error)
                _, response, error = await userdata.ollama_handler.model_choice_with_analysis(image, question)
                if error:
                    logger.warning(f"Ollama analysis error: {error}")
                return response[:200] if response else "Unable to analyze."
        except Exception as e:
            logger.error(f"Ollama fallback error: {e}")
        return "Unable to analyze."
    
    @function_tool()
    async def get_navigation_cue(
        self,
        context: RunContext_T
    ) -> str:
        """
        Get a quick navigation cue from a FRESH camera frame.
        Always captures a new image — never returns cached results.
        """
        userdata = context.userdata
        FAILSAFE = "I can't see clearly right now — proceed with caution."
        
        try:
            # FRESH-CONTEXT: always capture a new frame
            image = await userdata.visual_processor.capture_frame(userdata.room_ctx.room)
            if image is None:
                return "Camera unavailable. " + FAILSAFE

            # ── Freshness gate ──
            capture_ts = userdata.visual_processor.last_capture_epoch_ms
            if LIVE_INFRA_AVAILABLE and capture_ts and not is_frame_fresh(capture_ts):
                logger.warning("get_navigation_cue: stale frame, returning failsafe")
                return FALLBACK_MESSAGE
            
            try:
                warning = await asyncio.wait_for(
                    userdata.visual_processor.get_quick_warning(image),
                    timeout=0.5
                )
            except asyncio.TimeoutError:
                logger.warning("Navigation cue timed out")
                return FAILSAFE
            return warning
            
        except Exception as e:
            logger.error(f"Error getting navigation cue: {e}")
            return FAILSAFE
    
    @function_tool()
    async def scan_qr_code(
        self,
        context: RunContext_T,
        query: Annotated[str, Field(description="Optional context about the scan request")] = "scan"
    ) -> str:
        """
        Scan for QR codes or AR tags using the camera.
        Captures a fresh frame, decodes any QR/AR content,
        and returns a contextual spoken message.
        Use when the user says: scan QR, read code, what does this QR say, etc.
        """
        userdata = context.userdata
        userdata.current_tool = "qr"
        logger.info(f"[QR] scan_qr_code invoked — query='{query}'")

        if not userdata._qr_enabled or not userdata._qr_scanner:
            logger.warning("[QR] QR scanning disabled or scanner not initialised")
            return "QR scanning is not available."

        try:
            # ── Step 1: Fresh frame capture ────────────────────────────
            logger.info("[QR] Capturing fresh camera frame…")
            raw_frame = await userdata.visual_processor.capture_frame(userdata.room_ctx.room)
            if raw_frame is None:
                logger.error("[QR] capture_frame returned None — camera unavailable")
                return "Camera unavailable."

            # ── Freshness gate ──
            capture_ts = userdata.visual_processor.last_capture_epoch_ms
            if LIVE_INFRA_AVAILABLE and capture_ts and not is_frame_fresh(capture_ts):
                logger.warning("[QR] Stale frame detected")
                return "Camera feed interrupted — please try again."

            logger.info(f"[QR] Raw frame type: {type(raw_frame).__name__}")

            # ── Step 2: Convert LiveKit VideoFrame → PIL Image ─────────
            from PIL import Image as PILImage, ImageEnhance, ImageFilter
            if isinstance(raw_frame, PILImage.Image):
                pil_image = raw_frame
            else:
                pil_image = convert_video_frame_to_pil(raw_frame)
            if pil_image is None:
                logger.error("[QR] Frame-to-PIL conversion failed")
                return "Unable to process camera frame."
            logger.info(f"[QR] PIL image ready: {pil_image.size[0]}x{pil_image.size[1]} mode={pil_image.mode}")

            # ── Step 3: Pre-process for QR readability ─────────────────
            # Convert to grayscale (improves pyzbar binarisation)
            gray_image = pil_image.convert("L")
            # Sharpen to recover blurry edges
            sharp_image = gray_image.filter(ImageFilter.SHARPEN)
            # Also keep original colour version for fallback
            scan_images = [sharp_image, gray_image, pil_image]
            logger.info("[QR] Pre-processing complete (grayscale + sharpen)")

            # ── Step 4: Scan for QR codes ──────────────────────────
            detections = []
            for idx, img in enumerate(scan_images):
                logger.info(f"[QR] Scanning variant {idx+1}/{len(scan_images)} ({img.mode}, {img.size})…")
                found = await userdata._qr_scanner.scan_async(img)
                if found:
                    detections = found
                    logger.info(f"[QR] ✓ Found {len(found)} code(s) on variant {idx+1}")
                    break
            if not detections:
                logger.info("[QR] No QR codes found across all image variants")

            # ── Structured telemetry ───────────────────────────────────
            _qr_frame_id = f"qr_{int(time.time() * 1000)}"
            try:
                from shared.logging.logging_config import log_event as _qr_log
                _qr_log(
                    "qr-scanner", "qr_scan_attempt",
                    component="scan_qr_code",
                    frame_id=_qr_frame_id,
                    qr_found=bool(detections),
                    qr_data=detections[0].raw_data[:80] if detections else None,
                    num_variants_tried=idx + 1 if detections else len(scan_images),
                )
            except Exception:
                pass  # logging must never break the pipeline

            # ── Step 5: Scan for AR markers ────────────────────────────
            ar_markers = []
            if userdata._ar_handler and userdata._ar_handler.is_ready:
                logger.info("[QR] Checking for AR markers…")
                ar_markers = await userdata._ar_handler.detect_async(pil_image)
                if ar_markers:
                    logger.info(f"[QR] ✓ Found {len(ar_markers)} AR marker(s)")
                else:
                    logger.info("[QR] No AR markers detected")

            if not detections and not ar_markers:
                logger.info("[QR] Nothing detected — returning guidance")
                # ── Debug frame saving (gated by env var) ─────────────
                if os.environ.get("DEBUG_ENDPOINTS_ENABLED", "").lower() == "true":
                    try:
                        _dbg_dir = os.path.join("data", "debug_frames")
                        os.makedirs(_dbg_dir, exist_ok=True)
                        pil_image.save(os.path.join(_dbg_dir, f"qr_fail_{int(time.time()*1000)}.jpg"))
                        logger.info("[QR] Debug frame saved to %s", _dbg_dir)
                    except Exception as _save_err:
                        logger.debug("[QR] Debug frame save failed: %s", _save_err)
                return "No QR code or AR tag detected. Try pointing the camera directly at the code and holding steady."

            # ── Step 6: Decode first QR detection ──────────────────────
            if detections:
                raw = detections[0].raw_data
                logger.info(f"[QR] Decoding QR data: '{raw[:80]}' (format={detections[0].format_type})")

                # Check cache first (offline-first)
                if userdata._qr_cache:
                    cached = userdata._qr_cache.get(raw)
                    if cached:
                        msg = cached.contextual_message
                        if cached.navigation_available:
                            msg += " Would you like me to guide you there?"
                        logger.info(f"[QR] Cache HIT — returning cached message")
                        return msg

                # Decode and build context
                decoded = await userdata._qr_decoder.decode(raw)
                logger.info(f"[QR] Decoded type={decoded.content_type.value} nav={decoded.navigation_available}")

                # Store in cache
                if userdata._qr_cache:
                    userdata._qr_cache.put(
                        raw_data=decoded.raw_data,
                        content_type=decoded.content_type.value,
                        contextual_message=decoded.contextual_message,
                        metadata=decoded.metadata,
                        source="online",
                        navigation_available=decoded.navigation_available,
                        lat=decoded.lat,
                        lon=decoded.lon,
                    )
                    logger.info("[QR] Result cached")

                msg = decoded.contextual_message
                if decoded.navigation_available:
                    msg += " Would you like me to guide you there?"
                logger.info(f"[QR] Returning message: '{msg[:100]}'")
                return msg

            # Only AR markers
            ids = [str(m.marker_id) for m in ar_markers[:3]]
            msg = f"Detected AR marker(s): {', '.join(ids)}."
            logger.info(f"[QR] AR-only result: {msg}")
            return msg

        except Exception as e:
            logger.error(f"[QR] scan_qr_code exception: {e}", exc_info=True)
            return "Error scanning QR code."
        finally:
            # Release frame memory
            for _v in ("raw_frame", "pil_image", "gray_image", "sharp_image"):
                obj = locals().get(_v)
                if obj is not None and hasattr(obj, "close"):
                    try:
                        obj.close()
                    except Exception:
                        pass
            userdata.current_tool = "general"

    @function_tool()
    async def read_text(
        self,
        context: RunContext_T,
        query: Annotated[str, Field(description="Optional context for the OCR request")] = "read text"
    ) -> str:
        """
        Read text from the camera using OCR.
        Use when the user says: read this, what does this say, read text, etc.
        """
        userdata = context.userdata
        userdata.current_tool = "ocr"
        FAILSAFE = "I can't read the text clearly right now."

        if not OCR_ENGINE_AVAILABLE or userdata._ocr_pipeline is None:
            return "Text reading is not available."

        try:
            image = await userdata.visual_processor.capture_frame(userdata.room_ctx.room)
            if image is None:
                return "Camera unavailable. " + FAILSAFE

            from PIL import Image as PILImage
            if not isinstance(image, PILImage.Image):
                image = convert_video_frame_to_pil(image)
                if image is None:
                    return FAILSAFE

            result = await asyncio.wait_for(
                userdata._ocr_pipeline.process(image),
                timeout=2.0,
            )

            if result.error:
                logger.warning(f"OCR error: {result.error}")
                return FAILSAFE
            if not result.full_text.strip():
                return "No readable text detected."
            return f"Text reads: {result.full_text.strip()}"

        except asyncio.TimeoutError:
            logger.warning("OCR timed out")
            return FAILSAFE
        except Exception as e:
            logger.error(f"OCR error: {e}")
            return FAILSAFE
        finally:
            userdata.current_tool = "general"

    async def _process_stream(self, chat_ctx, tools, userdata):
        """FAST stream processing with minimal overhead."""
        full_response = ""
        
        # Handle vision analysis
        if userdata.current_tool == "visual" and userdata._model_choice:
            if userdata._model_choice == LLM_MODEL:
                # Fast streaming with shorter timeout
                chunk_queue = asyncio.Queue()
                done_event = asyncio.Event()
                userdata._add_chunk_callback = lambda c: chunk_queue.put_nowait(c)
                
                # Add existing chunks
                for c in userdata._ollama_chunks:
                    chunk_queue.put_nowait(c)
                
                try:
                    while not (done_event.is_set() and chunk_queue.empty()):
                        try:
                            chunk = await asyncio.wait_for(chunk_queue.get(), timeout=0.05)  # Faster timeout
                            full_response += chunk
                            yield ChatChunk(
                                id="cmpl",
                                delta=ChoiceDelta(role="assistant", content=chunk),
                                usage=None
                            )
                        except asyncio.TimeoutError:
                            if userdata._analysis_complete and chunk_queue.empty():
                                done_event.set()
                finally:
                    userdata._add_chunk_callback = None
                    userdata._ollama_chunks.clear()
            
            elif userdata._ollama_analysis:
                full_response = userdata._ollama_analysis
                yield ChatChunk(
                    id="cmpl",
                    delta=ChoiceDelta(role="assistant", content=full_response),
                    usage=None
                )
                userdata._ollama_analysis = None
            
            else:
                full_response = "Vision unavailable."
                yield ChatChunk(
                    id="cmpl",
                    delta=ChoiceDelta(role="assistant", content=full_response),
                    usage=None
                )
            
            userdata._model_choice = None
        
        # Standard LLM - FAST settings
        else:
            llm_instance = openai.LLM(
                model=LLM_MODEL,
                base_url=LLM_BASE_URL,
                api_key=LLM_API_KEY,
                temperature=0.2,  # Lower = faster
            )
            async with llm_instance.chat(chat_ctx=chat_ctx, tools=tools) as stream:
                async for chunk in stream:
                    if isinstance(chunk, ChatChunk) and chunk.delta and hasattr(chunk.delta, 'content') and chunk.delta.content:
                        full_response += chunk.delta.content
                    yield chunk
        
        userdata.last_response = full_response
    
    async def llm_node(self, chat_ctx, tools, model_settings=None):
        """FAST LLM node."""
        userdata = self.session.userdata
        async for chunk in self._process_stream(chat_ctx, tools, userdata):
            yield chunk

    @function_tool()
    async def manage_calendar(
        self,
        context: RunContext_T,
        action: Annotated[str, Field(description="Action to perform: 'add_event' or 'get_events'")],
        title: Annotated[Optional[str], Field(description="Title of the event (for add_event only)")] = None,
        description: Annotated[Optional[str], Field(description="Description of the event (for add_event only)")] = None,
        start_time: Annotated[Optional[str], Field(description="Start time of the event in ISO format (for add_event only)")] = None,
        start_date: Annotated[Optional[str], Field(description="Start date in ISO format (for get_events only)")] = None,
        end_date: Annotated[Optional[str], Field(description="End date in ISO format (for get_events only)")] = None,
    ) -> str:
        """
        Manage calendar events - add new events or view scheduled events.
        
        For adding events, specify action='add_event', title, description, and start_time.
        For viewing events, specify action='get_events', start_date, and end_date.
        """
        userdata = context.userdata
        
        # Switch to calendar mode
        userdata.current_tool = "calendar"
        
        # Ensure we have the calendar tool
        if userdata.calendar_tool is None:
            userdata.calendar_tool = CalendarTool()
            logger.info("Created calendar tool on demand")
        
        # Prepare kwargs based on action
        kwargs = {}
        if action == "add_event":
            if not all([title, start_time]):
                return "Title and start time are required for adding events."
            kwargs = {
                "title": title,
                "description": description or "",
                "start_time": start_time
            }
            logger.info(f"Adding calendar event: {title} at {start_time}")
        elif action == "get_events":
            if not all([start_date, end_date]):
                return "Start date and end date are required for viewing events."
            kwargs = {
                "start_date": start_date,
                "end_date": end_date
            }
            logger.info(f"Getting calendar events from {start_date} to {end_date}")
        else:
            return f"Unsupported calendar action: {action}"
        
        try:
            # Call the unified calendar management method
            result = await userdata.calendar_tool.manage_calendar(action, **kwargs)
            
            # Store the response for future reference
            userdata.last_response = result
            
            # Switch back to general mode after completing calendar action
            userdata.current_tool = "general"
            
            return result
            
        except Exception as e:
            logger.error(f"Error in calendar action {action}: {e}")
            return f"I encountered an error while performing the calendar operation: {str(e)}"

    @function_tool()
    async def manage_communication(
        self,
        context: RunContext_T,
        action: Annotated[str, Field(description="Action to perform: 'find_contact', 'read_emails', or 'send_email'")],
        name: Annotated[Optional[str], Field(description="Name of the contact to find (for find_contact only)")] = None,
        from_date: Annotated[Optional[str], Field(description="From date in ISO format (for read_emails only)")] = None,
        to_date: Annotated[Optional[str], Field(description="To date in ISO format (for read_emails only)")] = None,
        email: Annotated[Optional[str], Field(description="Email to filter by (optional for read_emails) or recipient (for send_email)")] = None,
        subject: Annotated[Optional[str], Field(description="Email subject (for send_email only)")] = None,
        body: Annotated[Optional[str], Field(description="Email body content (for send_email only)")] = None,
    ) -> str:
        """
        Manage contacts and emails - find contacts, read emails, or send messages.
        
        For finding contacts, specify action='find_contact' and name.
        For reading emails, specify action='read_emails', from_date, to_date, and optionally email.
        For sending emails, specify action='send_email', email (recipient), subject, and body.
        """
        userdata = context.userdata
        
        # Switch to communication mode
        userdata.current_tool = "communication"
        
        # Ensure we have the communication tool
        if userdata.communication_tool is None:
            userdata.communication_tool = CommunicationTool()
            logger.info("Created communication tool on demand")
        
        # Prepare kwargs based on action
        kwargs = {}
        if action == "find_contact":
            if not name:
                return "Contact name is required for finding contacts."
            kwargs = {"name": name}
            logger.info(f"Finding contact information for: {name}")
        elif action == "read_emails":
            if not all([from_date, to_date]):
                return "From date and to date are required for reading emails."
            kwargs = {
                "from_date": from_date,
                "to_date": to_date
            }
            if email:
                kwargs["email"] = email
            logger.info(f"Reading emails from {from_date} to {to_date}" + (f" from {email}" if email else ""))
        elif action == "send_email":
            if not all([email, subject, body]):
                return "Recipient email, subject, and body are required for sending emails."
            kwargs = {
                "to": email,
                "subject": subject,
                "body": body
            }
            logger.info(f"Sending email to: {email} with subject: {subject}")
        else:
            return f"Unsupported communication action: {action}"
        
        try:
            # Call the unified communication management method
            result = await userdata.communication_tool.manage_communication(action, **kwargs)
            
            # Store the response for future reference
            userdata.last_response = result
            
            # Switch back to general mode after completing communication action
            userdata.current_tool = "general"
            
            return result
            
        except Exception as e:
            logger.error(f"Error in communication action {action}: {e}")
            return f"I encountered an error while performing the communication operation: {str(e)}"

async def entrypoint(ctx: JobContext):
    """Set up and start the voice agent with all required tools"""
    try:
        # Connect with retry logic for transient LiveKit Cloud failures
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                await ctx.connect()
                break
            except Exception as conn_err:
                if attempt < max_retries:
                    wait = attempt * 2
                    logger.warning(
                        f"Room connect attempt {attempt}/{max_retries} failed: {conn_err}. "
                        f"Retrying in {wait}s..."
                    )
                    await asyncio.sleep(wait)
                else:
                    raise  # re-raise on final failure
        
        # Get spatial config
        spatial_config = get_spatial_config()
        
        # Create user data with tools
        userdata = UserData()
        userdata.room_ctx = ctx
        userdata._spatial_enabled = spatial_config["enabled"]
        
        # Initialize visual processor with spatial perception
        userdata.visual_processor = VisualProcessor(enable_spatial=spatial_config["enabled"])
        userdata.internet_search = InternetSearch()
        userdata.places_search = PlacesSearch()
        userdata.calendar_tool = CalendarTool()
        userdata.communication_tool = CommunicationTool()
        
        # Initialize VQA Engine if available
        if VQA_ENGINE_AVAILABLE:
            try:
                # Resolve "auto" → True/False based on model file presence
                _yolo_cfg = spatial_config.get("use_yolo", "auto")
                _midas_cfg = spatial_config.get("use_midas", "auto")
                _yolo_path = spatial_config.get("yolo_model_path", "models/yolov8n.onnx")
                _midas_path = spatial_config.get("midas_model_path", "models/midas_v21_small_256.onnx")

                if _yolo_cfg == "auto":
                    _use_yolo = os.path.isfile(_yolo_path)
                else:
                    _use_yolo = _yolo_cfg in (True, "true", "1")

                if _midas_cfg == "auto":
                    _use_midas = os.path.isfile(_midas_path)
                else:
                    _use_midas = _midas_cfg in (True, "true", "1")

                # ── Startup model-load diagnostics ──
                logger.info("YOLO model path: %s, exists=%s, use=%s", _yolo_path, os.path.isfile(_yolo_path), _use_yolo)
                logger.info("MiDaS model path: %s, exists=%s, use=%s", _midas_path, os.path.isfile(_midas_path), _use_midas)

                userdata._vqa_pipeline = create_perception_pipeline(
                    use_mock=False,
                    use_yolo=_use_yolo,
                    use_midas=_use_midas,
                )
                userdata._vqa_fuser = SpatialFuser()
                userdata._vqa_reasoner = VQAReasoner(
                    llm_client=None,  # Will use fallback MicroNav
                    model=LLM_MODEL,
                    use_micronav_fallback=True,
                )
                userdata._vqa_memory = VQAMemory()
                userdata._vqa_session_id = f"session_{int(time.time()*1000)}"
                logger.info("VQA Engine initialized: perception, fusion, reasoning, memory active")

                # ── Model warm-up: run a dummy inference to pre-fill caches ──
                try:
                    from PIL import Image as _PILImage
                    _warmup_img = _PILImage.new("RGB", (640, 480), color=(128, 128, 128))
                    await userdata._vqa_pipeline.process(_warmup_img)
                    logger.info("VQA pipeline warm-up complete (cold-start avoided)")
                except Exception as warmup_exc:
                    logger.warning("VQA warm-up skipped: %s", warmup_exc)
            except Exception as e:
                logger.warning(f"VQA Engine initialization failed, using fallback: {e}")
                userdata._vqa_pipeline = None
        else:
            logger.info("VQA Engine not available, using original spatial pipeline")
        
        # Initialize QR / AR scanning engine
        if QR_ENGINE_AVAILABLE and qr_enabled():
            try:
                qr_cfg = get_qr_config()
                userdata._qr_scanner = QRScanner()
                userdata._qr_decoder = QRDecoder()
                userdata._ar_handler = ARTagHandler()
                if qr_cfg["cache_enabled"]:
                    cache_kwargs = {"ttl": qr_cfg["cache_ttl"]}
                    if qr_cfg["cache_dir"]:
                        cache_kwargs["cache_dir"] = qr_cfg["cache_dir"]
                    userdata._qr_cache = CacheManager(**cache_kwargs)
                userdata._qr_enabled = True
                _qr_backend = "pyzbar" if userdata._qr_scanner._use_pyzbar else (
                    "cv2" if userdata._qr_scanner._use_cv2 else "none"
                )
                logger.info(
                    "QR/AR scanning engine initialised (scanner=%s, decoder + cache)",
                    _qr_backend,
                )
            except Exception as e:
                logger.warning(f"QR engine initialisation failed: {e}")
                userdata._qr_enabled = False
        else:
            logger.info("QR/AR scanning not available or disabled")

        # Log spatial perception status
        if userdata.visual_processor.spatial_enabled:
            logger.info("Spatial perception enabled: object detection, segmentation, and depth estimation active")
        else:
            logger.info("Spatial perception disabled or not available")

        # ── Voice Router (speech_vqa_bridge) ──────────────────────────
        if VOICE_ROUTER_AVAILABLE:
            try:
                userdata._voice_router = VoiceRouter()
                logger.info("VoiceRouter initialised for intent classification")
            except Exception as e:
                logger.warning(f"VoiceRouter init failed: {e}")

        # ── OCR Engine ────────────────────────────────────────────────
        if OCR_ENGINE_AVAILABLE:
            try:
                userdata._ocr_pipeline = OCRPipeline()
                if userdata._ocr_pipeline.is_ready:
                    logger.info("OCR pipeline ready")
                else:
                    logger.info("OCR pipeline created but no backend available")
            except Exception as e:
                logger.warning(f"OCR pipeline init failed: {e}")

        # ── Session Logger ────────────────────────────────────────────
        if SESSION_LOGGER_AVAILABLE:
            try:
                userdata._session_logger = SessionLogger()
                userdata._session_id = userdata._session_logger.create_session()
                logger.info(f"Session logger active: {userdata._session_id}")
            except Exception as e:
                logger.warning(f"Session logger init failed: {e}")

        # ── Live-frame infrastructure (Debouncer, Watchdog) ──────────
        if LIVE_INFRA_AVAILABLE:
            try:
                # Freshness budget from config
                lf_cfg = get_live_frame_config()
                set_freshness_max_age(lf_cfg.get("max_age_ms", 500))

                # Debouncer
                db_cfg = get_debounce_config()
                userdata._debouncer = Debouncer(DebouncerConfig(
                    debounce_window_seconds=db_cfg.get("window_seconds", 5.0),
                    distance_delta_meters=db_cfg.get("distance_delta_m", 0.5),
                    confidence_delta=db_cfg.get("confidence_delta", 0.15),
                ))

                # Watchdog
                wd_cfg = get_watchdog_config()
                userdata._watchdog = Watchdog(WatchdogConfig(
                    camera_stall_threshold_ms=wd_cfg.get("camera_stall_ms", 2000),
                    worker_stall_threshold_ms=wd_cfg.get("worker_stall_ms", 5000),
                    check_interval_ms=wd_cfg.get("check_interval_ms", 500),
                ))
                userdata._watchdog.register_component("camera")
                userdata._watchdog.register_component("orchestrator")

                # ── Watchdog alert: restart camera + speak warning ─────
                async def _on_watchdog_alert(component: str, message: str):
                    logger.warning("Watchdog alert [%s]: %s", component, message)
                    if component == "camera":
                        # Reset the persistent video stream so next capture retries
                        try:
                            vp = userdata.visual_processor
                            if vp._persistent_stream:
                                try:
                                    await vp._persistent_stream.aclose()
                                except Exception:
                                    pass
                                vp._persistent_stream = None
                                vp._cached_video_track = None
                                logger.info("Camera stream reset by watchdog")
                        except Exception as exc:
                            logger.error("Camera restart failed: %s", exc)

                userdata._watchdog.on_alert(_on_watchdog_alert)
                await userdata._watchdog.start()

                userdata._live_infra_ready = True
                logger.info("Live-frame infrastructure ready: freshness=%dms, debounce=%.1fs, watchdog active",
                            lf_cfg.get("max_age_ms", 500), db_cfg.get("window_seconds", 5.0))
            except Exception as e:
                logger.warning(f"Live-frame infra init failed (non-fatal): {e}")

        # Initialize optional components with graceful fallbacks
        try:
            userdata.ollama_handler = OllamaHandler()
        except Exception as e:
            logger.warning(f"Vision will use ollama:{LLM_MODEL} only: {e}")
            
        try:
            await userdata.visual_processor.enable_camera(ctx.room)
        except Exception as e:
            logger.warning(f"Camera setup failed: {e}")

        # ══════════════════════════════════════════════════════════════
        # RUNTIME DIAGNOSTICS — TTS & VQA preflight + SYSTEM_STATUS
        # ══════════════════════════════════════════════════════════════
        try:
            diag = get_diagnostics()

            async def _capture_for_preflight():
                """Capture a frame for VQA preflight using VisualProcessor."""
                return await userdata.visual_processor.capture_frame(ctx.room)

            system_status = await diag.run_all_preflight(
                vqa_pipeline=userdata._vqa_pipeline,
                capture_frame_fn=_capture_for_preflight,
                tts_provider="elevenlabs",
                tts_model="eleven_turbo_v2_5",
                tts_voice_id="21m00Tcm4TlvDq8ikWAM",
                tts_sample_rate=44100,
                tts_codec="mp3_44100_128",
            )

            # Log the full structured status
            logger.info("SYSTEM_STATUS: %s", system_status.to_json())
            logger.info("Startup health: %s | %s",
                        system_status.system_status, system_status.human_summary)

            # If VQA was skipped, log remediation
            if system_status.vqa and system_status.vqa.status == "skipped":
                logger.warning(
                    "VQA SKIPPED [%s]: %s\n  Remediation: %s\n  Reproduce: %s",
                    system_status.vqa.skip_code,
                    system_status.vqa.message,
                    system_status.vqa.remediation,
                    system_status.vqa.reproduce_command,
                )
        except Exception as diag_err:
            logger.warning(f"Runtime diagnostics failed (non-fatal): {diag_err}")
        
        # Create and start agent
        agent = AllyVisionAgent()
        
        # Configure LLM - FAST settings
        llm_instance = openai.LLM(
            model=LLM_MODEL,
            base_url=LLM_BASE_URL,
            api_key=LLM_API_KEY,
            parallel_tool_calls=False,
            temperature=0.2,  # Lower = faster, more deterministic
        )
        
        agent_session = AgentSession[UserData](
            userdata=userdata,
            stt=deepgram.STT(model="nova-3", language="en"),
            llm=llm_instance,
            tts=elevenlabs.TTS(
                model="eleven_turbo_v2_5",
                voice_id="21m00Tcm4TlvDq8ikWAM",
            ),
            vad=silero.VAD.load(),
            max_tool_steps=1,  # Single tool call for speed
        )
        
        # Check for avatar configuration
        config = get_config()
        avatar = None
        
        # Only enable avatar if explicitly configured and all required parameters are present
        avatar_enabled = config.get("ENABLE_AVATAR", False) and config.get("TAVUS_REPLICA_ID") and config.get("TAVUS_PERSONA_ID")
        
        if avatar_enabled:
            try:
                # Get avatar configuration from environment
                replica_id = config.get("TAVUS_REPLICA_ID")
                persona_id = config.get("TAVUS_PERSONA_ID")
                avatar_name = config.get("TAVUS_AVATAR_NAME", "ally-vision-avatar")
                
                # Initialize avatar session
                logger.info(f"Initializing Tavus avatar with replica_id: {replica_id}, persona_id: {persona_id}")
                avatar = tavus.AvatarSession(
                    replica_id=replica_id,
                    persona_id=persona_id,
                    avatar_participant_name=avatar_name
                )
                
                # Start the avatar and wait for it to join
                try:
                    await avatar.start(agent_session, room=ctx.room)
                    logger.info(f"Tavus avatar started successfully with name: {avatar_name}")
                except Exception as e:
                    logger.error(f"Failed to start Tavus avatar, continuing without avatar: {e}")
                    avatar = None
                    avatar_enabled = False
            except Exception as e:
                logger.error(f"Failed to initialize Tavus avatar: {e}")
                avatar = None
                avatar_enabled = False
        
        # Start the agent session with room options
        await agent_session.start(
            agent=agent,
            room=ctx.room,
            room_options=RoomOptions(
                audio_output=avatar is None,  # Disable if avatar handles audio
            ),
        )

        # ── Wire watchdog TTS warning now that agent_session exists ──
        if LIVE_INFRA_AVAILABLE and getattr(userdata, "_watchdog", None):
            _session_ref = agent_session  # capture for closure

            async def _on_watchdog_tts(component: str, message: str):
                try:
                    if hasattr(_session_ref, "say"):
                        await _session_ref.say(
                            f"Warning: {component} has stalled. Attempting recovery."
                        )
                except Exception as exc:
                    logger.debug("Watchdog TTS announcement failed: %s", exc)

            userdata._watchdog.on_alert(_on_watchdog_tts)
            logger.info("Watchdog TTS alerts wired to agent session")

        # ══════════════════════════════════════════════════════════════
        # CONTINUOUS FRAME PROCESSING — Producer → Consumer → Announce
        # ══════════════════════════════════════════════════════════════
        continuous_cfg = get_continuous_config()
        lf_cfg = get_live_frame_config()

        if LIVE_INFRA_AVAILABLE and continuous_cfg["continuous_processing"]:
            try:
                # ── Build capture function from VisualProcessor ──
                async def _livekit_capture():
                    """Capture one frame from the LiveKit video stream."""
                    img = await userdata.visual_processor.capture_frame(ctx.room)
                    if img is None:
                        return None
                    w = getattr(img, "width", 0)
                    h = getattr(img, "height", 0)
                    if w == 0 and hasattr(img, "size"):
                        w, h = img.size
                    return (img, w, h)

                # ── Create & start LiveFrameManager ──
                lfm = LiveFrameManager(
                    capture_fn=_livekit_capture,
                    cadence_ms=lf_cfg.get("capture_cadence_ms", 100),
                    buffer_capacity=lf_cfg.get("frame_buffer_capacity", 30),
                    max_age_ms=lf_cfg.get("live_frame_max_age_ms", 500),
                )
                userdata._live_frame_mgr = lfm

                # Wire watchdog heartbeat to every captured frame
                if userdata._watchdog:
                    lfm.on_frame(lambda _f: userdata._watchdog.heartbeat("camera"))

                # Subscribe a consumer
                consumer = lfm.subscribe("continuous_consumer", max_queue_size=3)

                # ── Create FrameOrchestrator ──
                scene_builder = None
                if VQA_ENGINE_AVAILABLE and userdata._vqa_pipeline:
                    try:
                        scene_builder = SceneGraphBuilder()
                    except Exception:
                        pass

                orch = FrameOrchestrator(
                    config=FrameOrchestratorConfig(
                        live_frame_max_age_ms=lf_cfg.get("live_frame_max_age_ms", 500),
                        hot_path_timeout_ms=lf_cfg.get("hot_path_timeout_ms", 500),
                        pipeline_timeout_ms=lf_cfg.get("pipeline_timeout_ms", 300),
                    ),
                    scene_graph_builder=scene_builder,
                )

                # Build detector function from VQA pipeline (if available)
                detector_fn = None
                depth_fn = None
                if VQA_ENGINE_AVAILABLE and userdata._vqa_pipeline:
                    pipeline = userdata._vqa_pipeline
                    # ── Detector callable ────────────────────────────
                    if hasattr(pipeline, "detect"):
                        detector_fn = pipeline.detect
                    elif hasattr(pipeline, "detector") and pipeline.detector is not None:
                        _det = pipeline.detector
                        if hasattr(_det, "detect"):
                            async def _detect(img, _d=_det):
                                return await _d.detect(img)
                            detector_fn = _detect
                    # ── Depth callable ───────────────────────────────
                    if hasattr(pipeline, "estimate_depth"):
                        depth_fn = pipeline.estimate_depth
                    elif hasattr(pipeline, "depth_estimator") and pipeline.depth_estimator is not None:
                        _de = pipeline.depth_estimator
                        if hasattr(_de, "estimate"):
                            async def _depth(img, _e=_de):
                                return await _e.estimate(img)
                            depth_fn = _depth

                    if detector_fn:
                        logger.info("Frame orchestrator: detector_fn WIRED from VQA pipeline")
                    else:
                        logger.warning("Frame orchestrator: detector_fn is None — no detections will run")
                    if depth_fn:
                        logger.info("Frame orchestrator: depth_fn WIRED from VQA pipeline")
                    else:
                        logger.info("Frame orchestrator: depth_fn is None — depth estimation disabled")

                # ── Latest result store (shared with proactive announcer) ──
                _latest_fused: dict = {"result": None}

                # ── Continuous consumer loop ──
                async def _continuous_consumer():
                    """Pull frames from LiveFrameManager → run through orchestrator."""
                    logger.info("Continuous frame consumer started")
                    while lfm.running:
                        frame = await consumer.get_frame(timeout=2.0)
                        if frame is None:
                            continue
                        try:
                            result = await orch.process_frame(
                                frame,
                                detector=detector_fn,
                                depth_estimator=depth_fn,
                            )
                            _latest_fused["result"] = result
                            if userdata._watchdog:
                                userdata._watchdog.heartbeat("orchestrator")
                        except Exception as exc:
                            logger.error("Continuous consumer error: %s", exc)
                    logger.info("Continuous frame consumer stopped")

                # ── Proactive announcer loop ──
                _tts_lock = asyncio.Lock()       # prevent concurrent say() calls
                _last_say_ts: float = 0.0        # epoch of last successful say()
                _MIN_SAY_INTERVAL = 3.0          # seconds between say() calls

                async def _proactive_announcer():
                    """Periodically speak hazard warnings without user input."""
                    nonlocal _last_say_ts
                    cadence = continuous_cfg.get("proactive_cadence_s", 2.0)
                    critical_only = continuous_cfg.get("proactive_critical_only", False)
                    debouncer = userdata._debouncer
                    logger.info("Proactive announcer started (cadence=%.1fs, critical_only=%s)",
                                cadence, critical_only)
                    while lfm.running:
                        await asyncio.sleep(cadence)
                        result = _latest_fused.get("result")
                        if result is None:
                            continue
                        if not result.is_fresh(lf_cfg.get("live_frame_max_age_ms", 500)):
                            continue
                        cue = result.short_cue
                        if not cue or cue == "Scene analyzed.":
                            continue
                        # Optional: only announce critical hazards
                        if critical_only and "stop" not in cue.lower() and "critical" not in cue.lower():
                            continue
                        # Debounce
                        if debouncer and not debouncer.should_speak(cue, scene_graph_hash=result.scene_graph_hash):
                            continue
                        if debouncer:
                            debouncer.record(cue, scene_graph_hash=result.scene_graph_hash)
                        # Speak via TTS — with lock & cooldown to avoid websocket churn
                        try:
                            if hasattr(agent_session, "say"):
                                # Guard: only speak when session is fully running.
                                _is_running = (
                                    getattr(agent_session, "started", None)
                                    or getattr(agent_session, "_started", None)
                                    or getattr(agent_session, "_running", None)
                                    or True  # Fallback: assume running if no flag exists
                                )
                                if not _is_running:
                                    logger.debug("Proactive cue skipped (session not started): %s", cue)
                                    continue

                                # Cooldown: don't spam ElevenLabs websockets
                                now = time.time()
                                if (now - _last_say_ts) < _MIN_SAY_INTERVAL:
                                    logger.debug("Proactive cue throttled (cooldown): %s", cue)
                                    continue

                                # Lock: only one say() at a time
                                if _tts_lock.locked():
                                    logger.debug("Proactive cue skipped (TTS busy): %s", cue)
                                    continue
                                async with _tts_lock:
                                    await agent_session.say(cue)
                                    _last_say_ts = time.time()
                                    logger.info("Proactive announce: %s", cue)
                            else:
                                logger.debug("Proactive cue (no TTS): %s", cue)
                        except Exception as exc:
                            logger.warning("Proactive TTS error: %s", exc)
                    logger.info("Proactive announcer stopped")

                # ── Launch background tasks ──
                asyncio.create_task(lfm.start(), name="live_frame_manager")
                asyncio.create_task(_continuous_consumer(), name="continuous_consumer")
                logger.info("Continuous frame processing ACTIVE (cadence=%.0fms)",
                            lf_cfg.get("capture_cadence_ms", 100))

                if continuous_cfg.get("always_on") and continuous_cfg.get("proactive_announce"):
                    userdata._proactive_enabled = True
                    asyncio.create_task(_proactive_announcer(), name="proactive_announcer")
                    logger.info("ALWAYS_ON proactive mode ACTIVE")

            except Exception as e:
                logger.warning(f"Continuous processing startup failed (non-fatal): {e}")
        else:
            logger.info("Continuous processing disabled or infrastructure unavailable")
        
    except Exception as e:
        logger.error(f"Agent startup failed: {e}")