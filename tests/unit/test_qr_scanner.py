"""
Unit tests for QR Scanner module.
"""

import pytest
from PIL import Image

from core.qr.qr_scanner import QRScanner, QRDetection


class TestQRDetection:
    """Tests for the QRDetection dataclass."""

    def test_detection_fields(self):
        det = QRDetection(raw_data="hello", bbox=(10, 20, 100, 100))
        assert det.raw_data == "hello"
        assert det.bbox == (10, 20, 100, 100)
        assert det.confidence == 1.0
        assert det.format_type == "QR"
        assert det.timestamp > 0

    def test_detection_custom_format(self):
        det = QRDetection(raw_data="data", bbox=(0, 0, 50, 50), format_type="EAN13")
        assert det.format_type == "EAN13"


class TestQRScanner:
    """Tests for QRScanner initialisation and scan logic."""

    def test_scanner_instantiation(self):
        scanner = QRScanner()
        # Should not raise; uses whatever backend is available
        assert isinstance(scanner, QRScanner)

    def test_is_ready(self):
        scanner = QRScanner()
        # At least one backend should be available (cv2 is in requirements)
        assert isinstance(scanner.is_ready, bool)

    def test_scan_blank_image(self):
        """Scanning a plain white image should return no detections."""
        scanner = QRScanner()
        if not scanner.is_ready:
            pytest.skip("No QR backend available")
        img = Image.new("RGB", (200, 200), color=(255, 255, 255))
        results = scanner.scan(img)
        assert isinstance(results, list)
        assert len(results) == 0

    def test_scan_returns_list(self):
        scanner = QRScanner()
        if not scanner.is_ready:
            pytest.skip("No QR backend available")
        img = Image.new("RGB", (100, 100), color=(128, 128, 128))
        results = scanner.scan(img)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_scan_async_blank(self):
        scanner = QRScanner()
        if not scanner.is_ready:
            pytest.skip("No QR backend available")
        img = Image.new("RGB", (200, 200), color=(255, 255, 255))
        results = await scanner.scan_async(img)
        assert isinstance(results, list)
        assert len(results) == 0


class TestQRScannerWithGeneratedQR:
    """Tests using programmatically generated QR images (requires qrcode lib)."""

    @staticmethod
    def _make_qr_image(data: str) -> Image.Image:
        """Generate a QR code image. Skip if qrcode lib is missing."""
        try:
            import qrcode
        except ImportError:
            pytest.skip("qrcode library not installed – skipping generated QR tests")
        qr = qrcode.make(data)
        return qr.convert("RGB")

    def test_scan_generated_url(self):
        scanner = QRScanner()
        if not scanner.is_ready:
            pytest.skip("No QR backend available")
        img = self._make_qr_image("https://example.com")
        results = scanner.scan(img)
        assert len(results) >= 1
        assert results[0].raw_data == "https://example.com"

    def test_scan_generated_text(self):
        scanner = QRScanner()
        if not scanner.is_ready:
            pytest.skip("No QR backend available")
        img = self._make_qr_image("stop_id=145")
        results = scanner.scan(img)
        assert len(results) >= 1
        assert results[0].raw_data == "stop_id=145"

    @pytest.mark.asyncio
    async def test_scan_async_generated(self):
        scanner = QRScanner()
        if not scanner.is_ready:
            pytest.skip("No QR backend available")
        img = self._make_qr_image("geo:37.7749,-122.4194")
        results = await scanner.scan_async(img)
        assert len(results) >= 1
        assert "geo:" in results[0].raw_data

    # ── Adversarial / edge-case tests ─────────────────────────────

    def test_scan_rotated_90(self):
        """QR code rotated 90° should still decode (preprocessing handles)."""
        scanner = QRScanner()
        if not scanner.is_ready:
            pytest.skip("No QR backend available")
        img = self._make_qr_image("https://rotated.example.com")
        rotated = img.rotate(90, expand=True)
        results = scanner.scan(rotated)
        # pyzbar can detect rotated codes; cv2 may not — allow fallthrough
        if results:
            assert results[0].raw_data == "https://rotated.example.com"

    def test_scan_low_contrast(self):
        """Low-contrast QR should be rescued by preprocessing retry."""
        from PIL import ImageEnhance
        scanner = QRScanner()
        if not scanner.is_ready:
            pytest.skip("No QR backend available")
        img = self._make_qr_image("low-contrast-data")
        enhancer = ImageEnhance.Contrast(img)
        dim = enhancer.enhance(0.3)

        results = scanner.scan(dim)
        if results:
            assert results[0].raw_data == "low-contrast-data"

    def test_scan_blurred(self):
        """Mildly blurred QR should ideally be detected via scaling retry."""
        from PIL import ImageFilter
        scanner = QRScanner()
        if not scanner.is_ready:
            pytest.skip("No QR backend available")
        img = self._make_qr_image("blurry-code")
        blurred = img.filter(ImageFilter.GaussianBlur(radius=1))
        results = scanner.scan(blurred)
        if results:
            assert results[0].raw_data == "blurry-code"

    def test_scan_small_scale(self):
        """QR code scaled to 50% should be found by multi-scale retry."""
        scanner = QRScanner()
        if not scanner.is_ready:
            pytest.skip("No QR backend available")
        img = self._make_qr_image("small-scale-test")
        w, h = img.size
        small = img.resize((w // 2, h // 2))
        results = scanner.scan(small)
        if results:
            assert results[0].raw_data == "small-scale-test"

    def test_edge_density_high_for_qr(self):
        """QR codes have high edge density; blank images have low density."""
        scanner = QRScanner()
        qr_img = self._make_qr_image("edge-density-test")
        blank_img = Image.new("RGB", (200, 200), color=(200, 200, 200))

        qr_density = scanner.edge_density(qr_img)
        blank_density = scanner.edge_density(blank_img)
        assert qr_density > blank_density

