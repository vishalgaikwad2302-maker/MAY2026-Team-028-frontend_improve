from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TransparencyPostCreate(BaseModel):
    """Payload for creating a transparency post (with or without linked complaint)."""

    complaint_id: int | None = Field(default=None, description="Optional linked complaint ID")
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    images: list[str] | None = Field(default_factory=list, max_length=3)
    before_photo_url: str | None = Field(default=None, max_length=2048)
    after_photo_url: str | None = Field(default=None, max_length=2048)


class TransparencyPostRead(BaseModel):
    """Transparency post response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    complaint_id: int | None = None
    ward_id: int | None = None
    title: str
    description: str | None = None
    images: list[str] | None = None
    before_photo_url: str | None = None
    after_photo_url: str | None = None
    applause_count: int = 0
    posted_by_user_id: int | None = None
    created_at: datetime
    updated_at: datetime


class PostCommentCreate(BaseModel):
    """Payload for commenting on a transparency post."""

    comment: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="before")
    @classmethod
    def accept_content_alias(cls, data: Any) -> Any:
        if isinstance(data, dict) and "content" in data and "comment" not in data:
            data["comment"] = data["content"]
        return data


class PostCommentRead(BaseModel):
    """Post comment response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    post_id: int
    user_id: int
    comment: str
    created_at: datetime
