"""Pydantic schemas for User entity."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class UserBase(BaseModel):
    """Base fields for user schemas."""

    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    role: UserRole = UserRole.CITIZEN
    phone: str | None = None
    ward_id: int | None = None


class UserCreate(UserBase):
    """Payload for user registration or creation."""

    password: str = Field(min_length=6, max_length=128)


class UserUpdate(BaseModel):
    """Payload for updating user details."""

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = None
    ward_id: int | None = None
    is_active: bool | None = None


class UserRead(UserBase):
    """User response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
