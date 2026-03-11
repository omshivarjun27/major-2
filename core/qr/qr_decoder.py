"""
QR Decoder – classifies raw QR data and builds contextual spoken messages.

Content types:
  URL, Location, Transport, Product, Contact (vCard/MeCard), WiFi,
  Plain Text, and custom project-specific tags.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger("qr-decoder")

# ---------------------------------------------------------------------------
# Content classification
# ---------------------------------------------------------------------------


class QRContentType(str, Enum):
    URL = "url"
    LOCATION = "location"
    TRANSPORT = "transport"
    PRODUCT = "product"
    CONTACT = "contact"
    WIFI = "wifi"
    TEXT = "text"
    CUSTOM_TAG = "custom_tag"


@dataclass
class DecodedQR:
    """Fully decoded and contextualised QR result."""

    raw_data: str
    content_type: QRContentType
    metadata: Dict[str, Any] = field(default_factory=dict)
    contextual_message: str = ""
    navigation_available: bool = False
    lat: Optional[float] = None
    lon: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_data": self.raw_data,
            "content_type": self.content_type.value,
            "metadata": self.metadata,
            "contextual_message": self.contextual_message,
            "navigation_available": self.navigation_available,
            "lat": self.lat,
            "lon": self.lon,
        }


# ---------------------------------------------------------------------------
# Decoder
# ---------------------------------------------------------------------------

# Regex helpers
_GEO_RE = re.compile(r"^geo:([-\d.]+),([-\d.]+)", re.IGNORECASE)
_WIFI_RE = re.compile(
    r"^WIFI:(?:T:(?P<type>[^;]*);)?S:(?P<ssid>[^;]*);(?:P:(?P<pass>[^;]*);)?",
    re.IGNORECASE,
)
_VCARD_RE = re.compile(r"^BEGIN:VCARD", re.IGNORECASE)
_MECARD_RE = re.compile(r"^MECARD:", re.IGNORECASE)
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


class QRDecoder:
    """
    Classify raw QR strings and produce human-friendly spoken context.

    May optionally fetch additional data from the network via a user-
    supplied async callback (`fetch_fn`).
    """

    # Known custom tag prefixes  → handler key
    CUSTOM_PREFIXES: Dict[str, str] = {
        "stop_id=": "transport",
        "product_id=": "product",
        "loc_id=": "location",
    }

    def __init__(self, fetch_fn=None):
        """
        Args:
            fetch_fn: optional async callable ``fetch_fn(url_or_tag: str) -> str``
                      used for online enrichment.  Receives the raw_data string.
        """
        self._fetch = fetch_fn

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    async def decode(self, raw: str) -> DecodedQR:
        """Classify, enrich (if online), and build contextual message."""
        raw = raw.strip()

        decoded = self._classify(raw)

        # Attempt online enrichment
        if self._fetch:
            try:
                extra = await self._fetch(raw)
                if extra:
                    decoded.metadata["online_data"] = extra
                    decoded.contextual_message = self._enrich_message(decoded, extra)
            except Exception as exc:
                logger.debug(f"Online enrichment skipped: {exc}")

        # Ensure there is always a contextual message
        if not decoded.contextual_message:
            decoded.contextual_message = self._build_offline_message(decoded)

        return decoded

    def decode_sync(self, raw: str) -> DecodedQR:
        """Synchronous decode without online enrichment."""
        raw = raw.strip()
        decoded = self._classify(raw)
        decoded.contextual_message = self._build_offline_message(decoded)
        return decoded

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    def _classify(self, raw: str) -> DecodedQR:
        # geo: URI
        m = _GEO_RE.match(raw)
        if m:
            lat, lon = float(m.group(1)), float(m.group(2))
            return DecodedQR(
                raw_data=raw,
                content_type=QRContentType.LOCATION,
                lat=lat,
                lon=lon,
                navigation_available=True,
                metadata={"lat": lat, "lon": lon},
            )

        # WiFi
        m = _WIFI_RE.match(raw)
        if m:
            return DecodedQR(
                raw_data=raw,
                content_type=QRContentType.WIFI,
                metadata={
                    "ssid": m.group("ssid") or "",
                    "password": m.group("pass") or "",
                    "security": m.group("type") or "WPA",
                },
            )

        # vCard / MeCard
        if _VCARD_RE.match(raw) or _MECARD_RE.match(raw):
            return DecodedQR(
                raw_data=raw,
                content_type=QRContentType.CONTACT,
                metadata=self._parse_contact(raw),
            )

        # Custom project tags  (stop_id=145, product_id=X, …)
        for prefix, tag_type in self.CUSTOM_PREFIXES.items():
            if raw.lower().startswith(prefix):
                return self._classify_custom(raw, tag_type)

        # JSON payload (custom structured data)
        if raw.startswith("{"):
            try:
                payload = json.loads(raw)
                return self._classify_json(raw, payload)
            except json.JSONDecodeError:
                pass

        # URL
        if _URL_RE.match(raw):
            return self._classify_url(raw)

        # Fallback: plain text
        return DecodedQR(raw_data=raw, content_type=QRContentType.TEXT)

    # ------------------------------------------------------------------

    def _classify_url(self, url: str) -> DecodedQR:
        parsed = urlparse(url)
        meta: Dict[str, Any] = {"host": parsed.hostname or "", "path": parsed.path}
        content_type = QRContentType.URL

        # Heuristic: maps links are navigable
        host_lower = (parsed.hostname or "").lower()
        nav = False
        if "maps" in host_lower or "map" in host_lower:
            content_type = QRContentType.LOCATION
            nav = True

        # Query params
        qs = parse_qs(parsed.query)
        if qs:
            meta["query_params"] = {k: v[0] if len(v) == 1 else v for k, v in qs.items()}

        return DecodedQR(
            raw_data=url,
            content_type=content_type,
            metadata=meta,
            navigation_available=nav,
        )

    def _classify_custom(self, raw: str, tag_type: str) -> DecodedQR:
        parts = dict(item.split("=", 1) for item in raw.split("&") if "=" in item)
        # Also handle single key=value
        if not parts and "=" in raw:
            k, v = raw.split("=", 1)
            parts = {k: v}

        ct = {
            "transport": QRContentType.TRANSPORT,
            "product": QRContentType.PRODUCT,
            "location": QRContentType.LOCATION,
        }.get(tag_type, QRContentType.CUSTOM_TAG)

        nav = ct in (QRContentType.LOCATION, QRContentType.TRANSPORT)
        return DecodedQR(
            raw_data=raw,
            content_type=ct,
            metadata=parts,
            navigation_available=nav,
        )

    def _classify_json(self, raw: str, payload: dict) -> DecodedQR:
        # Detect transport / location / product via keys
        if "stop_id" in payload or "route" in payload:
            ct = QRContentType.TRANSPORT
        elif "lat" in payload and "lon" in payload:
            ct = QRContentType.LOCATION
        elif "product_id" in payload or "sku" in payload:
            ct = QRContentType.PRODUCT
        else:
            ct = QRContentType.CUSTOM_TAG
        nav = ct in (QRContentType.LOCATION, QRContentType.TRANSPORT)
        lat = payload.get("lat")
        lon = payload.get("lon")
        return DecodedQR(
            raw_data=raw,
            content_type=ct,
            metadata=payload,
            navigation_available=nav,
            lat=float(lat) if lat else None,
            lon=float(lon) if lon else None,
        )

    # ------------------------------------------------------------------
    # Contact parsers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_contact(raw: str) -> Dict[str, str]:
        info: Dict[str, str] = {}
        if raw.upper().startswith("BEGIN:VCARD"):
            for line in raw.splitlines():
                if line.startswith("FN:"):
                    info["name"] = line[3:]
                elif line.startswith("TEL"):
                    info["phone"] = line.split(":")[-1]
                elif line.startswith("EMAIL"):
                    info["email"] = line.split(":")[-1]
        elif raw.upper().startswith("MECARD:"):
            body = raw[7:]
            for part in body.split(";"):
                if part.startswith("N:"):
                    info["name"] = part[2:]
                elif part.startswith("TEL:"):
                    info["phone"] = part[4:]
                elif part.startswith("EMAIL:"):
                    info["email"] = part[6:]
        return info

    # ------------------------------------------------------------------
    # Message builders
    # ------------------------------------------------------------------

    def _build_offline_message(self, d: DecodedQR) -> str:
        """Best-effort spoken sentence from local data only."""
        ct = d.content_type

        if ct == QRContentType.TRANSPORT:
            stop = d.metadata.get("stop_id", "unknown")
            route = d.metadata.get("route", "")
            dest = d.metadata.get("destination", "")
            msg = f"Bus stop {stop}."
            if route:
                msg = f"Bus stop {stop} — Route {route}"
                if dest:
                    msg += f" to {dest}."
                else:
                    msg += "."
            return msg

        if ct == QRContentType.LOCATION:
            name = d.metadata.get("name", "")
            if name:
                return f"Location: {name}."
            if d.lat is not None:
                return f"Location at coordinates {d.lat:.4f}, {d.lon:.4f}."
            return "Location QR detected."

        if ct == QRContentType.PRODUCT:
            name = d.metadata.get("name", d.metadata.get("product_id", "unknown"))
            price = d.metadata.get("price", "")
            msg = f"Product: {name}."
            if price:
                msg += f" Price: {price}."
            return msg

        if ct == QRContentType.CONTACT:
            name = d.metadata.get("name", "unknown")
            return f"Contact: {name}."

        if ct == QRContentType.WIFI:
            ssid = d.metadata.get("ssid", "unknown")
            return f"WiFi network: {ssid}."

        if ct == QRContentType.URL:
            host = d.metadata.get("host", d.raw_data[:40])
            return f"Link to {host}."

        # TEXT / CUSTOM_TAG
        short = d.raw_data[:80]
        return f"QR code says: {short}"

    def _enrich_message(self, d: DecodedQR, extra: str) -> str:
        """Merge online data into the spoken message."""
        # If the enrichment is short enough, use directly
        if len(extra) < 200:
            return extra
        return self._build_offline_message(d) + f" More info: {extra[:120]}"
