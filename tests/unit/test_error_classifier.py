"""Tests for infrastructure.resilience.error_classifier module."""

from __future__ import annotations

import pytest

from infrastructure.resilience.error_classifier import (
    ErrorCategory,
    classify_error,
    classify_status_code,
)

# ---------------------------------------------------------------------------
# HTTP status code classification
# ---------------------------------------------------------------------------

class TestStatusCodeClassification:
    """classify_status_code() with various HTTP codes."""

    @pytest.mark.parametrize(
        "code,expected",
        [
            (500, ErrorCategory.TRANSIENT),
            (502, ErrorCategory.TRANSIENT),
            (503, ErrorCategory.TRANSIENT),
            (504, ErrorCategory.TIMEOUT),
            (429, ErrorCategory.RATE_LIMIT),
            (401, ErrorCategory.AUTH),
            (403, ErrorCategory.AUTH),
            (400, ErrorCategory.PERMANENT),
            (404, ErrorCategory.PERMANENT),
            (422, ErrorCategory.PERMANENT),
        ],
    )
    def test_known_status_codes(self, code: int, expected: ErrorCategory):
        result = classify_status_code(code)
        assert result.category is expected

    def test_unknown_4xx_is_permanent(self):
        result = classify_status_code(418)  # I'm a teapot
        assert result.category is ErrorCategory.PERMANENT

    def test_unknown_5xx_is_transient(self):
        result = classify_status_code(599)
        assert result.category is ErrorCategory.TRANSIENT

    def test_unknown_code_is_unknown(self):
        result = classify_status_code(200)
        assert result.category is ErrorCategory.UNKNOWN


# ---------------------------------------------------------------------------
# Exception classification
# ---------------------------------------------------------------------------

class TestExceptionClassification:
    """classify_error() with various exception types."""

    def test_connection_error_is_transient(self):
        result = classify_error(ConnectionError("refused"))
        assert result.category is ErrorCategory.TRANSIENT
        assert result.should_retry is True

    def test_timeout_error_is_timeout(self):
        result = classify_error(TimeoutError("timed out"))
        assert result.category is ErrorCategory.TIMEOUT
        assert result.should_retry is True
        assert result.backoff_multiplier == 1.5

    def test_os_error_is_transient(self):
        result = classify_error(OSError("network unreachable"))
        assert result.category is ErrorCategory.TRANSIENT

    def test_connection_reset_is_transient(self):
        result = classify_error(ConnectionResetError("reset"))
        assert result.category is ErrorCategory.TRANSIENT

    def test_value_error_is_unknown(self):
        result = classify_error(ValueError("bad value"))
        assert result.category is ErrorCategory.UNKNOWN
        assert result.should_retry is True  # unknown defaults to retry

    def test_explicit_status_code_overrides(self):
        # Even if exception is ConnectionError, explicit 401 → auth
        result = classify_error(
            ConnectionError("weird"), status_code=401
        )
        assert result.category is ErrorCategory.AUTH
        assert result.should_retry is False


# ---------------------------------------------------------------------------
# Classification properties
# ---------------------------------------------------------------------------

class TestClassificationProperties:
    """Verify retry/failure/alert properties per category."""

    def test_transient_properties(self):
        c = classify_status_code(503)
        assert c.should_retry is True
        assert c.should_count_failure is True
        assert c.should_alert is False

    def test_permanent_properties(self):
        c = classify_status_code(400)
        assert c.should_retry is False
        assert c.should_count_failure is False
        assert c.should_alert is False

    def test_rate_limit_properties(self):
        c = classify_status_code(429)
        assert c.should_retry is True
        assert c.should_count_failure is True
        assert c.backoff_multiplier == 3.0

    def test_auth_properties(self):
        c = classify_status_code(401)
        assert c.should_retry is False
        assert c.should_count_failure is False
        assert c.should_alert is True

    def test_timeout_properties(self):
        c = classify_status_code(504)
        assert c.should_retry is True
        assert c.backoff_multiplier == 1.5


# ---------------------------------------------------------------------------
# Status code extraction from exceptions
# ---------------------------------------------------------------------------

class TestStatusCodeExtraction:
    """classify_error() extracts status codes from exception attributes."""

    def test_extracts_from_response_attribute(self):
        class FakeResponse:
            status_code = 429

        class FakeHTTPError(Exception):
            def __init__(self):
                self.response = FakeResponse()

        result = classify_error(FakeHTTPError())
        assert result.category is ErrorCategory.RATE_LIMIT

    def test_extracts_from_status_attribute(self):
        class FakeClientError(Exception):
            def __init__(self):
                self.status = 503

        result = classify_error(FakeClientError())
        assert result.category is ErrorCategory.TRANSIENT
