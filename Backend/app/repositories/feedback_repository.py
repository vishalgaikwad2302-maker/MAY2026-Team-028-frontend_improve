"""Feedback repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.feedback import Feedback

__all__ = ["FeedbackRepository"]


class FeedbackRepository:
    @staticmethod
    def get_by_complaint_id(db: Session, complaint_id: int) -> Feedback | None:
        return db.scalar(select(Feedback).where(Feedback.complaint_id == complaint_id))

    @staticmethod
    def create(db: Session, feedback: Feedback) -> Feedback:
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        return feedback
