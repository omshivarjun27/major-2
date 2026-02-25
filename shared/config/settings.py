"""
This file allows you to configure which vision model provider to use.
Includes spatial perception configuration for object detection, segmentation, and depth estimation.
"""

import logging
import os
from enum import Enum

from shared.config.secret_provider import create_secret_provider

# Get a logger for this module
logger = logging.getLogger("config")

# Vision provider options
class VisionProvider(Enum):
    OLLAMA = "ollama"  # Use Ollama API

# Helper function to determine vision provider from env
def _get_vision_provider():
    provider_str = os.environ.get("VISION_PROVIDER", "ollama").lower()
    return VisionProvider.OLLAMA

# Default configuration
_secret_provider = create_secret_provider()
CONFIG = {
    # Select which vision provider to use
    "VISION_PROVIDER": _get_vision_provider(),
    
    # Ollama configuration
    "OLLAMA_VL_API_KEY": _secret_provider.get_secret("OLLAMA_VL_API_KEY") or "",
    "OLLAMA_VL_MODEL_ID": os.environ.get("OLLAMA_VL_MODEL_ID", "qwen3-vl:235b-instruct-cloud"),
    
    # Tavus virtual avatar configuration
    "ENABLE_AVATAR": os.environ.get("ENABLE_AVATAR", "false") == "true",
    "TAVUS_API_KEY": _secret_provider.get_secret("TAVUS_API_KEY") or "",
    "TAVUS_REPLICA_ID": os.environ.get("TAVUS_REPLICA_ID", ""),
    "TAVUS_PERSONA_ID": os.environ.get("TAVUS_PERSONA_ID", ""),
    "TAVUS_AVATAR_NAME": os.environ.get("TAVUS_AVATAR_NAME", "ally-vision-avatar"),
    
    # =========================================================================
    # SPATIAL PERCEPTION CONFIGURATION
    # =========================================================================
    
    # Enable/disable spatial perception pipeline
    "SPATIAL_PERCEPTION_ENABLED": os.environ.get("SPATIAL_PERCEPTION_ENABLED", "true").lower() == "true",
    
    # Object Detection Configuration (auto-detected when model file exists)
    "SPATIAL_USE_YOLO": os.environ.get("SPATIAL_USE_YOLO", "auto").lower(),
    "YOLO_MODEL_PATH": os.environ.get("YOLO_MODEL_PATH", "models/yolov8n.onnx"),
    "YOLO_CONF_THRESHOLD": float(os.environ.get("YOLO_CONF_THRESHOLD", "0.5")),
    
    # Depth Estimation Configuration (auto-detected when model file exists)
    "SPATIAL_USE_MIDAS": os.environ.get("SPATIAL_USE_MIDAS", "auto").lower(),
    "MIDAS_MODEL_PATH": os.environ.get("MIDAS_MODEL_PATH", "models/midas_v21_small_256.onnx"),
    "MIDAS_MODEL_TYPE": os.environ.get("MIDAS_MODEL_TYPE", "MiDaS_small"),
    
    # Segmentation and Depth Configuration (DISABLED for performance)
    "ENABLE_SEGMENTATION": os.environ.get("ENABLE_SEGMENTATION", "false").lower() == "true",
    "ENABLE_DEPTH": os.environ.get("ENABLE_DEPTH", "false").lower() == "true",
    
    # Spatial Perception Thresholds
    "CRITICAL_DISTANCE_M": float(os.environ.get("CRITICAL_DISTANCE_M", "1.0")),
    "NEAR_DISTANCE_M": float(os.environ.get("NEAR_DISTANCE_M", "2.0")),
    "FAR_DISTANCE_M": float(os.environ.get("FAR_DISTANCE_M", "5.0")),
    
    # Low-latency mode: skip LLM and use direct TTS for critical obstacles
    "LOW_LATENCY_WARNINGS": os.environ.get("LOW_LATENCY_WARNINGS", "true").lower() == "true",
    
    # =========================================================================
    # NEW FEATURES CONFIGURATION
    # =========================================================================
    
    # Speech-VQA Bridge (STT ↔ VQA ↔ TTS)
    "ENABLE_SPEECH_VQA": os.environ.get("ENABLE_SPEECH_VQA", "true").lower() == "true",
    
    # Priority Scene Module (Top-3 Hazards)
    "ENABLE_PRIORITY_SCENE": os.environ.get("ENABLE_PRIORITY_SCENE", "true").lower() == "true",
    "PRIORITY_TOP_N": int(os.environ.get("PRIORITY_TOP_N", "3")),
    
    # Debug Visualizer
    "ENABLE_DEBUG_VISUALIZER": os.environ.get("ENABLE_DEBUG_VISUALIZER", "true").lower() == "true",

    # QR / AR Tag Scanning
    "ENABLE_QR_SCANNING": os.environ.get("ENABLE_QR_SCANNING", "true").lower() == "true",
    "QR_CACHE_ENABLED": os.environ.get("QR_CACHE_ENABLED", "true").lower() == "true",
    "QR_AUTO_DETECT": os.environ.get("QR_AUTO_DETECT", "true").lower() == "true",
    "QR_CACHE_TTL_SECONDS": int(os.environ.get("QR_CACHE_TTL_SECONDS", "86400")),
    "QR_CACHE_DIR": os.environ.get("QR_CACHE_DIR", ""),  # empty = default dir

    # Latency Targets (ms)
    "TARGET_STT_LATENCY_MS": float(os.environ.get("TARGET_STT_LATENCY_MS", "100")),
    "TARGET_VQA_LATENCY_MS": float(os.environ.get("TARGET_VQA_LATENCY_MS", "300")),
    "TARGET_TTS_LATENCY_MS": float(os.environ.get("TARGET_TTS_LATENCY_MS", "100")),
    "TARGET_TOTAL_LATENCY_MS": float(os.environ.get("TARGET_TOTAL_LATENCY_MS", "500")),

    # =========================================================================
    # LIVE FRAME & CONTINUOUS CAPTURE CONFIGURATION
    # =========================================================================
    "LIVE_FRAME_MAX_AGE_MS": float(os.environ.get("LIVE_FRAME_MAX_AGE_MS", "500")),
    "CAPTURE_CADENCE_MS": float(os.environ.get("CAPTURE_CADENCE_MS", "100")),
    "FRAME_BUFFER_CAPACITY": int(os.environ.get("FRAME_BUFFER_CAPACITY", "30")),
    "HOT_PATH_TIMEOUT_MS": float(os.environ.get("HOT_PATH_TIMEOUT_MS", "500")),
    "PIPELINE_TIMEOUT_MS": float(os.environ.get("PIPELINE_TIMEOUT_MS", "300")),

    # Worker pool concurrency
    "NUM_DETECT_WORKERS": int(os.environ.get("NUM_DETECT_WORKERS", "2")),
    "NUM_DEPTH_WORKERS": int(os.environ.get("NUM_DEPTH_WORKERS", "1")),
    "NUM_SEGMENT_WORKERS": int(os.environ.get("NUM_SEGMENT_WORKERS", "1")),
    "NUM_OCR_WORKERS": int(os.environ.get("NUM_OCR_WORKERS", "1")),
    "NUM_QR_WORKERS": int(os.environ.get("NUM_QR_WORKERS", "1")),
    "NUM_EMBEDDING_WORKERS": int(os.environ.get("NUM_EMBEDDING_WORKERS", "1")),

    # Debounce & deduplication
    "DEBOUNCE_WINDOW_SECONDS": float(os.environ.get("DEBOUNCE_WINDOW_SECONDS", "5.0")),
    "DISTANCE_DELTA_M": float(os.environ.get("DISTANCE_DELTA_M", "0.5")),
    "CONFIDENCE_DELTA": float(os.environ.get("CONFIDENCE_DELTA", "0.15")),

    # Watchdog
    "CAMERA_STALL_THRESHOLD_MS": float(os.environ.get("CAMERA_STALL_THRESHOLD_MS", "2000")),
    "WORKER_STALL_THRESHOLD_MS": float(os.environ.get("WORKER_STALL_THRESHOLD_MS", "5000")),

    # =========================================================================
    # ALWAYS-ON / PROACTIVE CONTINUOUS PROCESSING
    # =========================================================================
    "ALWAYS_ON": os.environ.get("ALWAYS_ON", "true").lower() == "true",
    "CONTINUOUS_PROCESSING": os.environ.get("CONTINUOUS_PROCESSING", "true").lower() == "true",
    "PROACTIVE_ANNOUNCE": os.environ.get("PROACTIVE_ANNOUNCE", "true").lower() == "true",
    "PROACTIVE_CADENCE_S": float(os.environ.get("PROACTIVE_CADENCE_S", "2.0")),
    "PROACTIVE_CRITICAL_ONLY": os.environ.get("PROACTIVE_CRITICAL_ONLY", "false").lower() == "true",

    # Privacy & consent
    "MEMORY_TELEMETRY": os.environ.get("MEMORY_TELEMETRY", "false").lower() == "true",
    "MEMORY_REQUIRE_CONSENT": os.environ.get("MEMORY_REQUIRE_CONSENT", "true").lower() == "true",

    # =========================================================================
    # FEATURE 8 — FACE DETECTION / RECOGNITION
    # =========================================================================
    "FACE_ENGINE_ENABLED": os.environ.get("FACE_ENGINE_ENABLED", "true").lower() == "true",
    "FACE_REGISTRATION_ENABLED": os.environ.get("FACE_REGISTRATION_ENABLED", "false").lower() == "true",
    "FACE_CONSENT_REQUIRED": os.environ.get("FACE_CONSENT_REQUIRED", "true").lower() == "true",
    "FACE_DETECTOR_BACKEND": os.environ.get("FACE_DETECTOR_BACKEND", "auto"),  # auto|mtcnn|retinaface|haar|mock
    "FACE_MIN_CONFIDENCE": float(os.environ.get("FACE_MIN_CONFIDENCE", "0.5")),
    "FACE_MAX_TRACKED": int(os.environ.get("FACE_MAX_TRACKED", "20")),
    "FACE_ENCRYPTION_ENABLED": os.environ.get("FACE_ENCRYPTION_ENABLED", "true").lower() == "true",
    "NUM_FACE_WORKERS": int(os.environ.get("NUM_FACE_WORKERS", "1")),

    # =========================================================================
    # FEATURE 9 — AUDIO ENGINE / SOUND SOURCE LOCALIZATION
    # =========================================================================
    "AUDIO_ENGINE_ENABLED": os.environ.get("AUDIO_ENGINE_ENABLED", "true").lower() == "true",
    "AUDIO_SSL_ENABLED": os.environ.get("AUDIO_SSL_ENABLED", "true").lower() == "true",
    "AUDIO_EVENT_DETECTION_ENABLED": os.environ.get("AUDIO_EVENT_DETECTION_ENABLED", "true").lower() == "true",
    "AUDIO_SAMPLE_RATE": int(os.environ.get("AUDIO_SAMPLE_RATE", "16000")),
    "AUDIO_MIN_ENERGY_DB": float(os.environ.get("AUDIO_MIN_ENERGY_DB", "-40")),
    "NUM_AUDIO_WORKERS": int(os.environ.get("NUM_AUDIO_WORKERS", "1")),

    # =========================================================================
    # FEATURE 10 — ACTION / INTENT RECOGNITION
    # =========================================================================
    "ACTION_ENGINE_ENABLED": os.environ.get("ACTION_ENGINE_ENABLED", "true").lower() == "true",
    "ACTION_CLIP_LENGTH": int(os.environ.get("ACTION_CLIP_LENGTH", "16")),
    "ACTION_CLIP_STRIDE": int(os.environ.get("ACTION_CLIP_STRIDE", "4")),
    "ACTION_MIN_CONFIDENCE": float(os.environ.get("ACTION_MIN_CONFIDENCE", "0.3")),
    "NUM_ACTION_WORKERS": int(os.environ.get("NUM_ACTION_WORKERS", "1")),

    # =========================================================================
    # FEATURE 11 — CLOUD SYNC / EVENT DETECTION
    # =========================================================================
    "CLOUD_SYNC_ENABLED": os.environ.get("CLOUD_SYNC", "false").lower() == "true",
    "CLOUD_SYNC_PROVIDER": os.environ.get("CLOUD_SYNC_PROVIDER", "stub"),
    "MEMORY_EVENT_DETECTION": os.environ.get("MEMORY_EVENT_DETECTION", "true").lower() == "true",
    "MEMORY_AUTO_SUMMARIZE": os.environ.get("MEMORY_AUTO_SUMMARIZE", "true").lower() == "true",

    # =========================================================================
    # FEATURE 12 — TAVUS INTEGRATION
    # =========================================================================
    "TAVUS_ENABLED": os.environ.get("TAVUS_ENABLED", "false").lower() == "true",

    # =========================================================================
    # RAW MEDIA & MISC
    # =========================================================================
    "RAW_MEDIA_SAVE": os.environ.get("RAW_MEDIA_SAVE", "false").lower() == "true",

    # =========================================================================

    # Common configuration
    "MAX_TOKENS": 500,
    "TEMPERATURE": 0.7,
}

