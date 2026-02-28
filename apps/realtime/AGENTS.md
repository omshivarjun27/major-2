# apps/realtime/AGENTS.md

## 1. Folder Purpose

`apps/realtime/` is the LiveKit WebRTC agent entrypoint (port 8081). It was decomposed from a 1,900-LOC monolith (`agent.py`) into 8 focused modules during T-038 through T-042.

The architecture follows the coordinator pattern: `agent.py` is a thin shell that delegates all business logic to specialized controllers and managers. No reasoning, no frame processing, no search logic lives in the coordinator.

## 2. Module Map

| Module | LOC | Responsibility |
|--------|-----|----------------|
| `agent.py` | 288 | Coordinator. Thin `@function_tool` wrappers, session lifecycle wiring. Delegates ALL logic. |
| `session_manager.py` | 739 | Session lifecycle: room connection with retry, component init (VQA, QR, OCR, voice router, live infra), avatar setup, continuous processing, diagnostics. |
| `vision_controller.py` | 499 | Frame capture, Ollama streaming analysis, spatial perception (detect obstacles, analyze scene), VQA pipeline dispatch, OCR/text reading. |
| `voice_controller.py` | 281 | Internet search dispatch, QR/AR scanning orchestration, LLM stream processing. |
| `tool_router.py` | 446 | `QueryType` classification (8 types), `ToolRegistry`, dispatch/auto_dispatch, input validation. |
| `user_data.py` | ~130 | `UserData` dataclass: per-session state bag (visual_processor, internet_search, ollama_handler, spatial, VQA, QR, voice, OCR, session logger, live infra, proactive announce). |
| `prompts.py` | ~180 | `VISION_SYSTEM_PROMPT`, `MICRO_NAV_SYSTEM_PROMPT` constants. |
| `entrypoint.py` | ~40 | LiveKit worker launcher, signal handling. |

## 3. Data Flow Diagrams

### 3.1 Request Flow (Coordinator Pattern)

```
LiveKit Room
    |
    v
agent.py (coordinator)
    |
    +--> tool_router.classify_query(query)
    |        |
    |        v
    |    QueryType enum
    |    (VISUAL | SPATIAL | SEARCH | QR_AR | OCR | VQA | NAVIGATION | GENERAL)
    |
    +--> dispatch to appropriate controller:
         VISUAL/SPATIAL/OCR/VQA/NAVIGATION --> vision_controller
         SEARCH/QR_AR                      --> voice_controller
```

### 3.2 Vision Flow

```
agent.analyze_vision(query)
    |
    v
vision_controller.analyze_vision(userdata, query, llm_model, ...)
    |
    +--> capture_fresh_frame(userdata)
    |        |
    |        v
    |    check_frame_freshness(userdata, capture_ts)
    |
    +--> run_ollama_analysis(userdata, analysis_llm, visual_ctx)
    |        |
    |        v
    |    Ollama streaming response
    |
    v
response string --> TTS
```

### 3.3 Spatial Flow

```
agent.detect_obstacles(detail_level)
    |
    v
vision_controller.detect_obstacles(userdata, detail_level)
    |
    +--> capture_fresh_frame(userdata)
    +--> core/vision/ spatial pipeline
    |        |
    |        +--> ObjectDetector
    |        +--> EdgeAwareSegmenter
    |        +--> DepthEstimator
    |        +--> SpatialFuser
    |
    v
navigation cue string --> TTS
```

### 3.4 Voice/QR Flow

```
agent.scan_qr_code(query)
    |
    v
voice_controller.scan_qr_code(userdata, query)
    |
    +--> vision_controller.capture_fresh_frame(userdata)
    +--> core/qr/ scanner + decoder + cache
    |
    v
contextual message --> TTS
```

### 3.5 Continuous Processing

```
session_manager.start_continuous_processing(userdata, ctx, agent_session)
    |
    +--> frame capture loop
    |        |
    |        v
    |    detection pipeline
    |        |
    |        v
    |    proactive announcer (priority filtering)
    |        |
    |        v
    |    TTS output (speak_with_priority)
```

## 4. Interface Contracts

### agent.py

```python
class AllyVisionAgent:
    def __init__(self) -> None
    async def on_enter(self) -> None                                    # session start, delegates to session_manager
    async def on_message(self, message, ...) -> None                    # fresh-context rule, profiling, delegates to tool_router

# @function_tool wrappers (thin delegation only):
async def search_internet(context, query: str) -> str
async def analyze_vision(context, query: str) -> str
async def detect_obstacles(context, detail_level: str) -> str
async def analyze_spatial_scene(context, query: str) -> str
async def ask_visual_question(context, question: str) -> str
async def get_navigation_cue(context) -> str
async def scan_qr_code(context, query: str) -> str
async def read_text(context, query: str) -> str

# Top-level entrypoint:
async def entrypoint(ctx: JobContext) -> None
```

