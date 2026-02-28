"""
Memory Engine - LLM Client Adapter Module
==========================================

Multi-backend LLM client supporting Claude Opus 4.6, qwen3-vl,
and local fallbacks.  Abstracts LLM calls behind a thin adapter so
callers never import provider-specific SDKs.
"""

import asyncio
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("memory-llm-client")

# ---------------------------------------------------------------------------
# Retry / timeout defaults (override via env)
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT_S: float = float(os.environ.get("LLM_TIMEOUT_S", "30"))
DEFAULT_MAX_RETRIES: int = int(os.environ.get("LLM_MAX_RETRIES", "3"))
DEFAULT_BACKOFF_BASE: float = 0.5  # seconds
logger = logging.getLogger("memory-llm-client")


# ============================================================================
# Backend registry
# ============================================================================

class LLMRole(str, Enum):
    """Roles for each backend."""
    VISION = "vision"       # qwen3-vl  – image-grounded VQA
    MEMORY = "memory"       # Claude Opus 4.6 – RAG reasoning / scenario analysis
    FALLBACK = "fallback"   # any local model used when primary is unavailable


# Default mapping – override via env  LLM_BACKEND_<ROLE>
DEFAULT_BACKENDS: Dict[str, str] = {
    LLMRole.VISION: "qwen3-vl",
    LLMRole.MEMORY: "us.anthropic.claude-opus-4-6-v1",
    LLMRole.FALLBACK: "qwen3-vl",
}


@dataclass
class LLMResponse:
    """Unified response from any LLM backend."""
    text: str
    model: str
    role: str
    usage: Dict[str, int] = field(default_factory=dict)
    latency_ms: float = 0.0
    raw: Optional[Any] = None


# ============================================================================
# Base class
# ============================================================================

