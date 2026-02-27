"""Unit tests for logging correlation module.

Tests T-094: Structured Logging Enhancement
"""

import asyncio
import logging
import pytest


class TestCorrelationIdGeneration:
    """Tests for correlation ID generation."""
    
    def test_generate_correlation_id_format(self):
        """Test correlation ID has correct format."""
        from shared.logging.correlation import generate_correlation_id
        
        cid = generate_correlation_id()
        assert cid.startswith("cor_")
        assert len(cid) == 20  # "cor_" + 16 hex chars
    
    def test_generate_correlation_id_unique(self):
        """Test each generated ID is unique."""
        from shared.logging.correlation import generate_correlation_id
        
        ids = {generate_correlation_id() for _ in range(100)}
        assert len(ids) == 100
    
    def test_generate_span_id_format(self):
        """Test span ID has correct format."""
        from shared.logging.correlation import generate_span_id
        
        sid = generate_span_id()
        assert sid.startswith("span_")
        assert len(sid) == 17  # "span_" + 12 hex chars


class TestContextVariables:
    """Tests for context variable getters and setters."""
    
    def test_set_and_get_correlation_id(self):
        """Test setting and getting correlation ID."""
        from shared.logging.correlation import (
            get_correlation_id,
            set_correlation_id,
        )
        
        token = set_correlation_id("cor_test123")
        assert get_correlation_id() == "cor_test123"
        
        # Reset for cleanup
        from shared.logging.correlation import _correlation_id
        _correlation_id.reset(token)
    
    def test_set_and_get_session_id(self):
        """Test setting and getting session ID."""
        from shared.logging.correlation import (
            get_session_id,
            set_session_id,
        )
        
        token = set_session_id("ses_abc123")
        assert get_session_id() == "ses_abc123"
        
        from shared.logging.correlation import _session_id
        _session_id.reset(token)
    
    def test_set_and_get_service_name(self):
        """Test setting and getting service name."""
        from shared.logging.correlation import (
            get_service_name,
            set_service_name,
        )
        
        token = set_service_name("test-service")
        assert get_service_name() == "test-service"
        
        from shared.logging.correlation import _service_name
        _service_name.reset(token)


class TestLogContext:
    """Tests for LogContext class."""
    
    def test_context_manager_sets_values(self):
        """Test context manager sets correlation values."""
        from shared.logging.correlation import (
            LogContext,
            get_correlation_id,
            get_session_id,
        )
        
        with LogContext(correlation_id="cor_ctx123", session_id="ses_ctx456"):
            assert get_correlation_id() == "cor_ctx123"
            assert get_session_id() == "ses_ctx456"
        
        # Values should be cleared after exiting
        assert get_correlation_id() == ""
    
    def test_context_manager_auto_generates_correlation_id(self):
        """Test context manager generates correlation ID if not provided."""
        from shared.logging.correlation import (
            LogContext,
            get_correlation_id,
        )
        
        with LogContext() as ctx:
            cid = get_correlation_id()
            assert cid.startswith("cor_")
            assert ctx.correlation_id == cid
    
    async def test_async_context_manager(self):
        """Test async context manager works."""
        from shared.logging.correlation import (
            LogContext,
            get_correlation_id,
        )
        
        async with LogContext(correlation_id="cor_async123"):
            assert get_correlation_id() == "cor_async123"
        
        assert get_correlation_id() == ""
    
    def test_child_context_inherits_values(self):
        """Test child context inherits parent values."""
        from shared.logging.correlation import LogContext
        
        parent = LogContext(
            correlation_id="cor_parent",
            session_id="ses_parent",
        )
        
        with parent:
            child = parent.child_context()
            
            # Child should inherit correlation and session
            assert child.correlation_id == "cor_parent"
            assert child.session_id == "ses_parent"
            
            # Child should have new span with parent as parent_span
            assert child.span_id.startswith("span_")
            assert child.parent_span_id == parent.span_id
    
    def test_to_dict(self):
        """Test context converts to dictionary."""
        from shared.logging.correlation import LogContext
        
        with LogContext(
            correlation_id="cor_dict123",
            session_id="ses_dict456",
            service_name="test-svc",
        ) as ctx:
            d = ctx.to_dict()
            
            assert d["correlation_id"] == "cor_dict123"
            assert d["session_id"] == "ses_dict456"
            assert d["service_name"] == "test-svc"
            assert "span_id" in d


class TestCorrelatedLoggerAdapter:
    """Tests for CorrelatedLoggerAdapter."""
    
    def test_adapter_adds_correlation_context(self):
        """Test adapter adds correlation context to logs."""
        from shared.logging.correlation import (
            LogContext,
            get_correlated_logger,
        )
        
        with LogContext(correlation_id="cor_log123", session_id="ses_log456"):
            logger = get_correlated_logger("test-logger")
            
            # The process method should add correlation context
            msg, kwargs = logger.process("test message", {})
            
            assert kwargs["extra"]["correlation_id"] == "cor_log123"
            assert kwargs["extra"]["session_id"] == "ses_log456"
    
    def test_adapter_preserves_existing_extra(self):
        """Test adapter doesn't overwrite existing extra."""
        from shared.logging.correlation import (
            LogContext,
            get_correlated_logger,
        )
        
        with LogContext(correlation_id="cor_exist"):
            logger = get_correlated_logger("test-logger")
            
            msg, kwargs = logger.process(
                "test",
                {"extra": {"correlation_id": "cor_custom", "custom_field": "value"}}
            )
            
            # Custom correlation_id should be preserved
            assert kwargs["extra"]["correlation_id"] == "cor_custom"
            # Custom field should be preserved
            assert kwargs["extra"]["custom_field"] == "value"


