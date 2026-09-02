"""API integration tests for ward collection schedule routes (S2-F04, US-32/US-33)."""

from datetime import date, timedelta

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


def _create_weekly_row(
    client: TestClient, admin_token: str, ward_id: int = 1, day_of_week: int = 2
) -> int:
    resp = client.post(
        "/api/v1/schedule",
        json={
            "ward_id": ward_id,
            "frequency": "weekly",
            "day_of_week": day_of_week,
            "time_slot": "Morning",
        },
        headers=_auth(admin_token),
    )
    assert resp.status_code == status.HTTP_201_CREATED, resp.text
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# POST /schedule
# ---------------------------------------------------------------------------


def test_create_schedule_happy_path(client: TestClient, db_session: Session):
    """Happy Path: admin creates a weekly schedule row for a ward."""
    admin_token = _register_and_login(db_session, client, "sched_admin@example.com", UserRole.ADMIN)
    resp = client.post(
        "/api/v1/schedule",
        json={"ward_id": 1, "frequency": "weekly", "day_of_week": 1, "time_slot": "Morning"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == status.HTTP_201_CREATED, resp.text
    assert resp.json()["day_of_week"] == 1


def test_create_schedule_validation_failure(client: TestClient, db_session: Session):
    """Validation Failure: a regular row missing day_of_week returns 422."""
    admin_token = _register_and_login(
        db_session, client, "sched_admin_val@example.com", UserRole.ADMIN
    )
    resp = client.post(
        "/api/v1/schedule", json={"ward_id": 1, "frequency": "weekly"}, headers=_auth(admin_token)
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_schedule_rbac_failure(client: TestClient, db_session: Session):
    """Auth/RBAC Failure: crew cannot create a schedule row (admin only)."""
    crew_token = _register_and_login(db_session, client, "sched_crew@example.com", UserRole.CREW)
    resp = client.post(
        "/api/v1/schedule",
        json={"ward_id": 1, "frequency": "weekly", "day_of_week": 1},
        headers=_auth(crew_token),
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_create_schedule_edge_case_exception_row(client: TestClient, db_session: Session):
    """Edge Case: an exception row requires exception_date, not day_of_week."""
    admin_token = _register_and_login(
        db_session, client, "sched_exc_admin@example.com", UserRole.ADMIN
    )
    resp = client.post(
        "/api/v1/schedule",
        json={
            "ward_id": 1,
            "is_exception": True,
            "exception_date": "2026-08-15",
            "notes": "Holiday shift",
        },
        headers=_auth(admin_token),
    )
    assert resp.status_code == status.HTTP_201_CREATED, resp.text
    assert resp.json()["is_exception"] is True
    assert resp.json()["exception_date"] == "2026-08-15"


# ---------------------------------------------------------------------------
# GET /schedule
# ---------------------------------------------------------------------------


def test_get_ward_schedule_happy_path(client: TestClient, db_session: Session):
    """Happy Path: any authenticated user can read a ward's schedule."""
    admin_token = _register_and_login(
        db_session, client, "sched_get_admin@example.com", UserRole.ADMIN
    )
    citizen_token = _register_and_login(
        db_session, client, "sched_get_citizen@example.com", UserRole.CITIZEN
    )
    _create_weekly_row(client, admin_token, ward_id=2)

    resp = client.get("/api/v1/schedule?ward_id=2", headers=_auth(citizen_token))
    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.json()) == 1


def test_get_ward_schedule_requires_auth(client: TestClient):
    """Validation/Auth Failure: GET without a token returns 401."""
    resp = client.get("/api/v1/schedule?ward_id=1")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_ward_schedule_validation_failure(client: TestClient, db_session: Session):
    """Validation Failure: missing required ward_id query param returns 422."""
    citizen_token = _register_and_login(
        db_session, client, "sched_get_val@example.com", UserRole.CITIZEN
    )
    resp = client.get("/api/v1/schedule", headers=_auth(citizen_token))
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_get_ward_schedule_edge_case_empty(client: TestClient, db_session: Session):
    """Edge Case: a ward with no schedule rows returns an empty list."""
    citizen_token = _register_and_login(
        db_session, client, "sched_get_empty@example.com", UserRole.CITIZEN
    )
    resp = client.get("/api/v1/schedule?ward_id=999", headers=_auth(citizen_token))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == []


# ---------------------------------------------------------------------------
# GET /schedule/reminders
# ---------------------------------------------------------------------------


def test_get_reminders_happy_path(client: TestClient, db_session: Session):
    """Happy Path: reminders compute the next occurrence of the ward's weekly slot."""
    admin_token = _register_and_login(
        db_session, client, "sched_rem_admin@example.com", UserRole.ADMIN
    )
    citizen_token = _register_and_login(
        db_session, client, "sched_rem_citizen@example.com", UserRole.CITIZEN
    )
    target_dow = 3
    _create_weekly_row(client, admin_token, ward_id=3, day_of_week=target_dow)

    resp = client.get("/api/v1/schedule/reminders?ward_id=3", headers=_auth(citizen_token))
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert len(data) == 1
    occurrence = date.fromisoformat(data[0]["occurrence_date"])
    assert occurrence.weekday() == target_dow
    assert occurrence >= date.today()
    assert occurrence < date.today() + timedelta(days=7)


def test_get_reminders_requires_auth(client: TestClient):
    """Validation/Auth Failure: reminders without a token returns 401."""
    resp = client.get("/api/v1/schedule/reminders?ward_id=1")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_reminders_edge_case_monthly(client: TestClient, db_session: Session):
    """Edge Case: a monthly row (hazardous-waste style) computes an nth-weekday occurrence."""
    admin_token = _register_and_login(
        db_session, client, "sched_rem_monthly_admin@example.com", UserRole.ADMIN
    )
    citizen_token = _register_and_login(
        db_session, client, "sched_rem_monthly_citizen@example.com", UserRole.CITIZEN
    )
    resp = client.post(
        "/api/v1/schedule",
        json={
            "ward_id": 4,
            "frequency": "monthly",
            "day_of_week": 5,
            "week_of_month": 0,
            "time_slot": "Morning",
        },
        headers=_auth(admin_token),
    )
    assert resp.status_code == status.HTTP_201_CREATED, resp.text

    reminders = client.get("/api/v1/schedule/reminders?ward_id=4", headers=_auth(citizen_token))
    assert reminders.status_code == status.HTTP_200_OK
    data = reminders.json()
    assert len(data) == 1
    occurrence = date.fromisoformat(data[0]["occurrence_date"])
    assert occurrence.weekday() == 5
    assert occurrence >= date.today()


def test_get_reminders_edge_case_empty(client: TestClient, db_session: Session):
    """Edge Case: a ward with no schedule rows returns no reminders."""
    citizen_token = _register_and_login(
        db_session, client, "sched_rem_empty@example.com", UserRole.CITIZEN
    )
    resp = client.get("/api/v1/schedule/reminders?ward_id=999", headers=_auth(citizen_token))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == []


# ---------------------------------------------------------------------------
# PATCH /schedule/{id}
# ---------------------------------------------------------------------------


def test_update_schedule_happy_path(client: TestClient, db_session: Session):
    """Happy Path: admin edits an existing schedule row's time slot."""
    admin_token = _register_and_login(
        db_session, client, "sched_upd_admin@example.com", UserRole.ADMIN
    )
    schedule_id = _create_weekly_row(client, admin_token)

    resp = client.patch(
        f"/api/v1/schedule/{schedule_id}", json={"time_slot": "Evening"}, headers=_auth(admin_token)
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["time_slot"] == "Evening"


def test_update_schedule_validation_failure(client: TestClient, db_session: Session):
    """Validation Failure: day_of_week out of range 0-6 returns 422."""
    admin_token = _register_and_login(
        db_session, client, "sched_upd_val_admin@example.com", UserRole.ADMIN
    )
    schedule_id = _create_weekly_row(client, admin_token)

    resp = client.patch(
        f"/api/v1/schedule/{schedule_id}", json={"day_of_week": 9}, headers=_auth(admin_token)
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_update_schedule_rbac_failure(client: TestClient, db_session: Session):
    """Auth/RBAC Failure: crew cannot edit a schedule row (admin only)."""
    admin_token = _register_and_login(
        db_session, client, "sched_upd_rbac_admin@example.com", UserRole.ADMIN
    )
    crew_token = _register_and_login(
        db_session, client, "sched_upd_rbac_crew@example.com", UserRole.CREW
    )
    schedule_id = _create_weekly_row(client, admin_token)

    resp = client.patch(
        f"/api/v1/schedule/{schedule_id}", json={"time_slot": "Evening"}, headers=_auth(crew_token)
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_update_schedule_edge_case_not_found(client: TestClient, db_session: Session):
    """Edge Case: updating a non-existent schedule row returns 404."""
    admin_token = _register_and_login(
        db_session, client, "sched_upd_404_admin@example.com", UserRole.ADMIN
    )
    resp = client.patch(
        "/api/v1/schedule/999999", json={"time_slot": "Evening"}, headers=_auth(admin_token)
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# DELETE /schedule/{id}
# ---------------------------------------------------------------------------


def test_delete_schedule_happy_path(client: TestClient, db_session: Session):
    """Happy Path: admin deletes a schedule row."""
    admin_token = _register_and_login(
        db_session, client, "sched_del_admin@example.com", UserRole.ADMIN
    )
    schedule_id = _create_weekly_row(client, admin_token, ward_id=5)

    resp = client.delete(f"/api/v1/schedule/{schedule_id}", headers=_auth(admin_token))
    assert resp.status_code == status.HTTP_204_NO_CONTENT

    listed = client.get("/api/v1/schedule?ward_id=5", headers=_auth(admin_token))
    assert listed.json() == []


def test_delete_schedule_validation_failure(client: TestClient, db_session: Session):
    """Validation Failure: non-integer schedule id returns 422."""
    admin_token = _register_and_login(
        db_session, client, "sched_del_val_admin@example.com", UserRole.ADMIN
    )
    resp = client.delete("/api/v1/schedule/not-an-id", headers=_auth(admin_token))
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_delete_schedule_rbac_failure(client: TestClient, db_session: Session):
    """Auth/RBAC Failure: citizen cannot delete a schedule row."""
    admin_token = _register_and_login(
        db_session, client, "sched_del_rbac_admin@example.com", UserRole.ADMIN
    )
    citizen_token = _register_and_login(
        db_session, client, "sched_del_rbac_citizen@example.com", UserRole.CITIZEN
    )
    schedule_id = _create_weekly_row(client, admin_token)

    resp = client.delete(f"/api/v1/schedule/{schedule_id}", headers=_auth(citizen_token))
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_delete_schedule_edge_case_not_found(client: TestClient, db_session: Session):
    """Edge Case: deleting a non-existent schedule row returns 404."""
    admin_token = _register_and_login(
        db_session, client, "sched_del_404_admin@example.com", UserRole.ADMIN
    )
    resp = client.delete("/api/v1/schedule/999999", headers=_auth(admin_token))
    assert resp.status_code == status.HTTP_404_NOT_FOUND
