"""API integration tests for reports endpoints."""

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import UserRole
from app.schemas.auth import LoginRequest
from app.schemas.user import UserCreate
from app.services.auth_service import AuthService


def _register_and_login(db: Session, client: TestClient, email: str, role: UserRole) -> str:
    AuthService.register_user(
        db,
        UserCreate(email=email, password="password123", full_name="Report User", role=role),
    )
    tokens = AuthService.authenticate_user(db, LoginRequest(email=email, password="password123"))
    return tokens.access_token


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# GET /reports/trends
# ---------------------------------------------------------------------------


def test_get_report_trends_happy_path(client: TestClient, db_session: Session):
    """Happy Path: GET /reports/trends returns status, hazard, and time series breakdown."""
    token = _register_and_login(db_session, client, "rep_trends@example.com", UserRole.ADMIN)

    # Create complaints to populate trends
    client.post(
        "/api/v1/complaints",
        json={"location": "Street A", "description": "Waste on road", "hazard": "Risk to Children"},
        headers=_auth(token),
    )
    client.post(
        "/api/v1/complaints",
        json={"location": "Street B", "description": "Foul smell", "hazard": "Mosquito Breeding"},
        headers=_auth(token),
    )

    resp = client.get("/api/v1/reports/trends", headers=_auth(token))
    assert resp.status_code == status.HTTP_200_OK, resp.text
    data = resp.json()
    assert "totals" in data
    assert "status_breakdown" in data
    assert "hazard_breakdown" in data
    assert "time_series" in data
    assert data["totals"]["total"] == 2
    assert data["totals"]["pending"] == 2


def test_get_report_trends_requires_auth(client: TestClient):
    """Auth Failure: GET /reports/trends without token returns 401."""
    resp = client.get("/api/v1/reports/trends")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# GET /reports/performance
# ---------------------------------------------------------------------------


def test_get_report_performance_happy_path(client: TestClient, db_session: Session):
    """Happy Path: GET /reports/performance returns average resolution days, ward & crew performance."""
    token = _register_and_login(db_session, client, "rep_perf@example.com", UserRole.ADMIN)

    resp = client.get("/api/v1/reports/performance", headers=_auth(token))
    assert resp.status_code == status.HTTP_200_OK, resp.text
    data = resp.json()
    assert "avg_resolution_days" in data
    assert "total_resolved" in data
    assert "ward_performance" in data
    assert "crew_performance" in data
    assert isinstance(data["ward_performance"], list)
    assert isinstance(data["crew_performance"], list)


def test_get_report_performance_requires_auth(client: TestClient):
    """Auth Failure: GET /reports/performance without token returns 401."""
    resp = client.get("/api/v1/reports/performance")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# GET /reports/public
# ---------------------------------------------------------------------------


def test_get_public_report_stats_happy_path(client: TestClient):
    """Happy Path: GET /reports/public returns public high-level cleanup stats without auth."""
    resp = client.get("/api/v1/reports/public")
    assert resp.status_code == status.HTTP_200_OK, resp.text
    data = resp.json()
    assert "total_complaints" in data
    assert "resolved_complaints" in data
    assert "active_complaints" in data
    assert "resolution_rate" in data
    assert "avg_resolution_days" in data
    assert "total_cleanups_completed" in data
    assert "top_wards" in data
    assert isinstance(data["top_wards"], list)


