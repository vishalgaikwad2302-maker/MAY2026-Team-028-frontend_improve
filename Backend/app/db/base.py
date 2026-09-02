"""SQLAlchemy declarative base + shared metadata."""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

__all__ = ["Base", "TimestampMixin"]


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    pass


class TimestampMixin:
    """Adds created_at/updated_at columns, both server-side defaults.

    Mix in wherever a row's own history matters. Deliberately excludes
    immutable audit rows (e.g. ComplaintStatusHistory) which only ever need
    created_at — adding this there would create an updated_at column that
    can never legitimately change.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
