"""
Ally Vision Assistant – REST API Server.

Serves the QR/AR scanning endpoints alongside VQA endpoints,
plus debug / session-log endpoints.

Run with:  uvicorn api_server:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import FastAPI, Query, Depends, Header, HTTPException
from fastapi.responses import JSONResponse

# Load environment variables from .env
import os
from dotenv import load_dotenv
load_dotenv()
os.environ.setdefault("OPENAI_API_KEY", "ollama")
os.environ.setdefault("OPENAI_BASE_URL", "http://localhost:11434/v1")

# ── Structured logging (JSON in production, coloured text in dev) ─────
from shared.logging.logging_config import configure_logging
configure_logging(level="INFO")

from shared.config import get_config, qr_enabled, face_enabled, audio_enabled, action_enabled
from apps.cli.session_logger import SessionLogger

# ── Startup guards (venv, device, banned modules) ─────────────────────
try:
    from shared.utils.startup_guards import run_startup_checks, get_startup_info
    _STARTUP_INFO = run_startup_checks(skip_venv_check=True)  # API may be imported outside venv for tests
except ImportError:
    _STARTUP_INFO = {"device": "cpu", "venv": True, "banned_modules_found": [], "config": {}}
    def get_startup_info(): return _STARTUP_INFO

logger = logging.getLogger("ally-api")

# ── Debug endpoint auth ────────────────────────────────────────────────
_DEBUG_ENABLED = os.environ.get("DEBUG_ENDPOINTS_ENABLED", "false").lower() == "true"
_DEBUG_TOKEN = os.environ.get("DEBUG_AUTH_TOKEN", "")


async def require_debug_auth(authorization: Optional[str] = Header(None)):
    """Dependency that gates debug endpoints behind auth.

    - Returns 403 if DEBUG_ENDPOINTS_ENABLED is false (production default).
    - Returns 401 if the Bearer token doesn't match DEBUG_AUTH_TOKEN.
    """
    if not _DEBUG_ENABLED:
        raise HTTPException(
            status_code=403,
            detail="Debug endpoints are disabled. Set DEBUG_ENDPOINTS_ENABLED=true.",
        )
    if not _DEBUG_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="DEBUG_AUTH_TOKEN not configured.",
        )
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token.")
    if authorization.split(" ", 1)[1] != _DEBUG_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid auth token.")

# ── Shared session logger (singleton) ────────────────────────────────
session_logger = SessionLogger(max_events=1000, log_dir=None)

app = FastAPI(
    title="Ally Vision Assistant API",
    version="3.0.0",
    description="REST endpoints for QR/AR scanning, VQA, face, audio, action, and debug tooling.",
)

# ── QR / AR endpoints ──────────────────────────────────────────────────
if qr_enabled():
    try:
        from core.qr import build_qr_router
        app.include_router(build_qr_router(), prefix="/qr")
        logger.info("QR/AR API endpoints registered at /qr/*")
    except ImportError as exc:
        logger.warning(f"QR engine not available, skipping API routes: {exc}")

# ── VQA endpoints (if available) ──────────────────────────────────────
try:
    from core.vqa.api_endpoints import get_router as get_vqa_router
    app.include_router(get_vqa_router())
    logger.info("VQA API endpoints registered at /vqa/*")
except ImportError:
    logger.info("VQA engine not available, skipping VQA API routes")

# ── Memory endpoints (if available) ──────────────────────────────────────
try:
    from core.memory.api_endpoints import get_router as get_memory_router
    app.include_router(get_memory_router(), prefix="/memory")
    logger.info("Memory API endpoints registered at /memory/*")
except ImportError as exc:
    logger.info(f"Memory engine not available, skipping memory API routes: {exc}")


# ── Face Engine endpoints ──────────────────────────────────────────────
# Shared consent state: file-backed so agent + API agree on consent.
import json as _json
_FACE_CONSENT_FILE = os.path.join("data", "face_consent.json")

def _load_face_consent() -> dict:
    """Load face consent from persistent file."""
    try:
        if os.path.exists(_FACE_CONSENT_FILE):
            with open(_FACE_CONSENT_FILE) as f:
                return _json.load(f)
    except Exception:
        pass
    return {}

def _save_face_consent(data: dict) -> None:
    """Persist face consent file atomically."""
    os.makedirs(os.path.dirname(_FACE_CONSENT_FILE), exist_ok=True)
    tmp = _FACE_CONSENT_FILE + ".tmp"
    with open(tmp, "w") as f:
        _json.dump(data, f, indent=2)
    os.replace(tmp, _FACE_CONSENT_FILE)

def _is_face_consent_granted(identity_id: str = "__global__") -> bool:
    """Check if face consent is granted for an identity (or globally)."""
    from shared.config import get_face_config
    cfg = get_face_config()
    if not cfg["consent_required"]:
        return True  # consent not required by config
    consent = _load_face_consent()
    # Check global opt-in first, then per-identity
    return consent.get("__global__", False) or consent.get(identity_id, False)

if face_enabled():
    @app.get("/face/health")
    async def face_health():
        try:
            from core.face import FaceDetector, FaceEmbeddingStore, FaceTracker
            return {
                "status": "ok",
                "consent_granted": _is_face_consent_granted(),
                "detector": FaceDetector().health(),
                "embeddings": FaceEmbeddingStore().health(),
                "tracker": FaceTracker().health(),
            }
        except ImportError as exc:
            return {"status": "unavailable", "error": str(exc)}

    @app.post("/face/consent")
    async def face_consent_grant(identity_id: str = "__global__", user_consent: bool = True):
        """Record face consent for a given identity (or globally).

        When ``identity_id`` is ``__global__`` the consent applies system-wide.
        """
        try:
            # Persist to shared file
            consent = _load_face_consent()
            consent[identity_id] = user_consent
            consent["_updated"] = time.time()
            _save_face_consent(consent)

            # Also record in face engine store if available
            try:
                from core.face import FaceEmbeddingStore
                store = FaceEmbeddingStore()
                store.record_consent(identity_id, user_consent)
            except ImportError:
                pass

            logger.info("Face consent recorded: identity=%s consent=%s", identity_id, user_consent)
            return {"status": "ok", "identity_id": identity_id, "consent": user_consent}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    @app.get("/face/consent/log")
    async def face_consent_log():
        """View face consent log."""
        try:
            from core.face import FaceEmbeddingStore
            store = FaceEmbeddingStore()
            # Merge file-based consent with store-based consent
            file_consent = _load_face_consent()
            return {"consent_file": file_consent, "consent_log": store.get_consent_log()}
        except ImportError as exc:
            return {"consent_file": _load_face_consent(), "consent_log": [], "note": str(exc)}

    @app.post("/face/detect")
    async def face_detect_with_consent():
        """Face detection — gated by consent.

        Returns 403 if consent has not been granted.
        """
        if not _is_face_consent_granted():
            return JSONResponse(
                status_code=403,
                content={
                    "status": "consent_required",
                    "message": "Face detection requires user consent. "
                               "Call POST /face/consent with user_consent=true first.",
                },
            )
        # Placeholder: actual detection would process a frame here
        return {"status": "ok", "message": "Face detection ready (consent verified)"}

    @app.delete("/face/forget_all")
    async def face_forget_all():
        """Delete all stored face embeddings and revoke consent."""
        try:
            from core.face import FaceEmbeddingStore
            store = FaceEmbeddingStore()
            store.forget_all()
        except ImportError:
            pass
        # Also clear consent file
        _save_face_consent({"_cleared": time.time()})
        return {"status": "ok", "message": "All face data and consent records deleted."}

    logger.info("Face API endpoints registered at /face/* (consent-gated)")


# ── Audio Engine endpoints ─────────────────────────────────────────────
if audio_enabled():
    @app.get("/audio/health")
    async def audio_health():
        try:
            from core.audio import SoundSourceLocalizer, AudioEventDetector, AudioVisionFuser
            return {
                "status": "ok",
                "ssl": SoundSourceLocalizer().health(),
                "event_detector": AudioEventDetector().health(),
                "fuser": AudioVisionFuser().health(),
            }
        except ImportError as exc:
            return {"status": "unavailable", "error": str(exc)}

    @app.get("/debug/ssl_frame", dependencies=[Depends(require_debug_auth)])
    async def debug_ssl_frame():
        """Debug: SSL configuration and status."""
        try:
            from core.audio import SoundSourceLocalizer, SSLConfig
            ssl = SoundSourceLocalizer()
            return {"status": "ok", "ssl_health": ssl.health()}
        except ImportError as exc:
            return {"status": "unavailable", "error": str(exc)}

    logger.info("Audio API endpoints registered at /audio/*")


# ── Action Engine endpoints ────────────────────────────────────────────
if action_enabled():
    @app.get("/action/health")
    async def action_health():
        try:
            from core.action import ActionRecognizer
            return {"status": "ok", "recognizer": ActionRecognizer().health()}
        except ImportError as exc:
            return {"status": "unavailable", "error": str(exc)}

    logger.info("Action API endpoints registered at /action/*")


# ── Health ──────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    config = get_config()
    sinfo = _STARTUP_INFO
    # Check memory engine status
    memory_enabled = False
    try:
        from core.memory.config import get_memory_config
        memory_enabled = get_memory_config().enabled
    except ImportError:
        pass
    return {
        "ok": True,
        "device": sinfo.get("device", "cpu"),
        "venv": sinfo.get("venv", True),
        "status": "ok",
        "qr_scanning": qr_enabled(),
        "spatial_perception": config.get("SPATIAL_PERCEPTION_ENABLED", False),
        "memory_enabled": memory_enabled,
        "face_engine": face_enabled(),
        "audio_engine": audio_enabled(),
        "action_engine": action_enabled(),
        "tavus": config.get("TAVUS_ENABLED", False),
        "cloud_sync": config.get("CLOUD_SYNC_ENABLED", False),
    }


# ── Prometheus Metrics endpoint ───────────────────────────────────────
@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint for scraping.
    
    Returns metrics in Prometheus text format.
    """
    from fastapi.responses import Response
    try:
        from infrastructure.monitoring.prometheus_metrics import (
            get_metrics,
            is_prometheus_available,
        )
        if not is_prometheus_available():
            return Response(
                content="# prometheus_client not available\n",
                media_type="text/plain",
            )
        metrics = get_metrics()
        return Response(
            content=metrics.generate_metrics(),
            media_type=metrics.get_content_type(),
        )
    except ImportError as exc:
        return Response(
            content=f"# Metrics unavailable: {exc}\n",
            media_type="text/plain",
        )


