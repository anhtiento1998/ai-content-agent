"""Retrying HTTP steps of an upload when the network drops.

Retries happen per request, not per publish: repeating one step (a status
poll, the same byte range of a chunk, "finish" for the same video id) cannot
create a second post, while repeating a whole publish can. Steps that are not
safe to repeat (a single-shot upload whose reply was lost) are marked
`idempotent=False` and are only retried when the connection was never
established.

When every attempt fails without ever reaching the server, NetworkDown is
raised: nothing was sent, so the pipeline may try the platform again later
without risking a duplicate.
"""

from __future__ import annotations

import logging
import time
from typing import Callable

from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import ConnectTimeout, Timeout

logger = logging.getLogger(__name__)

TRANSIENT_STATUS = {408, 429, 500, 502, 503, 504}
DEFAULT_ATTEMPTS = 4
_sleep = time.sleep  # replaced in tests
_NEVER_CONNECTED = ("NewConnectionError", "NameResolutionError", "Failed to establish a new connection",
                    "Name or service not known", "getaddrinfo failed", "Temporary failure in name resolution",
                    "Network is unreachable", "No route to host", "Connection refused")


class NetworkDown(ConnectionError):
    """The request never reached the server on any attempt — nothing was sent or changed."""


def never_connected(exc: BaseException) -> bool:
    if isinstance(exc, ConnectTimeout):
        return True
    text = repr(exc)
    return isinstance(exc, (RequestsConnectionError, OSError)) and any(marker in text for marker in _NEVER_CONNECTED)


def _retry_after(response) -> float | None:
    try:
        return float(response.headers.get("Retry-After"))
    except (AttributeError, TypeError, ValueError):
        return None


def send(request: Callable[[], object], what: str, *, attempts: int = DEFAULT_ATTEMPTS, base_delay: float = 2.0,
         idempotent: bool = True):
    """Run `request()` (which performs one HTTP call and returns the response), retrying network
    errors and 408/429/5xx with exponential backoff. Returns the last response."""

    attempts = max(1, attempts)
    unreachable = True
    for attempt in range(1, attempts + 1):
        wait = min(base_delay * 2 ** (attempt - 1), 60.0)
        try:
            response = request()
        except (RequestsConnectionError, Timeout) as exc:
            unreachable = unreachable and never_connected(exc)
            retryable = idempotent or never_connected(exc)
            if attempt == attempts or not retryable:
                if unreachable:
                    raise NetworkDown(f"No network connection while {what}: {exc}") from exc
                raise
            logger.warning("Network error while %s (attempt %d/%d): %s — retrying in %.0fs",
                           what, attempt, attempts, exc, wait)
        else:
            status = getattr(response, "status_code", 200)
            if status not in TRANSIENT_STATUS or attempt == attempts or not idempotent:
                return response
            unreachable = False
            wait = min(_retry_after(response) or wait, 120.0)
            logger.warning("HTTP %s while %s (attempt %d/%d) — retrying in %.0fs", status, what, attempt, attempts, wait)
        _sleep(wait)
    raise AssertionError("unreachable")  # the loop always returns or raises
