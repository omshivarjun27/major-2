# Test Report: Replace Embedding Model & Remove Calendar/Email/Contact/Places

**Branch:** `feat/replace-embedding-qwen3-4b-remove-google-and-other-models`  
**Date:** 2025-06-14  
**Status:** ✅ PASS

---

## Summary

| Metric | Value |
|--------|-------|
| Tests passed | 1711 |
| Tests failed | 15 (pre-existing) |
| Tests skipped | 2 |
| Tests errored | 20 (pre-existing) |
| Import contracts | 4/4 passed |
| Files analyzed (lint-imports) | 119 |
| Dependencies verified | 175 |
| Total runtime | ~111s |

---

## Changes Made

### 1. Embedding Model Replacement: `all-MiniLM-L6-v2` → `qwen3-embedding:4b`

| File | Change |
|------|--------|
| `core/memory/config.py` | Default `text_embedding_model` updated (2 locations) |
| `core/memory/embeddings.py` | Rewrote `TextEmbedder` to use Ollama embedding API instead of sentence-transformers |
| `core/vqa/memory.py` | Default `embedding_model` updated |
| `.env` | `EMBEDDING_MODEL=qwen3-embedding:4b` |
| `.env.example` | `EMBEDDING_MODEL=qwen3-embedding:4b` |
| `.github/workflows/ci.yml` | Secrets scan pattern updated |
| `core/memory/README.md` | Config table updated |
| `docs/PRODUCTION_AUDIT.md` | Code sample updated |
| `README.md` | RAG pipeline description updated |

**Architecture change:** `TextEmbedder` now uses `ollama.embed()` API instead of `sentence_transformers.SentenceTransformer.encode()`. Dimension is auto-detected on first use.

### 2. Removed Features

#### Files Deleted
- `shared/utils/calendar.py` — CalendarTool (local JSON calendar)
- `shared/utils/communication.py` — CommunicationTool (IMAP/SMTP email + contacts)
- `infrastructure/llm/google_places.py` — Backward-compat alias for PlacesSearch
- `infrastructure/llm/places_search.py` — PlacesSearch (OpenStreetMap Nominatim)
- `calendar_events.json` — Calendar data file
- `contacts.json` — Contacts data file

#### Code Removed from `apps/realtime/agent.py`
- 3 imports: `PlacesSearch`, `CalendarTool`, `CommunicationTool`
- 3 `UserData` fields: `places_search`, `calendar_tool`, `communication_tool`
- 3 `@function_tool` methods: `search_places`, `manage_calendar`, `manage_communication`
- 3 initialization lines in `entrypoint()`

#### Dependencies Removed
| Package | Reason |
|---------|--------|
| `geopy>=2.4.0` | Only used by PlacesSearch (deleted) |
| `icalendar>=5.0.0` | Listed but never actually imported |
| `imapclient>=3.0.0` | Listed but never actually imported |

Removed from both `pyproject.toml` and `requirements.txt`.

### 3. Already Absent Models (No Action Needed)

Verified that the following were **NOT present** anywhere in the codebase:
- Llama-4-Scout-17B
- GPT-4o
- groq

### 4. Documentation Updated

| File | Changes |
|------|---------|
| `README.md` | Mermaid diagram, features list, prerequisites, env config, directory tree, troubleshooting — all calendar/email/contact/places references removed |
| `docs/FEATURES.md` | Sections 7-8 rewritten (Calendar/Communication → Internet Search) |
| `docs/Voice_Vision_Assistant_HLD.md` | ~30 references removed across architecture diagrams, tables, function listings, config examples, file trees |
| `docs/create_word_doc.py` | ~12 references removed from diagram strings and data tables |
| `docs/bug_tracker.md` | google_places entry updated |
| `apps/realtime/entrypoint.py` | Docstring updated |

### 5. Test Updates

| File | Change |
|------|--------|
| `tests/unit/test_embeddings.py` | `test_dimension_property_triggers_load` updated to mock Ollama client |
| `tests/performance/test_offline_behavior.py` | Removed `test_places_search_without_network` |
| `tests/test_generated_scenarios.py` | Threshold lowered from 1000 to 990 |
| `tests/generated_scenarios.json` | Removed 11 scenarios (6 Google-Places + 5 find-nearby); 995 remain |
| `scripts/generate_scenarios.py` | Removed `Google-Places` service and `find-nearby` action |

---

## Test Results

### Directly Affected Tests: ✅ 18/18 passed

```
tests/unit/test_embeddings.py .......... (10 passed)
tests/performance/test_offline_behavior.py ...... (6 passed)
tests/test_generated_scenarios.py::test_minimum_scenario_count PASSED
tests/test_generated_scenarios.py::test_stt_scenario (995x PASSED)
```

### Full Suite: 1711 passed, 15 failed (pre-existing), 20 errors (pre-existing)

Pre-existing failures (unrelated to this PR):
- `test_debug_access_control.py` (7) — debug auth middleware issues
- `test_graceful_degradation.py` (4) — spatial/face/audio/QR graceful shutdown
- `test_ci_smoke.py` (1) — OCR engine import path
- `test_ocr_pipeline.py` (1) — CLAHE without cv2
- `test_smoke_api.py` (1) — health endpoint import

### Import Contracts: ✅ 4/4 kept

```
shared must not import any project packages          KEPT
core must not import application, infrastructure, or apps  KEPT
infrastructure must not import core, application, or apps  KEPT
application must not import infrastructure or apps       KEPT
```

---

## Smoke Checks

| Check | Result |
|-------|--------|
| `all-MiniLM` references in code (*.py) | 0 found ✅ |
| `CalendarTool` references in code | 0 found ✅ |
| `CommunicationTool` references in code | 0 found ✅ |
| `PlacesSearch` references in code | 0 found ✅ |
| `google_places.py` exists | No ✅ |
| `places_search.py` exists | No ✅ |
| `calendar.py` (shared/utils) exists | No ✅ |
| `communication.py` (shared/utils) exists | No ✅ |
| Import-linter contracts | 4/4 ✅ |
| `qwen3-embedding:4b` in config defaults | Yes ✅ |
