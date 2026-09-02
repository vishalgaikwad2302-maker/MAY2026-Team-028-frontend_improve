"""Worker repository."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.worker import Worker

__all__ = ["WorkerRepository"]


class WorkerRepository:
    @staticmethod
    def get_by_id(db: Session, worker_id: int) -> Worker | None:
        return db.get(Worker, worker_id)

    @staticmethod
    def list(db: Session) -> list[Worker]:
        return list(db.scalars(select(Worker).order_by(Worker.created_at.desc())).all())

    @staticmethod
    def create(db: Session, worker: Worker) -> Worker:
        db.add(worker)
        db.commit()
        db.refresh(worker)
        return worker

    @staticmethod
    def update(db: Session, worker: Worker, update_data: dict[str, Any]) -> Worker:
        for field, value in update_data.items():
            if hasattr(worker, field) and value is not None:
                setattr(worker, field, value)
        db.commit()
        db.refresh(worker)
        return worker
