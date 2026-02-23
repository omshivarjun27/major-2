---
id: ISSUE-003
title: No Input Sanitization on QR Code Payloads
severity: critical
source_artifact: architecture_risks.md
architecture_layer: core
---

## Description
The QR scanner passes raw decoded data directly without sanitization. While the system prompt specifies "no automatic click-through" for QR URLs, the scanner and decoder do not filter XSS/injection content before it reaches TTS output or downstream handlers.

## Root Cause
`QRScanner.scan()` returns raw decoded bytes as UTF-8 strings. `QRDecoder.decode()` classifies content by type but does not sanitize malicious payloads (e.g., javascript: URIs, excessively long strings, control characters).

## Impact
Malicious QR codes could inject harmful content into TTS output (e.g., phishing URLs spoken verbatim) or trigger unintended actions in downstream handlers. For a blind user, a convincing phishing URL spoken via TTS is especially dangerous.

## Reproducibility
always

## Remediation Plan
1. Add a `sanitize_payload()` function in `core/qr/qr_decoder.py`.
2. Validate URL schemes (allow only `http`, `https`, `mailto`, `tel`).
3. Strip executable protocols (`javascript:`, `data:`, `vbscript:`).
4. Limit payload length to prevent TTS overrun.
5. Escape or reject control characters and non-printable bytes.
6. Add unit tests with known malicious QR payloads.

## Implementation Suggestion
```python
ALLOWED_SCHEMES = {"http", "https", "mailto", "tel", "geo"}
MAX_PAYLOAD_LENGTH = 2048

def sanitize_payload(raw: str) -> str:
    if len(raw) > MAX_PAYLOAD_LENGTH:
        raw = raw[:MAX_PAYLOAD_LENGTH]
    parsed = urllib.parse.urlparse(raw)
    if parsed.scheme and parsed.scheme.lower() not in ALLOWED_SCHEMES:
        return f"[Blocked: unsupported URL scheme '{parsed.scheme}']"
    return raw.replace('\x00', '').strip()
```

## GPU Impact
N/A

## Cloud Impact
N/A

## Acceptance Criteria
- [ ] `sanitize_payload()` implemented and called before TTS output
- [ ] Malicious URL schemes (`javascript:`, `data:`) are blocked
- [ ] Payload length is capped
- [ ] Unit tests cover at least 5 malicious QR payload vectors