def get_config():
    """Get the current configuration."""
    return CONFIG


def get_secret_provider():
    """Access the active secret provider."""
    return _secret_provider

def use_ollama():
    """Check if Ollama is the current vision provider."""
    return CONFIG["VISION_PROVIDER"] == VisionProvider.OLLAMA

def spatial_enabled():
    """Check if spatial perception is enabled."""
    return CONFIG["SPATIAL_PERCEPTION_ENABLED"]

def get_spatial_config():
    """Get spatial perception specific configuration."""
    return {
        "enabled": CONFIG["SPATIAL_PERCEPTION_ENABLED"],
        "use_yolo": CONFIG["SPATIAL_USE_YOLO"],
        "yolo_model_path": CONFIG["YOLO_MODEL_PATH"],
        "yolo_conf_threshold": CONFIG["YOLO_CONF_THRESHOLD"],
        "use_midas": CONFIG["SPATIAL_USE_MIDAS"],
        "midas_model_path": CONFIG["MIDAS_MODEL_PATH"],
        "midas_model_type": CONFIG["MIDAS_MODEL_TYPE"],
        "enable_segmentation": CONFIG["ENABLE_SEGMENTATION"],
        "enable_depth": CONFIG["ENABLE_DEPTH"],
        "critical_distance": CONFIG["CRITICAL_DISTANCE_M"],
        "near_distance": CONFIG["NEAR_DISTANCE_M"],
        "far_distance": CONFIG["FAR_DISTANCE_M"],
        "low_latency_warnings": CONFIG["LOW_LATENCY_WARNINGS"],
    }


