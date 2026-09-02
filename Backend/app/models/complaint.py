"""Complaint ORM models."""

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ComplaintStatus(str, Enum):
    """Complaint lifecycle states."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    VERIFIED = "verified"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class ComplaintType(str, Enum):
    """Community-facing complaint category (S2-A18).

    Distinct from ``category``, which historically carries the hazard
    classification chosen on the report form (e.g. "Foul Smell",
    "Risk to Children") and feeds ``GET /complaints/high-risk``. This is a
    separate, optional axis describing what kind of service request the
    complaint actually is.
    """

    OVERFLOW = "overflow"
    DELAY = "delay"
    EXTRA_COLLECTION = "extra_collection"


class ComplaintCategory(str, Enum):
    """Hazard classification chosen on the report form (US-28/29/30).

    Values mirror ``Frontend/src/pages/ReportComplaint.jsx``'s ``#hazard``
    select exactly (including the "None" default) so the API can validate
    the field instead of accepting arbitrary free text.
    """

    NONE = "None"
    FOUL_SMELL = "Foul Smell"
    OVERFLOWING_BIN = "Overflowing Bin"
    MOSQUITO_BREEDING = "Mosquito Breeding"
    RISK_TO_CHILDREN = "Risk to Children"


class Complaint(Base, TimestampMixin):
    """Citizen-reported waste or sanitation issue."""

    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(
        String(100), default=ComplaintCategory.NONE.value, nullable=True
    )
    complaint_type: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    priority: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default=ComplaintStatus.PENDING.value, nullable=False, index=True
    )
    ward_id: Mapped[int | None] = mapped_column(ForeignKey("wards.id"), nullable=True, index=True)
    reported_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ComplaintStatusHistory(Base):
    """Audit trail for complaint status changes."""

    __tablename__ = "complaint_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    complaint_id: Mapped[int] = mapped_column(
        ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_status: Mapped[str] = mapped_column(String(50), nullable=False)
    to_status: Mapped[str] = mapped_column(String(50), nullable=False)
    changed_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
