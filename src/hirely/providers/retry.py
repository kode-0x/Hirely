"""Bounded, transient-only retry helper for provider HTTP calls.

All provider HTTP is centralized, so retry policy lives in one place. Retries
are strictly bounded, apply only to transient conditions, and never change the
model or provider. Rate limiting (HTTP 429) is deliberately *not* retried: it
surfaces as :class:`ModelUnavailable` so the UI can offer a deliberate switch
to Ollama rather than silently hammering a free model.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, TypeVar

import httpx

from hirely.providers.base import ProviderTimeout, ProviderUnavailable

if TYPE_CHECKING:
    from collections.abc import Callable

T = TypeVar("T")

#: HTTP status codes treated as transient server-side outages.
_TRANSIENT_STATUS = frozenset({502, 503, 504})

#: Fixed backoff between attempts, in seconds. Kept small and non-configurable
#: so retries can never approach a billable or long-blocking loop.
_BACKOFF_S = 0.5


class _TransientStatus(Exception):
    """Internal marker that a transient HTTP status was observed."""


def is_transient(exc: BaseException) -> bool:
    """Return whether an exception represents a retryable transient failure.

    Retryable conditions are connection errors, read timeouts, and the
    transient server statuses 502/503/504. Everything else, including HTTP 429,
    is non-transient.

    Args:
        exc: The exception raised by a provider call attempt.

    Returns:
        ``True`` if the call may be retried, ``False`` otherwise.
    """
    if isinstance(exc, _TransientStatus):
        return True
    if isinstance(exc, (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _TRANSIENT_STATUS
    return False


def retry_transient(func: Callable[[], T], *, max_retries: int) -> T:
    """Call ``func`` with bounded, transient-only retries.

    The callable is invoked up to ``max_retries + 1`` times. Between attempts a
    small fixed backoff is applied. The model and provider are never changed;
    only the exact same call is retried.

    Args:
        func: A zero-argument callable performing a single provider request.
        max_retries: Maximum number of retries after the first attempt
            (``>= 0``). Zero means a single attempt with no retries.

    Returns:
        The value returned by ``func`` on the first successful attempt.

    Raises:
        ProviderTimeout: If the final attempt fails with a read/connect
            timeout.
        ProviderUnavailable: If the final attempt fails with a connection error
            or a transient server status.
        Exception: Any non-transient exception raised by ``func`` is propagated
            unchanged on the first occurrence.
    """
    attempts = max_retries + 1
    last_exc: BaseException | None = None

    for attempt in range(attempts):
        try:
            return func()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in _TRANSIENT_STATUS:
                last_exc = exc
            else:
                raise
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as exc:
            last_exc = exc

        if attempt < attempts - 1:
            time.sleep(_BACKOFF_S)

    if isinstance(last_exc, (httpx.ReadTimeout, httpx.ConnectTimeout)):
        raise ProviderTimeout("provider request timed out after bounded retries") from last_exc
    raise ProviderUnavailable("provider unavailable after bounded retries") from last_exc
