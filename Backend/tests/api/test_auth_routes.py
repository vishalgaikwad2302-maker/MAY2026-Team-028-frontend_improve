"""API integration tests for authentication endpoints and RBAC."""

from fastapi import status
from fastapi.testclient import TestClient

from app.models.user import UserRole
from app.schemas.auth import LoginRequest
from app.schemas.user import UserCreate
from app.services.auth_service import AuthService


def test_register_endpoint(client: TestClient):
    """Test citizen registration endpoint."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "api_citizen@example.com",
            "password": "securepassword123",
            "full_name": "API Citizen",
            "role": "citizen",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == "api_citizen@example.com"
    assert data["role"] == "citizen"
    assert "id" in data


def test_register_endpoint_rejects_client_supplied_admin_role(client: TestClient):
    """POST /auth/register must not let an anonymous caller self-elevate.

    Regression test for the privilege-escalation bug where the public
    registration endpoint trusted a client-supplied `role` field, letting
    anyone create an admin (or crew) account with no authentication at all.
    """
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "attacker@example.com",
            "password": "securepassword123",
            "full_name": "Definitely Not An Admin",
            "role": "admin",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["role"] == "citizen"

    # And the token that results from logging into this account should
    # only ever carry citizen-level access.
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "attacker@example.com", "password": "securepassword123"},
    )
    assert login_resp.status_code == status.HTTP_200_OK
    access_token = login_resp.json()["access_token"]

    admin_check = client.get(
        "/api/v1/auth/admin-only",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert admin_check.status_code == status.HTTP_403_FORBIDDEN


def test_login_and_get_me_flow(client: TestClient):
    """Test full login flow and fetching /auth/me profile."""
    # 1. Register
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "flow_user@example.com",
            "password": "flowpassword123",
            "full_name": "Flow User",
            "role": "citizen",
        },
    )

    # 2. Login
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "flow_user@example.com", "password": "flowpassword123"},
    )
    assert login_resp.status_code == status.HTTP_200_OK
    tokens = login_resp.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    # 3. Access /auth/me without token -> 401
    unauth_resp = client.get("/api/v1/auth/me")
    assert unauth_resp.status_code == status.HTTP_401_UNAUTHORIZED
    assert unauth_resp.json()["error"]["code"] == "UNAUTHENTICATED"

    # 4. Access /auth/me with Bearer token -> 200
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    me_resp = client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == status.HTTP_200_OK
    me_data = me_resp.json()
    assert me_data["email"] == "flow_user@example.com"


def test_token_refresh_flow(client: TestClient):
    """Test token refresh endpoint."""
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "refresh_flow@example.com",
            "password": "password123",
            "full_name": "Refresh User",
        },
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "refresh_flow@example.com", "password": "password123"},
    )
    refresh_token = login_resp.json()["refresh_token"]

    refresh_resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == status.HTTP_200_OK
    new_tokens = refresh_resp.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens


def test_rbac_role_permissions(client: TestClient, db_session):
    """Test Role-Based Access Control (RBAC) permissions."""
    # Create Citizen and Admin users directly
    AuthService.register_user(
        db_session,
        UserCreate(
            email="role_citizen@example.com",
            password="password123",
            full_name="Role Citizen",
            role=UserRole.CITIZEN,
        ),
    )
    AuthService.register_user(
        db_session,
        UserCreate(
            email="role_admin@example.com",
            password="password123",
            full_name="Role Admin",
            role=UserRole.ADMIN,
        ),
    )

    citizen_tokens = AuthService.authenticate_user(
        db_session,
        LoginRequest(email="role_citizen@example.com", password="password123"),
    )
    admin_tokens = AuthService.authenticate_user(
        db_session,
        LoginRequest(email="role_admin@example.com", password="password123"),
    )

    citizen_headers = {"Authorization": f"Bearer {citizen_tokens.access_token}"}
    admin_headers = {"Authorization": f"Bearer {admin_tokens.access_token}"}

    # Citizen trying to access admin endpoint -> 403 Forbidden
    res_forbidden = client.get("/api/v1/auth/admin-only", headers=citizen_headers)
    assert res_forbidden.status_code == status.HTTP_403_FORBIDDEN
    assert res_forbidden.json()["error"]["code"] == "PERMISSION_DENIED"

    # Admin accessing admin endpoint -> 200 OK
    res_allowed = client.get("/api/v1/auth/admin-only", headers=admin_headers)
    assert res_allowed.status_code == status.HTTP_200_OK
    assert res_allowed.json()["message"] == "Admin access granted."
