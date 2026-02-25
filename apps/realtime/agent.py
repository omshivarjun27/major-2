import logging
import os
import time
from dataclasses import dataclass, field
from typing import Annotated, Any, List, Optional

from livekit.agents import JobContext
from livekit.agents.llm import function_tool
from livekit.agents.voice import Agent, RunContext
from livekit.plugins import deepgram, elevenlabs, silero, tavus  # noqa: F401 — used by session_manager
from pydantic import Field

# ── Tool router (T-041 extraction) ─────────────────────────────────────
from apps.realtime.tool_router import (
    validate_detail_level,
    validate_query,
)
from core.vision.spatial import NavigationOutput, ObstacleRecord

# Import the tools
from core.vision.visual import VisualProcessor
from infrastructure.llm.internet_search import InternetSearch
from infrastructure.llm.ollama.handler import OllamaHandler
from shared.config import (
    get_config,
)
from shared.utils.timing import get_profiler, time_end, time_start

# ── Live-frame & freshness infrastructure ─────────────────────────────────
try:
    from application.frame_processing.freshness import is_frame_fresh  # noqa: F401 — probe
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

# Import VQA Engine (probe — actual use in vision_controller)
try:
    import core.vqa  # noqa: F401
    VQA_ENGINE_AVAILABLE = True
except ImportError:
    VQA_ENGINE_AVAILABLE = False

# Import QR Engine (probe — actual use in voice_controller)
try:
    import core.qr  # noqa: F401
    QR_ENGINE_AVAILABLE = True
except ImportError:
    QR_ENGINE_AVAILABLE = False

# Import Speech-VQA Bridge (probe)
try:
    import core.speech.voice_router  # noqa: F401
    VOICE_ROUTER_AVAILABLE = True
except ImportError:
    VOICE_ROUTER_AVAILABLE = False

# Import OCR Engine (probe)
try:
    import core.ocr  # noqa: F401
    OCR_ENGINE_AVAILABLE = True
except ImportError:
    OCR_ENGINE_AVAILABLE = False

# Import Debug Session Logger (probe)
try:
    import apps.cli.session_logger  # noqa: F401
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

# Spatial trigger phrases — imported from tool_router (T-041)
# SPATIAL_TRIGGER_PHRASES is imported at the top of this file from tool_router


class AllyVisionAgent(Agent):
    """
    REAL-TIME Vision & Navigation Assistant.
    Consistent, contextual, non-trigger-happy.
    Target: <500ms end-to-end.
    """
    def __init__(self) -> None:
        super().__init__(instructions=VISION_SYSTEM_PROMPT)

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
    async def search_internet(
        self,
        context: RunContext_T,
        query: Annotated[str, Field(description="Search query for the web")]
    ) -> str:
        """
        Search for up-to-date information on the web.
        Provides results with source links.
        """
        from apps.realtime import voice_controller as voc
        return await voc.search_internet(context.userdata, validate_query(query))

    async def _run_ollama_analysis(self, userdata, analysis_llm, visual_ctx):
        """Delegate to vision_controller.run_ollama_analysis."""
        from apps.realtime import vision_controller as vc
        await vc.run_ollama_analysis(userdata, analysis_llm, visual_ctx)

    @function_tool()
    async def analyze_vision(
        self,
        context: RunContext_T,
        query: Annotated[str, Field(description="Query about the visual scene")]
    ) -> str:
        """FAST visual scene analysis with freshness gate and failsafe."""
        from apps.realtime import vision_controller as vc
        return await vc.analyze_vision(
            context.userdata,
            validate_query(query),
            llm_model=LLM_MODEL,
            llm_base_url=LLM_BASE_URL,
            llm_api_key=LLM_API_KEY,
        )

    @function_tool()
    async def detect_obstacles(
        self,
        context: RunContext_T,
        detail_level: Annotated[str, Field(description="'quick' or 'detailed'")] = "quick"
    ) -> str:
        """ULTRA-FAST obstacle detection with freshness gate. Target: <200ms."""
        from apps.realtime import vision_controller as vc
        return await vc.detect_obstacles(context.userdata, validate_detail_level(detail_level))

    @function_tool()
    async def analyze_spatial_scene(
        self,
        context: RunContext_T,
        query: Annotated[str, Field(description="Spatial/navigation question")] = "What obstacles?"
    ) -> str:
        """ULTRA-FAST spatial analysis with freshness gate. Target: <200ms."""
        from apps.realtime import vision_controller as vc
        return await vc.analyze_spatial_scene(context.userdata, validate_query(query))

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
        from apps.realtime import vision_controller as vc
        return await vc.ask_visual_question(context.userdata, validate_query(question))

    @function_tool()
    async def get_navigation_cue(
        self,
        context: RunContext_T
    ) -> str:
        """
        Get a quick navigation cue from a FRESH camera frame.
        Always captures a new image — never returns cached results.
        """
        from apps.realtime import vision_controller as vc
        return await vc.get_navigation_cue(context.userdata)

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
        from apps.realtime import voice_controller as voc
        return await voc.scan_qr_code(context.userdata, validate_query(query))

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
        from apps.realtime import vision_controller as vc
        return await vc.read_text(context.userdata, validate_query(query))

    async def _process_stream(self, chat_ctx, tools, userdata):
        """Delegate stream processing to voice_controller."""
        from apps.realtime import voice_controller as voc
        async for chunk in voc.process_stream(
            chat_ctx, tools, userdata,
            llm_model=LLM_MODEL, llm_base_url=LLM_BASE_URL, llm_api_key=LLM_API_KEY,
        ):
            yield chunk

    async def llm_node(self, chat_ctx, tools, model_settings=None):
        """FAST LLM node."""
        userdata = self.session.userdata
        async for chunk in self._process_stream(chat_ctx, tools, userdata):
            yield chunk
async def entrypoint(ctx: JobContext):
    """Set up and start the voice agent with all required tools.

    Delegates session lifecycle to session_manager (T-038 extraction).
    """
    from apps.realtime.session_manager import (
        _warmup_vqa,
        connect_with_retry,
        create_agent_session,
        initialize_components,
        run_diagnostics,
        setup_avatar,
        start_agent_session,
        start_continuous_processing,
        wire_watchdog_tts,
    )

    try:
        # 1. Connect to LiveKit room with retry
        await connect_with_retry(ctx)

        # 2. Create UserData and bootstrap all components
        userdata = UserData()
        await initialize_components(userdata, ctx)

        # 3. VQA warm-up (pre-fill caches)
        await _warmup_vqa(userdata)

        # 4. Runtime diagnostics (TTS & VQA preflight)
        await run_diagnostics(userdata, ctx)

        # 5. Create agent and session
        agent = AllyVisionAgent()
        agent_session, _ = create_agent_session(userdata, agent)

        # 6. Optional avatar
        avatar = await setup_avatar(agent_session, ctx)

        # 7. Start agent session
        await start_agent_session(agent_session, agent, ctx, avatar)

        # 8. Wire watchdog TTS alerts to session
        wire_watchdog_tts(userdata, agent_session)

        # 9. Launch continuous frame processing (background)
        await start_continuous_processing(userdata, ctx, agent_session)

    except Exception as e:
        logger.error("Agent startup failed: %s", e)
