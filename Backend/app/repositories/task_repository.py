"""Task repository."""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.models.task import Task, task_equipment, task_workers

__all__ = ["TaskRepository"]


class TaskRepository:
    @staticmethod
    def get_by_id(db: Session, task_id: int) -> Task | None:
        return db.get(Task, task_id)

    @staticmethod
    def list(db: Session) -> list[Task]:
        return list(db.scalars(select(Task).order_by(Task.created_at.desc())).all())

    @staticmethod
    def create(db: Session, task: Task) -> Task:
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def update(db: Session, task: Task, update_data: dict[str, Any]) -> Task:
        for field, value in update_data.items():
            if hasattr(task, field) and value is not None:
                setattr(task, field, value)
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def set_worker_ids(db: Session, task_id: int, worker_ids: list[int]) -> None:
        db.execute(delete(task_workers).where(task_workers.c.task_id == task_id))
        for worker_id in worker_ids:
            db.execute(insert(task_workers).values(task_id=task_id, worker_id=worker_id))
        db.commit()

    @staticmethod
    def set_equipment_ids(db: Session, task_id: int, equipment_ids: list[int]) -> None:
        db.execute(delete(task_equipment).where(task_equipment.c.task_id == task_id))
        for equipment_id in equipment_ids:
            db.execute(
                insert(task_equipment).values(
                    task_id=task_id, equipment_id=equipment_id, quantity=1
                )
            )
        db.commit()

    @staticmethod
    def get_worker_ids(db: Session, task_id: int) -> list[int]:
        rows = db.execute(select(task_workers.c.worker_id).where(task_workers.c.task_id == task_id))
        return [row[0] for row in rows.all()]

    @staticmethod
    def get_equipment_ids(db: Session, task_id: int) -> list[int]:
        rows = db.execute(
            select(task_equipment.c.equipment_id).where(task_equipment.c.task_id == task_id)
        )
        return [row[0] for row in rows.all()]
