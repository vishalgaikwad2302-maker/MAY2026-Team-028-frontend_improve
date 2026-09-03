"""API integration tests for the public transparency feed (S2-F03, US-25)."""

import io

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import UserRole
from app.schemas.auth import LoginRequest
from app.schemas.user import UserCreate
from app.services.auth_service import AuthService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _register_and_login(db: Session, client: TestClient, email: str, role: UserRole) -> str:
    AuthService.register_user(
        db,
        UserCreate(email=email, password="password123", full_name="Test User", role=role),
    )
    tokens = AuthService.authenticate_user(db, LoginRequest(email=email, password="password123"))
    return tokens.access_token


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_complaint(client: TestClient, token: str) -> int:
    resp = client.post(
        "/api/v1/complaints",
        json={
            "location": "Test Street",
            "description": "Garbage left on road.",
            "hazard": "Risk to Children",
        },
        headers=_auth(token),
    )
    assert resp.status_code == status.HTTP_201_CREATED, resp.text
    return resp.json()["id"]


def _resolve_complaint(client: TestClient, admin_token: str, complaint_id: int) -> None:
    for target in ("in_progress", "resolved"):
        resp = client.patch(
            f"/api/v1/complaints/{complaint_id}/status",
            json={"status_value": target},
            headers=_auth(admin_token),
        )
        assert resp.status_code == status.HTTP_200_OK, resp.text