def get_new_features_config():
    """Get configuration for new features (Speech-VQA, Priority Scene, Debug Visualizer)."""
    return {
        "speech_vqa_enabled": CONFIG["ENABLE_SPEECH_VQA"],
        "priority_scene_enabled": CONFIG["ENABLE_PRIORITY_SCENE"],
        "priority_top_n": CONFIG["PRIORITY_TOP_N"],
        "debug_visualizer_enabled": CONFIG["ENABLE_DEBUG_VISUALIZER"],
        "latency_targets": {
            "stt_ms": CONFIG["TARGET_STT_LATENCY_MS"],
            "vqa_ms": CONFIG["TARGET_VQA_LATENCY_MS"],
            "tts_ms": CONFIG["TARGET_TTS_LATENCY_MS"],
            "total_ms": CONFIG["TARGET_TOTAL_LATENCY_MS"],
        },
    }


def qr_enabled() -> bool:
    """Check if QR / AR tag scanning is enabled."""
    return CONFIG["ENABLE_QR_SCANNING"]


def get_qr_config():
    """Get QR / AR scanning configuration."""
    return {
        "enabled": CONFIG["ENABLE_QR_SCANNING"],
        "cache_enabled": CONFIG["QR_CACHE_ENABLED"],
        "auto_detect": CONFIG["QR_AUTO_DETECT"],
        "cache_ttl": CONFIG["QR_CACHE_TTL_SECONDS"],
        "cache_dir": CONFIG["QR_CACHE_DIR"],
    }


