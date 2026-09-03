"""API integration tests for complaint route authentication and ownership rules."""

import io
import json
from unittest.mock import MagicMock, patch

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import app.services.complaint_classification_service as classification_service_module
from app.models.user import UserRole
from app.schemas.auth import LoginRequest
from app.schemas.user import UserCreate
from app.services.auth_service import AuthService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _register_and_login(db: Session, client: TestClient, email: str, role: UserRole) -> str:
    """Create a user and return a valid access token."""
    AuthService.register_user(
        db,
        UserCreate(
            email=email,
            password="password123",
            full_name="Test User",
            role=role,
        ),
    )
    tokens = AuthService.authenticate_user(db, LoginRequest(email=email, password="password123"))
    return tokens.access_token


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_complaint(db: Session, token: str, client: TestClient) -> int:
    """Create a complaint via the API and return the new complaint's id."""
    resp = client.post(
        "/api/v1/complaints",
        json={
            "location": "Test Street",
            "description": "Garbage left on road.",
            "hazard": "Risk to Children",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_201_CREATED, resp.text
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Unauthenticated → 401
# ---------------------------------------------------------------------------


def test_list_complaints_requires_auth(client: TestClient):
    """GET /complaints without a token must return 401."""
    resp = client.get("/api/v1/complaints")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
    assert resp.json()["error"]["code"] == "UNAUTHENTICATED"


def test_get_complaint_requires_auth(client: TestClient, db_session: Session):
    """GET /complaints/{id} without a token must return 401."""
    citizen_token = _register_and_login(db_session, client, "c1_auth@example.com", UserRole.CITIZEN)
    complaint_id = _create_complaint(db_session, citizen_token, client)

    resp = client.get(f"/api/v1/complaints/{complaint_id}")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
    assert resp.json()["error"]["code"] == "UNAUTHENTICATED"


def test_patch_complaint_requires_auth(client: TestClient, db_session: Session):
    """PATCH /complaints/{id} without a token must return 401."""
    citizen_token = _register_and_login(db_session, client, "c2_auth@example.com", UserRole.CITIZEN)
    complaint_id = _create_complaint(db_session, citizen_token, client)

    resp = client.patch(
        f"/api/v1/complaints/{complaint_id}",
        json={"description": "Updated description"},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_history_requires_auth(client: TestClient, db_session: Session):
    """GET /complaints/{id}/history without a token must return 401."""
    citizen_token = _register_and_login(db_session, client, "c3_auth@example.com", UserRole.CITIZEN)
    complaint_id = _create_complaint(db_session, citizen_token, client)

    resp = client.get(f"/api/v1/complaints/{complaint_id}/history")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_duplicates_requires_auth(client: TestClient, db_session: Session):
    """GET /complaints/{id}/duplicates without a token must return 401."""
    citizen_token = _register_and_login(db_session, client, "c4_auth@example.com", UserRole.CITIZEN)
    complaint_id = _create_complaint(db_session, citizen_token, client)

    resp = client.get(f"/api/v1/complaints/{complaint_id}/duplicates")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_upload_photo_requires_auth(client: TestClient):
    """POST /complaints/upload-photo without a token must return 401."""
    fake_image = io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    resp = client.post(
        "/api/v1/complaints/upload-photo",
        files={"photo": ("test.png", fake_image, "image/png")},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# Ownership rules
# ---------------------------------------------------------------------------


def test_citizen_sees_own_complaints_only(client: TestClient, db_session: Session):
    """A citizen listing complaints should receive only their own entries."""
    token_a = _register_and_login(db_session, client, "owner_a@example.com", UserRole.CITIZEN)
    token_b = _register_and_login(db_session, client, "owner_b@example.com", UserRole.CITIZEN)

    # Citizen A creates two complaints; Citizen B creates one.
    _create_complaint(db_session, token_a, client)
    _create_complaint(db_session, token_a, client)
    _create_complaint(db_session, token_b, client)

    resp = client.get("/api/v1/complaints", headers=_auth(token_a))
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    # All returned complaints must belong to Citizen A.
    assert data["meta"]["total"] == 2
    assert all(item["reported_by_user_id"] != 0 for item in data["items"])


def test_citizen_forbidden_on_others_complaint(client: TestClient, db_session: Session):
    """A citizen must receive 403 when fetching another citizen's complaint."""
    token_a = _register_and_login(db_session, client, "forbid_a@example.com", UserRole.CITIZEN)
    token_b = _register_and_login(db_session, client, "forbid_b@example.com", UserRole.CITIZEN)

    complaint_id = _create_complaint(db_session, token_a, client)

    # Citizen B tries to read Citizen A's complaint.
    resp = client.get(f"/api/v1/complaints/{complaint_id}", headers=_auth(token_b))
    assert resp.status_code == status.HTTP_403_FORBIDDEN
    assert resp.json()["error"]["code"] == "PERMISSION_DENIED"


def test_admin_sees_all_complaints(client: TestClient, db_session: Session):
    """An admin listing complaints should receive all complaints regardless of owner."""
    token_citizen = _register_and_login(
        db_session, client, "admin_test_c@example.com", UserRole.CITIZEN
    )
    token_admin = _register_and_login(
        db_session, client, "admin_test_a@example.com", UserRole.ADMIN
    )

    _create_complaint(db_session, token_citizen, client)
    _create_complaint(db_session, token_citizen, client)

    resp = client.get("/api/v1/complaints", headers=_auth(token_admin))
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    # Admin should see both complaints (not filtered to their own user_id).
    assert data["meta"]["total"] >= 2


def test_citizen_forbidden_on_duplicates(client: TestClient, db_session: Session):
    """A citizen must be denied access to the duplicates endpoint (crew/admin only)."""
    token_citizen = _register_and_login(
        db_session, client, "dup_citizen@example.com", UserRole.CITIZEN
    )
    complaint_id = _create_complaint(db_session, token_citizen, client)

    resp = client.get(f"/api/v1/complaints/{complaint_id}/duplicates", headers=_auth(token_citizen))
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_patch_cannot_set_resolved_at(client: TestClient, db_session: Session):
    """PATCH /complaints/{id} silently ignores resolved_at/cancelled_at in the body.

    These fields were removed from ComplaintUpdate, so the server should return
    422 (unknown field with strict mode) or silently ignore them. Either way the
    timestamps on the complaint must not be altered by a direct PATCH.
    """
    token = _register_and_login(db_session, client, "ts_test@example.com", UserRole.CITIZEN)
    complaint_id = _create_complaint(db_session, token, client)

    resp = client.patch(
        f"/api/v1/complaints/{complaint_id}",
        json={"resolved_at": "2020-01-01T00:00:00Z", "description": "Still garbage."},
        headers=_auth(token),
    )
    # Either 200 (field ignored) or 422 (field rejected) — but resolved_at must be None.
    assert resp.status_code in (status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY)
    if resp.status_code == status.HTTP_200_OK:
        assert resp.json()["resolved_at"] is None


def test_change_complaint_status_happy_path(client: TestClient, db_session: Session):
    """Happy Path: Admin or Crew can update complaint status."""
    citizen_token = _register_and_login(db_session, client, "stat_cit@example.com", UserRole.CITIZEN)
    admin_token = _register_and_login(db_session, client, "stat_adm@example.com", UserRole.ADMIN)
    complaint_id = _create_complaint(db_session, citizen_token, client)

    resp = client.patch(
        f"/api/v1/complaints/{complaint_id}/status",
        json={"status_value": "in_progress"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == "in_progress"


def test_change_complaint_status_rbac_failure(client: TestClient, db_session: Session):
    """Auth/RBAC Failure: Citizen cannot directly change complaint status."""
    citizen_token = _register_and_login(db_session, client, "stat_cit_fail@example.com", UserRole.CITIZEN)
    complaint_id = _create_complaint(db_session, citizen_token, client)

    resp = client.patch(
        f"/api/v1/complaints/{complaint_id}/status",
        json={"status_value": "in_progress"},
        headers=_auth(citizen_token),
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# S2-A18: complaint_type enum
# ---------------------------------------------------------------------------


def test_create_complaint_with_valid_complaint_type(client: TestClient, db_session: Session):
    """A valid complaint_type is accepted and echoed back on the created complaint."""
    token = _register_and_login(db_session, client, "ctype_valid@example.com", UserRole.CITIZEN)
    resp = client.post(
        "/api/v1/complaints",
        json={
            "location": "Test Street",
            "description": "Bin has not been collected in a week.",
            "hazard": "None",
            "complaint_type": "delay",
        },
        headers=_auth(token),
    )
    assert resp.status_code == status.HTTP_201_CREATED, resp.text
    assert resp.json()["complaint_type"] == "delay"


def test_create_complaint_without_complaint_type_defaults_to_none(
    client: TestClient, db_session: Session
):
    """Omitting complaint_type is fine (optional field, backward compatible)."""
    token = _register_and_login(db_session, client, "ctype_none@example.com", UserRole.CITIZEN)
    complaint_id = _create_complaint(db_session, token, client)
    resp = client.get(f"/api/v1/complaints/{complaint_id}", headers=_auth(token))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["complaint_type"] is None


def test_create_complaint_rejects_invalid_complaint_type(client: TestClient, db_session: Session):
    """A complaint_type outside the enum must be rejected with 422, not silently stored."""
    token = _register_and_login(db_session, client, "ctype_bad@example.com", UserRole.CITIZEN)
    resp = client.post(
        "/api/v1/complaints",
        json={
            "location": "Test Street",
            "description": "Trying to sneak in a bogus category.",
            "complaint_type": "not_a_real_category",
        },
        headers=_auth(token),
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# US-28/29/30: category enum, validation, and filter support
# ---------------------------------------------------------------------------


def test_create_complaint_with_valid_category(client: TestClient, db_session: Session):
    """A valid hazard/category is accepted and echoed back on the created complaint."""
    token = _register_and_login(db_session, client, "cat_valid@example.com", UserRole.CITIZEN)
    resp = client.post(
        "/api/v1/complaints",
        json={
            "location": "Test Street",
            "description": "Standing water attracting mosquitoes.",
            "hazard": "Mosquito Breeding",
        },
        headers=_auth(token),
    )
    assert resp.status_code == status.HTTP_201_CREATED, resp.text
    assert resp.json()["category"] == "Mosquito Breeding"


def test_create_complaint_without_category_defaults_to_none(
    client: TestClient, db_session: Session
):
    """Omitting the hazard field defaults the category to 'None'."""
    token = _register_and_login(db_session, client, "cat_default@example.com", UserRole.CITIZEN)
    resp = client.post(
        "/api/v1/complaints",
        json={"location": "Test Street", "description": "General litter, no hazard."},
        headers=_auth(token),
    )
    assert resp.status_code == status.HTTP_201_CREATED, resp.text
    assert resp.json()["category"] == "None"


def test_create_complaint_rejects_invalid_category(client: TestClient, db_session: Session):
    """A hazard value outside the fixed enum must be rejected with 422."""
    token = _register_and_login(db_session, client, "cat_bad@example.com", UserRole.CITIZEN)
    resp = client.post(
        "/api/v1/complaints",
        json={
            "location": "Test Street",
            "description": "Trying to sneak in a bogus hazard.",
            "hazard": "biohazard",
        },
        headers=_auth(token),
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_list_complaints_filters_by_category(client: TestClient, db_session: Session):
    """GET /complaints?category=... only returns complaints matching that category."""
    token = _register_and_login(db_session, client, "cat_filter@example.com", UserRole.CITIZEN)
    client.post(
        "/api/v1/complaints",
        json={
            "location": "Street A",
            "description": "Risk to nearby school",
            "hazard": "Risk to Children",
        },
        headers=_auth(token),
    )
    client.post(
        "/api/v1/complaints",
        json={"location": "Street B", "description": "Just litter"},
        headers=_auth(token),
    )

    resp = client.get(
        "/api/v1/complaints",
        params={"category": "Risk to Children"},
        headers=_auth(token),
    )
    assert resp.status_code == status.HTTP_200_OK, resp.text
    data = resp.json()
    assert data["meta"]["total"] == 1
    assert data["items"][0]["category"] == "Risk to Children"


def test_list_complaints_rejects_invalid_category_filter(
    client: TestClient, db_session: Session
):
    """Filtering by a category outside the enum returns 422, not a silent no-op."""
    token = _register_and_login(db_session, client, "cat_filter_bad@example.com", UserRole.CITIZEN)
    resp = client.get(
        "/api/v1/complaints",
        params={"category": "not_a_real_hazard"},
        headers=_auth(token),
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# POST /complaints/{id}/classify — Claude hazard classification (US-28/29/30)
# ---------------------------------------------------------------------------


def _create_complaint_with_description(
    db_session: Session, token: str, client: TestClient, description: str
) -> int:
    resp = client.post(
        "/api/v1/complaints",
        json={"location": "Test Street", "description": description},
        headers=_auth(token),
    )
    assert resp.status_code == status.HTTP_201_CREATED, resp.text
    return resp.json()["id"]


def test_classify_complaint_falls_back_to_heuristic_without_api_key(
    client: TestClient, db_session: Session
):
    """Happy Path: with no Claude API key configured, classification degrades to keyword matching."""
    citizen_token = _register_and_login(
        db_session, client, "clsfy_heuristic_citizen@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(
        db_session, client, "clsfy_heuristic_admin@example.com", UserRole.ADMIN
    )
    complaint_id = _create_complaint_with_description(
        db_session, citizen_token, client, "Stagnant water breeding mosquitoes near the drain."
    )

    resp = client.post(
        f"/api/v1/complaints/{complaint_id}/classify", headers=_auth(admin_token)
    )
    assert resp.status_code == status.HTTP_200_OK, resp.text
    data = resp.json()
    assert data["source"] == "heuristic"
    assert data["category"] == "Mosquito Breeding"
    assert data["complaint"]["category"] == "Mosquito Breeding"


def test_classify_complaint_validation_failure(client: TestClient, db_session: Session):
    """Validation Failure: non-integer complaint id returns 422."""
    admin_token = _register_and_login(
        db_session, client, "clsfy_val@example.com", UserRole.ADMIN
    )
    resp = client.post(
        "/api/v1/complaints/not-an-id/classify", headers=_auth(admin_token)
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_classify_complaint_rbac_failure(client: TestClient, db_session: Session):
    """Auth/RBAC Failure: a citizen cannot trigger hazard classification."""
    citizen_token = _register_and_login(
        db_session, client, "clsfy_rbac@example.com", UserRole.CITIZEN
    )
    complaint_id = _create_complaint_with_description(
        db_session, citizen_token, client, "Garbage left uncollected."
    )
    resp = client.post(
        f"/api/v1/complaints/{complaint_id}/classify", headers=_auth(citizen_token)
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_classify_complaint_edge_case_not_found(client: TestClient, db_session: Session):
    """Edge Case: classifying a non-existent complaint returns 404."""
    admin_token = _register_and_login(
        db_session, client, "clsfy_404@example.com", UserRole.ADMIN
    )
    resp = client.post(
        "/api/v1/complaints/999999/classify", headers=_auth(admin_token)
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_classify_complaint_uses_claude_when_configured(
    client: TestClient, db_session: Session, monkeypatch
):
    """When an API key is configured and Claude responds, the LLM result is used and persisted."""
    citizen_token = _register_and_login(
        db_session, client, "clsfy_llm_citizen@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(
        db_session, client, "clsfy_llm_admin@example.com", UserRole.ADMIN
    )
    complaint_id = _create_complaint_with_description(
        db_session, citizen_token, client, "A pile of trash with an awful smell."
    )
    monkeypatch.setattr(classification_service_module.settings, "anthropic_api_key", "test-key")

    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = json.dumps({
        "category": "Foul Smell",
        "tags": ["Foul Odor & Decomposing Garbage", "Plastic Waste & Bottles", "Roadside Street Litter"],
        "confidence": 0.92,
    })
    mock_response = MagicMock(stop_reason="end_turn", content=[text_block])

    with patch("anthropic.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value.messages.create.return_value = mock_response
        resp = client.post(
            f"/api/v1/complaints/{complaint_id}/classify", headers=_auth(admin_token)
        )

    assert resp.status_code == status.HTTP_200_OK, resp.text
    data = resp.json()
    assert data["source"] == "llm"
    assert data["category"] == "Foul Smell"
    assert len(data["tags"]) == 3
    assert data["confidence"] == 0.92
    assert data["complaint"]["category"] == "Foul Smell"
    assert len(data["complaint"]["tags"]) == 3


def test_classify_complaint_falls_back_when_claude_call_fails(
    client: TestClient, db_session: Session, monkeypatch
):
    """Graceful fallback: an API key is set but the Claude call errors — heuristic still succeeds."""
    citizen_token = _register_and_login(
        db_session, client, "clsfy_fail_citizen@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(
        db_session, client, "clsfy_fail_admin@example.com", UserRole.ADMIN
    )
    complaint_id = _create_complaint_with_description(
        db_session, citizen_token, client, "Risk near the school playground."
    )
    monkeypatch.setattr(classification_service_module.settings, "anthropic_api_key", "test-key")

    with patch("anthropic.Anthropic", side_effect=RuntimeError("network unreachable")):
        resp = client.post(
            f"/api/v1/complaints/{complaint_id}/classify", headers=_auth(admin_token)
        )

    assert resp.status_code == status.HTTP_200_OK, resp.text
    data = resp.json()
    assert data["source"] == "heuristic"
    assert data["category"] == "Risk to Children"


def test_classify_complaint_falls_back_when_claude_refuses(
    client: TestClient, db_session: Session, monkeypatch
):
    """Graceful fallback: Claude refuses the request — heuristic classification is used instead."""
    citizen_token = _register_and_login(
        db_session, client, "clsfy_refusal_citizen@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(
        db_session, client, "clsfy_refusal_admin@example.com", UserRole.ADMIN
    )
    complaint_id = _create_complaint_with_description(
        db_session, citizen_token, client, "Overflowing bin spilling onto the street."
    )
    monkeypatch.setattr(classification_service_module.settings, "anthropic_api_key", "test-key")

    mock_response = MagicMock(stop_reason="refusal", content=[])
    with patch("anthropic.Anthropic") as mock_anthropic_cls:
        mock_anthropic_cls.return_value.messages.create.return_value = mock_response
        resp = client.post(
            f"/api/v1/complaints/{complaint_id}/classify", headers=_auth(admin_token)
        )

    assert resp.status_code == status.HTTP_200_OK, resp.text
    data = resp.json()
    assert data["source"] == "heuristic"
    assert data["category"] == "Overflowing Bin"


# ---------------------------------------------------------------------------
# S2-F05: upload hardening
# ---------------------------------------------------------------------------


def _register_citizen_token(db_session: Session, client: TestClient, email: str) -> str:
    return _register_and_login(db_session, client, email, UserRole.CITIZEN)


def test_upload_photo_succeeds_with_real_png(client: TestClient, db_session: Session):
    """A genuine PNG (correct magic bytes + matching declared type) is accepted and saved."""
    token = _register_citizen_token(db_session, client, "upload_ok@example.com")
    fake_png = io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 200)
    resp = client.post(
        "/api/v1/complaints/upload-photo",
        files={"photo": ("evidence.png", fake_png, "image/png")},
        headers=_auth(token),
    )
    assert resp.status_code == status.HTTP_200_OK, resp.text
    body = resp.json()
    assert body["url"].startswith("/uploads/")
    assert body["url"].endswith(".png")


def test_upload_photo_rejects_spoofed_content_type(client: TestClient, db_session: Session):
    """Declaring image/png while sending non-image bytes must be rejected, not trusted."""
    token = _register_citizen_token(db_session, client, "upload_spoof@example.com")
    fake_html = io.BytesIO(b"<html><body>not an image</body></html>")
    resp = client.post(
        "/api/v1/complaints/upload-photo",
        files={"photo": ("evidence.png", fake_html, "image/png")},
        headers=_auth(token),
    )
    assert resp.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE


def test_upload_photo_rejects_mismatched_signature(client: TestClient, db_session: Session):
    """Real JPEG bytes declared as image/png must be rejected (sniffed type disagrees)."""
    token = _register_citizen_token(db_session, client, "upload_mismatch@example.com")
    fake_jpeg_bytes_declared_png = io.BytesIO(b"\xff\xd8\xff" + b"\x00" * 200)
    resp = client.post(
        "/api/v1/complaints/upload-photo",
        files={"photo": ("evidence.png", fake_jpeg_bytes_declared_png, "image/png")},
        headers=_auth(token),
    )
    assert resp.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE


def test_upload_photo_rejects_path_traversal_filename(client: TestClient, db_session: Session):
    """A malicious filename must not influence where the file is written.

    save_upload() never derives the on-disk name from client input, so even a
    ../ filename should just succeed with a safe generated name (not error,
    not escape the upload dir).
    """
    token = _register_citizen_token(db_session, client, "upload_traversal@example.com")
    fake_png = io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 200)
    resp = client.post(
        "/api/v1/complaints/upload-photo",
        files={"photo": ("../../../../etc/passwd.png", fake_png, "image/png")},
        headers=_auth(token),
    )
    assert resp.status_code == status.HTTP_200_OK
    url = resp.json()["url"]
    assert ".." not in url
    assert url.startswith("/uploads/")


def test_attach_complaint_photo_persists_url(client: TestClient, db_session: Session):
    """POST /complaints/{id}/photo saves the file and persists its URL as photo_url."""
    token = _register_citizen_token(db_session, client, "upload_attach@example.com")
    complaint_id = _create_complaint(db_session, token, client)
    fake_png = io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 200)
    resp = client.post(
        f"/api/v1/complaints/{complaint_id}/photo",
        files={"photo": ("evidence.png", fake_png, "image/png")},
        headers=_auth(token),
    )
    assert resp.status_code == status.HTTP_200_OK, resp.text
    assert resp.json()["photo_url"].startswith("/uploads/")


def test_upload_photo_rejects_oversized_file(client: TestClient, db_session: Session):
    """A file over the configured size cap must return 413, never be written."""
    from app.core.config import settings

    token = _register_citizen_token(db_session, client, "upload_oversize@example.com")
    too_big = io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * (settings.upload_max_bytes + 1))
    resp = client.post(
        "/api/v1/complaints/upload-photo",
        files={"photo": ("big.png", too_big, "image/png")},
        headers=_auth(token),
    )
    assert resp.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE


def test_verify_complaint_happy_path(client: TestClient, db_session: Session):
    """Admin review verifies complaint status to 'verified'."""
    citizen_token = _register_citizen_token(db_session, client, "verify_cit@example.com")
    admin_token = _register_and_login(db_session, client, "verify_admin@example.com", UserRole.ADMIN)
    complaint_id = _create_complaint(db_session, citizen_token, client)

    # Admin verifies the complaint
    resp = client.patch(
        f"/api/v1/complaints/{complaint_id}/verify",
        json={"notes": "Inspection passed"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == status.HTTP_200_OK, resp.text
    assert resp.json()["status"] == "verified"


def test_verify_complaint_rbac_failure(client: TestClient, db_session: Session):
    """Citizen role cannot verify complaints (Admin only)."""
    citizen_token = _register_citizen_token(db_session, client, "verify_rbac_cit@example.com")
    complaint_id = _create_complaint(db_session, citizen_token, client)

    resp = client.patch(
        f"/api/v1/complaints/{complaint_id}/verify",
        json={"notes": "Illegal verify attempt"},
        headers=_auth(citizen_token),
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_close_complaint_happy_path(client: TestClient, db_session: Session):
    """Supervisor confirm closes complaint and stamps resolved_at timestamp."""
    citizen_token = _register_citizen_token(db_session, client, "close_cit@example.com")
    admin_token = _register_and_login(db_session, client, "close_admin@example.com", UserRole.ADMIN)
    complaint_id = _create_complaint(db_session, citizen_token, client)

    resp = client.patch(
        f"/api/v1/complaints/{complaint_id}/close",
        json={"notes": "Confirmed by supervisor"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == status.HTTP_200_OK, resp.text
    data = resp.json()
    assert data["status"] == "closed"
    assert data["resolved_at"] is not None


def test_crew_resolve_complaint_with_completion_photos_happy_path(
    client: TestClient, db_session: Session
):
    """Crew member resolves complaint providing 1-3 completion photos as proof of work."""
    citizen_token = _register_citizen_token(db_session, client, "res_cit@example.com")
    crew_token = _register_and_login(db_session, client, "res_crew@example.com", UserRole.CREW)
    admin_token = _register_and_login(db_session, client, "res_admin@example.com", UserRole.ADMIN)
    complaint_id = _create_complaint(db_session, citizen_token, client)

    # Admin moves complaint to in_progress
    client.patch(
        f"/api/v1/complaints/{complaint_id}/status",
        json={"status_value": "in_progress"},
        headers=_auth(admin_token),
    )

    # Crew resolves complaint with 2 proof photos and notes
    photos = ["/uploads/proof_1.jpg", "/uploads/proof_2.webp"]
    resp = client.post(
        f"/api/v1/complaints/{complaint_id}/resolve",
        json={"completion_photos": photos, "resolution_notes": "Garbage cleared and sanitized."},
        headers=_auth(crew_token),
    )
    assert resp.status_code == status.HTTP_200_OK, resp.text
    data = resp.json()
    assert data["status"] == "resolved"
    assert data["completion_photos"] == photos
    assert data["resolution_notes"] == "Garbage cleared and sanitized."
    assert data["resolved_at"] is not None


def test_resolve_complaint_photo_validation(client: TestClient, db_session: Session):
    """Validation: completion_photos requires 1 to 3 items."""
    citizen_token = _register_citizen_token(db_session, client, "val_cit@example.com")
    crew_token = _register_and_login(db_session, client, "val_crew@example.com", UserRole.CREW)
    complaint_id = _create_complaint(db_session, citizen_token, client)

    # Empty list should be rejected with 422
    resp_empty = client.post(
        f"/api/v1/complaints/{complaint_id}/resolve",
        json={"completion_photos": []},
        headers=_auth(crew_token),
    )
    assert resp_empty.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # 4 photos should be rejected with 422
    resp_over = client.post(
        f"/api/v1/complaints/{complaint_id}/resolve",
        json={"completion_photos": ["/u1.jpg", "/u2.jpg", "/u3.jpg", "/u4.jpg"]},
        headers=_auth(crew_token),
    )
    assert resp_over.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_citizen_cannot_resolve_complaint(client: TestClient, db_session: Session):
    """Citizen role cannot resolve a complaint (Crew/Admin only)."""
    citizen_token = _register_citizen_token(db_session, client, "unauth_res@example.com")
    complaint_id = _create_complaint(db_session, citizen_token, client)

    resp = client.post(
        f"/api/v1/complaints/{complaint_id}/resolve",
        json={"completion_photos": ["/proof.jpg"]},
        headers=_auth(citizen_token),
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN

