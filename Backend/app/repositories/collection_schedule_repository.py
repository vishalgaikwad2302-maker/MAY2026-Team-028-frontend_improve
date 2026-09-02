"""Collection schedule repository."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.collection_schedule import CollectionSchedule

__all__ = ["CollectionScheduleRepository"]


class CollectionScheduleRepository:
    @staticmethod
    def get_by_id(db: Session, schedule_id: int) -> CollectionSchedule | None:
        return db.get(CollectionSchedule, schedule_id)

    @staticmethod
    def create(db: Session, schedule: CollectionSchedule) -> CollectionSchedule:
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        return schedule

    @staticmethod
    def update(
        db: Session, schedule: CollectionSchedule, update_data: dict[str, Any]
    ) -> CollectionSchedule:
        for field, value in update_data.items():
            if hasattr(schedule, field) and value is not None:
                setattr(schedule, field, value)
        db.commit()
        db.refresh(schedule)
        return schedule

    @staticmethod
    def delete(db: Session, schedule: CollectionSchedule) -> None:
        db.delete(schedule)
        db.commit()

    @staticmethod
    def list_by_ward(db: Session, ward_id: int) -> list[CollectionSchedule]:
        stmt = select(CollectionSchedule).where(CollectionSchedule.ward_id == ward_id)
        return list(db.scalars(stmt.order_by(CollectionSchedule.id.asc())).all())