class TestDecoratorCorrelated:
    """Tests for @correlated decorator."""
    
    def test_decorator_sets_correlation_context(self):
        """Test decorator sets correlation context."""
        from shared.logging.correlation import (
            correlated,
            get_correlation_id,
        )
        
        @correlated
        def my_function():
            return get_correlation_id()
        
        result = my_function()
        assert result.startswith("cor_")
    
    async def test_async_decorator(self):
        """Test decorator works with async functions."""
        from shared.logging.correlation import (
            correlated,
            get_correlation_id,
        )
        
        @correlated
        async def my_async_function():
            return get_correlation_id()
        
        result = await my_async_function()
        assert result.startswith("cor_")
    
    def test_decorator_preserves_existing_context(self):
        """Test decorator doesn't override existing context."""
        from shared.logging.correlation import (
            correlated,
            LogContext,
            get_correlation_id,
        )
        
        @correlated
        def my_function():
            return get_correlation_id()
        
        with LogContext(correlation_id="cor_existing"):
            result = my_function()
            assert result == "cor_existing"


class TestWithSpanDecorator:
    """Tests for @with_span decorator."""
    
    def test_with_span_creates_child_span(self):
        """Test with_span creates a child span."""
        from shared.logging.correlation import (
            with_span,
            LogContext,
            get_span_id,
            get_parent_span_id,
        )
        
        parent_span = None
        child_span = None
        child_parent = None
        
        with LogContext() as ctx:
            parent_span = ctx.span_id
            
            @with_span("test-span")
            def my_function():
                nonlocal child_span, child_parent
                child_span = get_span_id()
                child_parent = get_parent_span_id()
            
            my_function()
        
        # Child should have different span from parent
        assert child_span != parent_span
        # Child's parent should be the parent span
        assert child_parent == parent_span
    
    async def test_async_with_span(self):
        """Test with_span works with async functions."""
        from shared.logging.correlation import (
            with_span,
            LogContext,
            get_span_id,
        )
        
        spans = []
        
        async with LogContext():
            @with_span("async-span")
            async def my_async_function():
                spans.append(get_span_id())
            
            await my_async_function()
        
        assert len(spans) == 1
        assert spans[0].startswith("span_")


class TestLogCorrelatedEvent:
    """Tests for log_correlated_event function."""
    
    def test_emits_event_with_correlation(self, caplog):
        """Test event is emitted with correlation context."""
        from shared.logging.correlation import (
            LogContext,
            log_correlated_event,
        )
        
        with caplog.at_level(logging.INFO):
            with LogContext(correlation_id="cor_event123"):
                log_correlated_event(
                    "test-component",
                    "test_event",
                    component="subcomponent",
                    latency_ms=42.5,
                )
        
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.name == "test-component"
        assert hasattr(record, "correlation_id")


class TestAsyncContextPropagation:
    """Tests for correlation propagation across async tasks."""
    
    async def test_propagation_in_gather(self):
        """Test correlation propagates through asyncio.gather."""
        from shared.logging.correlation import (
            LogContext,
            get_correlation_id,
        )
        
        results = []
        
        async def task1():
            results.append(("task1", get_correlation_id()))
        
        async def task2():
            results.append(("task2", get_correlation_id()))
        
        async with LogContext(correlation_id="cor_gather123"):
            await asyncio.gather(task1(), task2())
        
        # Both tasks should have the same correlation ID
        assert results[0][1] == "cor_gather123"
        assert results[1][1] == "cor_gather123"
    
    async def test_isolation_between_contexts(self):
        """Test different contexts are isolated."""
        from shared.logging.correlation import (
            LogContext,
            get_correlation_id,
        )
        
        async def task_with_context(cid: str) -> str:
            async with LogContext(correlation_id=cid):
                await asyncio.sleep(0.01)
                return get_correlation_id()
        
        results = await asyncio.gather(
            task_with_context("cor_a"),
            task_with_context("cor_b"),
            task_with_context("cor_c"),
        )
        
        # Each should have its own correlation ID
        assert results[0] == "cor_a"
        assert results[1] == "cor_b"
        assert results[2] == "cor_c"


class TestThreadSafety:
    """Tests for thread safety."""
    
    def test_correlation_isolated_between_threads(self):
        """Test correlation IDs are isolated between threads."""
        import threading
        from shared.logging.correlation import (
            LogContext,
            get_correlation_id,
        )
        
        results = {}
        
        def thread_task(thread_id: str, cid: str):
            with LogContext(correlation_id=cid):
                # Simulate some work
                import time
                time.sleep(0.01)
                results[thread_id] = get_correlation_id()
        
        threads = [
            threading.Thread(target=thread_task, args=(f"t{i}", f"cor_t{i}"))
            for i in range(5)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Each thread should have its own correlation ID
        for i in range(5):
            assert results[f"t{i}"] == f"cor_t{i}"
