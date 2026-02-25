"""Session lifecycle manager for the LiveKit real-time agent.

Extracts session creation, component initialization, teardown, and
reconnection logic from the monolithic agent.py god-file (T-038).

Responsibilities:
  - Room connection with retry
  - UserData initialization and component bootstrapping
  - Agent session creation and plugin wiring
  - Continuous frame processing lifecycle
  - Graceful shutdown

The coordinator (agent.py) delegates to this module rather than
embedding lifecycle logic inline.
"""

import asyncio
import logging
import os
import time
from typing import Any, Dict, Optional, Tuple

from livekit.agents import JobContext
from livekit.agents.voice import AgentSession
from livekit.agents.voice.room_io import RoomOptions
from livekit.plugins import deepgram, elevenlabs, openai, silero

from shared.config import (
    get_config,
    get_continuous_config,
    get_debounce_config,
    get_live_frame_config,
    get_qr_config,
    get_spatial_config,
    get_watchdog_config,
    qr_enabled,
)

logger = logging.getLogger("ally-vision-agent")

# ── Constants from agent-level config ────────────────────────────────────
_CFG = get_config()
LLM_MODEL = _CFG.get("OLLAMA_VL_MODEL_ID", "qwen3-vl:235b-instruct-cloud")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", _CFG.get("LLM_BASE_URL", "http://localhost:11434/v1"))
LLM_API_KEY = os.environ.get("LLM_API_KEY", _CFG.get("LLM_API_KEY", "ollama"))

# Maximum connection retries for transient LiveKit Cloud failures
MAX_CONNECT_RETRIES = 3


# ── Optional imports (guarded so the system starts even if deps are missing)
try:
    from application.frame_processing.frame_orchestrator import (
        FrameOrchestrator,
        FrameOrchestratorConfig,
    )
    from application.frame_processing.freshness import (
        set_max_age as set_freshness_max_age,
    )
    from application.frame_processing.live_frame_manager import LiveFrameManager
    from application.pipelines.debouncer import Debouncer, DebouncerConfig
    from application.pipelines.watchdog import Watchdog, WatchdogConfig

    LIVE_INFRA_AVAILABLE = True
except ImportError as _live_err:
    LIVE_INFRA_AVAILABLE = False
    logger.warning("Live-frame infrastructure not available: %s", _live_err)

try:
    from core.vqa import (
        SceneGraphBuilder,
        SpatialFuser,
        VQAMemory,
        VQAReasoner,
        create_perception_pipeline,
    )

    VQA_ENGINE_AVAILABLE = True
except ImportError:
    VQA_ENGINE_AVAILABLE = False

try:
    from core.qr import ARTagHandler, CacheManager, QRDecoder, QRScanner

    QR_ENGINE_AVAILABLE = True
except ImportError:
    QR_ENGINE_AVAILABLE = False

try:
    from core.speech.voice_router import VoiceRouter

    VOICE_ROUTER_AVAILABLE = True
except ImportError:
    VOICE_ROUTER_AVAILABLE = False

try:
    from core.ocr import OCRPipeline

    OCR_ENGINE_AVAILABLE = True
except ImportError:
    OCR_ENGINE_AVAILABLE = False

try:
    from apps.cli.session_logger import SessionLogger

    SESSION_LOGGER_AVAILABLE = True
except ImportError:
    SESSION_LOGGER_AVAILABLE = False

try:
    from livekit.plugins import tavus

    TAVUS_AVAILABLE = True
except ImportError:
    TAVUS_AVAILABLE = False


# =====================================================================
# Connection Management
# =====================================================================


async def connect_with_retry(ctx: JobContext, max_retries: int = MAX_CONNECT_RETRIES) -> None:
    """Connect to the LiveKit room with retry logic for transient failures."""
    for attempt in range(1, max_retries + 1):
        try:
            await ctx.connect()
            return
        except Exception as conn_err:
            if attempt < max_retries:
                wait = attempt * 2
                logger.warning(
                    "Room connect attempt %d/%d failed: %s. Retrying in %ds...",
                    attempt,
                    max_retries,
                    conn_err,
                    wait,
                )
                await asyncio.sleep(wait)
            else:
                raise


# =====================================================================
# Component Initialization
# =====================================================================


