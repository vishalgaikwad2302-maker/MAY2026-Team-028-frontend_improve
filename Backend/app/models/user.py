"""User SQLAlchemy ORM model."""

from enum import Enum

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class UserRole(str, Enum):
    """User roles for Role-Based Access Control (RBAC)."""

    CITIZEN = "citizen"
    CREW = "crew"
    ADMIN = "admin"


class User(Base, TimestampMixin):
    """User entity for citizens, cleanup crew, and ward supervisors/admins."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(50), default=UserRole.CITIZEN.value, nullable=False, index=True
    )
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ward_id: Mapped[int | None] = mapped_column(ForeignKey("wards.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
