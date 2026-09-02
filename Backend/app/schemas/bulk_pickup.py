"""Pydantic DTOs for bulk waste pickup requests (S2-F04, US-31)."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class BulkPickupStatus(str, Enum):
    """Lifecycle states exposed through the API. Mirrors the ORM enum."""

    REQUESTED = "requested"
    SCHEDULED = "scheduled"
    COLLECTED = "collected"
    CANCELLED = "cancelled"


class BulkPickupCategory(str, Enum):
    """Waste category. Mirrors the ORM enum."""

    GENERAL = "general"
    E_WASTE = "e_waste"
    CONSTRUCTION_DEBRIS = "construction_debris"
    SCRAP_METAL = "scrap_metal"


class BulkPickupLoadBand(str, Enum):
    """Load size. Mirrors the ORM enum."""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    EXTRA_LARGE = "extra_large"


class BulkPickupCreate(BaseModel):
    """Payload for a citizen requesting a bulk pickup."""

    category: BulkPickupCategory = BulkPickupCategory.GENERAL
    load_band: BulkPickupLoadBand
    address: str = Field(min_length=1, max_length=255)
    ward_id: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    preferred_date: datetime | None = None
    notes: str | None = None


class BulkPickupUpdate(BaseModel):
    """Payload for crew/admin managing a pickup's lifecycle."""

    status: BulkPickupStatus | None = None
    assigned_vehicle_id: int | None = None
    assigned_worker_id: int | None = None
    scheduled_at: datetime | None = None
    notes: str | None = None


class BulkPickupAssign(BaseModel):
    """Payload for dispatching a crew member and vehicle to a pickup."""

    worker_id: int
    vehicle_id: int


class BulkPickupRead(BaseModel):
    """Bulk pickup response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    requested_by_user_id: int
    ward_id: int | None = None
    category: str
    load_band: str
    address: str
    latitude: float | None = None
    longitude: float | None = None
    preferred_date: datetime | None = None
    status: str
    assigned_vehicle_id: int | None = None
    assigned_worker_id: int | None = None
    notes: str | None = None
    scheduled_at: datetime | None = None
    collected_at: datetime | None = None
    cancelled_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
