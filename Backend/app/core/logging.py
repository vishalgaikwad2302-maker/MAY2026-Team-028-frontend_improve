"""Logging configuration.

Two jobs:

1. ``configure_logging()`` — install one console handler with a consistent
   format, called once from the app factory.
2. ``request_id_var`` — a ``ContextVar`` holding the current request's id, so
   every log line emitted while handling a request carries that id without any
   function having to pass it around.

Why a ContextVar and not a parameter: a request touches route -> service ->
repository. Threading a ``request_id`` argument through all three layers would
pollute every signature. A ContextVar is set once by the middleware and read
implicitly by the log filter. Under asyncio each task gets its own copy, so
concurrent requests cannot see each other's id.
"""

import logging
import sys
from contextvars import ContextVar

__all__ = ["configure_logging", "get_request_id", "request_id_var"]

# "-" is the sentinel for log lines emitted outside any request (startup, CLI).
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

_LOG_FORMAT = "%(asctime)s %(levelname)-8s [%(request_id)s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


def get_request_id() -> str:
    """Current request id, or ``"-"`` outside a request."""
    return request_id_var.get()


class _RequestIdFilter(logging.Filter):
    """Inject ``record.request_id`` so the format string can reference it.

    A logging *filter* is the standard hook for enriching records — it runs for
    every record and may mutate it. Without this, ``%(request_id)s`` in the
    format string would raise a ``KeyError`` on records logged by third-party
    libraries (uvicorn, sqlalchemy) that know nothing about our ContextVar.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True  # never actually filter anything out


def configure_logging(level: str = "INFO") -> None:
    """Install the application's root log handler. Idempotent.

    Called from ``create_app()``. Safe to call twice — existing handlers are
    replaced, so reloads under ``uvicorn --reload`` do not stack up duplicate
    handlers printing every line N times.
    """
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT))
    handler.addFilter(_RequestIdFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())

    # uvicorn installs its own handlers; clearing them and letting records
    # propagate to root means access logs share our format and request id.
    for noisy in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(noisy)
        logger.handlers = []
        logger.propagate = True

    # SQLAlchemy logs every statement at INFO when echo is on. Keep it at
    # WARNING here; use DB_ECHO=true to turn statements back on deliberately.
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
