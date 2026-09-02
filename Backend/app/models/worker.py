"""Worker ORM model."""

from enum import Enum

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class WorkerStatus(str, Enum):
    """Operational availability states for crew members."""

    AVAILABLE = "available"
    ASSIGNED = "assigned"
    OFF_DUTY = "off_duty"
    UNAVAILABLE = "unavailable"


class Worker(Base, TimestampMixin):
    """Assignable cleanup crew member."""

    __tablename__ = "workers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    employee_code: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    role_title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default=WorkerStatus.AVAILABLE.value, nullable=False, index=True
    )
    ward_id: Mapped[int | None] = mapped_column(ForeignKey("wards.id"), nullable=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
