"""Unit tests for AuthService logic."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.exceptions import AuthenticationError, ConflictError
from app.db.base import Base
from app.models.user import UserRole
from app.schemas.auth import LoginRequest
from app.schemas.user import UserCreate
from app.services.auth_service import AuthService


@pytest.fixture
def db_session():
    """Create an isolated in-memory SQLite database session for unit tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_register_user_success(db_session: Session):
    """Verify registering a new citizen user."""
    user_in = UserCreate(
        email="citizen@example.com",
        password="password123",
        full_name="Jane Doe",
        role=UserRole.CITIZEN,
    )
    user = AuthService.register_user(db_session, user_in)
    assert user.id is not None
    assert user.email == "citizen@example.com"
    assert user.role == "citizen"


# NOTE: AuthService.register_user is intentionally a generic, role-aware
# helper (see test_rbac_role_permissions in test_auth_routes.py, which
# relies on it to seed an admin fixture directly). The guarantee that public
# self-registration can't grant elevated roles is enforced at the route
# layer (POST /auth/register forces role=citizen before calling this
# service) and is covered by
# test_register_endpoint_rejects_client_supplied_admin_role in
# tests/api/test_auth_routes.py — not here.


def test_register_duplicate_email_raises_conflict(db_session: Session):
    """Verify registering duplicate email raises ConflictError."""
    user_in = UserCreate(
        email="duplicate@example.com",
        password="password123",
        full_name="Original User",
    )
    AuthService.register_user(db_session, user_in)

    with pytest.raises(ConflictError):
        AuthService.register_user(db_session, user_in)


def test_authenticate_user_success(db_session: Session):
    """Verify authenticating valid credentials returns tokens."""
    user_in = UserCreate(
        email="auth@example.com",
        password="correct_password",
        full_name="Auth User",
    )
    AuthService.register_user(db_session, user_in)

    tokens = AuthService.authenticate_user(
        db_session, LoginRequest(email="auth@example.com", password="correct_password")
    )
    assert tokens.access_token is not None
    assert tokens.refresh_token is not None
    assert tokens.token_type == "bearer"


def test_authenticate_invalid_password_raises_error(db_session: Session):
    """Verify authenticating invalid password raises AuthenticationError."""
    user_in = UserCreate(
        email="auth2@example.com",
        password="correct_password",
        full_name="Auth User 2",
    )
    AuthService.register_user(db_session, user_in)

    with pytest.raises(AuthenticationError):
        AuthService.authenticate_user(
            db_session, LoginRequest(email="auth2@example.com", password="wrong_password")
        )


def test_refresh_token_success(db_session: Session):
    """Verify refreshing token using valid refresh_token."""
    user_in = UserCreate(
        email="refresh@example.com",
        password="password123",
        full_name="Refresh User",
    )
    AuthService.register_user(db_session, user_in)

    tokens = AuthService.authenticate_user(
        db_session, LoginRequest(email="refresh@example.com", password="password123")
    )
    new_tokens = AuthService.refresh_token(db_session, tokens.refresh_token)
    assert new_tokens.access_token is not None
    assert new_tokens.refresh_token is not None
