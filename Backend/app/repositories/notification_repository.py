"""Notification repository."""

from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.notification import Notification

__all__ = ["NotificationRepository"]


class NotificationRepository:
    @staticmethod
    def get_by_id(db: Session, notification_id: int) -> Notification | None:
        return db.get(Notification, notification_id)

    @staticmethod
    def create(db: Session, notification: Notification) -> Notification:
        db.add(notification)
        db.commit()
        db.refresh(notification)
        return notification

    @staticmethod
    def list_for_user(
        db: Session,
        user_id: int,
        *,
        unread_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Notification], int]:
        stmt = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            stmt = stmt.where(Notification.is_read.is_(False))

        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        stmt = (
            stmt.order_by(Notification.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(db.scalars(stmt).all()), total

    @staticmethod
    def mark_read(db: Session, notification: Notification, read_at) -> Notification:
        notification.is_read = True
        notification.read_at = read_at
        db.commit()
        db.refresh(notification)
        return notification

    @staticmethod
    def mark_all_read(db: Session, user_id: int, read_at) -> int:
        result = db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            .values(is_read=True, read_at=read_at)
        )
        db.commit()
        return result.rowcount or 0
