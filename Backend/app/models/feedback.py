"""Citizen feedback ORM model (S2-F02)."""

from sqlalchemy import ForeignKey, Integer, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Feedback(Base, TimestampMixin):
    """Post-cleanup rating + comment left by the reporting citizen (US-24).

    One feedback row per complaint: ``POST /complaints/{id}/feedback`` is only
    valid once a complaint has moved to ``resolved``, and the route layer is
    responsible for rejecting a second submission for the same complaint.
    """

    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    complaint_id: Mapped[int] = mapped_column(
        ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    submitted_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
