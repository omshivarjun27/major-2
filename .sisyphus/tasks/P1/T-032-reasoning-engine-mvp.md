# T-032: reasoning-engine-mvp

> Phase: P1 | Cluster: CL-RSN | Risk: Medium | State: not_started

## Objective

Create a `ReasoningEngine` class in `core/reasoning/` that orchestrates VQA, OCR, and
memory retrieval into a unified query-response flow. Currently `core/reasoning/` is a
placeholder stub (only `__init__.py` with empty or minimal exports). The engine accepts
a question plus an optional image, routes to the appropriate subsystem based on query
classification, and returns a unified `ReasoningResult`.

This MVP establishes the reasoning abstraction layer that downstream application code
(frame orchestrator, API endpoints) will use instead of directly calling VQA, OCR, or
memory subsystems. It consolidates the three query paths into a single entry point with
consistent error handling and latency tracking.

## Current State (Codebase Audit 2026-02-25)

- `core/reasoning/` directory contains only `__init__.py` (placeholder/stub).
- No `ReasoningEngine` class or any real logic exists.
- Related subsystems that the engine will orchestrate:
  - `core/vqa/vqa_reasoner.py` (581 lines): `VQAReasoner` with `answer()` method,
    `QuickAnswers` for pattern matching, LLM fallback.
  - `core/ocr/engine.py` (292 lines): `ocr_read()` async function, returns text string
    (to be `OCRResult` after T-026).
  - `core/memory/retriever.py` (270 lines): `MemoryRetriever` with `search()` method.
- `core/vqa/perception.py` `PerceptionPipeline`: processes images into `PerceptionResult`.
- Query classification needed: visual questions ("what do you see?"), text questions
  ("read this sign"), recall questions ("what did I see earlier?").
- No unified result type exists for cross-subsystem responses.

## Implementation Plan

### Step 1: Define ReasoningResult in shared/schemas

Add a result type for unified reasoning responses:

```python
@dataclass
class ReasoningResult:
    answer: str
    source: str           # "vqa" | "ocr" | "memory" | "quick" | "fallback"
    confidence: float
    latency_ms: float
    metadata: dict         # source-specific details (e.g., memory hits, OCR text)
```

### Step 2: Create QueryClassifier

A lightweight classifier that categorizes questions into routing targets:
- Visual: "what", "describe", "how many", "is there" + image present -> VQA
- Text: "read", "what does it say", "text", "sign", "label" + image present -> OCR
- Recall: "remember", "earlier", "before", "last time", "history" -> Memory
- Default: VQA if image present, else Memory

```python
class QueryClassifier:
    VISUAL_PATTERNS = ["what do you see", "describe", "how many", "is there"]
    TEXT_PATTERNS = ["read", "what does it say", "text on", "sign", "label"]
    RECALL_PATTERNS = ["remember", "earlier", "before", "last time", "did i see"]

    def classify(self, question: str, has_image: bool) -> str:
        q = question.lower()
        # pattern matching logic
```

### Step 3: Create ReasoningEngine class

```python
class ReasoningEngine:
    def __init__(self, vqa_reasoner, ocr_reader, memory_retriever, classifier=None):
        self._vqa = vqa_reasoner
        self._ocr = ocr_reader
        self._memory = memory_retriever
        self._classifier = classifier or QueryClassifier()

    async def reason(self, question: str, image=None) -> ReasoningResult:
        route = self._classifier.classify(question, image is not None)
        # dispatch to appropriate subsystem
```

### Step 4: Implement routing with fallback chain

Each route tries its primary subsystem first. If it fails or returns low confidence,
fall back to the next subsystem (VQA -> OCR -> Memory -> generic fallback message).

### Step 5: Wire factory function

Create `create_reasoning_engine()` factory that assembles the engine from available
subsystem instances, with graceful degradation if some subsystems are not configured.

### Step 6: Write 6 unit tests

Cover query classification, VQA routing, OCR routing, memory routing, fallback
behavior, and factory function.

## Files to Create

| File | Purpose |
|------|---------|
| `core/reasoning/engine.py` | ReasoningEngine, QueryClassifier, create_reasoning_engine factory |
| `tests/unit/test_reasoning_engine.py` | 6 unit tests for ReasoningEngine |

## Files to Modify

| File | Change |
|------|--------|
| `shared/schemas/__init__.py` | Add ReasoningResult dataclass |
| `core/reasoning/__init__.py` | Export ReasoningEngine, QueryClassifier, create_reasoning_engine |
| `core/reasoning/AGENTS.md` | Create AGENTS.md documenting the reasoning engine architecture |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/unit/test_reasoning_engine.py` | `test_classify_visual_question` - "what do you see?" with image routes to VQA |
| | `test_classify_text_question` - "read the sign" with image routes to OCR |
| | `test_classify_recall_question` - "what did I see earlier?" routes to Memory |
| | `test_reason_vqa_route` - mock VQA reasoner, verify engine calls vqa.answer() |
| | `test_reason_fallback_on_failure` - mock VQA raises, verify fallback to generic response |
| | `test_factory_creates_engine` - create_reasoning_engine() returns configured ReasoningEngine |

## Acceptance Criteria

- [ ] `ReasoningResult` dataclass in `shared/schemas/__init__.py` with answer, source, confidence, latency_ms, metadata
- [ ] `QueryClassifier` correctly routes visual, text, and recall questions
- [ ] `ReasoningEngine.reason()` dispatches to correct subsystem based on classification
- [ ] Fallback chain activates when primary subsystem fails
- [ ] `create_reasoning_engine()` factory assembles engine with graceful degradation
- [ ] All 6 tests pass: `pytest tests/unit/test_reasoning_engine.py -v`
- [ ] `ruff check .` clean
- [ ] `lint-imports` clean (core/reasoning imports only from shared/ and core/ siblings)
- [ ] `core/reasoning/AGENTS.md` created

## Upstream Dependencies

T-024 (perception-orchestrator-tests) — perception pipeline tested and verified.

## Downstream Unblocks

T-031 (frame-processing-integration) — application layer needs ReasoningEngine.

## Estimated Scope

- New code: ~200 LOC (QueryClassifier ~50, ReasoningEngine ~100, factory ~30, schemas ~20)
- Modified code: ~5 lines in core/reasoning/__init__.py
- Tests: ~100 LOC
- Risk: Medium. Creates a new orchestration layer. Must respect core/ import constraints
  (can import from shared/ and other core/ subpackages, but NOT from application/ or infrastructure/).
