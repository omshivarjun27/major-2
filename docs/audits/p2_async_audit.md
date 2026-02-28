# P2 Async Blocking Call Audit Report

**Date**: 2026-02-27
**Task**: T-046
**Auditor**: Automated scan + manual review
**Scope**: core/, application/, infrastructure/ (excluding tests/)

## Executive Summary

Scanned 45 files with async functions across core/, application/, and infrastructure/.
Found 10 blocking calls across 3 files. All critical findings have been resolved.
Zero blocking calls remain in hot-path code.

## Findings

### Critical (Hot-Path)

| # | File | Line | Function | Blocking Call | Resolution |
|---|------|------|----------|---------------|------------|
| 1 | infrastructure/llm/internet_search.py | 72 | search() | self._search.invoke(query) | Wrapped with asyncio.to_thread() |
| 2 | infrastructure/llm/internet_search.py | 80 | search() | self._search_detailed.invoke(query) | Wrapped with asyncio.to_thread() |
| 3 | infrastructure/llm/internet_search.py | 89 | search() | self._news_search.invoke(query) | Wrapped with asyncio.to_thread() |

### Medium (Maintenance/Background)

| # | File | Line | Function | Blocking Call | Resolution |
|---|------|------|----------|---------------|------------|
| 4 | core/memory/maintenance.py | 97 | run() | self._indexer.save() | Wrapped with asyncio.to_thread() |
| 5 | core/memory/maintenance.py | 170 | compact_index() | self._indexer.compact() | Wrapped with asyncio.to_thread() |
| 6 | core/memory/maintenance.py | 158 | enforce_retention() | self._indexer.delete() loop | Moved to sync helper + asyncio.to_thread() |
| 7 | core/memory/maintenance.py | 194 | backup() | shutil.copy2() | Wrapped in sync helper + asyncio.to_thread() |
| 8 | core/memory/maintenance.py | 203 | backup() | open() + json.dump() | Wrapped in sync helper + asyncio.to_thread() |
| 9 | core/memory/ingest.py | 479 | _store_raw_media() | open() + write() | Wrapped in sync helper + asyncio.to_thread() |
| 10 | core/memory/ingest.py | 488 | _store_raw_media() | open() + write() | Wrapped in sync helper + asyncio.to_thread() |

### Low (Setup/Init — Deferred)

| # | File | Line | Function | Blocking Call | Justification |
|---|------|------|----------|---------------|---------------|
| 11 | core/memory/indexer.py | 399 | _compute_checksum() | open() + read | Only during save; protected by threading.Lock |
| 12 | core/memory/indexer.py | 453 | _rotate_backups() | shutil.copy2/move | Only during save; protected by threading.Lock |
| 13 | core/memory/indexer.py | 510 | save() | open() + json.dump | Sync method with threading.Lock; safe from async via to_thread |

### Already Clean (Verified)

The following files were audited and confirmed to already use proper async patterns:

- **core/vision/spatial.py** — run_in_executor() for YOLO/MiDaS inference
- **core/vision/visual.py** — LiveKit native async
- **core/ocr/engine.py** — run_in_executor() for OCR backends
- **core/memory/retriever.py** — asyncio.to_thread() for FAISS search
- **core/memory/embeddings.py** — ollama.AsyncClient for embeddings
- **core/memory/rag_reasoner.py** — async LLM calls throughout
- **core/speech/tts_handler.py** — httpx.AsyncClient for ElevenLabs
- **core/speech/speech_handler.py** — httpx.AsyncClient for Deepgram
- **core/vqa/perception.py** — run_in_executor() for YOLO inference
- **core/vqa/orchestrator.py** — asyncio.wait_for() for timeouts
- **infrastructure/storage/adapter.py** — asyncio.to_thread() for file ops
- **infrastructure/tavus/adapter.py** — aiohttp for WebSocket/REST
- **infrastructure/llm/ollama/handler.py** — httpx.AsyncClient for Ollama API
- **core/qr/qr_scanner.py** — run_in_executor() for pyzbar/OpenCV scan
- **core/memory/cloud_sync.py** — native async throughout

## Confirmation

- [x] All core/ files with async def scanned
- [x] All application/ files with async def scanned
- [x] All infrastructure/ files with async def scanned
- [x] Zero critical blocking calls remain in hot-path code
- [x] `requests` library not imported in any hot-path module
- [x] `time.sleep` not used in any async context
- [x] All medium-severity items resolved
