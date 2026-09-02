"""Unit tests for the shared envelopes (S1-M08).

``Page.build`` centralises one ceil-division. That is exactly the kind of
three-line helper where an off-by-one hides for weeks, so its edge cases are
pinned here: exact multiples, remainders, and the empty result set.
"""

from pydantic import BaseModel

from app.schemas.common import ErrorDetail, Page, error_response


class _Item(BaseModel):
    """Stand-in for a real Read schema."""

    id: int


class TestPageBuild:
    def test_exact_multiple_has_no_extra_page(self) -> None:
        page = Page[_Item].build([], page=1, page_size=20, total=40)
        assert page.meta.total_pages == 2

    def test_remainder_rounds_up(self) -> None:
        """41 items at 20 per page is 3 pages, not 2 — the last holds one item."""
        page = Page[_Item].build([], page=1, page_size=20, total=41)
        assert page.meta.total_pages == 3

    def test_empty_result_set_has_zero_pages(self) -> None:
        """Zero, not one. An empty list has no page to navigate to."""
        page = Page[_Item].build([], page=1, page_size=20, total=0)
        assert page.meta.total_pages == 0
        assert page.items == []

    def test_single_item_is_one_page(self) -> None:
        assert Page[_Item].build([_Item(id=1)], page=1, page_size=20, total=1).meta.total_pages == 1

    def test_items_are_preserved_and_typed(self) -> None:
        page = Page[_Item].build([_Item(id=7), _Item(id=8)], page=1, page_size=2, total=2)
        assert [item.id for item in page.items] == [7, 8]

    def test_serialises_to_the_documented_shape(self) -> None:
        """The contract the frontend codes against — items + meta, nothing else."""
        dumped = Page[_Item].build([_Item(id=1)], page=2, page_size=1, total=3).model_dump()
        assert dumped == {
            "items": [{"id": 1}],
            "meta": {"page": 2, "page_size": 1, "total": 3, "total_pages": 3},
        }


class TestErrorResponse:
    def test_minimal_error_has_all_keys(self) -> None:
        """``details`` and ``request_id`` are always present, so the client never
        has to check for key existence — only for emptiness."""
        body = error_response("NOT_FOUND", "Complaint 42 was not found.")
        assert body == {
            "error": {
                "code": "NOT_FOUND",
                "message": "Complaint 42 was not found.",
                "details": [],
                "request_id": None,
            }
        }

    def test_details_are_included(self) -> None:
        body = error_response(
            "VALIDATION_ERROR",
            "One or more fields failed validation.",
            details=[ErrorDetail(field="ward_id", issue="must be an integer")],
            request_id="abc123",
        )
        assert body["error"]["details"] == [{"field": "ward_id", "issue": "must be an integer"}]
        assert body["error"]["request_id"] == "abc123"

    def test_field_is_optional_for_non_field_errors(self) -> None:
        """Some validation problems are about the body as a whole, not one field."""
        body = error_response(
            "VALIDATION_ERROR",
            "Body must be a JSON object.",
            details=[ErrorDetail(issue="expected object, got array")],
        )
        assert body["error"]["details"][0]["field"] is None