def _resolve_model_flag(cfg_value: Any, model_path: str) -> bool:
    """Resolve 'auto' | bool | str flag to concrete bool based on file existence."""
    if cfg_value == "auto":
        return os.path.isfile(model_path)
    return cfg_value in (True, "true", "1")


async def initialize_components(userdata: Any, ctx: JobContext) -> None:
    """Bootstrap all optional components onto *userdata*.

    Each subsystem is guarded with try/except so a single failure
    doesn't prevent the rest of the system from starting.
    """
    spatial_config = get_spatial_config()
    userdata.room_ctx = ctx
    userdata._spatial_enabled = spatial_config["enabled"]

    # ── Visual Processor (lazy import to avoid import-time failures) ──
    from core.vision.visual import VisualProcessor
    from infrastructure.llm.internet_search import InternetSearch

    userdata.visual_processor = VisualProcessor(enable_spatial=spatial_config["enabled"])
    userdata.internet_search = InternetSearch()

    # ── VQA Engine ──
    _init_vqa(userdata, spatial_config)

    # ── QR / AR scanning ──
    _init_qr(userdata)

    # ── Log spatial status ──
    if userdata.visual_processor.spatial_enabled:
        logger.info("Spatial perception enabled: object detection, segmentation, and depth estimation active")
    else:
        logger.info("Spatial perception disabled or not available")

    # ── Voice Router ──
    _init_voice_router(userdata)

    # ── OCR Engine ──
    _init_ocr(userdata)

    # ── Session Logger ──
    _init_session_logger(userdata)

    # ── Live-frame infrastructure (Debouncer, Watchdog) ──
    await _init_live_infra(userdata)

    # ── Ollama handler (fallback vision, lazy import) ──
    try:
        from infrastructure.llm.ollama.handler import OllamaHandler

        userdata.ollama_handler = OllamaHandler()
    except Exception as e:
        logger.warning("Vision will use ollama:%s only: %s", LLM_MODEL, e)

    # ── Camera ──
    try:
        await userdata.visual_processor.enable_camera(ctx.room)
    except Exception as e:
        logger.warning("Camera setup failed: %s", e)


def _init_vqa(userdata: Any, spatial_config: Dict[str, Any]) -> None:
    """Initialize VQA Engine components."""
    if not VQA_ENGINE_AVAILABLE:
        logger.info("VQA Engine not available, using original spatial pipeline")
        return
    try:
        _yolo_path = spatial_config.get("yolo_model_path", "models/yolov8n.onnx")
        _midas_path = spatial_config.get("midas_model_path", "models/midas_v21_small_256.onnx")
        _use_yolo = _resolve_model_flag(spatial_config.get("use_yolo", "auto"), _yolo_path)
        _use_midas = _resolve_model_flag(spatial_config.get("use_midas", "auto"), _midas_path)

        logger.info("YOLO model path: %s, exists=%s, use=%s", _yolo_path, os.path.isfile(_yolo_path), _use_yolo)
        logger.info("MiDaS model path: %s, exists=%s, use=%s", _midas_path, os.path.isfile(_midas_path), _use_midas)

        userdata._vqa_pipeline = create_perception_pipeline(
            use_mock=False,
            use_yolo=_use_yolo,
            use_midas=_use_midas,
        )
        userdata._vqa_fuser = SpatialFuser()
        userdata._vqa_reasoner = VQAReasoner(
            llm_client=None,
            model=LLM_MODEL,
            use_micronav_fallback=True,
        )
        userdata._vqa_memory = VQAMemory()
        userdata._vqa_session_id = f"session_{int(time.time() * 1000)}"
        logger.info("VQA Engine initialized: perception, fusion, reasoning, memory active")
    except Exception as e:
        logger.warning("VQA Engine initialization failed, using fallback: %s", e)
        userdata._vqa_pipeline = None


async def _warmup_vqa(userdata: Any) -> None:
    """Run a dummy inference through the VQA pipeline to pre-fill caches."""
    if not VQA_ENGINE_AVAILABLE or userdata._vqa_pipeline is None:
        return
    try:
        from PIL import Image as _PILImage

        _warmup_img = _PILImage.new("RGB", (640, 480), color=(128, 128, 128))
        await userdata._vqa_pipeline.process(_warmup_img)
        logger.info("VQA pipeline warm-up complete (cold-start avoided)")
    except Exception as warmup_exc:
        logger.warning("VQA warm-up skipped: %s", warmup_exc)


