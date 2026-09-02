"""Equipment repository."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.equipment import Equipment

__all__ = ["EquipmentRepository"]


class EquipmentRepository:
    @staticmethod
    def get_by_id(db: Session, equipment_id: int) -> Equipment | None:
        return db.get(Equipment, equipment_id)

    @staticmethod
    def list(db: Session) -> list[Equipment]:
        return list(db.scalars(select(Equipment).order_by(Equipment.created_at.desc())).all())

    @staticmethod
    def create(db: Session, equipment: Equipment) -> Equipment:
        db.add(equipment)
        db.commit()
        db.refresh(equipment)
        return equipment

    @staticmethod
    def update(db: Session, equipment: Equipment, update_data: dict[str, Any]) -> Equipment:
        for field, value in update_data.items():
            if hasattr(equipment, field) and value is not None:
                setattr(equipment, field, value)
        db.commit()
        db.refresh(equipment)
        return equipment
