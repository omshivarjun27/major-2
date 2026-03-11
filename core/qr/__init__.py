"""
QR/AR Tag Scanning Engine with Contextual Deep Linking and Offline Cache.

Provides:
- QRScanner: detect QR codes from camera frames
- QRDecoder: decode and classify QR payloads
- ARTagHandler: detect AprilTag / ArUco markers
- CacheManager: offline-first local cache for scan results
- QR API helpers: FastAPI endpoint builders
"""

from .ar_tag_handler import ARDetection, ARTagHandler
from .cache_manager import CacheEntry, CacheManager
from .qr_api import build_qr_router
from .qr_decoder import DecodedQR, QRContentType, QRDecoder
from .qr_scanner import QRDetection, QRScanner

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