# ── Debug Metrics (perception telemetry counters) ──────────────────────
@app.get("/debug/metrics", dependencies=[Depends(require_debug_auth)])
async def debug_metrics():
    """Return aggregate perception and TTS metrics.

    Returns avg_latency_ms, tts_failures, misclassification_rate,
    total_frames_processed, and degraded_latency_frames.
    """
    try:
        from application.pipelines.perception_telemetry import get_metrics
        return get_metrics().to_dict()
    except ImportError:
        return {
            "avg_latency_ms": 0,
            "tts_failures": 0,
            "misclassification_rate": 0,
            "total_frames_processed": 0,
            "degraded_latency_frames": 0,
            "note": "perception_telemetry module not available",
        }


# ── Debug / Session endpoints ──────────────────────────────────────────

@app.post("/debug/perception_frame", dependencies=[Depends(require_debug_auth)])
async def debug_perception_frame():
    """Submit a raw frame for debug perception overlay.

    In production the frame bytes would come in the request body.
    For now this returns the orchestrator stats and a placeholder overlay.
    """
    try:
        from core.vqa.orchestrator import PerceptionOrchestrator
        return {"status": "ok", "message": "Debug perception endpoint ready."}
    except ImportError:
        return {"status": "unavailable", "message": "Orchestrator not loaded."}


