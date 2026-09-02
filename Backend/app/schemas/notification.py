"""Pydantic DTOs for in-app notifications (S2-F02, US-06/US-23)."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class NotificationType(str, Enum):
    """Events that emit an in-app notification. Mirrors the ORM enum."""

    DUPLICATE_DETECTED = "duplicate_detected"
    COMPLAINT_RESOLVED = "complaint_resolved"


class NotificationRead(BaseModel):
    """Notification response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    type: str
    title: str
    message: str
    related_complaint_id: int | None = None
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
