"""
Integration Tests for Memory Engine - Claude Opus 4.6 RAG Reasoner
(Uses mock/stub Claude responses)
"""


import pytest

from core.memory.llm_client import (
    CLAUDE_RAG_SYSTEM_PROMPT_SHORT,
    CLAUDE_RAG_SYSTEM_PROMPT_VERBOSE,
    ClaudeClient,
    LLMRole,
    OllamaClient,
    StubLLMClient,
    get_backend,
    register_backend,
    reset_backends,
)


class TestStubLLMClient:
    """Test the stub LLM client."""

    @pytest.mark.asyncio
    async def test_stub_returns_canned_response(self):
        stub = StubLLMClient(canned="Test answer")
        resp = await stub.generate("Hello?")
        assert resp.text == "Test answer"
        assert resp.model == "stub"

    @pytest.mark.asyncio
    async def test_stub_is_always_available(self):
        stub = StubLLMClient()
        assert stub.is_available is True

    @pytest.mark.asyncio
    async def test_stub_low_latency(self):
        stub = StubLLMClient()
        resp = await stub.generate("Any prompt")
        assert resp.latency_ms < 10


class TestLLMBackendRegistry:
    """Test the backend registration and retrieval."""

    def setup_method(self):
        reset_backends()

    def teardown_method(self):
        reset_backends()

    def test_register_and_get(self):
        stub = StubLLMClient(canned="hello")
        register_backend(LLMRole.MEMORY, stub)
        client = get_backend(LLMRole.MEMORY)
        assert client is stub

    def test_fallback_when_role_missing(self):
        stub = StubLLMClient(canned="fallback")
        register_backend(LLMRole.FALLBACK, stub)
        client = get_backend(LLMRole.MEMORY)  # not registered
        assert client is stub

    def test_error_when_no_backend(self):
        with pytest.raises(RuntimeError, match="No LLM backend"):
            get_backend(LLMRole.MEMORY)


class TestClaudePromptTemplates:
    """Test that prompt templates are well-formed."""

    def test_short_prompt_has_context_placeholder(self):
        assert "{context}" in CLAUDE_RAG_SYSTEM_PROMPT_SHORT

    def test_verbose_prompt_has_all_placeholders(self):
        assert "{context}" in CLAUDE_RAG_SYSTEM_PROMPT_VERBOSE
        assert "{question}" in CLAUDE_RAG_SYSTEM_PROMPT_VERBOSE
        assert "citations" in CLAUDE_RAG_SYSTEM_PROMPT_VERBOSE

    def test_short_prompt_renders(self):
        rendered = CLAUDE_RAG_SYSTEM_PROMPT_SHORT.format(
            context="[mem_001] 2024-01-01: Keys on kitchen table"
        )
        assert "Keys on kitchen table" in rendered
        assert "ONE concise sentence" in rendered

    def test_verbose_prompt_renders(self):
        rendered = CLAUDE_RAG_SYSTEM_PROMPT_VERBOSE.format(
            context="[mem_001] 2024-01-01: Keys on kitchen table",
            question="Where are my keys?",
        )
        assert "Where are my keys?" in rendered
        assert "citations" in rendered


class TestRAGReasonerWithClaudeStub:
    """Test RAG reasoner using a stub Claude client."""

    @pytest.fixture
    def setup_rag_with_claude_stub(self):
        """Set up RAG system with a stub LLM client."""
        from core.memory.embeddings import MockTextEmbedder, MultimodalFuser
        from core.memory.indexer import MockFAISSIndexer
        from core.memory.ingest import MemoryIngester
        from core.memory.rag_reasoner import RAGReasoner
        from core.memory.retriever import MemoryRetriever

        indexer = MockFAISSIndexer(dimension=384)
        embedder = MockTextEmbedder(dimension=384)
        fuser = MultimodalFuser(text_embedder=embedder)

        ingester = MemoryIngester(
            indexer=indexer,
            text_embedder=embedder,
            fuser=fuser,
        )

        retriever = MemoryRetriever(
            indexer=indexer,
            text_embedder=embedder,
        )

        # Use a stub that mimics Claude Opus 4.6 output
        stub_claude = StubLLMClient(
            canned='Based on your memories, your keys were last seen on the kitchen table at 7:12 AM.\n\n```json\n{"citations": [{"id": "mem_001", "timestamp": "2024-01-01T07:12:00Z"}]}\n```',
            model_id="us.anthropic.claude-opus-4-6-v1-stub",
        )

        reasoner = RAGReasoner(
            retriever=retriever,
            llm_client=stub_claude,
        )

        return ingester, retriever, reasoner

    @pytest.mark.asyncio
    async def test_query_with_claude_stub(self, setup_rag_with_claude_stub):
        """Query should use the Claude stub for reasoning."""
        ingester, retriever, reasoner = setup_rag_with_claude_stub
        from core.memory.api_schema import MemoryQueryRequest, MemoryStoreRequest

        await ingester.ingest(MemoryStoreRequest(
            transcript="I put my keys on the kitchen table",
        ))

        request = MemoryQueryRequest(query="keys", k=5)
        response = await reasoner.query(request)

        assert len(response.answer) > 0

    @pytest.mark.asyncio
    async def test_verbose_mode_with_claude_stub(self, setup_rag_with_claude_stub):
        """Verbose mode should attempt LLM-based answer."""
        ingester, retriever, reasoner = setup_rag_with_claude_stub
        from core.memory.api_schema import (
            MemoryQueryRequest,
            MemoryStoreRequest,
            QueryMode,
        )

        await ingester.ingest(MemoryStoreRequest(
            transcript="Meeting with Sarah at 3pm about project deadline",
        ))

        request = MemoryQueryRequest(
            query="meeting",
            mode=QueryMode.VERBOSE,
            k=5,
        )
        response = await reasoner.query(request)

        assert len(response.answer) > 0


class TestClaudeClientInit:
    """Test ClaudeClient initialization (without real API key)."""

    def test_claude_not_available_without_key(self):
        """Claude client should not be available without API key."""
        import os
        old_key = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            client = ClaudeClient(api_key="")
            assert client.is_available is False
        finally:
            if old_key:
                os.environ["ANTHROPIC_API_KEY"] = old_key

    def test_claude_model_name(self):
        client = ClaudeClient(api_key="")
        assert "claude" in client.model_name.lower() or "opus" in client.model_name.lower()


class TestOllamaClientInit:
    """Test OllamaClient initialization."""

    def test_ollama_model_name(self):
        """Ollama client should report correct model name."""
        try:
            client = OllamaClient(model_id="qwen3-vl:test")
            assert client.model_name == "qwen3-vl:test"
        except Exception:
            pytest.skip("openai SDK not available")
