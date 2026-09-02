"""Request-id and access-log middleware.

Task S1-F06. One middleware doing two related things:

1. assign every request an id (reusing an inbound ``X-Request-ID`` if the caller
   supplied one), publish it to the logging ContextVar, and echo it back as a
   response header;
2. log one line per request with method, path, status, and duration.

Why the id is worth the code: a user reports "submitting a complaint failed".
With a request id in the error toast, that becomes a grep. Without one, it is a
guess about which of many similar log lines was theirs. Reusing an inbound header
means the id survives across the frontend and any future service hop.
"""

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import request_id_var

__all__ = ["REQUEST_ID_HEADER", "RequestContextMiddleware"]

REQUEST_ID_HEADER = "X-Request-ID"

logger = logging.getLogger("app.access")

# Health probes fire every few seconds; logging them buries real traffic.
_UNLOGGED_PATHS = frozenset({"/health/live", "/health/ready", "/favicon.ico"})


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request id to the log context and time the request."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # 16 hex chars: long enough to avoid collisions in our volume, short
        # enough that a user can read one out over a phone call.
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex[:16]
        token = request_id_var.set(request_id)

        # perf_counter, not time(): monotonic, so an NTP adjustment mid-request
        # cannot produce a negative duration.
        started = time.perf_counter()
        try:
            response = await call_next(request)
            elapsed_ms = (time.perf_counter() - started) * 1000
            response.headers[REQUEST_ID_HEADER] = request_id

            if request.url.path not in _UNLOGGED_PATHS:
                logger.info(
                    "%s %s -> %d in %.1fms",
                    request.method,
                    request.url.path,
                    response.status_code,
                    elapsed_ms,
                )
            return response
        except Exception:
            # The exception handler produces the response body; this only records
            # the timing that would otherwise be lost, then re-raises.
            elapsed_ms = (time.perf_counter() - started) * 1000
            logger.error(
                "%s %s -> unhandled exception in %.1fms",
                request.method,
                request.url.path,
                elapsed_ms,
            )
            raise
        finally:
            # Reset rather than leave it set: ContextVars are per-task, and
            # resetting keeps a stale id out of any code that runs after.
            # Both log calls above happen before this, so they still see the id.
            request_id_var.reset(token)
