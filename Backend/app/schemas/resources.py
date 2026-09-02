"""Pydantic DTOs for operational resources."""

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class WorkerStatus(str, Enum):
    """Crew availability states exposed via the API."""

    AVAILABLE = "available"
    ASSIGNED = "assigned"
    OFF_DUTY = "off_duty"
    UNAVAILABLE = "unavailable"


class VehicleStatus(str, Enum):
    """Fleet availability states exposed via the API."""

    AVAILABLE = "available"
    EN_ROUTE = "en_route"
    ON_SITE = "on_site"
    MAINTENANCE = "maintenance"


class EquipmentStatus(str, Enum):
    """Equipment stock states exposed via the API."""

    AVAILABLE = "available"
    IN_USE = "in_use"
    MAINTENANCE = "maintenance"
    RETIRED = "retired"


class WorkerBase(BaseModel):
    """Shared worker fields."""

    full_name: str = Field(min_length=1, max_length=255)
    employee_code: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    role_title: str | None = Field(default=None, max_length=100)
    ward_id: int | None = None
    status: WorkerStatus = WorkerStatus.AVAILABLE
    is_active: bool = True


class WorkerCreate(WorkerBase):
    """Payload for onboarding a worker (with optional user credentials)."""

    password: str | None = Field(default=None, min_length=6)


class WorkerUpdate(BaseModel):
    """Payload for updating a worker."""

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    employee_code: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    role_title: str | None = Field(default=None, max_length=100)
    ward_id: int | None = None
    status: WorkerStatus | None = None
    is_active: bool | None = None


class WorkerRead(WorkerBase):
    """Worker response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None = None
    created_at: datetime
    updated_at: datetime


class VehicleBase(BaseModel):
    """Shared vehicle fields."""

    plate_number: str = Field(min_length=1, max_length=50)
    model_name: str = Field(min_length=1, max_length=255)
    vehicle_type: str | None = Field(default=None, max_length=100)
    capacity_tons: Decimal | None = None
    ward_id: int | None = None
    driver_name: str | None = Field(default=None, max_length=255)
    status: VehicleStatus = VehicleStatus.AVAILABLE
    is_active: bool = True


class VehicleCreate(VehicleBase):
    """Payload for creating a vehicle."""


class VehicleUpdate(BaseModel):
    """Payload for updating a vehicle."""

    plate_number: str | None = Field(default=None, min_length=1, max_length=50)
    model_name: str | None = Field(default=None, min_length=1, max_length=255)
    vehicle_type: str | None = Field(default=None, max_length=100)
    capacity_tons: Decimal | None = None
    ward_id: int | None = None
    driver_name: str | None = Field(default=None, max_length=255)
    status: VehicleStatus | None = None
    is_active: bool | None = None


class VehicleRead(VehicleBase):
    """Vehicle response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class EquipmentBase(BaseModel):
    """Shared equipment fields."""

    name: str = Field(min_length=1, max_length=255)
    asset_tag: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    total_quantity: int = Field(default=1, ge=1)
    available_quantity: int = Field(default=1, ge=0)
    ward_id: int | None = None
    status: EquipmentStatus = EquipmentStatus.AVAILABLE
    is_active: bool = True


class EquipmentCreate(EquipmentBase):
    """Payload for creating equipment."""


class EquipmentUpdate(BaseModel):
    """Payload for updating equipment."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    asset_tag: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    total_quantity: int | None = Field(default=None, ge=1)
    available_quantity: int | None = Field(default=None, ge=0)
    ward_id: int | None = None
    status: EquipmentStatus | None = None
    is_active: bool | None = None


class EquipmentRead(EquipmentBase):
    """Equipment response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