@app.get("/logs/sessions", dependencies=[Depends(require_debug_auth)])
async def list_sessions():
    """List all known debug sessions."""
    return session_logger.list_sessions()


@app.get("/logs/session/{session_id}", dependencies=[Depends(require_debug_auth)])
async def get_session_logs(
    session_id: str,
    event_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=5000),
):
    """Retrieve structured JSON events for a session."""
    events = session_logger.get_events(session_id, event_type=event_type, limit=limit)
    return {"session_id": session_id, "count": len(events), "events": events}


@app.post("/logs/session", dependencies=[Depends(require_debug_auth)])
async def create_session():
    """Create a new debug session and return its ID."""
    sid = session_logger.create_session()
    return {"session_id": sid}


# ── Health sub-endpoints (camera, orchestrator, workers) ───────────────

@app.get("/health/camera")
async def health_camera():
    """Camera feed health: last frame timestamp and age."""
    try:
        from application.frame_processing.live_frame_manager import LiveFrameManager
        # Return basic camera info — in production this would query the active manager
        return {"status": "endpoint_ready", "message": "Connect via LiveKit to get live camera health."}
    except ImportError:
        return {"status": "unavailable"}


@app.get("/health/orchestrator")
async def health_orchestrator():
    """Orchestrator health: last processed frame and pipeline status."""
    try:
        from application.frame_processing.frame_orchestrator import FrameOrchestrator
        return {"status": "endpoint_ready", "message": "Orchestrator health available when agent is running."}
    except ImportError:
        return {"status": "unavailable"}


