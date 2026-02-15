"""
QR/AR Tag Scanning Engine with Contextual Deep Linking and Offline Cache.

Provides:
- QRScanner: detect QR codes from camera frames
- QRDecoder: decode and classify QR payloads
- ARTagHandler: detect AprilTag / ArUco markers
- CacheManager: offline-first local cache for scan results
- QR API helpers: FastAPI endpoint builders
"""

from .qr_scanner import QRScanner, QRDetection
from .qr_decoder import QRDecoder, QRContentType, DecodedQR
from .ar_tag_handler import ARTagHandler, ARDetection
from .cache_manager import CacheManager, CacheEntry
from .qr_api import build_qr_router

__all__ = [
    "QRScanner",
    "QRDetection",
    "QRDecoder",
    "QRContentType",
    "DecodedQR",
    "ARTagHandler",
    "ARDetection",
    "CacheManager",
    "CacheEntry",
    "build_qr_router",
]
