"""
Integration tests for the full QR scanning flow.

Covers: scan → decode → cache → API endpoints.
"""

import base64
import io
import json
from typing import Optional

import pytest
from PIL import Image

from core.qr.cache_manager import CacheManager
from core.qr.qr_decoder import QRContentType, QRDecoder

# ── Component imports ────────────────────────────────────────────────
from core.qr.qr_scanner import QRScanner

# ── Helpers ──────────────────────────────────────────────────────────

def _make_qr_image(data: str) -> Optional[Image.Image]:
    """Generate a QR code image. Returns None if qrcode is missing."""
    try:
        import qrcode
        return qrcode.make(data).convert("RGB")
    except ImportError:
        return None


def _image_to_b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# ── End-to-end scan → decode → cache ────────────────────────────────

class TestFullScanFlow:
    """Scan an image, decode the QR, store in cache, retrieve from cache."""

    @pytest.fixture
    def scanner(self):
        s = QRScanner()
        if not s.is_ready:
            pytest.skip("No QR backend available")
        return s

    @pytest.fixture
    def decoder(self):
        return QRDecoder()

    @pytest.fixture
    def cache(self, tmp_path):
        return CacheManager(cache_dir=str(tmp_path / "test_cache"), ttl=3600)

    def test_url_flow(self, scanner, decoder, cache):
        img = _make_qr_image("https://example.com/info")
        if img is None:
            pytest.skip("qrcode library not installed")

        # Scan
        detections = scanner.scan(img)
        assert len(detections) >= 1
        raw = detections[0].raw_data

        # Decode (sync)
        decoded = decoder.decode_sync(raw)
        assert decoded.content_type == QRContentType.URL
        assert "example.com" in decoded.contextual_message

        # Cache
        cache.put(
            raw_data=decoded.raw_data,
            content_type=decoded.content_type.value,
            contextual_message=decoded.contextual_message,
        )
        cached = cache.get(raw)
        assert cached is not None
        assert cached.contextual_message == decoded.contextual_message

    def test_transport_flow(self, scanner, decoder, cache):
        img = _make_qr_image("stop_id=145&route=14&destination=Downtown")
        if img is None:
            pytest.skip("qrcode library not installed")

        detections = scanner.scan(img)
        assert len(detections) >= 1

        decoded = decoder.decode_sync(detections[0].raw_data)
        assert decoded.content_type == QRContentType.TRANSPORT
        assert "145" in decoded.contextual_message
        assert decoded.navigation_available is True

        # Cache round-trip
        cache.put(
            raw_data=decoded.raw_data,
            content_type=decoded.content_type.value,
            contextual_message=decoded.contextual_message,
            navigation_available=decoded.navigation_available,
        )
        cached = cache.get(decoded.raw_data)
        assert cached is not None
        assert cached.navigation_available is True

    def test_geo_flow(self, scanner, decoder, cache):
        img = _make_qr_image("geo:37.7749,-122.4194")
        if img is None:
            pytest.skip("qrcode library not installed")

        detections = scanner.scan(img)
        assert len(detections) >= 1

        decoded = decoder.decode_sync(detections[0].raw_data)
        assert decoded.content_type == QRContentType.LOCATION
        assert decoded.lat == pytest.approx(37.7749)
        assert decoded.navigation_available is True

    def test_wifi_flow(self, scanner, decoder, cache):
        img = _make_qr_image("WIFI:T:WPA;S:MyNetwork;P:secret123;")
        if img is None:
            pytest.skip("qrcode library not installed")

        detections = scanner.scan(img)
        decoded = decoder.decode_sync(detections[0].raw_data)
        assert decoded.content_type == QRContentType.WIFI
        assert "MyNetwork" in decoded.contextual_message

    def test_json_transport_flow(self, scanner, decoder, cache):
        payload = json.dumps({"stop_id": 42, "route": "7A", "destination": "Airport"})
        img = _make_qr_image(payload)
        if img is None:
            pytest.skip("qrcode library not installed")

        detections = scanner.scan(img)
        decoded = decoder.decode_sync(detections[0].raw_data)
        assert decoded.content_type == QRContentType.TRANSPORT


