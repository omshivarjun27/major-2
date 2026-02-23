# tests/AGENTS.md
429+ tests across 4 layers.
**Config**: `asyncio_mode=auto` via `pyproject.toml`. No `@pytest.mark.asyncio` needed.

## TEST HIERARCHY
| Directory | Files | Purpose |
|-----------|-------|---------|
| `unit/` | 13 | Fast, isolated tests for engines (OCR, Memory, QR, Braille). |
| `integration/` | 8 | Cross-module tests (VQA API, RAG flow, SiliconFlow). |
| `performance/` | 17 | NFR/SLA tests for latency, FPS, and privacy. |
| `realtime/` | 5 | Live pipeline harnesses (**NOT** run via pytest). |
| `fixtures/` | - | Synthetic data generators (Braille patterns, detection sets). |

## MOCK PATTERNS
Mocks are typically defined locally within test files to avoid brittle shared fixtures.
```python
class MockDetector:
    def __init__(self, detections=None, delay_s=0.0, should_raise=False):
        self.detections = detections or []
        self.delay_s = delay_s
        self.should_raise = should_raise

    async def detect(self, image):
        if self.should_raise: raise RuntimeError("Mock error")
        await asyncio.sleep(self.delay_s)
        return self.detections
```
**Use `delay_s`** to verify concurrent execution and timeouts.
**Use `should_raise=True`** to verify "never-raise" guarantees in the orchestrator.

## KEY CONVENTIONS
- **Fixture Chaining**: `mock_indexer → mock_embedder → ingester` (dependency injection).
- **Env Overrides**: Use the `env_overrides` fixture to safely mutate settings for a single test.
- **ASGI Transport**: Use `AsyncClient(transport=ASGITransport(app=app))` for testing FastAPI endpoints.
- **Assertion Style**: Use descriptive messages: `assert elapsed < 500, f"Hot path took {elapsed}ms (limit: 500)"`.

## REALTIME TOOLS
The `tests/realtime/` directory contains standalone scripts for manual benchmarking and live-frame inspection. Run directly: `python tests/realtime/realtime_test.py --debug`.