def _init_qr(userdata: Any) -> None:
    """Initialize QR / AR scanning engine."""
    if not (QR_ENGINE_AVAILABLE and qr_enabled()):
        logger.info("QR/AR scanning not available or disabled")
        return
    try:
        qr_cfg = get_qr_config()
        userdata._qr_scanner = QRScanner()
        userdata._qr_decoder = QRDecoder()
        userdata._ar_handler = ARTagHandler()
        if qr_cfg["cache_enabled"]:
            cache_kwargs: Dict[str, Any] = {"ttl": qr_cfg["cache_ttl"]}
            if qr_cfg["cache_dir"]:
                cache_kwargs["cache_dir"] = qr_cfg["cache_dir"]
            userdata._qr_cache = CacheManager(**cache_kwargs)
        userdata._qr_enabled = True
        _qr_backend = (
            "pyzbar"
            if userdata._qr_scanner._use_pyzbar
            else ("cv2" if userdata._qr_scanner._use_cv2 else "none")
        )
        logger.info("QR/AR scanning engine initialised (scanner=%s, decoder + cache)", _qr_backend)
    except Exception as e:
        logger.warning("QR engine initialisation failed: %s", e)
        userdata._qr_enabled = False


def _init_voice_router(userdata: Any) -> None:
    """Initialize VoiceRouter for intent classification."""
    if not VOICE_ROUTER_AVAILABLE:
        return
    try:
        userdata._voice_router = VoiceRouter()
        logger.info("VoiceRouter initialised for intent classification")
    except Exception as e:
        logger.warning("VoiceRouter init failed: %s", e)


def _init_ocr(userdata: Any) -> None:
    """Initialize OCR pipeline."""
    if not OCR_ENGINE_AVAILABLE:
        return
    try:
        userdata._ocr_pipeline = OCRPipeline()
        if userdata._ocr_pipeline.is_ready:
            logger.info("OCR pipeline ready")
        else:
            logger.info("OCR pipeline created but no backend available")
    except Exception as e:
        logger.warning("OCR pipeline init failed: %s", e)


def _init_session_logger(userdata: Any) -> None:
    """Initialize debug session logger."""
    if not SESSION_LOGGER_AVAILABLE:
        return
    try:
        userdata._session_logger = SessionLogger()
        userdata._session_id = userdata._session_logger.create_session()
        logger.info("Session logger active: %s", userdata._session_id)
    except Exception as e:
        logger.warning("Session logger init failed: %s", e)


async def _init_live_infra(userdata: Any) -> None:
    """Initialize live-frame infrastructure (debouncer, watchdog)."""
    if not LIVE_INFRA_AVAILABLE:
        return
    try:
        lf_cfg = get_live_frame_config()
        set_freshness_max_age(lf_cfg.get("max_age_ms", 500))

        # Debouncer
        db_cfg = get_debounce_config()
        userdata._debouncer = Debouncer(
            DebouncerConfig(
                debounce_window_seconds=db_cfg.get("window_seconds", 5.0),
                distance_delta_meters=db_cfg.get("distance_delta_m", 0.5),
                confidence_delta=db_cfg.get("confidence_delta", 0.15),
            )
        )

        # Watchdog
        wd_cfg = get_watchdog_config()
        userdata._watchdog = Watchdog(
            WatchdogConfig(
                camera_stall_threshold_ms=wd_cfg.get("camera_stall_ms", 2000),
                worker_stall_threshold_ms=wd_cfg.get("worker_stall_ms", 5000),
                check_interval_ms=wd_cfg.get("check_interval_ms", 500),
            )
        )
        userdata._watchdog.register_component("camera")
        userdata._watchdog.register_component("orchestrator")

        # Watchdog alert: restart camera on stall
        async def _on_watchdog_alert(component: str, message: str) -> None:
            logger.warning("Watchdog alert [%s]: %s", component, message)
            if component == "camera":
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
        logger.info(
            "Live-frame infrastructure ready: freshness=%dms, debounce=%.1fs, watchdog active",
            lf_cfg.get("max_age_ms", 500),
            db_cfg.get("window_seconds", 5.0),
        )
    except Exception as e:
        logger.warning("Live-frame infra init failed (non-fatal): %s", e)