class TestOfflineCache:
    """Cache must serve results when "offline" (no fetch callback)."""

    @pytest.fixture
    def cache(self, tmp_path):
        return CacheManager(cache_dir=str(tmp_path / "offline"), ttl=3600)

    def test_offline_hit(self, cache):
        cache.put(
            raw_data="stop_id=99",
            content_type="transport",
            contextual_message="Bus stop 99 — Route 5 to Central.",
            source="online",
            navigation_available=True,
        )
        # Simulate "offline" by not calling any fetch — just cache.get
        entry = cache.get("stop_id=99")
        assert entry is not None
        assert entry.source == "online"
        assert "Bus stop 99" in entry.contextual_message

    def test_offline_miss_then_populate(self, cache):
        assert cache.get("new_code") is None
        # Simulate scanning and caching locally
        cache.put(
            raw_data="new_code",
            content_type="text",
            contextual_message="Decoded locally.",
            source="offline",
        )
        entry = cache.get("new_code")
        assert entry is not None
        assert entry.source == "offline"


# ── API endpoint integration (requires FastAPI test client) ──────────

class TestQRAPI:
    @pytest.fixture
    def app(self, tmp_path):
        try:
            from fastapi import FastAPI
        except ImportError:
            pytest.skip("FastAPI not installed")

        from core.qr import build_qr_router

        app = FastAPI()
        cache = CacheManager(cache_dir=str(tmp_path / "api_cache"), ttl=3600)
        app.include_router(build_qr_router(cache=cache), prefix="/qr")
        return app

    @pytest.fixture
    def client(self, app):
        """Async client using httpx ASGITransport (httpx >=0.28)."""
        import httpx
        transport = httpx.ASGITransport(app=app)
        return httpx.AsyncClient(transport=transport, base_url="http://test")

    @pytest.mark.asyncio
    async def test_scan_no_qr(self, client):
        img = Image.new("RGB", (100, 100), color=(255, 255, 255))
        resp = await client.post("/qr/scan", json={"image": _image_to_b64(img)})
        assert resp.status_code == 200
        data = resp.json()
        assert "No QR" in data["contextual_message"] or data["raw_data"] == ""

    @pytest.mark.asyncio
    async def test_scan_with_qr(self, client):
        img = _make_qr_image("https://example.com")
        if img is None:
            pytest.skip("qrcode library not installed")
        resp = await client.post("/qr/scan", json={"image": _image_to_b64(img)})
        assert resp.status_code == 200
        data = resp.json()
        assert data["raw_data"] == "https://example.com"
        assert data["source"] in ("online", "cache")
        assert data["content_type"] == "url"

    @pytest.mark.asyncio
    async def test_scan_cache_hit(self, client):
        """Second scan should return source='cache'."""
        img = _make_qr_image("https://cached.example.com")
        if img is None:
            pytest.skip("qrcode library not installed")
        # First scan: populates cache
        resp1 = await client.post("/qr/scan", json={"image": _image_to_b64(img)})
        assert resp1.json()["source"] == "online"
        # Second scan: cache hit
        resp2 = await client.post("/qr/scan", json={"image": _image_to_b64(img)})
        assert resp2.json()["source"] == "cache"

    @pytest.mark.asyncio
    async def test_manual_cache(self, client):
        resp = await client.post(
            "/qr/cache",
            json={
                "raw_data": "manual_entry",
                "content_type": "text",
                "contextual_message": "Manually cached.",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_history(self, client):
        # Insert entries
        for i in range(3):
            await client.post(
                "/qr/cache",
                json={
                    "raw_data": f"hist_{i}",
                    "content_type": "text",
                    "contextual_message": f"entry {i}",
                },
            )
        resp = await client.get("/qr/history?limit=10")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) >= 3

    @pytest.mark.asyncio
    async def test_debug_endpoint(self, client):
        img = Image.new("RGB", (100, 100), color=(200, 200, 200))
        resp = await client.post("/qr/debug", json={"image": _image_to_b64(img)})
        assert resp.status_code == 200
        data = resp.json()
        assert "qr_detections" in data
        assert "elapsed_ms" in data

    @pytest.mark.asyncio
    async def test_scan_invalid_image(self, client):
        resp = await client.post("/qr/scan", json={"image": "NOT_BASE64!!!"})
        assert resp.status_code == 400
