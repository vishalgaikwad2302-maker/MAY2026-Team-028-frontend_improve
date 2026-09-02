"""API integration tests for complaint feedback routes (S2-F02, US-24)."""

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


# ---------------------------------------------------------------------------
# POST /complaints/{id}/feedback
# ---------------------------------------------------------------------------


def test_submit_feedback_happy_path(client: TestClient, db_session: Session):
    """Happy Path: reporter submits feedback on their own resolved complaint."""
    citizen_token = _register_and_login(
        db_session, client, "fb_citizen@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(db_session, client, "fb_admin@example.com", UserRole.ADMIN)
    complaint_id = _create_complaint(client, citizen_token)
    _resolve_complaint(client, admin_token, complaint_id)

    resp = client.post(
        f"/api/v1/complaints/{complaint_id}/feedback",
        json={"rating": 5, "comment": "Great job!"},
        headers=_auth(citizen_token),
    )
    assert resp.status_code == status.HTTP_201_CREATED, resp.text
    data = resp.json()
    assert data["rating"] == 5
    assert data["comment"] == "Great job!"
    assert data["complaint_id"] == complaint_id


def test_submit_feedback_validation_failure(client: TestClient, db_session: Session):
    """Validation Failure: rating outside 1-5 returns 422."""
    citizen_token = _register_and_login(
        db_session, client, "fb_citizen_val@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(
        db_session, client, "fb_admin_val@example.com", UserRole.ADMIN
    )
    complaint_id = _create_complaint(client, citizen_token)
    _resolve_complaint(client, admin_token, complaint_id)

    resp = client.post(
        f"/api/v1/complaints/{complaint_id}/feedback",
        json={"rating": 7},
        headers=_auth(citizen_token),
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_submit_feedback_rbac_failure(client: TestClient, db_session: Session):
    """Auth/RBAC Failure: a different citizen cannot leave feedback on someone else's complaint."""
    owner_token = _register_and_login(db_session, client, "fb_owner@example.com", UserRole.CITIZEN)
    other_token = _register_and_login(db_session, client, "fb_other@example.com", UserRole.CITIZEN)
    admin_token = _register_and_login(
        db_session, client, "fb_admin_rbac@example.com", UserRole.ADMIN
    )
    complaint_id = _create_complaint(client, owner_token)
    _resolve_complaint(client, admin_token, complaint_id)

    resp = client.post(
        f"/api/v1/complaints/{complaint_id}/feedback",
        json={"rating": 3},
        headers=_auth(other_token),
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN
    assert resp.json()["error"]["code"] == "PERMISSION_DENIED"


def test_submit_feedback_edge_case_not_resolved(client: TestClient, db_session: Session):
    """Edge Case: feedback on a still-pending complaint returns 409 Conflict."""
    citizen_token = _register_and_login(
        db_session, client, "fb_pending@example.com", UserRole.CITIZEN
    )
    complaint_id = _create_complaint(client, citizen_token)

    resp = client.post(
        f"/api/v1/complaints/{complaint_id}/feedback",
        json={"rating": 4},
        headers=_auth(citizen_token),
    )
    assert resp.status_code == status.HTTP_409_CONFLICT
    assert resp.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


def test_submit_feedback_edge_case_duplicate(client: TestClient, db_session: Session):
    """Edge Case: a second feedback submission for the same complaint returns 409 Conflict."""
    citizen_token = _register_and_login(db_session, client, "fb_dup@example.com", UserRole.CITIZEN)
    admin_token = _register_and_login(
        db_session, client, "fb_dup_admin@example.com", UserRole.ADMIN
    )
    complaint_id = _create_complaint(client, citizen_token)
    _resolve_complaint(client, admin_token, complaint_id)

    first = client.post(
        f"/api/v1/complaints/{complaint_id}/feedback",
        json={"rating": 5},
        headers=_auth(citizen_token),
    )
    assert first.status_code == status.HTTP_201_CREATED

    second = client.post(
        f"/api/v1/complaints/{complaint_id}/feedback",
        json={"rating": 2},
        headers=_auth(citizen_token),
    )
    assert second.status_code == status.HTTP_409_CONFLICT
    assert second.json()["error"]["code"] == "CONFLICT"


def test_submit_feedback_closed_complaint(client: TestClient, db_session: Session):
    """Happy Path: feedback can be submitted on a closed complaint."""
    citizen_token = _register_and_login(
        db_session, client, "fb_closed_citizen@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(
        db_session, client, "fb_closed_admin@example.com", UserRole.ADMIN
    )
    complaint_id = _create_complaint(client, citizen_token)

    # Close complaint via admin/supervisor close
    client.patch(f"/api/v1/complaints/{complaint_id}/close", headers=_auth(admin_token))

    resp = client.post(
        f"/api/v1/complaints/{complaint_id}/feedback",
        json={"rating": 4, "comment": "Good job closing it!"},
        headers=_auth(citizen_token),
    )
    assert resp.status_code == status.HTTP_201_CREATED, resp.text
    assert resp.json()["rating"] == 4



# ---------------------------------------------------------------------------
# GET /complaints/{id}/feedback
# ---------------------------------------------------------------------------


def test_get_feedback_happy_path(client: TestClient, db_session: Session):
    """Happy Path: reporter (or crew/admin) can read submitted feedback."""
    citizen_token = _register_and_login(db_session, client, "fb_get@example.com", UserRole.CITIZEN)
    admin_token = _register_and_login(
        db_session, client, "fb_get_admin@example.com", UserRole.ADMIN
    )
    complaint_id = _create_complaint(client, citizen_token)
    _resolve_complaint(client, admin_token, complaint_id)
    client.post(
        f"/api/v1/complaints/{complaint_id}/feedback",
        json={"rating": 4, "comment": "Good"},
        headers=_auth(citizen_token),
    )

    resp = client.get(f"/api/v1/complaints/{complaint_id}/feedback", headers=_auth(admin_token))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["rating"] == 4


def test_get_feedback_requires_auth(client: TestClient, db_session: Session):
    """Validation/Auth Failure: GET without a token returns 401."""
    citizen_token = _register_and_login(
        db_session, client, "fb_get_noauth@example.com", UserRole.CITIZEN
    )
    complaint_id = _create_complaint(client, citizen_token)

    resp = client.get(f"/api/v1/complaints/{complaint_id}/feedback")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_feedback_rbac_failure(client: TestClient, db_session: Session):
    """Auth/RBAC Failure: a different citizen cannot read someone else's feedback."""
    owner_token = _register_and_login(
        db_session, client, "fb_get_owner@example.com", UserRole.CITIZEN
    )
    other_token = _register_and_login(
        db_session, client, "fb_get_other@example.com", UserRole.CITIZEN
    )
    complaint_id = _create_complaint(client, owner_token)

    resp = client.get(f"/api/v1/complaints/{complaint_id}/feedback", headers=_auth(other_token))
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_get_feedback_edge_case_not_found(client: TestClient, db_session: Session):
    """Edge Case: no feedback submitted yet returns 404 Not Found."""
    citizen_token = _register_and_login(
        db_session, client, "fb_get_404@example.com", UserRole.CITIZEN
    )
    complaint_id = _create_complaint(client, citizen_token)

    resp = client.get(f"/api/v1/complaints/{complaint_id}/feedback", headers=_auth(citizen_token))
    assert resp.status_code == status.HTTP_404_NOT_FOUND
    assert resp.json()["error"]["code"] == "NOT_FOUND"
