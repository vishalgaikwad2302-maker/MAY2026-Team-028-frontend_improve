"""Authentication API routes: register, login, refresh, profile, and role-protected endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_role
from app.models.user import User, UserRole
from app.schemas.auth import LoginRequest, RefreshTokenRequest, Token
from app.schemas.user import UserCreate, UserRead
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new citizen account",
)
def register(user_in: UserCreate, db: Session = Depends(get_db)) -> User:
    """Register a new citizen account.

    Public self-registration is restricted to Citizens only.
    Crew members are onboarded and provisioned directly by Administrators
    via the operational management portal.
    """
    safe_user = user_in.model_copy(update={"role": UserRole.CITIZEN})
    return AuthService.register_user(db, safe_user)


@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user and issue JWT access and refresh tokens",
)
def login(login_data: LoginRequest, db: Session = Depends(get_db)) -> Token:
    """Authenticate user with email and password."""
    return AuthService.authenticate_user(db, login_data)


@router.post(
    "/refresh",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token using valid refresh token",
)
def refresh_token(req: RefreshTokenRequest, db: Session = Depends(get_db)) -> Token:
    """Issue new token pair using a valid refresh token."""
    return AuthService.refresh_token(db, req.refresh_token)


@router.get(
    "/me",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Get profile of current logged-in user",
)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Return currently authenticated user details."""
    return current_user


@router.get(
    "/admin-only",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
    summary="Admin-restricted endpoint for role authorization checks",
)
def admin_only_check() -> dict[str, str]:
    """Endpoint accessible only by Admin role."""
    return {"message": "Admin access granted."}


@router.get(
    "/crew-only",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role(UserRole.CREW, UserRole.ADMIN))],
    summary="Crew and Admin restricted endpoint",
)
def crew_only_check() -> dict[str, str]:
    """Endpoint accessible by Crew and Admin roles."""
    return {"message": "Crew or Admin access granted."}
