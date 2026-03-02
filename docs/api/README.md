# API Documentation

**Version**: 1.0.0 | **Date**: 2026-03-02

The Voice & Vision Assistant exposes a FastAPI REST API on port 8000.

## OpenAPI Spec

The machine-readable OpenAPI 3.0 specification is at:

```
docs/api/openapi.json
```

When the service is running, interactive docs are available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Endpoint Groups

| Group | Prefix | Description |
|-------|--------|-------------|
| Health | `/health` | Service health and dependency status |
| VQA | `/vqa/` | Visual question answering |
| QR / AR | `/qr/` | QR code scanning and AR tag detection |
| Memory | `/memory/` | RAG memory (consent-gated) |
| Face | `/face/` | Face detection and recognition (consent-gated) |
| Audio | `/audio/` | Audio event detection |
| Action | `/action/` | Action / intent recognition |
| OCR | `/ocr/` | Optical character recognition |
| Braille | `/braille/` | Braille reading |
| Spatial | `/spatial/` | Spatial perception / obstacle detection |

Total endpoints: **56**

## Authentication

API keys are passed via the `Authorization: Bearer <token>` header for endpoints
that require authentication. For local/development use, authentication is optional.

## Versioning Strategy

- Current version: **v1**
- Version is encoded in the base URL: `/api/v1/...` (planned for v2+)
- Backward-incompatible changes increment the major version
- Deprecation notices are announced in `CHANGELOG.md` one release in advance

## Error Format

All errors follow this shape:

```json
{
  "detail": "Human-readable error message",
  "code": "ERROR_CODE",
  "status": 400
}
```

## Rate Limits

No rate limiting is applied by default. For production deployments, configure
rate limiting at the reverse proxy (nginx, Caddy) or API gateway layer.
