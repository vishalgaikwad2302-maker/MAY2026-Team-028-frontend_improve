"""Pydantic schemas for authentication and tokens."""

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Payload for user login."""

    email: EmailStr
    password: str = Field(min_length=1)


class Token(BaseModel):
    """Token response schema containing access and refresh tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Payload for refreshing an access token."""

    refresh_token: str
