"""Vehicle repository."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.vehicle import Vehicle

__all__ = ["VehicleRepository"]


class VehicleRepository:
    @staticmethod
    def get_by_id(db: Session, vehicle_id: int) -> Vehicle | None:
        return db.get(Vehicle, vehicle_id)

    @staticmethod
    def list(db: Session) -> list[Vehicle]:
        return list(db.scalars(select(Vehicle).order_by(Vehicle.created_at.desc())).all())

    @staticmethod
    def create(db: Session, vehicle: Vehicle) -> Vehicle:
        db.add(vehicle)
        db.commit()
        db.refresh(vehicle)
        return vehicle

    @staticmethod
    def update(db: Session, vehicle: Vehicle, update_data: dict[str, Any]) -> Vehicle:
        for field, value in update_data.items():
            if hasattr(vehicle, field) and value is not None:
                setattr(vehicle, field, value)
        db.commit()
        db.refresh(vehicle)
        return vehicle
