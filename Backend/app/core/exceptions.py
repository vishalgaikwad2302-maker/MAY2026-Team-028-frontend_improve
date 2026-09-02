"""Typed domain exceptions + the FastAPI handlers that render them.

Task S1-F05. The rule this file exists to enforce: **services and repositories
raise domain exceptions; they never import ``fastapi`` and never build an HTTP
response.** A service says "this complaint does not exist" by raising
``NotFoundError``; deciding that this means HTTP 404 with our error envelope is
this module's job alone.

Why that separation is worth the extra class:

* the same service can back an HTTP route, a CLI command, or a background job
  without dragging HTTP semantics along;
* every error response has an identical shape because exactly one function
  builds it;
* tests can assert ``pytest.raises(InvalidStateTransitionError)`` on the service
  and assert the status code on the route, testing each layer at its own level.

``register_exception_handlers(app)`` wires all four handlers and is called by
``create_app()``.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_request_id
from app.schemas.common import ErrorDetail, error_response

__all__ = [
    "AppError",
    "AuthenticationError",
    "ConflictError",
    "InvalidInputError",
    "InvalidStateTransitionError",
    "NotFoundError",
    "PayloadTooLargeError",
    "PermissionDeniedError",
    "UnsupportedMediaTypeError",
    "register_exception_handlers",
]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------------


class AppError(Exception):
    """Base class for every expected, business-level failure.

    "Expected" is the key word. ``AppError`` and its subclasses describe things
    that legitimately happen (missing row, forbidden role, illegal transition)
    and map to a 4xx. Anything *not* derived from this is a bug and becomes a
    500 — that distinction is what lets us log the two groups differently.
    """

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "BAD_REQUEST"
    message: str = "The request could not be processed."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        details: list[ErrorDetail] | None = None,
    ) -> None:
        # Per-instance overrides fall back to the class-level defaults, so
        # `raise NotFoundError()` works and so does a bespoke message.
        self.message = message or self.message
        self.code = code or self.code
        self.details = details or []
        super().__init__(self.message)


class InvalidInputError(AppError):
    """Input is well-formed but semantically wrong. HTTP 400."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "INVALID_INPUT"
    message = "The request contained invalid input."


class AuthenticationError(AppError):
    """Missing, malformed, or expired credentials. HTTP 401."""

    status_code = status.HTTP_401_UNAUTHORIZED
    code = "UNAUTHENTICATED"
    message = "Authentication is required."


class PermissionDeniedError(AppError):
    """Authenticated but not allowed. HTTP 403.

    Distinct from 401 on purpose: the frontend must redirect to login on 401 but
    show "not for your role" on 403. Collapsing them makes correct client
    behaviour impossible.
    """

    status_code = status.HTTP_403_FORBIDDEN
    code = "PERMISSION_DENIED"
    message = "You do not have permission to perform this action."


class NotFoundError(AppError):
    """Requested resource does not exist. HTTP 404."""

    status_code = status.HTTP_404_NOT_FOUND
    code = "NOT_FOUND"
    message = "The requested resource was not found."


class ConflictError(AppError):
    """Request collides with current state, e.g. duplicate email. HTTP 409."""

    status_code = status.HTTP_409_CONFLICT
    code = "CONFLICT"
    message = "The request conflicts with the current state of the resource."


class InvalidStateTransitionError(ConflictError):
    """An illegal move in a status state machine. HTTP 409.

    Example: cancelling a complaint that is already ``Resolved``. Carries its own
    code so the client can distinguish "you cannot do that yet" from a generic
    conflict, which matters for the complaint and task status flows.
    """

    code = "INVALID_STATE_TRANSITION"
    message = "That status change is not allowed from the current state."


class PayloadTooLargeError(AppError):
    """Upload exceeds ``settings.upload_max_bytes``. HTTP 413."""

    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    code = "PAYLOAD_TOO_LARGE"
    message = "The uploaded file is too large."


class UnsupportedMediaTypeError(AppError):
    """Upload MIME type is not in the allow-list. HTTP 415."""

    status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    code = "UNSUPPORTED_MEDIA_TYPE"
    message = "The uploaded file type is not supported."


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------
# Each handler converts one exception family into the shared envelope. They are
# the only place in the codebase that constructs an error JSONResponse.


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Render a domain exception. Logged at WARNING — expected, not a bug."""
    logger.warning(
        "%s %s -> %s (%s): %s",
        request.method,
        request.url.path,
        exc.status_code,
        exc.code,
        exc.message,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(
            exc.code,
            exc.message,
            details=exc.details,
            request_id=get_request_id(),
        ),
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Reshape framework-raised HTTPExceptions into our envelope.

    Starlette and FastAPI raise these themselves (404 for an unknown path, 405
    for a wrong method), and their default body is ``{"detail": "..."}``. Without
    this handler the API would speak two different error dialects depending on
    whether our code or the framework produced the error.
    """
    code = _http_status_to_code(exc.status_code)
    message = exc.detail if isinstance(exc.detail, str) else code.replace("_", " ").title()
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(code, message, request_id=get_request_id()),
        headers=getattr(exc, "headers", None),
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Flatten Pydantic's validation report into ``details``. HTTP 422.

    Pydantic gives a nested ``loc`` tuple such as ``("body", "ward_id")``. The
    leading segment is the request part (body/query/path), which the client does
    not need, so it is dropped and the rest joined with dots — the frontend can
    then match ``field`` straight onto its form field names.
    """
    details = [
        ErrorDetail(
            field=".".join(str(segment) for segment in err["loc"][1:]) or None,
            issue=err["msg"],
        )
        for err in exc.errors()
    ]
    logger.info("422 validation failure on %s %s: %s", request.method, request.url.path, details)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response(
            "VALIDATION_ERROR",
            "One or more fields failed validation.",
            details=details,
            request_id=get_request_id(),
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Last resort for genuine bugs. HTTP 500.

    Logged at ERROR with a full traceback, but the response deliberately says
    nothing specific: exception text can leak table names, file paths, or
    connection strings. The ``request_id`` is the bridge — the user reports it,
    we grep the logs for the traceback.
    """
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response(
            "INTERNAL_ERROR",
            "An unexpected error occurred. Please report the request id.",
            request_id=get_request_id(),
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach every handler to the app. Called once from ``create_app()``."""
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    # Broad on purpose: guarantees no route can ever return a non-enveloped body.
    app.add_exception_handler(Exception, unhandled_exception_handler)


_STATUS_CODE_NAMES = {
    400: "BAD_REQUEST",
    401: "UNAUTHENTICATED",
    403: "PERMISSION_DENIED",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    503: "SERVICE_UNAVAILABLE",
}


def _http_status_to_code(status_code: int) -> str:
    """Map an HTTP status to our ``code`` vocabulary, keeping the two aligned."""
    return _STATUS_CODE_NAMES.get(status_code, f"HTTP_{status_code}")
