# Memory Engine Consent & Privacy Policy

## Overview

The Voice-Vision Assistant memory engine stores scene observations, navigation landmarks, and user notes for long-term recall. All memory features are **disabled by default** and require explicit user opt-in.

## Default State

| Feature | Default | Notes |
|---------|---------|-------|
| `MEMORY_ENABLED` | `false` | Must be explicitly enabled |
| `MEMORY_SAVE_RAW` | `false` | Raw images/audio never saved |
| `MEMORY_TELEMETRY` | `false` | No usage analytics |
| `MEMORY_ENCRYPTION` | `false` | Optional encryption at rest |
| `CLOUD_SYNC` | `false` | No cloud upload |

## What Is Stored

When memory is enabled, the system stores:
- **Text embeddings** — Mathematical vectors representing scene descriptions
- **Metadata** — Timestamps, categories (landmark, obstacle, etc.), confidence scores
- **User notes** — Explicit verbal notes from the user

## What Is NEVER Stored (by default)

- Raw camera images
- Raw audio recordings
- Face images (only mathematical embeddings, with consent)
- Conversations of other people
- Location data (unless user explicitly enables)

## User Controls

### Enable/Disable Memory
- Voice command: "Turn on memory" / "Turn off memory"
- Environment: `MEMORY_ENABLED=true/false`
- Disabling preserves existing data (does not delete)

### View Stored Memories
- `/memory/search` — Search memories by text query
- `/memory/query` — Ask questions about past observations (RAG)

### Delete Memories
- `/memory/delete_all` — Irreversibly delete ALL stored memories
- Deletion includes: index files, metadata, backup files
- Cloud sync cascades deletions to remote storage

## Cloud Sync

### When Enabled
- Memories are synced to a user-chosen vector database (Milvus, Weaviate)
- All data encrypted in transit
- User retains full control: can delete from both local and cloud

### When Disabled (Default)
- All data stays on the user's device
- No network requests for memory operations
- Full functionality maintained offline

## Retention Policy

- Default retention: 30 days (`MEMORY_RETENTION_DAYS=30`)
- Expired memories are automatically purged during maintenance cycles
- Maintenance runs on configurable intervals
- Users can set custom retention from 1 day to unlimited

## Event Detection & Auto-Summarization

The event detection module (`EventDetector`) automatically identifies significant events:
- **Obstacles** — Objects within 3m of the user
- **Landmarks** — Navigational points (intersections, buildings, etc.)
- **Safety events** — Critical audio alerts (sirens, car horns)

Events are summarized and stored as memory entries only when:
1. Memory is enabled
2. The event passes confidence thresholds
3. The event is not a duplicate (cooldown prevents spam)

## Technical Architecture

```
Scene Analysis Data
       ↓
   EventDetector  ← Detects significant events
       ↓
   MemoryIngester ← Creates embeddings
       ↓
   FAISSIndexer   ← Stores locally
       ↓
   CloudSyncAdapter ← (optional) Syncs to cloud
```

## For Developers

```python
from memory_engine.config import get_memory_config

config = get_memory_config()
print(config.enabled)           # False by default
print(config.save_raw_media)    # False
print(config.encryption_enabled)  # False
```

## Compliance

- Aligned with GDPR data minimization principles (Art. 5(1)(c))
- Right to erasure supported (Art. 17)
- Data portability: memories exportable as JSON
- No automated profiling or decision-making based on stored data
