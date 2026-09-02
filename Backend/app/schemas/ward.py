"""Pydantic DTOs for wards."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WardBase(BaseModel):
    """Shared ward fields."""

    name: str = Field(min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=50)
    zone: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool = True


class WardCreate(WardBase):
    """Payload for creating a ward."""


class WardUpdate(BaseModel):
    """Payload for updating ward metadata."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=50)
    zone: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class WardRead(WardBase):
    """Ward response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