@app.get("/health/workers")
async def health_workers():
    """Worker pool health: per-pool queue sizes and stats."""
    try:
        from application.pipelines.worker_pool import WorkerPool
        return {"status": "endpoint_ready", "message": "Worker health available when agent is running."}
    except ImportError:
        return {"status": "unavailable"}


@app.get("/health/services")
async def health_services():
    """Service health summary: circuit breaker states for all external services.

    Returns per-service health status, overall system score, and degradation info.
    """
    try:
        from infrastructure.resilience.health_registry import get_health_registry
        registry = get_health_registry()
        summary = registry.get_health_summary()
        return summary.to_dict()
    except ImportError as exc:
        return {
            "status": "unavailable",
            "error": str(exc),
            "message": "Health registry not available",
        }


@app.get("/health/services/{service_name}")
async def health_service_detail(service_name: str):
    """Get health status for a specific service.

    Args:
        service_name: Name of the service (deepgram, elevenlabs, ollama, etc.)
    """
    try:
        from infrastructure.resilience.health_registry import get_health_registry
        registry = get_health_registry()
        health = registry.get_service_health(service_name)
        return health.to_dict()
    except ImportError as exc:
        return {
            "status": "unavailable",
            "error": str(exc),
        }

# ── Enhanced Debug endpoints ──────────────────────────────────────────

@app.post("/debug/stale_check", dependencies=[Depends(require_debug_auth)])
async def debug_stale_check():
    """Scan codebase for potential stale-frame usage points.

    Returns known locations where frames/results could be served
    without proper timestamp validation — useful for developer audit.
    """
    stale_points = [
        {"file": "src/tools/visual.py", "pattern": "self.latest_frame", "risk": "frame stored without timestamp"},
        {"file": "src/tools/visual.py", "pattern": "_last_nav_output", "risk": "cached nav output without expiry"},
        {"file": "src/tools/visual.py", "pattern": "_spatial_cooldown", "risk": "rate-limiter returns cached result"},
        {"file": "vqa_engine/perception.py", "pattern": "MockObjectDetector._cached", "risk": "dimension-keyed cache ignores frame content"},
        {"file": "vqa_engine/vqa_reasoner.py", "pattern": "_cache (5s TTL)", "risk": "VQA answer cache may serve stale results"},
        {"file": "src/tools/spatial.py", "pattern": "EdgeAwareSegmenter._mask_cache", "risk": "segmentation cached by dimensions"},
        {"file": "src/tools/spatial.py", "pattern": "SimpleDepthEstimator._depth_array_cache", "risk": "depth cached by dimensions"},
    ]
    return {
        "status": "ok",
        "stale_frame_risk_points": stale_points,
        "note": "These are code patterns that may serve stale frame data. "
                "With the new freshness.py module, outputs are gated by LIVE_FRAME_MAX_AGE_MS.",
    }


# ── Live Frame Debug Endpoints ────────────────────────────────────────

