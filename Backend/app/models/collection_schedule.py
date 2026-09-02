"""Ward collection timetable ORM model (S2-F04, US-32/US-33).

Persistence shape for the eventual server-side port of
``Frontend/src/utils/collectionSchedule.js`` (4 ward timetables,
nth-weekday-of-month math, exception dates). ``GET /schedule`` and
``GET /schedule/reminders`` (S2-A16/S2-A17) read this table; building those
routes is separate follow-up work.
"""

from datetime import date
from enum import Enum

from sqlalchemy import Boolean, Date, ForeignKey, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class CollectionFrequency(str, Enum):
    """How often a ward's regular collection slot repeats."""

    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"


class CollectionSchedule(Base, TimestampMixin):
    """A single recurring collection slot for a ward, or a one-off exception.

    Regular rows use ``day_of_week`` (+ ``week_of_month`` for "2nd and 4th
    Tuesday"-style monthly rules); ``is_exception`` rows instead pin an exact
    ``exception_date`` (e.g. a public holiday shift) and take precedence over
    the regular rule for that date.
    """

    __tablename__ = "collection_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    ward_id: Mapped[int] = mapped_column(ForeignKey("wards.id"), nullable=False, index=True)
    frequency: Mapped[str] = mapped_column(
        String(50), default=CollectionFrequency.WEEKLY.value, nullable=False
    )
    day_of_week: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    week_of_month: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    time_slot: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_exception: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    exception_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
