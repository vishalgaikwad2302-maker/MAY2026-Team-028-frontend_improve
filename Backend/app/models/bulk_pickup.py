"""Bulk waste pickup ORM model (S2-F04, US-31).

Field shape mirrors ``Frontend/src/context/BulkPickupContext.jsx``, minus fee:
the service is municipality-run with no payment processing, so there is no
fee/pricing concept on the backend.
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class BulkPickupStatus(str, Enum):
    """Lifecycle states — must match the frontend's fixed enum exactly."""

    REQUESTED = "requested"
    SCHEDULED = "scheduled"
    COLLECTED = "collected"
    CANCELLED = "cancelled"


class BulkPickupCategory(str, Enum):
    """Waste category."""

    GENERAL = "general"
    E_WASTE = "e_waste"
    CONSTRUCTION_DEBRIS = "construction_debris"
    SCRAP_METAL = "scrap_metal"


class BulkPickupLoadBand(str, Enum):
    """Load size."""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    EXTRA_LARGE = "extra_large"


class BulkPickup(Base, TimestampMixin):
    """Citizen-requested bulk waste collection."""

    __tablename__ = "bulk_pickups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    requested_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    ward_id: Mapped[int | None] = mapped_column(ForeignKey("wards.id"), nullable=True, index=True)
    category: Mapped[str] = mapped_column(
        String(50), default=BulkPickupCategory.GENERAL.value, nullable=False, index=True
    )
    load_band: Mapped[str] = mapped_column(String(50), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    preferred_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default=BulkPickupStatus.REQUESTED.value, nullable=False, index=True
    )
    assigned_vehicle_id: Mapped[int | None] = mapped_column(
        ForeignKey("vehicles.id"), nullable=True, index=True
    )
    assigned_worker_id: Mapped[int | None] = mapped_column(
        ForeignKey("workers.id"), nullable=True, index=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