class BaseLLMClient(ABC):
    """Abstract LLM client."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.3,
        stop: Optional[List[str]] = None,
    ) -> LLMResponse:
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...

    @property
    @abstractmethod
    def is_available(self) -> bool:
        ...


# ============================================================================
# Claude Opus 4.6 client (Anthropic API)
# ============================================================================

class ClaudeClient(BaseLLMClient):
    """Claude Opus 4.6 client via the Anthropic SDK.

    Requires env var ``ANTHROPIC_API_KEY``.  Falls back gracefully
    if the key or the SDK is missing.

    Supports configurable timeout and retry with exponential backoff.
    """

    MODEL_ID = "us.anthropic.claude-opus-4-6-v1"  # Amazon Bedrock global (cross-region) model id

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_id: Optional[str] = None,
        timeout_s: Optional[float] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._model_id = model_id or self.MODEL_ID
        self._timeout_s = timeout_s or DEFAULT_TIMEOUT_S
        self._max_retries = max_retries
        self._client: Optional[Any] = None
        self._available = False
        self._init_client()

    def _init_client(self):
        if not self._api_key:
            logger.info("ANTHROPIC_API_KEY not set \u2013 Claude backend disabled")
            return
        try:
            import anthropic  # type: ignore

            self._client = anthropic.AsyncAnthropic(
                api_key=self._api_key,
                timeout=self._timeout_s,
                max_retries=0,  # we handle retries ourselves
            )
            self._available = True
            logger.info("Claude client ready (model=%s, timeout=%.0fs)", self._model_id, self._timeout_s)
        except ImportError:
            logger.warning("anthropic SDK not installed \u2013 pip install anthropic")

    async def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.3,
        stop: Optional[List[str]] = None,
    ) -> LLMResponse:
        if not self._available or self._client is None:
            raise RuntimeError("Claude client is not available")

        t0 = time.time()
        messages = [{"role": "user", "content": prompt}]

        kwargs: Dict[str, Any] = dict(
            model=self._model_id,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=messages,
        )
        if system:
            kwargs["system"] = system
        if stop:
            kwargs["stop_sequences"] = stop

        last_exc: Optional[Exception] = None
        for attempt in range(1, self._max_retries + 1):
            try:
                resp = await self._client.messages.create(**kwargs)
                text = resp.content[0].text
                latency = (time.time() - t0) * 1000
                return LLMResponse(
                    text=text,
                    model=self._model_id,
                    role=LLMRole.MEMORY,
                    usage={
                        "input_tokens": resp.usage.input_tokens,
                        "output_tokens": resp.usage.output_tokens,
                    },
                    latency_ms=latency,
                    raw=resp,
                )
            except Exception as e:
                last_exc = e
                if attempt < self._max_retries:
                    delay = DEFAULT_BACKOFF_BASE * (2 ** (attempt - 1))
                    logger.warning(
                        "Claude generate attempt %d/%d failed: %s. Retrying in %.1fs",
                        attempt, self._max_retries, e, delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error("Claude generate failed after %d retries: %s", self._max_retries, e)
        raise last_exc  # type: ignore[misc]

    @property
    def model_name(self) -> str:
        return self._model_id

    @property
    def is_available(self) -> bool:
        return self._available


# ============================================================================
# Qwen3-VL / Ollama OpenAI-compat client
# ============================================================================

class OllamaClient(BaseLLMClient):
    """OpenAI-compatible client for the local Ollama server (qwen3-vl).

    Supports configurable timeout, connection pool, and retry with backoff.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_id: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_s: Optional[float] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        self._base_url = base_url or os.environ.get(
            "OPENAI_BASE_URL", "http://localhost:11434/v1"
        )
        self._model_id = model_id or os.environ.get(
            "OLLAMA_VL_MODEL_ID", "qwen3-vl:235b-instruct-cloud"
        )
        self._api_key = api_key or os.environ.get("OLLAMA_VL_API_KEY", "ollama")
        self._timeout_s = timeout_s or DEFAULT_TIMEOUT_S
        self._max_retries = max_retries
        self._client: Optional[Any] = None
        self._available = False
        self._init_client()

    def _init_client(self):
        try:
            import httpx
            from openai import AsyncOpenAI  # type: ignore

            # Connection pool limits for concurrent requests
            transport = httpx.AsyncHTTPTransport(
                retries=0,  # we handle retries ourselves
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            )
            http_client = httpx.AsyncClient(transport=transport, timeout=self._timeout_s)

            self._client = AsyncOpenAI(
                base_url=self._base_url,
                api_key=self._api_key,
                http_client=http_client,
                timeout=self._timeout_s,
            )
            self._available = True
            logger.info(
                "Ollama/OpenAI client ready (%s, model=%s, timeout=%.0fs)",
                self._base_url, self._model_id, self._timeout_s,
            )
        except ImportError:
            logger.warning("openai SDK not installed \u2013 pip install openai")

    async def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.3,
        stop: Optional[List[str]] = None,
    ) -> LLMResponse:
        if not self._available or self._client is None:
            raise RuntimeError("Ollama/OpenAI client is not available")

        t0 = time.time()
        messages: List[Dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs: Dict[str, Any] = dict(
            model=self._model_id,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        if stop:
            kwargs["stop"] = stop

        last_exc: Optional[Exception] = None
        for attempt in range(1, self._max_retries + 1):
            try:
                resp = await self._client.chat.completions.create(**kwargs)
                text = resp.choices[0].message.content or ""
                latency = (time.time() - t0) * 1000
                return LLMResponse(
                    text=text,
                    model=self._model_id,
                    role=LLMRole.VISION,
                    usage={
                        "prompt_tokens": getattr(resp.usage, "prompt_tokens", 0),
                        "completion_tokens": getattr(resp.usage, "completion_tokens", 0),
                    },
                    latency_ms=latency,
                    raw=resp,
                )
            except Exception as e:
                last_exc = e
                if attempt < self._max_retries:
                    delay = DEFAULT_BACKOFF_BASE * (2 ** (attempt - 1))
                    logger.warning(
                        "Ollama generate attempt %d/%d failed: %s. Retrying in %.1fs",
                        attempt, self._max_retries, e, delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error("Ollama generate failed after %d retries: %s", self._max_retries, e)
        raise last_exc  # type: ignore[misc]

    @property
    def model_name(self) -> str:
        return self._model_id

    @property
    def is_available(self) -> bool:
        return self._available


# ============================================================================
# Stub / mock client for testing
# ============================================================================

class StubLLMClient(BaseLLMClient):
    """In-process stub that returns canned answers.  Used for tests and
    offline-only deployments where no LLM API is reachable."""

    def __init__(self, canned: str = "I don't have enough information to answer.", model_id: str = "stub"):
        self._canned = canned
        self._model_id = model_id

    async def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.3,
        stop: Optional[List[str]] = None,
    ) -> LLMResponse:
        return LLMResponse(
            text=self._canned,
            model=self._model_id,
            role=LLMRole.FALLBACK,
            latency_ms=0.1,
        )

    @property
    def model_name(self) -> str:
        return self._model_id

    @property
    def is_available(self) -> bool:
        return True


# ============================================================================
# Factory / registry
# ============================================================================

_registry: Dict[str, BaseLLMClient] = {}


def register_backend(role: str, client: BaseLLMClient):
    """Register an LLM client for a role."""
    _registry[role] = client
    logger.info(f"Registered LLM backend: role={role} model={client.model_name}")


def get_backend(role: str) -> BaseLLMClient:
    """Return the client for *role*, falling back to FALLBACK if needed."""
    if role in _registry and _registry[role].is_available:
        return _registry[role]
    if LLMRole.FALLBACK in _registry:
        logger.warning(f"Backend for role '{role}' unavailable, using fallback")
        return _registry[LLMRole.FALLBACK]
    raise RuntimeError(f"No LLM backend available for role '{role}'")


def init_backends():
    """Auto-initialise backends from environment variables.

    Call once at application startup.  Backends that cannot initialise
    (missing SDK / key) are silently skipped.
    """
    # Claude Opus 4.6 – memory reasoning
    try:
        claude = ClaudeClient()
        if claude.is_available:
            register_backend(LLMRole.MEMORY, claude)
    except Exception as exc:
        logger.debug(f"Claude init skipped: {exc}")

    # Ollama / qwen3-vl – vision VQA
    try:
        ollama = OllamaClient()
        if ollama.is_available:
            register_backend(LLMRole.VISION, ollama)
            # Also doubles as fallback when Claude is absent
            if LLMRole.MEMORY not in _registry:
                register_backend(LLMRole.MEMORY, ollama)
            register_backend(LLMRole.FALLBACK, ollama)
    except Exception as exc:
        logger.debug(f"Ollama init skipped: {exc}")

    # Absolute fallback – stub
    if LLMRole.FALLBACK not in _registry:
        register_backend(LLMRole.FALLBACK, StubLLMClient())

    logger.info(f"LLM backends initialised: {list(_registry.keys())}")


def reset_backends():
    """Clear all registered backends (for testing)."""
    _registry.clear()


# ============================================================================
# Claude Opus 4.6 prompt templates
# ============================================================================

CLAUDE_RAG_SYSTEM_PROMPT_SHORT = """\
You are a memory assistant for a visually impaired user.
Answer the question using ONLY the retrieved memories below.
If the memories do not contain relevant information, reply:
"I don't have that in my recent memories."

MEMORIES:
{context}

Respond in ONE concise sentence. Do NOT add information beyond the memories.
"""

CLAUDE_RAG_SYSTEM_PROMPT_VERBOSE = """\
You are a memory assistant for a visually impaired user.
Answer the question using ONLY the retrieved memories below.
Provide a detailed answer with reasoning.

RULES:
1. Use ONLY information from the provided memories.
2. Cite every claim with the memory ID and timestamp.
3. If evidence is insufficient say so explicitly.
4. End your answer with a JSON block:
   ```json
   {{"citations": [{{"id": "mem_xxx", "timestamp": "..."}}]}}
   ```

MEMORIES:
{context}

Question: {question}
"""

CLAUDE_SCENARIO_ANALYSIS_PROMPT = """\
You are an expert accessibility researcher analysing how a RAG-powered
memory assistant benefits visually impaired users in the following scenario.

Scenario: {scenario}

Provide:
1. Environment & task description
2. How perception + memory helps (concrete use-cases)
3. What should be stored and recalled
4. Example user dialogue (3-4 turns)
5. Safety considerations & fallback behaviours

Be specific, practical, and empathetic. Format in markdown.
"""
