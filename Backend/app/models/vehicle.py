"""Vehicle ORM model."""

from decimal import Decimal
from enum import Enum

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class VehicleStatus(str, Enum):
    """Fleet availability states."""

    AVAILABLE = "available"
    EN_ROUTE = "en_route"
    ON_SITE = "on_site"
    MAINTENANCE = "maintenance"


class Vehicle(Base, TimestampMixin):
    """Assignable municipal fleet vehicle."""

    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    plate_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    vehicle_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    capacity_tons: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default=VehicleStatus.AVAILABLE.value, nullable=False, index=True
    )
    ward_id: Mapped[int | None] = mapped_column(ForeignKey("wards.id"), nullable=True, index=True)
    driver_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