# =====================================================================
# Runtime Diagnostics
# =====================================================================


async def run_diagnostics(userdata: Any, ctx: JobContext) -> None:
    """Run TTS & VQA preflight checks and log SYSTEM_STATUS."""
    try:
        from shared.utils.runtime_diagnostics import get_diagnostics

        diag = get_diagnostics()

        async def _capture_for_preflight():
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

        logger.info("SYSTEM_STATUS: %s", system_status.to_json())
        logger.info("Startup health: %s | %s", system_status.system_status, system_status.human_summary)

        if system_status.vqa and system_status.vqa.status == "skipped":
            logger.warning(
                "VQA SKIPPED [%s]: %s\n  Remediation: %s\n  Reproduce: %s",
                system_status.vqa.skip_code,
                system_status.vqa.message,
                system_status.vqa.remediation,
                system_status.vqa.reproduce_command,
            )
    except Exception as diag_err:
        logger.warning("Runtime diagnostics failed (non-fatal): %s", diag_err)


# =====================================================================
# Agent Session Creation
# =====================================================================


def create_agent_session(
    userdata: Any,
    agent: Any,
) -> Tuple[AgentSession, Optional[Any]]:
    """Create an AgentSession with all configured plugins.

    Returns (agent_session, avatar_or_none).
    """
    llm_instance = openai.LLM(
        model=LLM_MODEL,
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY,
        parallel_tool_calls=False,
        temperature=0.2,
    )

    agent_session: AgentSession = AgentSession(
        userdata=userdata,
        stt=deepgram.STT(model="nova-3", language="en"),
        llm=llm_instance,
        tts=elevenlabs.TTS(
            model="eleven_turbo_v2_5",
            voice_id="21m00Tcm4TlvDq8ikWAM",
        ),
        vad=silero.VAD.load(),
        max_tool_steps=1,
    )

    return agent_session, None  # avatar handled separately


async def setup_avatar(
    agent_session: AgentSession,
    ctx: JobContext,
) -> Optional[Any]:
    """Initialize and start the Tavus avatar if configured.

    Returns the avatar instance or None.
    """
    if not TAVUS_AVAILABLE:
        return None

    config = get_config()
    avatar_enabled = (
        config.get("ENABLE_AVATAR", False)
        and config.get("TAVUS_REPLICA_ID")
        and config.get("TAVUS_PERSONA_ID")
    )
    if not avatar_enabled:
        return None

    try:
        replica_id = config.get("TAVUS_REPLICA_ID")
        persona_id = config.get("TAVUS_PERSONA_ID")
        avatar_name = config.get("TAVUS_AVATAR_NAME", "ally-vision-avatar")

        logger.info("Initializing Tavus avatar with replica_id: %s, persona_id: %s", replica_id, persona_id)
        avatar = tavus.AvatarSession(
            replica_id=replica_id,
            persona_id=persona_id,
            avatar_participant_name=avatar_name,
        )
        try:
            await avatar.start(agent_session, room=ctx.room)
            logger.info("Tavus avatar started successfully with name: %s", avatar_name)
            return avatar
        except Exception as e:
            logger.error("Failed to start Tavus avatar, continuing without avatar: %s", e)
            return None
    except Exception as e:
        logger.error("Failed to initialize Tavus avatar: %s", e)
        return None


async def start_agent_session(
    agent_session: AgentSession,
    agent: Any,
    ctx: JobContext,
    avatar: Optional[Any] = None,
) -> None:
    """Start the agent session with room options."""
    await agent_session.start(
        agent=agent,
        room=ctx.room,
        room_options=RoomOptions(
            audio_output=avatar is None,
        ),
    )


# =====================================================================
# Watchdog TTS Wiring
# =====================================================================


