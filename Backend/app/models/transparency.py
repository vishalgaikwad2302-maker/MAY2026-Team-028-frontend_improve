"""Public transparency feed ORM models (S2-F03).

``TransparencyPost`` is what makes US-25 real rather than seeded: per the
plan, a post is auto-generated when a complaint is closed (S2-A04), carrying
before/after photos. ``PostComment`` is a simple append-only comment thread
on a post, mirroring the audit-log shape already used for
``ComplaintStatusHistory`` (created-once, never edited).
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class TransparencyPost(Base, TimestampMixin):
    """Public-facing cleanup record shown on the transparency feed."""

    __tablename__ = "transparency_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    complaint_id: Mapped[int | None] = mapped_column(
        ForeignKey("complaints.id", ondelete="CASCADE"), nullable=True, unique=False, index=True
    )
    ward_id: Mapped[int | None] = mapped_column(ForeignKey("wards.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    images: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    before_photo_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    after_photo_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    applause_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    posted_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )


class PostComment(Base):
    """A single comment on a transparency post. Append-only, like status history."""

    __tablename__ = "post_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(
        ForeignKey("transparency_posts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