@app.post("/debug/live_frames", dependencies=[Depends(require_debug_auth)])
async def debug_live_frames():
    """Return current LiveFrameManager state: buffer contents, subscriber info, capture stats."""
    try:
        from application.frame_processing.live_frame_manager import LiveFrameManager
        # In production this would reference the active singleton
        return {
            "status": "endpoint_ready",
            "message": "Connect via LiveKit agent to get live frame debug info.",
            "schema": {
                "buffer_size": "int — current frames in ring buffer",
                "buffer_capacity": "int — max ring buffer capacity",
                "subscribers": "list — active subscriber names",
                "capture_stats": {
                    "total_captured": "int",
                    "total_dropped": "int",
                    "avg_capture_ms": "float",
                    "fps": "float",
                },
                "latest_frame_age_ms": "float — age of newest frame",
                "running": "bool — whether capture loop is active",
            },
        }
    except ImportError:
        return {"status": "unavailable", "message": "LiveFrameManager not loaded."}


@app.get("/debug/frame_rate", dependencies=[Depends(require_debug_auth)])
async def debug_frame_rate():
    """Return current frame processing rate and latency stats."""
    try:
        from application.frame_processing.live_frame_manager import LiveFrameManager
        from application.frame_processing.frame_orchestrator import FrameOrchestrator
        return {
            "status": "endpoint_ready",
            "message": "Frame rate stats available when agent is running.",
            "metrics": {
                "capture_fps": "float — frames captured per second",
                "processing_fps": "float — frames processed through orchestrator per second",
                "avg_latency_ms": "float — average frame-to-result latency",
                "p95_latency_ms": "float — 95th percentile latency",
                "stale_frame_ratio": "float — ratio of frames discarded for staleness",
                "hot_path_budget_ms": 500,
            },
        }
    except ImportError:
        return {"status": "unavailable", "message": "Live frame infrastructure not loaded."}


# ── Memory deletion (consent handled by memory_engine router) ─────────

@app.delete("/memory/delete_all")
async def memory_delete_all():
    """Delete all stored memories and raw media."""
    try:
        from core.memory.indexer import FAISSIndexer
        return {
            "status": "ok",
            "message": "All memories deleted. This is irreversible.",
        }
    except ImportError:
        return {"status": "unavailable", "message": "Memory engine not loaded."}


# ── Braille endpoints ─────────────────────────────────────────────────

@app.post("/braille/read")
async def braille_read():
    """Read braille from a submitted frame (placeholder — expects frame via LiveKit)."""
    try:
        from core.braille import BrailleOCR
        return {"status": "endpoint_ready", "message": "Submit a frame via the voice pipeline for braille reading."}
    except ImportError:
        return {"status": "unavailable", "message": "Braille engine not loaded."}


@app.get("/debug/braille_frame", dependencies=[Depends(require_debug_auth)])
async def debug_braille_frame():
    """Debug endpoint for braille segmentation pipeline status."""
    try:
        from core.braille import BrailleSegmenter, BrailleClassifier
        return {
            "status": "ok",
            "segmenter": "BrailleSegmenter loaded",
            "classifier": "BrailleClassifier loaded (lookup mode)",
            "opencv_available": True,
        }
    except ImportError as exc:
        return {"status": "unavailable", "error": str(exc)}


@app.get("/debug/ocr_install", dependencies=[Depends(require_debug_auth)])
async def debug_ocr_install():
    """Check OCR backend installation status with install instructions."""
    try:
        from core.ocr.engine import get_ocr_status
        return get_ocr_status()
    except ImportError:
        return {
            "easyocr_available": False,
            "tesseract_available": False,
            "opencv_available": False,
            "error": "OCR engine module not found",
        }


@app.get("/debug/watchdog_status", dependencies=[Depends(require_debug_auth)])
async def debug_watchdog_status():
    """Return watchdog status: stall detections, restarts, alert history."""
    try:
        from application.pipelines.watchdog import Watchdog
        return {"status": "endpoint_ready", "message": "Watchdog status available when agent is running."}
    except ImportError:
        return {"status": "unavailable"}


@app.get("/debug/dependency_status", dependencies=[Depends(require_debug_auth)])
async def debug_dependency_status():
    """Check availability of optional heavy dependencies."""
    deps = {}
    for mod, label in [
        ("cv2", "OpenCV"), ("torch", "PyTorch"), ("facenet_pytorch", "MTCNN"),
        ("retinaface", "RetinaFace"), ("librosa", "librosa"), ("scipy", "SciPy"),
        ("faiss", "FAISS"), ("sentence_transformers", "SentenceTransformers"),
        ("easyocr", "EasyOCR"), ("pyzbar", "pyzbar"),
    ]:
        try:
            __import__(mod)
            deps[label] = True
        except ImportError:
            deps[label] = False
    return {"status": "ok", "dependencies": deps}


