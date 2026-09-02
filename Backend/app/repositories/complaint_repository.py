"""Complaint repository for database operations."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.complaint import Complaint, ComplaintStatusHistory

__all__ = ["ComplaintRepository"]


class ComplaintRepository:
    """Persistence helpers for complaint records and history."""

    @staticmethod
    def get_by_id(db: Session, complaint_id: int) -> Complaint | None:
        return db.get(Complaint, complaint_id)

    @staticmethod
    def create(db: Session, complaint: Complaint) -> Complaint:
        db.add(complaint)
        db.commit()
        db.refresh(complaint)
        return complaint

    @staticmethod
    def update(db: Session, complaint: Complaint, update_data: dict[str, Any]) -> Complaint:
        for field, value in update_data.items():
            if hasattr(complaint, field) and value is not None:
                setattr(complaint, field, value)
        db.commit()
        db.refresh(complaint)
        return complaint

    @staticmethod
    def list(db: Session, *, filters: dict[str, Any] | None = None) -> tuple[list[Complaint], int]:
        filters = filters or {}
        stmt = select(Complaint)

        status = filters.get("status")
        if status:
            stmt = stmt.where(Complaint.status == status)

        ward_id = filters.get("ward_id")
        if ward_id is not None:
            stmt = stmt.where(Complaint.ward_id == ward_id)

        complaint_type = filters.get("complaint_type")
        if complaint_type:
            stmt = stmt.where(Complaint.complaint_type == complaint_type)

        category = filters.get("category")
        if category:
            stmt = stmt.where(Complaint.category == category)

        reporter_id = filters.get("reported_by_user_id")
        if reporter_id is not None:
            stmt = stmt.where(Complaint.reported_by_user_id == reporter_id)

        search = filters.get("search")
        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                (Complaint.title.ilike(pattern))
                | (Complaint.description.ilike(pattern))
                | (Complaint.address.ilike(pattern))
            )

        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        page = int(filters.get("page", 1))
        page_size = int(filters.get("page_size", 20))
        stmt = (
            stmt.order_by(Complaint.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(db.scalars(stmt).all()), total

    @staticmethod
    def add_history(db: Session, history: ComplaintStatusHistory) -> ComplaintStatusHistory:
        db.add(history)
        db.commit()
        db.refresh(history)
        return history

    @staticmethod
    def get_history(db: Session, complaint_id: int) -> list[ComplaintStatusHistory]:
        stmt = select(ComplaintStatusHistory).where(
            ComplaintStatusHistory.complaint_id == complaint_id
        )
        return list(db.scalars(stmt.order_by(ComplaintStatusHistory.created_at.asc())).all())
