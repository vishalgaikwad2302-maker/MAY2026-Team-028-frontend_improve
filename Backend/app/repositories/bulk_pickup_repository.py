"""Bulk pickup repository."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.bulk_pickup import BulkPickup

__all__ = ["BulkPickupRepository"]


class BulkPickupRepository:
    @staticmethod
    def get_by_id(db: Session, pickup_id: int) -> BulkPickup | None:
        return db.get(BulkPickup, pickup_id)

    @staticmethod
    def create(db: Session, pickup: BulkPickup) -> BulkPickup:
        db.add(pickup)
        db.commit()
        db.refresh(pickup)
        return pickup

    @staticmethod
    def update(db: Session, pickup: BulkPickup, update_data: dict[str, Any]) -> BulkPickup:
        for field, value in update_data.items():
            if hasattr(pickup, field) and value is not None:
                setattr(pickup, field, value)
        db.commit()
        db.refresh(pickup)
        return pickup

    @staticmethod
    def list(
        db: Session, *, filters: dict[str, Any] | None = None, page: int = 1, page_size: int = 20
    ) -> tuple[list[BulkPickup], int]:
        filters = filters or {}
        stmt = select(BulkPickup)

        requester_id = filters.get("requested_by_user_id")
        if requester_id is not None:
            stmt = stmt.where(BulkPickup.requested_by_user_id == requester_id)

        status = filters.get("status")
        if status:
            stmt = stmt.where(BulkPickup.status == status)

        ward_id = filters.get("ward_id")
        if ward_id is not None:
            stmt = stmt.where(BulkPickup.ward_id == ward_id)

        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        stmt = (
            stmt.order_by(BulkPickup.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(db.scalars(stmt).all()), total
