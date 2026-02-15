# Claude Opus 4.6 Scenario Insights — Ethical & UX Analysis

> Deep analysis of blind-user assistive scenarios through the lens of
> ethics, accessibility UX, privacy, and responsible AI design.

---

## 1. Privacy-First Design Philosophy

### Face Recognition Consent Model
The face engine implements a **strict opt-in consent model**:
- No face embedding is stored without explicit user consent
- Consent is logged with timestamps for audit trails
- Users can revoke consent and trigger complete data deletion (`forget_all`)
- Unknown faces are processed transiently — never persisted
- Optional AES-256 encryption for stored embeddings

**Ethical Insight:** In blind-user contexts, face recognition serves a fundamentally different purpose than surveillance — it enables social connection. However, the same technology could be misused. Our consent-first approach ensures the user retains agency over whose faces are stored.

### Memory Consent Architecture
- Memory engine is disabled by default (`MEMORY_ENABLED=false`)
- Raw media is never saved unless explicitly enabled (`RAW_MEDIA_SAVE=false`)
- Telemetry is off by default (`MEMORY_TELEMETRY=false`)
- All memory deletion is irreversible and auditable
- Cloud sync encrypts data in transit

---

## 2. Audio Scene Analysis — Ethical Considerations

### Sound Source Localization
The audio engine provides spatial awareness of sounds but raises questions:
- **Eavesdropping risk:** The system processes ambient audio. We mitigate by:
  - Only classifying predefined event types (car horn, siren, etc.)
  - Not performing speech-to-text on ambient conversations
  - Not storing raw audio data
  - Processing entirely on-device (no cloud audio streaming)

### Critical Event Priority
Safety-critical events (car horn, siren, alarm) receive highest priority:
- Immediately interrupt any ongoing narration
- Bypass debouncer cooldowns
- Include directional information for evasion

**Ethical Insight:** False positives for critical events can cause unnecessary anxiety. The minimum confidence threshold (0.3) balances safety against alarm fatigue.

---

## 3. Action Recognition — Interpreting Intent

### The Challenge of Intent Assignment
Action recognition from video (approaching, reaching, waving) involves **implicit intent interpretation**. Key concerns:

- **"Approaching" ≠ "threatening"**: The system reports motion patterns without assigning malicious intent
- **"Reaching" ambiguity**: Could be a handshake, pointing, or genuinely threatening. We supplement with facial expression analysis (SocialCueAnalyzer) to provide context
- **Falling detection**: Reporting "someone may have fallen" empowers the user to help without making assumptions

**Design Decision:** All action cues use neutral, factual language. "Person approaching" rather than "someone is coming toward you aggressively."

---

## 4. Multimodal Fusion — Confidence Calibration

### Audio-Vision Fusion Ethics
When audio and visual signals disagree:
- The system reports both signals with their confidence levels
- Does not force resolution — lets the user decide
- Critical events from ANY single modality still trigger alerts

### Scenario: Phantom Car Horn
If audio detects a car horn but vision sees no car:
- Report: "Car horn detected on your left" (audio-only confidence)
- Do NOT say "There's a car on your left"
- Visual absence reduces fusion confidence but doesn't suppress the audio alert

---

## 5. Cloud Sync — Data Sovereignty

### User Data Ownership
- Cloud sync is disabled by default
- When enabled, users choose the backend (Milvus, Weaviate, or stub)
- Sync is bidirectional — deleting locally also queues cloud deletion
- No vendor lock-in: abstract backend interface supports migration

**Ethical Insight:** Blind users may be less aware of data flowing to cloud services. The explicit opt-in and clear verbal confirmation ("Your memories are now syncing to the cloud") ensure informed consent.

---

## 6. Tavus Avatar — Representation Ethics

### Virtual Persona Considerations
- The avatar is a supplementary output channel, not a replacement for audio
- Avatar expressions should match the emotional tone of the narration
- Avoid making the avatar appear to "see" — it narrates what the system detects
- Disabled by default to prevent unnecessary API calls and data sharing

---

## 7. Accessibility UX Patterns

### Temporal Coherence
Blind users rely on consistent, predictable information flow:
- Debouncer prevents repetitive alerts
- Proactive announcer provides regular scene updates (every 2s)
- State changes (new obstacle, person left) are explicitly narrated

### Spatial Language
All directions use **egocentric reference frame** (user-centered):
- "on your left" instead of "to the west"
- "about 3 meters ahead" instead of absolute coordinates
- Clock-face directions for precision: "at your 2 o'clock"

### Alert Hierarchy
1. **Critical:** Immediate safety threats (car horn, siren, falling) — interrupt everything
2. **Important:** Navigation hazards (obstacles < 2m, stairs) — next announcement
3. **Informational:** Scene context (landmarks, signs, people) — during calm periods

---

## 8. Failure Modes & Graceful Degradation

### Camera Occlusion / Dark Scenes
When vision fails, the system:
- Explicitly tells the user: "Lighting is too low for my camera"
- Switches to audio-primary mode
- Increases audio event detection sensitivity

### Single Microphone
With only one mic (no SSL):
- Event detection still works (spectral classification)
- Spatial localization degraded but energy-based distance estimation continues
- System reports events without directional info: "Car horn detected nearby"

### Offline Mode (No Cloud)
- All core features work entirely on-device
- Cloud sync queues updates for when connectivity returns
- No degradation in real-time processing

---

## 9. Long-Term Memory Ethics

### What to Remember
The event detector uses conservative criteria:
- **Always remember:** Safety events, landmarks, navigation context
- **Remember with consent:** Face identities, personal notes
- **Never remember:** Raw images/audio, conversations of others, biometric data of non-consenting individuals

### Right to Be Forgotten
Complete data deletion through:
- `/memory/delete_all` — wipes all memories
- `/face/forget_all` — deletes all face data
- Cloud sync deletion cascades to remote storage
- Backup files are also purged

---

## 10. Claude Opus 4.6 RAG Integration Analysis

### Why Claude Opus 4.6 for RAG
- Superior reasoning for complex multi-step queries ("Where did I leave my keys based on what I saw yesterday?")
- Better contextual understanding of blind-user needs
- Chain-of-thought reasoning improves answer quality for navigational queries
- Fallback to Ollama (qwen3-vl) when cloud is unavailable

### RAG Retrieval Quality
The memory engine uses FAISS with sentence-transformers embeddings:
- Top-k retrieval (default k=5) with similarity threshold
- Temporal weighting: recent memories rank higher
- Category filtering: safety events weighted more than routine observations

---

## Conclusion

The Voice-Vision Assistant treats the blind user as an autonomous agent who deserves:
1. **Accurate, timely information** — not filtered opinions
2. **Full control** over personal data — consent-first, delete-always
3. **Graceful degradation** — system always provides something useful
4. **Neutral language** — factual descriptions, not emotional interpretations
5. **Privacy by default** — every data-collecting feature is opt-in
