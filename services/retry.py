"""
Retry mechanism with exponential backoff and jitter for transient LLM errors.
"""

import time
import random
import sys
import logging
from typing import Callable, TypeVar, Any
from functools import wraps

T = TypeVar("T")

logger = logging.getLogger(__name__)


def is_transient_error(exc: Exception) -> bool:
    """
    Determines if an exception is transient (eligible for retry).
    """
    exc_type = type(exc).__name__
    exc_msg = str(exc).lower()

    # Permanent error indicators (do NOT retry)
    permanent_keywords = [
        "invalid_api_key",
        "api_key_invalid",
        "authentication",
        "unauthorized",
        "invalid api key",
        "permission_denied",
        "invalid_request_error",
        "model_not_found",
        "not_found",
    ]
    if any(kw in exc_msg for kw in permanent_keywords):
        return False

    # Status codes in exception message or attributes
    status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if isinstance(status_code, int):
        if status_code in (401, 403, 404, 400, 422):
            return False
        if status_code in (429, 500, 502, 503, 504):
            return True

    # Transient error keywords or exception names
    transient_keywords = [
        "429", "503", "500", "502", "504",
        "rate limit", "quota", "overloaded",
        "timeout", "timed out", "connection",
        "unavailable", "temporarily", "try again"
    ]
    if any(kw in exc_msg for kw in transient_keywords):
        return True

    # Standard python network/timeout exceptions
    if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return True

    return False


def with_retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    jitter: float = 0.5
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for executing a function with exponential backoff and jitter.

    Args:
        max_retries: Maximum number of retry attempts (default: 3).
        initial_delay: Initial delay in seconds (default: 1.0s).
        backoff_factor: Multiplier for backoff calculation (default: 2.0).
        jitter: Max random jitter in seconds (default: 0.5s).
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            attempts = 0
            delay = initial_delay

            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    attempts += 1
                    if attempts > max_retries or not is_transient_error(exc):
                        if not is_transient_error(exc):
                            sys.stderr.write(f"[RETRY] Permanent error encountered ({type(exc).__name__}): {exc}. Not retrying.\n")
                        else:
                            sys.stderr.write(f"[RETRY] Exceeded max retries ({max_retries}). Final exception: {exc}\n")
                        raise exc

                    # Calculate sleep duration with backoff + jitter
                    sleep_time = delay + random.uniform(0, jitter)
                    sys.stderr.write(
                        f"[RETRY] Transient failure ({type(exc).__name__}: {exc}). "
                        f"Attempt {attempts}/{max_retries}. Retrying in {sleep_time:.2f}s...\n"
                    )
                    time.sleep(sleep_time)
                    delay *= backoff_factor

        return wrapper
    return decorator
