"""
Unit tests for QR Decoder module — all content type paths.
"""

import pytest

from core.qr.qr_decoder import DecodedQR, QRContentType, QRDecoder


class TestQRContentClassification:
    """Verify _classify picks the right QRContentType for every format."""

    def setup_method(self):
        self.decoder = QRDecoder()

    def test_url(self):
        d = self.decoder.decode_sync("https://example.com/about")
        assert d.content_type == QRContentType.URL
        assert d.metadata["host"] == "example.com"

    def test_geo_uri(self):
        d = self.decoder.decode_sync("geo:37.7749,-122.4194")
        assert d.content_type == QRContentType.LOCATION
        assert d.navigation_available is True
        assert d.lat == pytest.approx(37.7749)
        assert d.lon == pytest.approx(-122.4194)

    def test_wifi(self):
        d = self.decoder.decode_sync("WIFI:T:WPA;S:MyNetwork;P:secret123;")
        assert d.content_type == QRContentType.WIFI
        assert d.metadata["ssid"] == "MyNetwork"
        assert d.metadata["password"] == "secret123"

    def test_vcard(self):
        vcard = "BEGIN:VCARD\nFN:Jane Doe\nTEL:+1234567890\nEMAIL:jane@example.com\nEND:VCARD"
        d = self.decoder.decode_sync(vcard)
        assert d.content_type == QRContentType.CONTACT
        assert d.metadata["name"] == "Jane Doe"

    def test_mecard(self):
        d = self.decoder.decode_sync("MECARD:N:Smith;TEL:555-1234;EMAIL:smith@test.com;")
        assert d.content_type == QRContentType.CONTACT
        assert d.metadata["name"] == "Smith"

    def test_transport_tag(self):
        d = self.decoder.decode_sync("stop_id=145&route=42&destination=Downtown")
        assert d.content_type == QRContentType.TRANSPORT
        assert d.navigation_available is True

    def test_product_tag(self):
        d = self.decoder.decode_sync("product_id=ABC123")
        assert d.content_type == QRContentType.PRODUCT

    def test_json_transport(self):
        d = self.decoder.decode_sync('{"stop_id": "145", "route": "42"}')
        assert d.content_type == QRContentType.TRANSPORT

    def test_json_location(self):
        d = self.decoder.decode_sync('{"lat": 40.7128, "lon": -74.006, "name": "NYC"}')
        assert d.content_type == QRContentType.LOCATION
        assert d.lat == pytest.approx(40.7128)

    def test_plain_text_fallback(self):
        d = self.decoder.decode_sync("Hello World 123")
        assert d.content_type == QRContentType.TEXT

    def test_maps_url_navigable(self):
        d = self.decoder.decode_sync("https://maps.google.com/place?q=Cafe")
        assert d.content_type == QRContentType.LOCATION
        assert d.navigation_available is True


class TestDecodedQRSerialization:
    """Ensure DecodedQR.to_dict() is JSON-safe."""

    def test_to_dict_keys(self):
        d = DecodedQR(
            raw_data="test",
            content_type=QRContentType.TEXT,
            contextual_message="QR code says: test",
        )
        out = d.to_dict()
        assert "raw_data" in out
        assert "content_type" in out
        assert out["content_type"] == "text"

    def test_contextual_message_always_set(self):
        decoder = QRDecoder()
        d = decoder.decode_sync("just some text")
        assert len(d.contextual_message) > 0


class TestOfflineMessage:
    """Verify _build_offline_message for every content type."""

    def setup_method(self):
        self.decoder = QRDecoder()

    def test_transport_message(self):
        d = self.decoder.decode_sync("stop_id=42&route=7&destination=Airport")
        assert "Bus stop 42" in d.contextual_message

    def test_wifi_message(self):
        d = self.decoder.decode_sync("WIFI:S:CoffeeShop;P:pass;")
        assert "CoffeeShop" in d.contextual_message

    def test_url_message(self):
        d = self.decoder.decode_sync("https://github.com/project")
        assert "github.com" in d.contextual_message

    def test_text_message(self):
        d = self.decoder.decode_sync("Room 214")
        assert "Room 214" in d.contextual_message
