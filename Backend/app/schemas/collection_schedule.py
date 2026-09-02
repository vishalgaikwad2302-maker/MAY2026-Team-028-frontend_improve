"""Pydantic DTOs for ward collection schedules (S2-F04, US-32/US-33).

``day_of_week`` uses Python's ``date.weekday()`` convention: Monday=0 .. Sunday=6.
``week_of_month`` is 0-indexed (0=first, 1=second, 2=third, 3=fourth) to match
the zero-based "nth occurrence" math used for monthly rules.
"""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CollectionFrequency(str, Enum):
    """How often a ward's regular collection slot repeats. Mirrors the ORM enum."""

    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"


class CollectionScheduleCreate(BaseModel):
    """Payload for an admin creating a regular slot or a one-off exception."""

    ward_id: int
    frequency: CollectionFrequency = CollectionFrequency.WEEKLY
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    week_of_month: int | None = Field(default=None, ge=0, le=3)
    time_slot: str | None = Field(default=None, max_length=50)
    is_exception: bool = False
    exception_date: date | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def _check_required_fields(self) -> "CollectionScheduleCreate":
        if self.is_exception:
            if self.exception_date is None:
                raise ValueError("exception_date is required when is_exception is true.")
        elif self.day_of_week is None:
            raise ValueError("day_of_week is required for a regular (non-exception) schedule row.")
        if self.frequency == CollectionFrequency.MONTHLY and self.week_of_month is None:
            raise ValueError("week_of_month is required for a monthly frequency rule.")
        return self


class CollectionScheduleUpdate(BaseModel):
    """Payload for an admin editing a schedule row."""

    frequency: CollectionFrequency | None = None
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    week_of_month: int | None = Field(default=None, ge=0, le=3)
    time_slot: str | None = Field(default=None, max_length=50)
    is_exception: bool | None = None
    exception_date: date | None = None
    notes: str | None = None


class CollectionScheduleRead(BaseModel):
    """Collection schedule response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    ward_id: int
    frequency: str
    day_of_week: int | None = None
    week_of_month: int | None = None
    time_slot: str | None = None
    is_exception: bool
    exception_date: date | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class ScheduleReminderRead(BaseModel):
    """One computed upcoming-pickup reminder for a ward."""

    schedule_id: int
    ward_id: int
    occurrence_date: date
    time_slot: str | None = None
    is_exception: bool
    notes: str | None = None