def wire_watchdog_tts(userdata: Any, agent_session: AgentSession) -> None:
    """Wire watchdog alerts to TTS announcements via agent_session.say()."""
    if not LIVE_INFRA_AVAILABLE or not getattr(userdata, "_watchdog", None):
        return

    _session_ref = agent_session

    async def _on_watchdog_tts(component: str, message: str) -> None:
        try:
            if hasattr(_session_ref, "say"):
                await _session_ref.say(f"Warning: {component} has stalled. Attempting recovery.")
        except Exception as exc:
            logger.debug("Watchdog TTS announcement failed: %s", exc)

    userdata._watchdog.on_alert(_on_watchdog_tts)
    logger.info("Watchdog TTS alerts wired to agent session")


# =====================================================================
# Continuous Frame Processing
# =====================================================================


async def start_continuous_processing(
    userdata: Any,
    ctx: JobContext,
    agent_session: AgentSession,
) -> None:
    """Set up and launch continuous frame capture, processing, and proactive announcements.

    This is a fire-and-forget setup — background tasks are launched via
    ``asyncio.create_task`` and run until the LiveFrameManager stops.
    """
    if not LIVE_INFRA_AVAILABLE:
        logger.info("Continuous processing disabled or infrastructure unavailable")
        return

    continuous_cfg = get_continuous_config()
    lf_cfg = get_live_frame_config()

    if not continuous_cfg["continuous_processing"]:
        logger.info("Continuous processing disabled or infrastructure unavailable")
        return

    try:
        # ── Build capture function from VisualProcessor ──
        async def _livekit_capture():
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

        # Wire watchdog heartbeat
        if userdata._watchdog:
            lfm.on_frame(lambda _f: userdata._watchdog.heartbeat("camera"))

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

        # ── Detector / depth function wiring ──
        detector_fn = None
        depth_fn = None
        if VQA_ENGINE_AVAILABLE and userdata._vqa_pipeline:
            pipeline = userdata._vqa_pipeline
            if hasattr(pipeline, "detect"):
                detector_fn = pipeline.detect
            elif hasattr(pipeline, "detector") and pipeline.detector is not None:
                _det = pipeline.detector
                if hasattr(_det, "detect"):

                    async def _detect(img, _d=_det):
                        return await _d.detect(img)

                    detector_fn = _detect

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

        # ── Latest result store ──
        _latest_fused: Dict[str, Any] = {"result": None}

        # ── Continuous consumer loop ──
        async def _continuous_consumer() -> None:
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
        _tts_lock = asyncio.Lock()
        _last_say_ts: float = 0.0
        _MIN_SAY_INTERVAL = 3.0

        async def _proactive_announcer() -> None:
            nonlocal _last_say_ts
            cadence = continuous_cfg.get("proactive_cadence_s", 2.0)
            critical_only = continuous_cfg.get("proactive_critical_only", False)
            debouncer = userdata._debouncer
            logger.info("Proactive announcer started (cadence=%.1fs, critical_only=%s)", cadence, critical_only)
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
                if critical_only and "stop" not in cue.lower() and "critical" not in cue.lower():
                    continue
                if debouncer and not debouncer.should_speak(cue, scene_graph_hash=result.scene_graph_hash):
                    continue
                if debouncer:
                    debouncer.record(cue, scene_graph_hash=result.scene_graph_hash)
                try:
                    if hasattr(agent_session, "say"):
                        _is_running = (
                            getattr(agent_session, "started", None)
                            or getattr(agent_session, "_started", None)
                            or getattr(agent_session, "_running", None)
                            or True
                        )
                        if not _is_running:
                            logger.debug("Proactive cue skipped (session not started): %s", cue)
                            continue
                        now = time.time()
                        if (now - _last_say_ts) < _MIN_SAY_INTERVAL:
                            logger.debug("Proactive cue throttled (cooldown): %s", cue)
                            continue
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
        logger.info(
            "Continuous frame processing ACTIVE (cadence=%.0fms)",
            lf_cfg.get("capture_cadence_ms", 100),
        )

        if continuous_cfg.get("always_on") and continuous_cfg.get("proactive_announce"):
            userdata._proactive_enabled = True
            asyncio.create_task(_proactive_announcer(), name="proactive_announcer")
            logger.info("ALWAYS_ON proactive mode ACTIVE")

    except Exception as e:
        logger.warning("Continuous processing startup failed (non-fatal): %s", e)