### session_manager.py

```python
async def connect_with_retry(ctx, max_retries=3) -> None
async def initialize_components(userdata, ctx) -> None          # bootstraps all subsystems
def create_agent_session(userdata, agent) -> AgentSession
async def setup_avatar(agent_session, ctx) -> Optional[avatar]
async def start_agent_session(agent_session, agent, ctx, avatar) -> None
async def start_continuous_processing(userdata, ctx, agent_session) -> None
async def run_diagnostics(userdata, ctx) -> None
def wire_watchdog_tts(userdata, agent_session) -> None
```

### vision_controller.py

```python
async def capture_fresh_frame(userdata) -> Optional[image]
def check_frame_freshness(userdata, capture_ts) -> Optional[str]
def heartbeat(userdata, component="camera") -> None
async def run_ollama_analysis(userdata, analysis_llm, visual_ctx) -> str
async def analyze_vision(userdata, query, llm_model, llm_base_url, llm_api_key) -> str
async def detect_obstacles(userdata, detail_level) -> str
async def analyze_spatial_scene(userdata, query) -> str
async def ask_visual_question(userdata, question) -> str
async def get_navigation_cue(userdata) -> str
async def read_text(userdata, query) -> str
```

### voice_controller.py

```python
async def search_internet(userdata, query: str) -> str
async def scan_qr_code(userdata, query: str) -> str
async def process_stream(chat_ctx, tools, userdata, ...) -> AsyncGenerator
```

### tool_router.py

```python
# Enum
class QueryType(Enum):
    VISUAL, SPATIAL, SEARCH, QR_AR, OCR, VQA, NAVIGATION, GENERAL

# Registry
class ToolRegistry:
    def register(tool_name, query_type, handler) -> None
    def get(tool_name) -> ToolEntry
    def get_for_type(query_type) -> list[ToolEntry]
    @property
    def tool_names -> list[str]

# Result
@dataclass
class DispatchResult:
    tool_name: str
    query_type: QueryType
    response: str
    error: Optional[str]

# Functions
def classify_query(query: str) -> QueryType
def get_registry() -> ToolRegistry
async def dispatch(tool_name, userdata, **kwargs) -> DispatchResult
async def auto_dispatch(query, userdata, **kwargs) -> DispatchResult
def validate_detail_level(detail_level: str) -> str
def validate_query(query: str, max_length: int) -> str
```

## 5. Import Dependency Graph

```
agent.py --> prompts, session_manager (via entrypoint), tool_router, user_data, shared.config
session_manager.py --> shared.config (8 imports), livekit plugins
vision_controller.py --> prompts (lazy: application.frame_processing)
voice_controller.py --> vision_controller (for frame capture)
tool_router.py --> (stdlib only, no project imports)
user_data.py --> (stdlib only)
prompts.py --> (stdlib only)
entrypoint.py --> agent (for worker registration)
```

Layer enforcement: 6/6 import-linter contracts KEPT, including DAG enforcement for these modules. Run `lint-imports` to verify.

## 6. Key Conventions

- **Fresh-Context Rule**: `userdata.clear_perception_cache()` fires on every new query. Vision is never stale.
- **UserData is the session state bag**: passed to all controller functions. No globals, no module-level state.
- **Heavy imports guarded**: all torch, FAISS, and similar imports wrapped in `try/except` with `_*_AVAILABLE` flags.
- **Failsafe returns**: every public function has `try/except` and returns a user-friendly error string on failure. The pipeline never crashes.
- **Coordinator pattern**: `agent.py` contains ZERO business logic. Only thin `@function_tool` wrappers that delegate immediately.
- **No cross-controller imports**: controllers don't import each other, except `voice_controller` importing `vision_controller` for frame capture.

## 7. Change Log

- 2026-02-23: Created AGENTS.md for apps/realtime; identified high-risk god-file status.
- 2026-02-27: T-038 through T-042: Decomposed monolithic agent.py (1,900 LOC) into 8 modules.
- 2026-02-27: T-043: Added 15 unit + 37 integration tests for decomposed modules.
- 2026-02-27: T-048: Import boundary enforcement, 6 contracts KEPT, DAG enforced.
- 2026-02-27: T-049: Rewrote AGENTS.md to reflect decomposed architecture.
