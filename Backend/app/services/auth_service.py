"""Authentication service — handles user registration, login, and token refresh."""

from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, Token
from app.schemas.user import UserCreate

__all__ = ["AuthService"]


class AuthService:
    """Business logic for authentication and account management."""

    @staticmethod
    def register_user(db: Session, user_in: UserCreate) -> User:
        """Create a new user account with the role given in `user_in`.

        This is a generic account-creation helper — it honours whatever
        role is passed in. It is NOT safe to call directly from a public,
        unauthenticated endpoint with a client-supplied role; the public
        self-registration route (POST /auth/register) is responsible for
        restricting the role to citizen/crew and forcing anything else
        (e.g. admin) down to citizen before it reaches this method. See
        app/api/v1/routes/auth.py.
        """
        existing = UserRepository.get_by_email(db, user_in.email)
        if existing:
            raise ConflictError("User with this email already exists.")

        hashed_pw = hash_password(user_in.password)
        user = User(
            email=user_in.email.lower().strip(),
            hashed_password=hashed_pw,
            full_name=user_in.full_name,
            role=user_in.role.value if hasattr(user_in.role, "value") else str(user_in.role),
            phone=user_in.phone,
            ward_id=user_in.ward_id,
        )
        return UserRepository.create(db, user)

    @staticmethod
    def authenticate_user(db: Session, login_data: LoginRequest) -> Token:
        """Authenticate user credentials and return JWT tokens."""
        user = UserRepository.get_by_email(db, login_data.email)
        if not user or not verify_password(login_data.password, user.hashed_password):
            raise AuthenticationError("Invalid email or password.")

        if not user.is_active:
            raise AuthenticationError("Inactive user account.")

        access_token = create_access_token(subject=user.id, role=user.role)
        refresh_token = create_refresh_token(subject=user.id, role=user.role)
        return Token(access_token=access_token, refresh_token=refresh_token)

    @staticmethod
    def refresh_token(db: Session, refresh_token_str: str) -> Token:
        """Validate a refresh token and issue a new token pair."""
        payload = decode_token(refresh_token_str)
        if payload.get("type") != "refresh":
            raise AuthenticationError("Invalid token type. Refresh token required.")

        user_id_str = payload.get("sub")
        if not user_id_str or not user_id_str.isdigit():
            raise AuthenticationError("Invalid user subject in token.")

        user = UserRepository.get_by_id(db, int(user_id_str))
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive.")

        access_token = create_access_token(subject=user.id, role=user.role)
        new_refresh_token = create_refresh_token(subject=user.id, role=user.role)
        return Token(access_token=access_token, refresh_token=new_refresh_token)
