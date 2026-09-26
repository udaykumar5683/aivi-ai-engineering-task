"""Retry mechanism with exponential backoff and jitter."""

import random
import sys
import time
from functools import wraps
from typing import Any, Callable, TypeVar

T = TypeVar("T")


def is_transient_error(exc: Exception) -> bool:
    """Return True for errors that are reasonable to retry."""
    message = str(exc).lower()
    status_code = getattr(exc, "status_code", None)
    if status_code is None:
        status_code = getattr(exc, "code", None)

    permanent_keywords = (
        "invalid_api_key",
        "api_key_invalid",
        "invalid api key",
        "authentication",
        "unauthorized",
        "permission_denied",
        "invalid_request_error",
        "model_not_found",
        "not_found",
    )
    if any(keyword in message for keyword in permanent_keywords):
        return False

    if isinstance(status_code, int):
        if status_code in {400, 401, 402, 403, 404, 422}:
            return False
        if status_code in {408, 429, 500, 502, 503, 504}:
            return True

    transient_keywords = (
        "408",
        "429",
        "500",
        "502",
        "503",
        "504",
        "rate limit",
        "quota",
        "overloaded",
        "timeout",
        "timed out",
        "connection",
        "unavailable",
        "temporarily",
        "try again",
    )
    if any(keyword in message for keyword in transient_keywords):
        return True

    return isinstance(exc, (TimeoutError, ConnectionError, OSError))


def with_retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    jitter: float = 0.5,
    max_delay: float = 30.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry transient failures with bounded exponential backoff and jitter."""
    if max_retries < 0:
        raise ValueError("max_retries must be non-negative.")
    if initial_delay < 0 or backoff_factor <= 0 or jitter < 0 or max_delay <= 0:
        raise ValueError("Invalid retry timing configuration.")

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            delay = initial_delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    retryable = is_transient_error(exc)
                    last_attempt = attempt >= max_retries

                    if not retryable or last_attempt:
                        kind = "permanent" if not retryable else "retry limit reached"
                        sys.stderr.write(
                            f"[RETRY] {kind}: {type(exc).__name__}: {exc}\n"
                        )
                        raise

                    sleep_time = min(delay, max_delay) + random.uniform(0, jitter)
                    sys.stderr.write(
                        f"[RETRY] transient error ({type(exc).__name__}); "
                        f"retry {attempt + 1}/{max_retries} in {sleep_time:.2f}s\n"
                    )
                    time.sleep(sleep_time)
                    delay *= backoff_factor

        return wrapper

    return decorator
