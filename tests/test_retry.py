"""
Unit tests for retry mechanism decision logic (transient vs permanent errors).
"""

import pytest
from unittest.mock import MagicMock
from services.retry import is_transient_error, with_retry


def test_transient_error_classification():
    """Test transient error detection for 429, 503, connection timeouts."""
    class MockRateLimitError(Exception):
        status_code = 429

    class MockServiceUnavailableError(Exception):
        status_code = 503

    assert is_transient_error(MockRateLimitError("Rate limit exceeded")) is True
    assert is_transient_error(MockServiceUnavailableError("Service unavailable")) is True
    assert is_transient_error(TimeoutError("Request timed out")) is True
    assert is_transient_error(ConnectionError("Connection refused")) is True


def test_permanent_error_classification():
    """Test permanent error detection for invalid API keys, 401, 404, bad requests."""
    class MockAuthError(Exception):
        status_code = 401

    class MockNotFoundError(Exception):
        status_code = 404

    assert is_transient_error(MockAuthError("Invalid API key provided")) is False
    assert is_transient_error(MockNotFoundError("Model not found")) is False
    assert is_transient_error(ValueError("Invalid argument schema")) is False


def test_with_retry_decorator_retries_transient_then_succeeds():
    """Test decorator retries transient error and succeeds on 3rd attempt."""
    mock_func = MagicMock()
    mock_func.side_effect = [
        TimeoutError("Connection timeout"),
        TimeoutError("Connection timeout"),
        "Success result"
    ]

    decorated = with_retry(max_retries=3, initial_delay=0.01, jitter=0.01)(mock_func)
    result = decorated()

    assert result == "Success result"
    assert mock_func.call_count == 3


def test_with_retry_decorator_does_not_retry_permanent_error():
    """Test decorator immediately fails on permanent error without retrying."""
    mock_func = MagicMock()
    mock_func.side_effect = ValueError("Invalid API key")

    decorated = with_retry(max_retries=3, initial_delay=0.01, jitter=0.01)(mock_func)

    with pytest.raises(ValueError):
        decorated()

    assert mock_func.call_count == 1
