"""
QR/AR REST API – FastAPI router for scan, cache, history, and debug endpoints.

Usage in app.py:
    from core.qr import build_qr_router
    app.include_router(build_qr_router(), prefix="/qr")
"""

from __future__ import annotations

import base64
import io
import logging
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from PIL import Image

from .qr_scanner import QRScanner, QRDetection
from .qr_decoder import QRDecoder, DecodedQR
from .ar_tag_handler import ARTagHandler
from .cache_manager import CacheManager

logger = logging.getLogger("qr-api")

# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class ScanRequest(BaseModel):
    """POST /qr/scan body."""

    image: str = Field(..., description="Base64-encoded image (JPEG or PNG)")


class ScanResponse(BaseModel):
    raw_data: str = ""
    contextual_message: str = ""
    content_type: str = "text"
    source: str = "online"  # "online" | "cache"
    navigation_available: bool = False
    lat: Optional[float] = None
    lon: Optional[float] = None
    elapsed_ms: float = 0.0
    ar_markers: List[Dict[str, Any]] = Field(default_factory=list)


class CachePayload(BaseModel):
    raw_data: str
    content_type: str = "text"
    contextual_message: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    ttl: Optional[int] = None


class HistoryItem(BaseModel):
    raw_data: str
    content_type: str
    contextual_message: str
    source: str
    created_at: float
    navigation_available: bool = False


class DebugResponse(BaseModel):
    qr_detections: List[Dict[str, Any]] = Field(default_factory=list)
    ar_detections: List[Dict[str, Any]] = Field(default_factory=list)
    decoded: Optional[Dict[str, Any]] = None
    cache_status: str = "miss"
    elapsed_ms: float = 0.0


# ---------------------------------------------------------------------------
# Router factory
# ---------------------------------------------------------------------------


def build_qr_router(
    scanner: Optional[QRScanner] = None,
    decoder: Optional[QRDecoder] = None,
    ar_handler: Optional[ARTagHandler] = None,
    cache: Optional[CacheManager] = None,
) -> APIRouter:
    """
    Build and return a FastAPI ``APIRouter`` with all QR endpoints.

    Any dependency that is ``None`` will be created with defaults.
    """
    _scanner = scanner or QRScanner()
    _decoder = decoder or QRDecoder()
    _ar = ar_handler or ARTagHandler()
    _cache = cache or CacheManager()

    router = APIRouter(tags=["QR / AR Scanning"])

    # ---- helpers --------------------------------------------------------

    def _decode_image(b64: str) -> Image.Image:
        try:
            raw_bytes = base64.b64decode(b64)
            return Image.open(io.BytesIO(raw_bytes)).convert("RGB")
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid image: {exc}")

    # ---- POST /qr/scan --------------------------------------------------

    @router.post("/scan", response_model=ScanResponse)
    async def scan_qr(req: ScanRequest) -> ScanResponse:
        """Scan an image for QR codes and AR markers, return contextual info."""
        start = time.time()
        image = _decode_image(req.image)

        # 1. QR detection
        qr_hits: List[QRDetection] = await _scanner.scan_async(image)

        # 2. AR detection (parallel-safe, independent)
        ar_hits = await _ar.detect_async(image) if _ar.is_ready else []

        if not qr_hits and not ar_hits:
            return ScanResponse(
                contextual_message="No QR code or AR tag detected.",
                elapsed_ms=(time.time() - start) * 1000,
            )

        # Process first QR hit
        source = "online"
        decoded: Optional[DecodedQR] = None
        if qr_hits:
            raw = qr_hits[0].raw_data

            # Check cache first
            cached = _cache.get(raw)
            if cached:
                return ScanResponse(
                    raw_data=cached.raw_data,
                    contextual_message=cached.contextual_message,
                    content_type=cached.content_type,
                    source="cache",
                    navigation_available=cached.navigation_available,
                    lat=cached.lat,
                    lon=cached.lon,
                    elapsed_ms=(time.time() - start) * 1000,
                    ar_markers=[d.to_dict() for d in ar_hits],
                )

            # Decode fresh
            decoded = await _decoder.decode(raw)
            source = "online"

            # Store in cache
            _cache.put(
                raw_data=decoded.raw_data,
                content_type=decoded.content_type.value,
                contextual_message=decoded.contextual_message,
                metadata=decoded.metadata,
                source=source,
                navigation_available=decoded.navigation_available,
                lat=decoded.lat,
                lon=decoded.lon,
            )

        # Build response
        if decoded:
            return ScanResponse(
                raw_data=decoded.raw_data,
                contextual_message=decoded.contextual_message,
                content_type=decoded.content_type.value,
                source=source,
                navigation_available=decoded.navigation_available,
                lat=decoded.lat,
                lon=decoded.lon,
                elapsed_ms=(time.time() - start) * 1000,
                ar_markers=[d.to_dict() for d in ar_hits],
            )

        # Only AR markers
        return ScanResponse(
            contextual_message=f"Detected {len(ar_hits)} AR marker(s).",
            elapsed_ms=(time.time() - start) * 1000,
            ar_markers=[d.to_dict() for d in ar_hits],
        )

    # ---- POST /qr/cache -------------------------------------------------

    @router.post("/cache")
    async def add_to_cache(payload: CachePayload) -> Dict[str, Any]:
        """Manually add or update a cache entry."""
        entry = _cache.put(
            raw_data=payload.raw_data,
            content_type=payload.content_type,
            contextual_message=payload.contextual_message,
            metadata=payload.metadata,
            source="manual",
            ttl=payload.ttl,
        )
        return {"status": "ok", "key": entry.key, "expires_at": entry.expires_at}

    # ---- GET /qr/history -------------------------------------------------

    @router.get("/history", response_model=List[HistoryItem])
    async def get_history(limit: int = 50) -> List[HistoryItem]:
        """Return recent scan history from cache."""
        entries = _cache.history(limit=limit)
        return [
            HistoryItem(
                raw_data=e.raw_data,
                content_type=e.content_type,
                contextual_message=e.contextual_message,
                source=e.source,
                created_at=e.created_at,
                navigation_available=e.navigation_available,
            )
            for e in entries
        ]

    # ---- POST /qr/debug --------------------------------------------------

    @router.post("/debug", response_model=DebugResponse)
    async def debug_scan(req: ScanRequest) -> DebugResponse:
        """Developer endpoint: return raw detections, decoded payload, cache status."""
        start = time.time()
        image = _decode_image(req.image)

        qr_hits = await _scanner.scan_async(image)
        ar_hits = await _ar.detect_async(image) if _ar.is_ready else []

        decoded_dict = None
        cache_status = "miss"

        if qr_hits:
            raw = qr_hits[0].raw_data
            cached = _cache.get(raw)
            if cached:
                cache_status = "hit"

            d = await _decoder.decode(raw)
            decoded_dict = d.to_dict()

        return DebugResponse(
            qr_detections=[
                {"raw_data": q.raw_data, "bbox": q.bbox, "format": q.format_type}
                for q in qr_hits
            ],
            ar_detections=[a.to_dict() for a in ar_hits],
            decoded=decoded_dict,
            cache_status=cache_status,
            elapsed_ms=(time.time() - start) * 1000,
        )

    return router