def _create_post(client: TestClient, admin_token: str, complaint_id: int) -> int:
    resp = client.post(
        "/api/v1/transparency",
        json={"complaint_id": complaint_id, "title": "Street cleaned up"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == status.HTTP_201_CREATED, resp.text
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# POST /transparency
# ---------------------------------------------------------------------------


def test_create_post_happy_path(client: TestClient, db_session: Session):
    """Happy Path: admin publishes a post for a resolved complaint."""
    citizen_token = _register_and_login(
        db_session, client, "tp_citizen@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(db_session, client, "tp_admin@example.com", UserRole.ADMIN)
    complaint_id = _create_complaint(client, citizen_token)
    _resolve_complaint(client, admin_token, complaint_id)

    resp = client.post(
        "/api/v1/transparency",
        json={
            "complaint_id": complaint_id,
            "title": "Street cleaned up",
            "before_photo_url": "/uploads/before.jpg",
            "after_photo_url": "/uploads/after.jpg",
        },
        headers=_auth(admin_token),
    )
    assert resp.status_code == status.HTTP_201_CREATED, resp.text
    data = resp.json()
    assert data["title"] == "Street cleaned up"
    assert data["applause_count"] == 0
    assert data["complaint_id"] == complaint_id


def test_create_post_validation_failure(client: TestClient, db_session: Session):
    """Validation Failure: missing required title returns 422."""
    admin_token = _register_and_login(
        db_session, client, "tp_admin_val@example.com", UserRole.ADMIN
    )
    resp = client.post("/api/v1/transparency", json={"complaint_id": 1}, headers=_auth(admin_token))
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_post_rbac_failure(client: TestClient, db_session: Session):
    """Auth/RBAC Failure: a citizen cannot publish a transparency post."""
    citizen_token = _register_and_login(
        db_session, client, "tp_citizen_rbac@example.com", UserRole.CITIZEN
    )
    complaint_id = _create_complaint(client, citizen_token)

    resp = client.post(
        "/api/v1/transparency",
        json={"complaint_id": complaint_id, "title": "Should fail"},
        headers=_auth(citizen_token),
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_create_post_edge_case_not_resolved(client: TestClient, db_session: Session):
    """Edge Case: publishing for a still-pending complaint returns 409 Conflict."""
    citizen_token = _register_and_login(
        db_session, client, "tp_pending@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(
        db_session, client, "tp_admin_pending@example.com", UserRole.ADMIN
    )
    complaint_id = _create_complaint(client, citizen_token)

    resp = client.post(
        "/api/v1/transparency",
        json={"complaint_id": complaint_id, "title": "Too early"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == status.HTTP_409_CONFLICT
    assert resp.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


def test_create_post_edge_case_duplicate(client: TestClient, db_session: Session):
    """Edge Case: a second post for the same complaint returns 409 Conflict."""
    citizen_token = _register_and_login(db_session, client, "tp_dup@example.com", UserRole.CITIZEN)
    admin_token = _register_and_login(
        db_session, client, "tp_admin_dup@example.com", UserRole.ADMIN
    )
    complaint_id = _create_complaint(client, citizen_token)
    _resolve_complaint(client, admin_token, complaint_id)
    _create_post(client, admin_token, complaint_id)

    resp = client.post(
        "/api/v1/transparency",
        json={"complaint_id": complaint_id, "title": "Duplicate post"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == status.HTTP_409_CONFLICT
    assert resp.json()["error"]["code"] == "CONFLICT"


# ---------------------------------------------------------------------------
# GET /transparency, GET /transparency/{id} — public, no auth
# ---------------------------------------------------------------------------


def test_list_posts_happy_path(client: TestClient, db_session: Session):
    """Happy Path: anyone can list the public feed without a token."""
    citizen_token = _register_and_login(
        db_session, client, "tp_list_citizen@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(
        db_session, client, "tp_list_admin@example.com", UserRole.ADMIN
    )
    complaint_id = _create_complaint(client, citizen_token)
    _resolve_complaint(client, admin_token, complaint_id)
    _create_post(client, admin_token, complaint_id)

    resp = client.get("/api/v1/transparency")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["meta"]["total"] >= 1


def test_get_post_validation_failure(client: TestClient):
    """Validation Failure: non-integer post id returns 422."""
    resp = client.get("/api/v1/transparency/not-an-id")
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_get_post_no_auth_required(client: TestClient, db_session: Session):
    """No-auth: fetching a single post detail requires no token."""
    citizen_token = _register_and_login(
        db_session, client, "tp_get_citizen@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(
        db_session, client, "tp_get_admin@example.com", UserRole.ADMIN
    )
    complaint_id = _create_complaint(client, citizen_token)
    _resolve_complaint(client, admin_token, complaint_id)
    post_id = _create_post(client, admin_token, complaint_id)

    resp = client.get(f"/api/v1/transparency/{post_id}")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["id"] == post_id


def test_get_post_edge_case_not_found(client: TestClient):
    """Edge Case: fetching a non-existent post returns 404."""
    resp = client.get("/api/v1/transparency/999999")
    assert resp.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# POST /transparency/{id}/applaud — public
# ---------------------------------------------------------------------------


def test_applaud_post_happy_path(client: TestClient, db_session: Session):
    """Happy Path: applauding increments the counter without auth."""
    citizen_token = _register_and_login(
        db_session, client, "tp_ap_citizen@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(db_session, client, "tp_ap_admin@example.com", UserRole.ADMIN)
    complaint_id = _create_complaint(client, citizen_token)
    _resolve_complaint(client, admin_token, complaint_id)
    post_id = _create_post(client, admin_token, complaint_id)

    resp = client.post(f"/api/v1/transparency/{post_id}/applaud")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["applause_count"] == 1


def test_applaud_post_validation_failure(client: TestClient):
    """Validation Failure: non-integer post id returns 422."""
    resp = client.post("/api/v1/transparency/not-an-id/applaud")
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_applaud_post_edge_case_multiple(client: TestClient, db_session: Session):
    """Edge Case: applauding twice accumulates the counter to 2."""
    citizen_token = _register_and_login(
        db_session, client, "tp_ap2_citizen@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(
        db_session, client, "tp_ap2_admin@example.com", UserRole.ADMIN
    )
    complaint_id = _create_complaint(client, citizen_token)
    _resolve_complaint(client, admin_token, complaint_id)
    post_id = _create_post(client, admin_token, complaint_id)

    client.post(f"/api/v1/transparency/{post_id}/applaud")
    resp = client.post(f"/api/v1/transparency/{post_id}/applaud")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["applause_count"] == 2


def test_applaud_post_edge_case_not_found(client: TestClient):
    """Edge Case: applauding a non-existent post returns 404."""
    resp = client.post("/api/v1/transparency/999999/applaud")
    assert resp.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# POST/GET /transparency/{id}/comments
# ---------------------------------------------------------------------------


def test_create_comment_happy_path(client: TestClient, db_session: Session):
    """Happy Path: a logged-in user can comment on a post."""
    citizen_token = _register_and_login(
        db_session, client, "tp_c_citizen@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(db_session, client, "tp_c_admin@example.com", UserRole.ADMIN)
    complaint_id = _create_complaint(client, citizen_token)
    _resolve_complaint(client, admin_token, complaint_id)
    post_id = _create_post(client, admin_token, complaint_id)

    resp = client.post(
        f"/api/v1/transparency/{post_id}/comments",
        json={"comment": "Great work!"},
        headers=_auth(citizen_token),
    )
    assert resp.status_code == status.HTTP_201_CREATED, resp.text
    assert resp.json()["comment"] == "Great work!"


def test_create_comment_validation_failure(client: TestClient, db_session: Session):
    """Validation Failure: an empty comment body returns 422."""
    citizen_token = _register_and_login(
        db_session, client, "tp_c_val_citizen@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(
        db_session, client, "tp_c_val_admin@example.com", UserRole.ADMIN
    )
    complaint_id = _create_complaint(client, citizen_token)
    _resolve_complaint(client, admin_token, complaint_id)
    post_id = _create_post(client, admin_token, complaint_id)

    resp = client.post(
        f"/api/v1/transparency/{post_id}/comments",
        json={"comment": ""},
        headers=_auth(citizen_token),
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_comment_rbac_failure(client: TestClient, db_session: Session):
    """Auth/RBAC Failure: commenting without a token returns 401."""
    citizen_token = _register_and_login(
        db_session, client, "tp_c_noauth_citizen@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(
        db_session, client, "tp_c_noauth_admin@example.com", UserRole.ADMIN
    )
    complaint_id = _create_complaint(client, citizen_token)
    _resolve_complaint(client, admin_token, complaint_id)
    post_id = _create_post(client, admin_token, complaint_id)

    resp = client.post(f"/api/v1/transparency/{post_id}/comments", json={"comment": "Anon"})
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_comment_edge_case_not_found(client: TestClient, db_session: Session):
    """Edge Case: commenting on a non-existent post returns 404."""
    citizen_token = _register_and_login(
        db_session, client, "tp_c_404_citizen@example.com", UserRole.CITIZEN
    )
    resp = client.post(
        "/api/v1/transparency/999999/comments",
        json={"comment": "Nobody home"},
        headers=_auth(citizen_token),
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_list_comments_happy_path(client: TestClient, db_session: Session):
    """Happy Path: comments can be listed without auth, in creation order."""
    citizen_token = _register_and_login(
        db_session, client, "tp_lc_citizen@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(db_session, client, "tp_lc_admin@example.com", UserRole.ADMIN)
    complaint_id = _create_complaint(client, citizen_token)
    _resolve_complaint(client, admin_token, complaint_id)
    post_id = _create_post(client, admin_token, complaint_id)
    client.post(
        f"/api/v1/transparency/{post_id}/comments",
        json={"comment": "First"},
        headers=_auth(citizen_token),
    )

    resp = client.get(f"/api/v1/transparency/{post_id}/comments")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert len(data) == 1
    assert data[0]["comment"] == "First"


def test_list_comments_edge_case_empty(client: TestClient, db_session: Session):
    """Edge Case: a post with no comments returns an empty list, not 404."""
    citizen_token = _register_and_login(
        db_session, client, "tp_lc_empty_citizen@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(
        db_session, client, "tp_lc_empty_admin@example.com", UserRole.ADMIN
    )
    complaint_id = _create_complaint(client, citizen_token)
    _resolve_complaint(client, admin_token, complaint_id)
    post_id = _create_post(client, admin_token, complaint_id)

    resp = client.get(f"/api/v1/transparency/{post_id}/comments")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == []


def test_auto_generate_transparency_post_on_close(client: TestClient, db_session: Session):
    """Closing a complaint auto-generates a transparency post with before/after photos."""
    citizen_token = _register_and_login(
        db_session, client, "tp_auto_citizen@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(
        db_session, client, "tp_auto_admin@example.com", UserRole.ADMIN
    )
    complaint_id = _create_complaint(client, citizen_token)

    # Attach before photo to complaint
    client.post(
        f"/api/v1/complaints/{complaint_id}/photo",
        files={"photo": ("before.png", io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 10), "image/png")},
        headers=_auth(citizen_token),
    )

    # Close complaint with after photo URL
    close_resp = client.patch(
        f"/api/v1/complaints/{complaint_id}/close",
        json={"after_photo_url": "/uploads/after_clean.png", "notes": "Supervisor verified"},
        headers=_auth(admin_token),
    )
    assert close_resp.status_code == status.HTTP_200_OK

    # Verify auto-generated TransparencyPost exists for complaint
    feed_resp = client.get("/api/v1/transparency")
    assert feed_resp.status_code == status.HTTP_200_OK
    posts = feed_resp.json()["items"]
    matched = [p for p in posts if p["complaint_id"] == complaint_id]
    assert len(matched) == 1
    auto_post = matched[0]
    assert auto_post["before_photo_url"].startswith("/uploads/")
    assert auto_post["after_photo_url"] == "/uploads/after_clean.png"


def test_citizen_can_create_standalone_transparency_post(client: TestClient, db_session: Session):
    """Any logged-in citizen can publish a standalone minimal post with up to 3 images."""
    citizen_token = _register_and_login(
        db_session, client, "standalone_citizen@example.com", UserRole.CITIZEN
    )
    resp = client.post(
        "/api/v1/transparency",
        json={
            "title": "Community Park Cleanup",
            "description": "Volunteers collected 5 bags of recyclables from the playground.",
            "images": ["/uploads/img1.jpg", "/uploads/img2.jpg", "/uploads/img3.jpg"],
        },
        headers=_auth(citizen_token),
    )
    assert resp.status_code == status.HTTP_201_CREATED, resp.text
    data = resp.json()
    assert data["title"] == "Community Park Cleanup"
    assert data["complaint_id"] is None
    assert len(data["images"]) == 3
    assert data["images"][0] == "/uploads/img1.jpg"


def test_citizen_can_create_standalone_feed_post(client: TestClient, db_session: Session):
    """POST /api/v1/feed also works for creating standalone posts."""
    citizen_token = _register_and_login(
        db_session, client, "feed_citizen@example.com", UserRole.CITIZEN
    )
    resp = client.post(
        "/api/v1/feed",
        json={
            "title": "Cleaned Roadway",
            "description": "Quick sweep along Main Street.",
            "images": ["/uploads/photo1.jpg"],
        },
        headers=_auth(citizen_token),
    )
    assert resp.status_code == status.HTTP_201_CREATED, resp.text
    data = resp.json()
    assert data["title"] == "Cleaned Roadway"
    assert data["images"] == ["/uploads/photo1.jpg"]


def test_create_post_max_images_validation(client: TestClient, db_session: Session):
    """Posting more than 3 images triggers a 422 validation error."""
    citizen_token = _register_and_login(
        db_session, client, "four_images_citizen@example.com", UserRole.CITIZEN
    )
    resp = client.post(
        "/api/v1/transparency",
        json={
            "title": "Too Many Images",
            "description": "Attempting 4 images",
            "images": ["/1.jpg", "/2.jpg", "/3.jpg", "/4.jpg"],
        },
        headers=_auth(citizen_token),
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
