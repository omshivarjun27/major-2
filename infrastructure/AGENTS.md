# infrastructure/AGENTS.md
External system adapters: providing unified interfaces for LLMs, speech, and hardware.
**Constraint**: Imports from `shared/` only. Never from `core/`, `application/`, or `apps/`.

## ADAPTER MAP
| Directory | Adapter | Status | Key Class |
|-----------|---------|--------|-----------|
| `llm/ollama/` | Ollama/SiliconFlow Vision | Active | `OllamaHandler` |
| `llm/internet_search.py` | DuckDuckGo search | Active | `InternetSearch` |
| `llm/embeddings/` | Embedding model adapter | Active | `BaseEmbedder` interface |
| `speech/elevenlabs/` | TTS (ElevenLabs) | Active | `TTSManager` |
| `tavus/` | Virtual avatar | Active | `TavusAdapter` (default=off) |
| `llm/siliconflow/` | SiliconFlow LLM | Stub | - |
| `speech/deepgram/` | STT (Deepgram) | Active | Via LiveKit plugins |
| `resilience/` | Circuit breakers, retry, degradation | Active | `DegradationCoordinator` |
| `backup/` | FAISS/SQLite backup (S3, Azure, local) | Active | `BackupScheduler` |
| `storage/` | Metadata storage | Stub | - |
| `monitoring/` | Prometheus metrics + instrumentation | Active | `PrometheusMetrics` |

## ADAPTER CONVENTIONS
- **Lazy Initialization**: Resource-heavy clients (e.g., embeddings) are initialized on first use.
- **Graceful Fallback**: Use `fallback_used` flags in return types.
- **Timeouts**: Every external I/O operation MUST specify a timeout (default: 2s).
- **Latency Tracking**: Every adapter call must log `latency_ms` to the `PipelineMonitor`.
- **Feature Gating**: Adapters should provide no-op modes when their feature flag is disabled.

## OLLAMA HANDLER
- **LRU Cache**: Image processing results are cached (64 entries, SHA-256 keys).
- **Routing**: Automatically routes to the appropriate model based on people detection (QWEN for people, OLLAMA for scenes).

## TTS MANAGER (ElevenLabs)
- **3-Tier Chain**: Cache (Local) → Remote (API) → Fallback (Local stub).
- **Chunking**: `TTSChunker` splits long responses into ≤2s chunks (approx 5 words) for low-latency streaming.

## TAVUS ADAPTER
- **Requirement**: Requires `TAVUS_ENABLED=true` plus API Key, Replica ID, and Persona ID.
- **Handshake**: Coordinates the REST + WebSocket handshake required for live narrations.

## RESILIENCE
- **Circuit Breakers**: Per-service breakers with configurable `CB_{SERVICE}_THRESHOLD` / `CB_{SERVICE}_RESET_S`.
- **Retry Policies**: Exponential backoff per service (`RETRY_{SERVICE}_MAX`, `_BASE_DELAY_S`, `_MAX_DELAY_S`).
- **Degradation Coordinator**: `DegradationCoordinator` (19 methods) manages graceful degradation across all services.
- **Health Registry**: Tracks per-adapter health status; exposes `.health()` and `.stats()` per component.

## BACKUP
- **BackupScheduler**: Orchestrates FAISS index + SQLite metadata backups on configurable intervals.
- **Storage Backends**: Local filesystem, S3 (`boto3`), Azure Blob (`azure.storage.blob`).
- **Restore**: Point-in-time restore from any backend with integrity verification.

## MONITORING
- **PrometheusMetrics**: Central metrics class (41 methods) covering request timing, inference, memory, circuit breakers, WebRTC, FAISS.
- **Instrumentation**: `PipelineStageInstrumentation` wraps each pipeline stage with latency histograms and error counters.
- **Integration**: Scraped by Prometheus in staging/prod Docker Compose stacks.
