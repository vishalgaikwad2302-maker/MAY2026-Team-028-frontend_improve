"""Notification API routes."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.common import Page
from app.schemas.notification import NotificationRead
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=Page[NotificationRead])
def list_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    unread_only: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> Page[NotificationRead]:
    items, total = NotificationService.list_notifications(
        db, current_user, unread_only=unread_only, page=page, page_size=page_size
    )
    return Page[NotificationRead].build(
        [NotificationRead.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.patch("/{notification_id}/read", response_model=NotificationRead)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationRead:
    notification = NotificationService.mark_read(db, notification_id, current_user)
    return NotificationRead.model_validate(notification)


@router.post("/read-all", status_code=status.HTTP_200_OK)
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, int]:
    marked = NotificationService.mark_all_read(db, current_user)
    return {"marked": marked}
