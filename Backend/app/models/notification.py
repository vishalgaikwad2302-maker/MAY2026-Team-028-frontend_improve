"""In-app notification ORM model (S2-F02)."""

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class NotificationType(str, Enum):
    """Events that emit an in-app notification (US-06, US-23).

    In-app only, per the plan's safe defaults: rows are polled by the
    client, there is no email/SMS delivery.
    """

    DUPLICATE_DETECTED = "duplicate_detected"
    COMPLAINT_RESOLVED = "complaint_resolved"


class Notification(Base, TimestampMixin):
    """A single notification-inbox entry for one user."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    related_complaint_id: Mapped[int | None] = mapped_column(
        ForeignKey("complaints.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
