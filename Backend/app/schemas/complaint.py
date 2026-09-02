import json
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ComplaintStatus(str, Enum):
    """Complaint lifecycle values exposed through the API."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    VERIFIED = "verified"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class ComplaintType(str, Enum):
    """Community-facing complaint category (S2-A18).

    Separate from ``category`` (the hazard classification field). Pydantic
    validates any value outside this set as a 422 automatically.
    """

    OVERFLOW = "overflow"
    DELAY = "delay"
    EXTRA_COLLECTION = "extra_collection"


class ComplaintCategory(str, Enum):
    """Hazard classification. Mirrors the ORM enum (US-28/29/30)."""

    NONE = "None"
    FOUL_SMELL = "Foul Smell"
    OVERFLOWING_BIN = "Overflowing Bin"
    MOSQUITO_BREEDING = "Mosquito Breeding"
    RISK_TO_CHILDREN = "Risk to Children"


class ComplaintBase(BaseModel):
    """Shared complaint fields."""

    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    ward_id: int | None = None
    category: ComplaintCategory | None = None
    complaint_type: ComplaintType | None = None
    priority: str | None = Field(default=None, max_length=50)
    address: str | None = Field(default=None, max_length=255)
    latitude: float | None = None
    longitude: float | None = None
    photo_url: str | None = Field(default=None, max_length=10_000_000)
    tags: list[str] = Field(default_factory=list)


class ComplaintCreate(ComplaintBase):
    """Payload for creating a complaint."""

    reported_by_user_id: int | None = None


class ComplaintSubmit(BaseModel):
    """Payload coming directly from the citizen report form."""

    location: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    hazard: ComplaintCategory | None = None
    complaint_type: ComplaintType | None = None
    photo: str | None = Field(default=None, max_length=10_000_000)
    coords: dict[str, float] | None = None
    ward_id: int | None = None


class DuplicateCheckRequest(BaseModel):
    """Draft complaint fields used for an advisory duplicate scan."""

    location: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    coords: dict[str, float] | None = None
    ward_id: int | None = None


class ComplaintUpdate(BaseModel):
    """Payload for updating a complaint."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1)
    ward_id: int | None = None
    category: ComplaintCategory | None = None
    complaint_type: ComplaintType | None = None
    priority: str | None = Field(default=None, max_length=50)
    status: ComplaintStatus | None = None
    address: str | None = Field(default=None, max_length=255)
    latitude: float | None = None
    longitude: float | None = None
    photo_url: str | None = Field(default=None, max_length=10_000_000)
    tags: list[str] | None = None


class ComplaintVerify(BaseModel):
    """Payload for verifying a complaint (Admin review)."""

    notes: str | None = Field(default=None, description="Review notes by admin")


class ComplaintClose(BaseModel):
    """Payload for closing a complaint (Supervisor confirm)."""

    notes: str | None = Field(default=None, description="Confirmation notes by supervisor")
    after_photo_url: str | None = Field(default=None, description="Optional after photo URL")


class ComplaintRead(ComplaintBase):
    """Complaint response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    reported_by_user_id: int
    status: ComplaintStatus
    resolved_at: datetime | None = None
    cancelled_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("tags", mode="before")
    @classmethod
    def _parse_tags(cls, v: object) -> list[str]:
        if isinstance(v, list):
            return [str(x) for x in v]
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(x) for x in parsed]
            except Exception:
                return [t.strip() for t in v.split(",") if t.strip()]
        return []


class ComplaintFilter(BaseModel):
    """Optional list filters for complaints."""

    search: str | None = Field(default=None, max_length=255)
    status: ComplaintStatus | None = None
    ward_id: int | None = None
    complaint_type: ComplaintType | None = None
    category: ComplaintCategory | None = None
    reported_by_user_id: int | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    created_from: datetime | None = None
    created_to: datetime | None = None


class ComplaintClassifyRead(BaseModel):
    """Response for POST /complaints/{id}/classify (US-28/29/30)."""

    complaint: ComplaintRead
    category: ComplaintCategory
    tags: list[str] = Field(default_factory=list)
    source: Literal["llm", "heuristic"]
    confidence: float | None = None
    reasoning: str | None = None


class ComplaintStatusHistoryRead(BaseModel):
    """Complaint status audit trail response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    complaint_id: int
    from_status: str
    to_status: str
    changed_by_user_id: int
    notes: str | None = None
    created_at: datetime
