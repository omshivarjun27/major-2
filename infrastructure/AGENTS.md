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
| `storage/` | Metadata storage | Stub | - |
| `monitoring/` | Observability adapters | Stub | - |

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