def get_live_frame_config():
    """Get live-frame and continuous capture configuration."""
    return {
        "live_frame_max_age_ms": CONFIG["LIVE_FRAME_MAX_AGE_MS"],
        "capture_cadence_ms": CONFIG["CAPTURE_CADENCE_MS"],
        "frame_buffer_capacity": CONFIG["FRAME_BUFFER_CAPACITY"],
        "hot_path_timeout_ms": CONFIG["HOT_PATH_TIMEOUT_MS"],
        "pipeline_timeout_ms": CONFIG["PIPELINE_TIMEOUT_MS"],
    }


def get_worker_config():
    """Get worker pool concurrency configuration."""
    return {
        "num_detect_workers": CONFIG["NUM_DETECT_WORKERS"],
        "num_depth_workers": CONFIG["NUM_DEPTH_WORKERS"],
        "num_segment_workers": CONFIG["NUM_SEGMENT_WORKERS"],
        "num_ocr_workers": CONFIG["NUM_OCR_WORKERS"],
        "num_qr_workers": CONFIG["NUM_QR_WORKERS"],
        "num_embedding_workers": CONFIG["NUM_EMBEDDING_WORKERS"],
    }


def get_debounce_config():
    """Get debounce and deduplication configuration."""
    return {
        "debounce_window_seconds": CONFIG["DEBOUNCE_WINDOW_SECONDS"],
        "distance_delta_m": CONFIG["DISTANCE_DELTA_M"],
        "confidence_delta": CONFIG["CONFIDENCE_DELTA"],
    }


