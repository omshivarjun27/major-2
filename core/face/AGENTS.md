# AGENTS.md — core/face

## 1. Folder Purpose
- Privacy-first face subsystem handling detection, tracking, and recognition
- Provides opt-in consent gating and minimal-data processing
- Integrates with global privacy controls and consent registry

## 2. Contained Components
- FaceDetector: RetinaFace or MTCCN-based detector (opt-in)
- FaceEmbeddingStore: encrypted vector embeddings storage (opt-in)
- FaceTracker: tracking of detected identities (opt-in)
- SocialCueAnalyzer: emotion and head-pose analysis (opt-in)
- All components require explicit user consent before processing any face data

## 3. Dependency Graph
- Depends on shared layer: config, logging, privacy utilities
- Apps layer consumes via face_enabled() feature flag
- No direct infra imports without consent gating
- Imports follow 5-layer architecture constraints

## 4. Task Tracking
- Current status: mostly complete
- There are 3 stubs awaiting implementation or extension
- Privacy consent flow is implemented and tested for gating
- No hard-coded defaults; all features gated behind explicit opt-in

## 5. Design Thinking
- Privacy by design as a non-functional requirement
- Encryption of embeddings at rest and in transit
- Consent must be captured and auditable before any face data usage
- Data minimization and on-device processing where feasible

## 6. Research Notes
- Face model VRAM footprint ~300MB on consumer GPUs
- RetinaFace/MTCCN provide tradeoffs between accuracy and speed
- Consent and audit need to be tracked across sessions
- Potential future: on-device face embeddings with secure enclave

## 7. Risk Assessment
- Privacy sensitivity: MEDIUM
- Key mitigations: encryption, consent gating, access controls
- Potential risks: misconfiguration of opt-in, leakage of embeddings
- Mitigation plan: strict policy checks and zero-privilege data access

## 8. Improvement Suggestions
- Complete remaining 3 stubs with integration tests
- Implement consent audit trail logging for each face operation
- Add automated data retention policies and deletion hooks
- Review encryption keys rotation and access control models

## 9. Folder Change Log
- 2026-02-23: Initial creation

End of AGENTS.md
