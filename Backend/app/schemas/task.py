"""Pydantic DTOs for tasks and assignments."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class TaskStatus(str, Enum):
    """Assignment lifecycle states exposed through the API."""

    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskBase(BaseModel):
    """Shared task fields."""

    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    complaint_id: int | None = None
    ward_id: int | None = None
    vehicle_id: int | None = None
    status: TaskStatus = TaskStatus.ASSIGNED


class TaskCreate(TaskBase):
    """Payload for creating a task."""

    worker_ids: list[int] = Field(default_factory=list)
    equipment_ids: list[int] = Field(default_factory=list)
    assigned_by_user_id: int | None = None


class TaskUpdate(BaseModel):
    """Payload for updating a task."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    complaint_id: int | None = None
    ward_id: int | None = None
    vehicle_id: int | None = None
    status: TaskStatus | None = None
    worker_ids: list[int] | None = None
    equipment_ids: list[int] | None = None
    resolution_notes: str | None = None


class TaskComplete(BaseModel):
    """Payload for completing a task."""

    completion_photos: list[str] | None = Field(
        default=None, max_length=3, description="1 to 3 URLs of completion proof photos"
    )
    completion_photo_url: str | None = Field(
        default=None, description="URL of photo after task completion"
    )
    waste_removed: str | None = Field(
        default=None, description="Quantity or description of waste removed (e.g. '1.4 Tons')"
    )
    resolution_notes: str | None = Field(default=None, description="Notes on task completion")


class TaskRead(TaskBase):
    """Task response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    assigned_by_user_id: int | None = None
    resolution_notes: str | None = None
    completion_photo_url: str | None = None
    completion_photos: list[str] | None = None
    waste_removed: str | None = None
    assigned_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    worker_ids: list[int] = Field(default_factory=list)
    equipment_ids: list[int] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