def get_watchdog_config():
    """Get watchdog configuration."""
    return {
        "camera_stall_threshold_ms": CONFIG["CAMERA_STALL_THRESHOLD_MS"],
        "worker_stall_threshold_ms": CONFIG["WORKER_STALL_THRESHOLD_MS"],
    }


def get_continuous_config():
    """Get always-on / continuous processing configuration."""
    return {
        "always_on": CONFIG["ALWAYS_ON"],
        "continuous_processing": CONFIG["CONTINUOUS_PROCESSING"],
        "proactive_announce": CONFIG["PROACTIVE_ANNOUNCE"],
        "proactive_cadence_s": CONFIG["PROACTIVE_CADENCE_S"],
        "proactive_critical_only": CONFIG["PROACTIVE_CRITICAL_ONLY"],
    }


def face_enabled() -> bool:
    """Check if face engine is enabled."""
    return CONFIG["FACE_ENGINE_ENABLED"]


def get_face_config():
    """Get face engine configuration."""
    return {
        "enabled": CONFIG["FACE_ENGINE_ENABLED"],
        "registration_enabled": CONFIG["FACE_REGISTRATION_ENABLED"],
        "consent_required": CONFIG["FACE_CONSENT_REQUIRED"],
        "detector_backend": CONFIG["FACE_DETECTOR_BACKEND"],
        "min_confidence": CONFIG["FACE_MIN_CONFIDENCE"],
        "max_tracked": CONFIG["FACE_MAX_TRACKED"],
        "encryption_enabled": CONFIG["FACE_ENCRYPTION_ENABLED"],
        "num_workers": CONFIG["NUM_FACE_WORKERS"],
    }


def audio_enabled() -> bool:
    """Check if audio engine is enabled."""
    return CONFIG["AUDIO_ENGINE_ENABLED"]


def get_audio_config():
    """Get audio engine configuration."""
    return {
        "enabled": CONFIG["AUDIO_ENGINE_ENABLED"],
        "ssl_enabled": CONFIG["AUDIO_SSL_ENABLED"],
        "event_detection_enabled": CONFIG["AUDIO_EVENT_DETECTION_ENABLED"],
        "sample_rate": CONFIG["AUDIO_SAMPLE_RATE"],
        "min_energy_db": CONFIG["AUDIO_MIN_ENERGY_DB"],
        "num_workers": CONFIG["NUM_AUDIO_WORKERS"],
    }


def action_enabled() -> bool:
    """Check if action engine is enabled."""
    return CONFIG["ACTION_ENGINE_ENABLED"]


def get_action_config():
    """Get action engine configuration."""
    return {
        "enabled": CONFIG["ACTION_ENGINE_ENABLED"],
        "clip_length": CONFIG["ACTION_CLIP_LENGTH"],
        "clip_stride": CONFIG["ACTION_CLIP_STRIDE"],
        "min_confidence": CONFIG["ACTION_MIN_CONFIDENCE"],
        "num_workers": CONFIG["NUM_ACTION_WORKERS"],
    }


def tavus_enabled() -> bool:
    """Check if Tavus integration is enabled."""
    return CONFIG["TAVUS_ENABLED"]


def cloud_sync_enabled() -> bool:
    """Check if cloud sync is enabled."""
    return CONFIG["CLOUD_SYNC_ENABLED"]


def get_cloud_sync_config():
    """Get cloud sync configuration."""
    return {
        "enabled": CONFIG["CLOUD_SYNC_ENABLED"],
        "provider": CONFIG["CLOUD_SYNC_PROVIDER"],
        "event_detection": CONFIG["MEMORY_EVENT_DETECTION"],
        "auto_summarize": CONFIG["MEMORY_AUTO_SUMMARIZE"],
    }
