"""Notification service — in-app inbox, polled by the client (US-06, US-23)."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.models.complaint import Complaint
from app.models.notification import Notification, NotificationType
from app.models.user import User
from app.repositories.notification_repository import NotificationRepository

__all__ = ["NotificationService"]


class NotificationService:
    @staticmethod
    def create_notification(
        db: Session,
        *,
        user_id: int,
        notification_type: NotificationType | str,
        title: str,
        message: str,
        related_complaint_id: int | None = None,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            type=(
                notification_type.value
                if hasattr(notification_type, "value")
                else str(notification_type)
            ),
            title=title,
            message=message,
            related_complaint_id=related_complaint_id,
        )
        return NotificationRepository.create(db, notification)

    @staticmethod
    def notify_complaint_resolved(db: Session, complaint: Complaint) -> Notification:
        """Notify the reporting citizen that their complaint has been resolved."""
        return NotificationService.create_notification(
            db,
            user_id=complaint.reported_by_user_id,
            notification_type=NotificationType.COMPLAINT_RESOLVED,
            title="Complaint resolved",
            message=f"Your complaint '{complaint.title}' has been marked resolved.",
            related_complaint_id=complaint.id,
        )

    @staticmethod
    def notify_duplicate_detected(
        db: Session,
        complaint: Complaint,
        duplicate_count: int,
    ) -> Notification:
        """Notify the submitter that their new complaint may already be tracked.

        Emitted immediately after complaint creation when
        DuplicateDetectionService finds one or more likely matches (S2-A05).
        """
        return NotificationService.create_notification(
            db,
            user_id=complaint.reported_by_user_id,
            notification_type=NotificationType.DUPLICATE_DETECTED,
            title="Possible duplicate complaint",
            message=(
                f"Your complaint '{complaint.title}' may already be tracked — "
                f"{duplicate_count} similar report{'s' if duplicate_count != 1 else ''} "
                "found nearby. No action needed; our team will review."
            ),
            related_complaint_id=complaint.id,
        )

    @staticmethod
    def list_notifications(
        db: Session,
        current_user: User,
        *,
        unread_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Notification], int]:
        return NotificationRepository.list_for_user(
            db, current_user.id, unread_only=unread_only, page=page, page_size=page_size
        )

    @staticmethod
    def mark_read(db: Session, notification_id: int, current_user: User) -> Notification:
        notification = NotificationRepository.get_by_id(db, notification_id)
        if not notification:
            raise NotFoundError("Notification not found.")
        if notification.user_id != current_user.id:
            raise PermissionDeniedError("You do not have permission to access this notification.")
        if notification.is_read:
            return notification
        return NotificationRepository.mark_read(db, notification, datetime.now(UTC))

    @staticmethod
    def mark_all_read(db: Session, current_user: User) -> int:
        return NotificationRepository.mark_all_read(db, current_user.id, datetime.now(UTC))
