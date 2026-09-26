"""Retry classification and bounded backoff tests."""

from unittest.mock import MagicMock

from services.retry import is_transient_error, with_retry


def test_transient_error_classification():
    class MockRateLimitError(Exception):
        status_code = 429

    class MockServiceUnavailableError(Exception):
        status_code = 503

    assert is_transient_error(MockRateLimitError("Rate limit exceeded")) is True
    assert is_transient_error(MockServiceUnavailableError("Service unavailable")) is True
    assert is_transient_error(TimeoutError("Request timed out")) is True
    assert is_transient_error(ConnectionError("Connection refused")) is True
    assert is_transient_error(ValueError("408 timeout")) is True


def test_permanent_error_classification():
    class MockAuthError(Exception):
        status_code = 401

    class MockNotFoundError(Exception):
        status_code = 404

    assert is_transient_error(MockAuthError("Invalid API key provided")) is False
    assert is_transient_error(MockNotFoundError("Model not found")) is False
    assert is_transient_error(ValueError("Invalid argument schema")) is False


def test_with_retry_retries_transient_then_succeeds():
    mock_func = MagicMock()
    mock_func.side_effect = [
        TimeoutError("Connection timeout"),
        TimeoutError("Connection timeout"),
        "Success result",
    ]

    decorated = with_retry(max_retries=3, initial_delay=0.01, jitter=0.01)(mock_func)
    result = decorated()

    assert result == "Success result"
    assert mock_func.call_count == 3


def test_with_retry_does_not_retry_permanent_error():
    mock_func = MagicMock()
    mock_func.side_effect = ValueError("Invalid API key")

    decorated = with_retry(max_retries=3, initial_delay=0.01, jitter=0.01)(mock_func)

    try:
        decorated()
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")

    assert mock_func.call_count == 1
