"""Pydantic DTOs for citizen feedback (S2-F02, US-24)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FeedbackCreate(BaseModel):
    """Payload for submitting feedback on a resolved complaint."""

    rating: int = Field(ge=1, le=5, description="Star rating, 1 (worst) to 5 (best).")
    comment: str | None = Field(default=None, max_length=2000)


class FeedbackRead(BaseModel):
    """Feedback response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    complaint_id: int
    submitted_by_user_id: int
    rating: int
    comment: str | None = None
    created_at: datetime
    updated_at: datetime
