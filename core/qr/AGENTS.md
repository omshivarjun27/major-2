Folder Purpose
- QR/AR scanning, decoding, offline TTL cache

Contained Components
- QRScanner: barcode/QR detection pipeline (pyzbar user-space wrapper; may leverage OpenCV for visualization and pre-processing)
- QRDecoder: decodes QR payloads, validates integrity, handles error correction fallbacks
- ARTagHandler: supports AprilTag/ArUco markers for spatial anchoring and AR cues
- CacheManager: TTL-based cache for recently-decoded results and AR tag lookups
- Factory: build_qr_router() for wiring components and routing inputs to appropriate handlers

Dependency Graph
- Depends on shared/ for logging, configuration, and utilities
- Dependency path: shared -> core/qr -> apps/

Task Tracking
- Status: mostly complete
- 4 stubs exist for optional AR tagging variants and alternative decoders
- Owners: qr team, vision-infra

Design Thinking
- Content classification targets: URL payloads, physical location data, product identifiers, and WiFi SSIDs when advertised in scanned content
- Offline TTL cache reduces external API calls and improves resilience when connectivity is intermittent
- Router strategy prioritizes QR-only flows, with AR tag fallback to ensure scene understanding parity

Research Notes
- pyzbar selected over OpenCV QR module for reliability and ease of integration in constrained environments
- AprilTag vs ArUco: AprilTag preferred for robust localization under perspective distortion; ArUco used as fallback

Risk Assessment
- Overall: Low risk, stable feature area with clear fallbacks
- Risks center on decoder false-positives and cache invalidation edge cases; mitigations documented in code

Improvement Suggestions
- Complete remaining 4 stubs: add AR tag variant handlers, add optional decoder backends, improve cache eviction policy, enhance error reporting
- Introduce unit tests for QR decoding edge cases and AR tag parsing
- Consider runtime metrics for latency impact of AR routing and caching

Folder Change Log
- 2026-02-23: Initial creation
