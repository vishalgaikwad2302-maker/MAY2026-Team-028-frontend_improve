"""Shared response envelopes — the error shape and the pagination shape.

Task S1-M08. Every endpoint in ``docs/sprint-1/openapi.yaml`` references these
two schemas, so they are defined exactly once here and nowhere else.

Two contracts, fixed for both sprints:

Error (any 4xx/5xx)::

    {"error": {"code": "NOT_FOUND",
               "message": "Complaint 42 was not found.",
               "details": [{"field": "ward_id", "issue": "must be an integer"}],
               "request_id": "3f9c..."}}

Page (any list endpoint)::

    {"items": [...],
     "meta": {"page": 1, "page_size": 20, "total": 57, "total_pages": 3}}

Why an envelope at all: the frontend needs one branch to render an error, not
one per endpoint. ``code`` is a stable machine-readable string the client can
switch on; ``message`` is human-facing and may be reworded freely. ``request_id``
lets a user paste an id from a toast into a bug report and have us find the exact
log lines.
"""

from math import ceil
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ErrorDetail",
    "ErrorPayload",
    "ErrorResponse",
    "Page",
    "PageMeta",
    "error_response",
]

ItemT = TypeVar("ItemT")


class ErrorDetail(BaseModel):
    """One field-level problem. Populated mainly from Pydantic 422s."""

    model_config = ConfigDict(json_schema_extra={"example": {"field": "email", "issue": "invalid"}})

    field: str | None = Field(
        default=None,
        description="Dotted path to the offending input field, when applicable.",
    )
    issue: str = Field(description="What is wrong with it, in plain language.")


class ErrorPayload(BaseModel):
    """The body of the ``error`` key."""

    code: str = Field(description="Stable machine-readable error code, SCREAMING_SNAKE_CASE.")
    message: str = Field(description="Human-readable summary, safe to show a user.")
    details: list[ErrorDetail] = Field(
        default_factory=list,
        description="Zero or more field-level problems. Empty for non-validation errors.",
    )
    request_id: str | None = Field(
        default=None,
        description="Correlation id, matching the X-Request-ID response header.",
    )


class ErrorResponse(BaseModel):
    """The complete error response body. Referenced by every non-2xx in OpenAPI."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Complaint 42 was not found.",
                    "details": [],
                    "request_id": "1f0c9e8a4b7d4c2e",
                }
            }
        }
    )

    error: ErrorPayload


class PageMeta(BaseModel):
    """Pagination counters. ``total_pages`` is derived, never supplied."""

    page: int = Field(ge=1, description="1-based index of the returned page.")
    page_size: int = Field(ge=1, description="Maximum items per page.")
    total: int = Field(ge=0, description="Total matching rows, ignoring pagination.")
    total_pages: int = Field(ge=0, description="ceil(total / page_size).")


class Page(BaseModel, Generic[ItemT]):
    """Generic paginated envelope.

    Usage in a route's response model: ``Page[ComplaintRead]``. FastAPI expands
    the generic into a concrete named schema in the OpenAPI document, so the
    frontend sees ``PageComplaintRead`` with a properly typed ``items`` array.
    """

    items: list[ItemT]
    meta: PageMeta

    @classmethod
    def build(cls, items: list[ItemT], *, page: int, page_size: int, total: int) -> "Page[ItemT]":
        """Assemble a page and compute ``total_pages`` so no caller has to.

        Centralising the ceil-division is the point: every list endpoint would
        otherwise reimplement it, and one of them would get the edge case wrong.
        """
        return cls(
            items=items,
            meta=PageMeta(
                page=page,
                page_size=page_size,
                total=total,
                # total=0 -> 0 pages, not 1. An empty result set has no pages.
                total_pages=ceil(total / page_size) if page_size else 0,
            ),
        )


def error_response(
    code: str,
    message: str,
    *,
    details: list[ErrorDetail] | None = None,
    request_id: str | None = None,
) -> dict:
    """Build the error body as a plain dict, ready for ``JSONResponse``.

    Returns a dict rather than a model because exception handlers must produce
    JSON-serialisable content directly; going through the model and back would
    just add a round trip.
    """
    return ErrorResponse(
        error=ErrorPayload(
            code=code,
            message=message,
            details=details or [],
            request_id=request_id,
        )
    ).model_dump()
