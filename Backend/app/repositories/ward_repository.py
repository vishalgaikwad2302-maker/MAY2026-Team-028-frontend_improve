"""Ward repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ward import Ward

__all__ = ["WardRepository"]


class WardRepository:
    @staticmethod
    def get_by_id(db: Session, ward_id: int) -> Ward | None:
        return db.get(Ward, ward_id)

    @staticmethod
    def list(db: Session) -> list[Ward]:
        return list(db.scalars(select(Ward).order_by(Ward.name.asc())).all())