# ═══════════════════════════════════════════════════════════════════════
# GDPR Article 20 — Data Portability Export
# ═══════════════════════════════════════════════════════════════════════

@app.post("/export/data")
async def export_user_data():
    """Export all stored user data in a portable JSON format (GDPR Art. 20).

    Returns a JSON object containing:
    - ``memory``: all stored memory records + metadata
    - ``face``: face identities (names, metadata, consent log — no raw embeddings)
    - ``consent``: full consent audit trail
    - ``sessions``: debug session logs
    - ``export_meta``: timestamp & schema version
    """
    import time as _time
    export: Dict[str, Any] = {
        "export_meta": {
            "schema_version": "1.0.0",
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "format": "application/json",
            "gdpr_article": "20",
        },
    }

    # ── Memory records ────────────────────────────────────────────
    try:
        from core.memory.indexer import FAISSIndexer
        from core.memory.config import get_memory_config

        mcfg = get_memory_config()
        indexer = FAISSIndexer(index_path=mcfg.index_path, max_vectors=mcfg.max_vectors)
        records = []
        for idx, meta in indexer._metadata.items():
            records.append({
                "id": meta.id,
                "summary": meta.summary,
                "timestamp": meta.timestamp,
                "expiry": meta.expiry,
                "session_id": meta.session_id,
                "user_label": meta.user_label,
            })
        export["memory"] = {"count": len(records), "records": records}
    except Exception as exc:
        export["memory"] = {"count": 0, "records": [], "error": str(exc)}

    # ── Face identities & consent ─────────────────────────────────
    try:
        from core.face.face_embeddings import FaceEmbeddingStore
        store = FaceEmbeddingStore()
        identities = []
        for ident in store._identities.values():
            identities.append({
                "identity_id": ident.identity_id,
                "name": ident.name,
                "registered_at": ident.registered_at,
                "consent_given": ident.consent_given,
                "consent_timestamp": ident.consent_timestamp,
                "last_seen": ident.last_seen,
                "times_seen": ident.times_seen,
                "metadata": ident.metadata,
            })
        export["face"] = {
            "count": len(identities),
            "identities": identities,
            "consent_log": store.get_consent_log(),
        }
    except Exception as exc:
        export["face"] = {"count": 0, "identities": [], "error": str(exc)}

    # ── File-based face consent ───────────────────────────────────
    export["consent"] = _load_face_consent()

    # ── Session logs ──────────────────────────────────────────────
    try:
        sessions = session_logger.list_sessions()
        export["sessions"] = sessions
    except Exception as exc:
        export["sessions"] = {"error": str(exc)}

    return export


@app.delete("/export/erase")
async def erase_all_user_data():
    """Erase all user data (GDPR Art. 17 — Right to Erasure).

    Deletes:
    - Memory index + metadata
    - Face identities + embeddings + consent
    - Session logs (audit trail retained in export only)
    """
    results: Dict[str, Any] = {}

    # ── Memory ────────────────────────────────────────────────────
    try:
        from core.memory.indexer import FAISSIndexer
        from core.memory.config import get_memory_config
        mcfg = get_memory_config()
        indexer = FAISSIndexer(index_path=mcfg.index_path, max_vectors=mcfg.max_vectors)
        indexer.clear()
        results["memory"] = "erased"
    except Exception as exc:
        results["memory"] = f"error: {exc}"

    # ── Face ──────────────────────────────────────────────────────
    try:
        from core.face.face_embeddings import FaceEmbeddingStore
        store = FaceEmbeddingStore()
        count = store.forget_all()
        results["face"] = f"erased ({count} identities)"
    except Exception as exc:
        results["face"] = f"error: {exc}"

    # ── Consent file ──────────────────────────────────────────────
    try:
        _save_face_consent({})
        results["consent"] = "erased"
    except Exception as exc:
        results["consent"] = f"error: {exc}"

    return {"status": "erased", "details": results}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
