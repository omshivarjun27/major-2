# Agent Decomposition: Migration Guide

How and why `apps/realtime/agent.py` was split from a 1,900-LOC monolith into 8 focused modules.

## Why We Split

`agent.py` was the single highest-risk file in the codebase:

| Problem | Impact |
|---------|--------|
| 1,900 LOC in one file | Unreviable diffs, merge conflicts, cognitive overload |
| Single-responsibility violation | WebRTC session lifecycle, frame capture, spatial perception, QR scanning, search, TTS, avatar — all in one file |
| Untestable | No seam between concerns; testing any behavior required mocking the entire agent |
| Blast radius | Every change touched the same file, risking regressions in unrelated features |
| Onboarding cost | New contributors could not determine where to make changes |

The decomposition was tracked as tasks T-038 through T-042 in Phase P2 (Architecture Remediation).

## How The Split Was Performed

Each task extracted one concern from `agent.py` into a dedicated module:

| Task | Module Created | What Moved |
|------|---------------|------------|
| T-038 | `session_manager.py` | Room connection, component init, avatar, continuous processing, diagnostics |
| T-039 | `vision_controller.py` | Frame capture, Ollama analysis, spatial perception, VQA, OCR |
| T-040 | `voice_controller.py` | Internet search, QR/AR scanning, LLM stream processing |
| T-041 | `tool_router.py` | Query classification, tool registry, dispatch, validation |
| T-042 | `agent.py` (slimmed) | Coordinator reduced to 288 LOC: only `@function_tool` wrappers and wiring |

Supporting modules (`user_data.py`, `prompts.py`) were extracted earlier as prerequisites.

## Where Logic Lives Now

| Old agent.py Responsibility | New Module | Key Function |
|---------------------------|------------|-------------|
| Room connection with retry | `session_manager.py` | `connect_with_retry()` |
| Component initialization (VQA, QR, OCR, voice) | `session_manager.py` | `initialize_components()` |
| Tavus avatar setup | `session_manager.py` | `setup_avatar()` |
| Continuous frame processing | `session_manager.py` | `start_continuous_processing()` |
| Proactive obstacle announcements | `session_manager.py` | `_proactive_announcer()` |
| Camera frame capture | `vision_controller.py` | `capture_fresh_frame()` |
| Ollama streaming analysis | `vision_controller.py` | `run_ollama_analysis()` |
| Spatial obstacle detection | `vision_controller.py` | `detect_obstacles()` |
| VQA question answering | `vision_controller.py` | `ask_visual_question()` |
| OCR text reading | `vision_controller.py` | `read_text()` |
| Internet search | `voice_controller.py` | `search_internet()` |
| QR/AR scanning | `voice_controller.py` | `scan_qr_code()` |
| LLM stream processing | `voice_controller.py` | `process_stream()` |
| Query classification | `tool_router.py` | `classify_query()` |
| Tool dispatch | `tool_router.py` | `dispatch()`, `auto_dispatch()` |
| Input validation | `tool_router.py` | `validate_query()`, `validate_detail_level()` |
| Per-session state | `user_data.py` | `UserData` dataclass |
| System/nav prompts | `prompts.py` | `VISION_SYSTEM_PROMPT`, `MICRO_NAV_SYSTEM_PROMPT` |
| `@function_tool` wrappers | `agent.py` | Thin delegation to controllers |

## How To Add New Functionality

### Decision tree:

```
Is it a new tool the LLM can call?
  YES --> Register in tool_router.py (_register_default_tools)
          + Add handler in the appropriate controller
          + Add @function_tool wrapper in agent.py
  NO  --> Continue below.

Is it session lifecycle (startup, teardown, reconnection)?
  YES --> session_manager.py
  NO  --> Continue below.

Is it visual (frames, models, perception, depth)?
  YES --> vision_controller.py
  NO  --> Continue below.

Is it voice/audio/search related?
  YES --> voice_controller.py
  NO  --> Continue below.

Is it per-session state?
  YES --> user_data.py (add a field to the UserData dataclass)
  NO  --> It probably belongs in core/ or infrastructure/, not apps/realtime/.
```

### Adding a new tool (example: "read_braille")

1. **tool_router.py**: Add `"braille"` to trigger phrases, register handler in `_register_default_tools()`
2. **vision_controller.py**: Add `async def read_braille(userdata, query) -> str` with frame capture + core/braille/ dispatch
3. **agent.py**: Add `@function_tool` wrapper that calls `vision_controller.read_braille()`
4. **tests/**: Add unit test for the controller function and integration test for the dispatch chain

## Common Pitfalls

### Circular imports
The modules form a strict DAG enforced by `import-linter`:
```
tool_router --> voice_controller --> vision_controller --> prompts | user_data | session_manager
```
Never import a module that is above you in this chain. If `vision_controller` imported `tool_router`, the build would break.

### Shared state via UserData only
All per-session state lives in `UserData`. Do not use module-level globals for session data. Every controller function receives `userdata` as its first argument.

### Never put business logic in agent.py
`agent.py` is the coordinator. Its `@function_tool` methods must be one-liners that delegate to a controller. If your wrapper is more than 3 lines, the logic belongs in a controller.

### Heavy imports must be guarded
Wrap torch, FAISS, and similar imports in `try/except` with `_*_AVAILABLE` flags. The agent must start even if optional dependencies are missing.

### Every public function must have a failsafe
All controller functions wrap their body in `try/except` and return a user-friendly error string on failure. The pipeline never crashes.

## Verification

The decomposition is validated by:

| Verification | Tool | Result |
|-------------|------|--------|
| Unit tests for controllers | `pytest tests/unit/test_voice_controller.py` | 15 tests |
| Integration tests for module wiring | `pytest tests/integration/test_agent_coordinator.py` | 37 tests |
| Import boundary enforcement | `lint-imports` | 6/6 contracts KEPT |
| Circular dependency prevention | `lint-imports` (layers contract) | DAG enforced |
| LOC compliance | `test_agent_coordinator.py::TestLOCCompliance` | agent.py <= 500 LOC |
| Documentation accuracy | `pytest tests/unit/test_docs_accuracy.py` | All modules documented |
