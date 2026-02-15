# Face Recognition Consent Policy

## Overview

The Voice-Vision Assistant face recognition system is designed with a **privacy-first, consent-required** architecture. No face data is stored, processed for identification, or shared without explicit user consent.

## Consent Requirements

### For Face Storage (Embedding Registration)
- **Explicit opt-in required** before any face embedding is stored
- User must verbally confirm: "Yes, store [name]'s face"
- Consent is recorded with timestamp and stored in the consent log
- Registration without consent returns `None` — data is discarded

### For Face Detection (Transient Processing)
- Face **detection** (bounding box, count) is always permitted — no biometric data is stored
- Detection data is transient: discarded after the frame is processed
- No images are saved to disk during detection

### For Face Identification (Matching)
- Only matches against faces with active consent
- Unknown faces are reported as "someone" — no attempt to identify
- Matching is performed entirely on-device

## User Rights

### Right to Know
- `/face/consent/log` — View all consent records with timestamps
- Face health endpoint shows how many identities are stored

### Right to Delete
- `/face/forget_all` — Irreversibly deletes ALL stored face embeddings
- Individual deletion: Remove specific identity by ID
- Deletion cascades to backup files and encrypted storage

### Right to Withdraw
- Consent can be revoked at any time
- Revocation triggers automatic deletion of associated embedding
- System immediately stops identifying that person

## Technical Safeguards

### On-Device Processing
- All face detection, embedding generation, and matching happen on the user's device
- No face data is sent to cloud services (unless cloud sync is explicitly enabled)

### Encryption
- Optional AES-256 encryption for stored embeddings (`FACE_ENCRYPTION_ENABLED=true`)
- Encryption key sourced from environment variable (`FACE_ENCRYPTION_KEY`)
- Encrypted files are unreadable without the key

### Data Minimization
- Only mathematical embeddings (128-dimensional vectors) are stored — not images
- Embeddings cannot be reverse-engineered into face images
- Metadata stored: name, consent status, creation date — nothing else

## Configuration

| Setting | Default | Description |
|---------|---------|------------|
| `FACE_ENGINE_ENABLED` | `true` | Enable face detection |
| `FACE_REGISTRATION_ENABLED` | `false` | Allow new face registrations |
| `FACE_CONSENT_REQUIRED` | `true` | Require consent before storing |
| `FACE_ENCRYPTION_ENABLED` | `false` | Encrypt stored embeddings |

## For Developers

The `FaceEmbeddingStore` class enforces consent internally:
```python
store = FaceEmbeddingStore(EmbeddingConfig(consent_required=True))

# This will return None — no consent recorded
result = store.register("alice", embedding)  # → None

# Grant consent first
store.record_consent("alice", True)
result = store.register("alice", embedding)  # → FaceIdentity(name="alice", ...)
```

## Compliance Notes

- This system is designed to align with GDPR Article 9 (biometric data processing)
- Face data is classified as "special category" personal data
- Processing basis: explicit consent (GDPR Art. 9(2)(a))
- Data retention follows `MEMORY_RETENTION_DAYS` setting
