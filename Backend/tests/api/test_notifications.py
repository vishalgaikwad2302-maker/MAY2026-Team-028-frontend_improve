"""API integration tests for notification routes (S2-F02, US-06/US-23)."""

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


def _create_complaint(
    client: TestClient,
    token: str,
    location: str = "Test Street",
    description: str = "Garbage left on road.",
    hazard: str = "Risk to Children",
) -> int:
    resp = client.post(
        "/api/v1/complaints",
        json={
            "location": location,
            "description": description,
            "hazard": hazard,
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


# ---------------------------------------------------------------------------
# GET /notifications, and the complaint_resolved auto-notify hook
# ---------------------------------------------------------------------------


def test_list_notifications_happy_path(client: TestClient, db_session: Session):
    """Happy Path: resolving a complaint auto-creates a notification the reporter can list."""
    citizen_token = _register_and_login(
        db_session, client, "notif_citizen@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(db_session, client, "notif_admin@example.com", UserRole.ADMIN)
    complaint_id = _create_complaint(client, citizen_token)
    _resolve_complaint(client, admin_token, complaint_id)

    resp = client.get("/api/v1/notifications", headers=_auth(citizen_token))
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["meta"]["total"] == 1
    assert data["items"][0]["type"] == "complaint_resolved"
    assert data["items"][0]["related_complaint_id"] == complaint_id
    assert data["items"][0]["is_read"] is False


def test_list_notifications_requires_auth(client: TestClient):
    """Validation/Auth Failure: GET without a token returns 401."""
    resp = client.get("/api/v1/notifications")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_list_notifications_scoped_to_user(client: TestClient, db_session: Session):
    """Auth/RBAC: a user only sees their own notifications, never someone else's."""
    citizen_token = _register_and_login(
        db_session, client, "notif_owner@example.com", UserRole.CITIZEN
    )
    other_token = _register_and_login(
        db_session, client, "notif_other@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(
        db_session, client, "notif_admin2@example.com", UserRole.ADMIN
    )
    complaint_id = _create_complaint(client, citizen_token)
    _resolve_complaint(client, admin_token, complaint_id)

    resp = client.get("/api/v1/notifications", headers=_auth(other_token))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["meta"]["total"] == 0


def test_list_notifications_edge_case_unread_only(client: TestClient, db_session: Session):
    """Edge Case: unread_only filter excludes a notification after it is marked read."""
    citizen_token = _register_and_login(
        db_session, client, "notif_unread@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(
        db_session, client, "notif_admin3@example.com", UserRole.ADMIN
    )
    complaint_id = _create_complaint(client, citizen_token)
    _resolve_complaint(client, admin_token, complaint_id)

    listed = client.get("/api/v1/notifications", headers=_auth(citizen_token)).json()
    notification_id = listed["items"][0]["id"]
    client.patch(f"/api/v1/notifications/{notification_id}/read", headers=_auth(citizen_token))

    resp = client.get("/api/v1/notifications?unread_only=true", headers=_auth(citizen_token))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["meta"]["total"] == 0


def test_list_notifications_pagination(client: TestClient, db_session: Session):
    """Happy Path: GET /notifications supports page and page_size parameters."""
    citizen_token = _register_and_login(
        db_session, client, "notif_page@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(
        db_session, client, "notif_admin_page@example.com", UserRole.ADMIN
    )
    c1 = _create_complaint(
        client,
        citizen_token,
        location="Alpha North Road",
        description="Broken street lamp post near park.",
    )
    c2 = _create_complaint(
        client,
        citizen_token,
        location="Beta South Avenue",
        description="Water pipe leakage beside bus stop.",
    )
    _resolve_complaint(client, admin_token, c1)
    _resolve_complaint(client, admin_token, c2)

    resp = client.get("/api/v1/notifications?page=1&page_size=1", headers=_auth(citizen_token))
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["meta"]["total"] == 2
    assert data["meta"]["page"] == 1
    assert data["meta"]["page_size"] == 1
    assert data["meta"]["total_pages"] == 2



# ---------------------------------------------------------------------------
# PATCH /notifications/{id}/read
# ---------------------------------------------------------------------------


def test_mark_notification_read_happy_path(client: TestClient, db_session: Session):
    """Happy Path: owner marks their notification read."""
    citizen_token = _register_and_login(
        db_session, client, "notif_read@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(
        db_session, client, "notif_admin4@example.com", UserRole.ADMIN
    )
    complaint_id = _create_complaint(client, citizen_token)
    _resolve_complaint(client, admin_token, complaint_id)
    notification_id = client.get("/api/v1/notifications", headers=_auth(citizen_token)).json()[
        "items"
    ][0]["id"]

    resp = client.patch(
        f"/api/v1/notifications/{notification_id}/read", headers=_auth(citizen_token)
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["is_read"] is True
    assert data["read_at"] is not None


def test_mark_notification_read_validation_failure(client: TestClient, db_session: Session):
    """Validation Failure: non-integer notification id returns 422."""
    citizen_token = _register_and_login(
        db_session, client, "notif_read_val@example.com", UserRole.CITIZEN
    )
    resp = client.patch("/api/v1/notifications/not-an-id/read", headers=_auth(citizen_token))
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_mark_notification_read_rbac_failure(client: TestClient, db_session: Session):
    """Auth/RBAC Failure: a different user cannot mark someone else's notification read."""
    citizen_token = _register_and_login(
        db_session, client, "notif_read_owner@example.com", UserRole.CITIZEN
    )
    other_token = _register_and_login(
        db_session, client, "notif_read_other@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(
        db_session, client, "notif_admin5@example.com", UserRole.ADMIN
    )
    complaint_id = _create_complaint(client, citizen_token)
    _resolve_complaint(client, admin_token, complaint_id)
    notification_id = client.get("/api/v1/notifications", headers=_auth(citizen_token)).json()[
        "items"
    ][0]["id"]

    resp = client.patch(f"/api/v1/notifications/{notification_id}/read", headers=_auth(other_token))
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_mark_notification_read_edge_case_idempotent(client: TestClient, db_session: Session):
    """Edge Case: marking an already-read notification read again returns 200 idempotently."""
    citizen_token = _register_and_login(
        db_session, client, "notif_read_idem@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(
        db_session, client, "notif_admin6@example.com", UserRole.ADMIN
    )
    complaint_id = _create_complaint(client, citizen_token)
    _resolve_complaint(client, admin_token, complaint_id)
    notification_id = client.get("/api/v1/notifications", headers=_auth(citizen_token)).json()[
        "items"
    ][0]["id"]

    client.patch(f"/api/v1/notifications/{notification_id}/read", headers=_auth(citizen_token))
    resp = client.patch(
        f"/api/v1/notifications/{notification_id}/read", headers=_auth(citizen_token)
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["is_read"] is True


def test_mark_notification_read_edge_case_not_found(client: TestClient, db_session: Session):
    """Edge Case: marking a non-existent notification returns 404."""
    citizen_token = _register_and_login(
        db_session, client, "notif_read_404@example.com", UserRole.CITIZEN
    )
    resp = client.patch("/api/v1/notifications/999999/read", headers=_auth(citizen_token))
    assert resp.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# POST /notifications/read-all
# ---------------------------------------------------------------------------


def test_mark_all_notifications_read_happy_path(client: TestClient, db_session: Session):
    """Happy Path: mark-all-read flips every unread notification for the caller.

    Uses distinct complaint content so no duplicate_detected notification is
    emitted alongside the resolved ones, keeping the expected count at exactly 2.
    """
    citizen_token = _register_and_login(
        db_session, client, "notif_all@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(
        db_session, client, "notif_admin7@example.com", UserRole.ADMIN
    )
    for loc, desc in [
        ("Unique Alpha Street 1111", "Alpha issue one."),
        ("Unique Beta Avenue 2222", "Beta issue two."),
    ]:
        resp = client.post(
            "/api/v1/complaints",
            json={"location": loc, "description": desc, "hazard": "Risk to Children"},
            headers=_auth(citizen_token),
        )
        assert resp.status_code == status.HTTP_201_CREATED, resp.text
        _resolve_complaint(client, admin_token, resp.json()["id"])

    resp = client.post("/api/v1/notifications/read-all", headers=_auth(citizen_token))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["marked"] == 2

    listed = client.get("/api/v1/notifications?unread_only=true", headers=_auth(citizen_token))
    assert listed.json()["meta"]["total"] == 0


def test_mark_all_notifications_read_requires_auth(client: TestClient):
    """Validation/Auth Failure: mark-all-read without a token returns 401."""
    resp = client.post("/api/v1/notifications/read-all")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_mark_all_notifications_read_edge_case_empty(client: TestClient, db_session: Session):
    """Edge Case: mark-all-read with zero notifications returns marked=0."""
    citizen_token = _register_and_login(
        db_session, client, "notif_all_empty@example.com", UserRole.CITIZEN
    )
    resp = client.post("/api/v1/notifications/read-all", headers=_auth(citizen_token))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["marked"] == 0


# ---------------------------------------------------------------------------
# S2-A05: duplicate_detected notification emitter
# ---------------------------------------------------------------------------


def test_duplicate_detected_notification_emitted_on_duplicate_complaint(
    client: TestClient, db_session: Session
):
    """Happy Path: submitting a complaint that matches an existing one emits a
    duplicate_detected notification for the submitter."""
    citizen_token = _register_and_login(
        db_session, client, "dup_citizen@example.com", UserRole.CITIZEN
    )
    # First complaint — becomes the existing record.
    _create_complaint(client, citizen_token)

    # Second complaint with identical content — should trigger duplicate detection.
    resp = client.post(
        "/api/v1/complaints",
        json={
            "location": "Test Street",
            "description": "Garbage left on road.",
            "hazard": "Risk to Children",
        },
        headers=_auth(citizen_token),
    )
    assert resp.status_code == status.HTTP_201_CREATED

    notifs = client.get("/api/v1/notifications", headers=_auth(citizen_token)).json()
    dup_notifs = [n for n in notifs["items"] if n["type"] == "duplicate_detected"]
    assert len(dup_notifs) >= 1, "Expected at least one duplicate_detected notification"
    assert dup_notifs[0]["is_read"] is False
    assert dup_notifs[0]["related_complaint_id"] == resp.json()["id"]


def test_duplicate_detected_notification_not_emitted_for_unique_complaint(
    client: TestClient, db_session: Session
):
    """Edge Case: a complaint with no matching records does NOT emit a
    duplicate_detected notification."""
    citizen_token = _register_and_login(
        db_session, client, "uniq_citizen@example.com", UserRole.CITIZEN
    )
    client.post(
        "/api/v1/complaints",
        json={
            "location": "Completely Unique Zebra Lane 99999",
            "description": "Totally unique issue that matches nothing.",
            "hazard": "Risk to Children",
        },
        headers=_auth(citizen_token),
    )

    notifs = client.get("/api/v1/notifications", headers=_auth(citizen_token)).json()
    dup_notifs = [n for n in notifs["items"] if n["type"] == "duplicate_detected"]
    assert len(dup_notifs) == 0, "Unexpected duplicate_detected notification for a unique complaint"
