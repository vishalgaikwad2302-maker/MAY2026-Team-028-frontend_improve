"""Shared FastAPI route dependencies: DB session, get_current_user, and require_role."""

from collections.abc import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository

__all__ = ["get_current_user", "get_db", "require_role"]

security_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> User:
    """Validate Bearer JWT access token and return the current authenticated User."""
    if not credentials or not credentials.credentials:
        raise AuthenticationError("Authentication token missing.")

    token = credentials.credentials
    payload = decode_token(token)

    if payload.get("type") != "access":
        raise AuthenticationError("Invalid token type. Access token required.")

    user_id_str = payload.get("sub")
    if not user_id_str or not user_id_str.isdigit():
        raise AuthenticationError("Invalid user subject in token.")

    user = UserRepository.get_by_id(db, int(user_id_str))
    if not user:
        raise AuthenticationError("User associated with token not found.")
    if not user.is_active:
        raise PermissionDeniedError("User account is inactive.")

    return user


def require_role(*roles: str | UserRole) -> Callable[[User], User]:
    """Dependency factory for Role-Based Access Control (RBAC).

    Usage:
        @router.get("/admin-panel", dependencies=[Depends(require_role(UserRole.ADMIN))])
        def admin_panel(): ...
    """
    allowed_roles = {r.value if isinstance(r, UserRole) else str(r) for r in roles}

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise PermissionDeniedError(
                f"Role '{current_user.role}' does not have permission to access this resource."
            )
        return current_user

    return role_checker
