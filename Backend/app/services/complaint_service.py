"""Complaint service — CRUD and status state machine."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import InvalidStateTransitionError, NotFoundError, PermissionDeniedError
from app.models.complaint import Complaint, ComplaintStatus, ComplaintStatusHistory
from app.models.user import User, UserRole
from app.repositories.complaint_repository import ComplaintRepository
from app.schemas.complaint import ComplaintSubmit, ComplaintUpdate
from app.services.duplicate_detection_service import DuplicateDetectionService
from app.services.notification_service import NotificationService

__all__ = ["ComplaintService"]


_ALLOWED_TRANSITIONS = {
    ComplaintStatus.PENDING.value: {
        ComplaintStatus.IN_PROGRESS.value,
        ComplaintStatus.VERIFIED.value,
        ComplaintStatus.CLOSED.value,
        ComplaintStatus.CANCELLED.value,
    },
    ComplaintStatus.IN_PROGRESS.value: {
        ComplaintStatus.RESOLVED.value,
        ComplaintStatus.VERIFIED.value,
        ComplaintStatus.CLOSED.value,
        ComplaintStatus.CANCELLED.value,
    },
    ComplaintStatus.RESOLVED.value: {
        ComplaintStatus.VERIFIED.value,
        ComplaintStatus.CLOSED.value,
        ComplaintStatus.CANCELLED.value,
    },
    ComplaintStatus.VERIFIED.value: {
        ComplaintStatus.CLOSED.value,
        ComplaintStatus.RESOLVED.value,
        ComplaintStatus.CANCELLED.value,
    },
    ComplaintStatus.CLOSED.value: set(),
    ComplaintStatus.CANCELLED.value: set(),
}


class ComplaintService:
    @staticmethod
    def create_complaint(
        db: Session, current_user: User, complaint_in: ComplaintSubmit
    ) -> Complaint:
        photo_val = complaint_in.photo
        if photo_val and photo_val.startswith("data:"):
            try:
                import base64
                from app.services.upload_service import save_upload

                header, b64 = photo_val.split(",", 1)
                ctype = header.split(";")[0].split(":")[1] if ":" in header else "image/jpeg"
                raw_bytes = base64.b64decode(b64)
                photo_val = save_upload(raw_bytes, declared_content_type=ctype)
            except Exception:
                pass

        complaint = Complaint(
            title=complaint_in.location,
            description=complaint_in.description,
            category=complaint_in.hazard.value if complaint_in.hazard else None,
            complaint_type=(
                complaint_in.complaint_type.value if complaint_in.complaint_type else None
            ),
            address=complaint_in.location,
            latitude=(complaint_in.coords or {}).get("lat") if complaint_in.coords else None,
            longitude=(complaint_in.coords or {}).get("lng") if complaint_in.coords else None,
            photo_url=photo_val,
            ward_id=complaint_in.ward_id or current_user.ward_id,
            reported_by_user_id=current_user.id,
            status=ComplaintStatus.PENDING.value,
        )
        created = ComplaintRepository.create(db, complaint)
        ComplaintRepository.add_history(
            db,
            ComplaintStatusHistory(
                complaint_id=created.id,
                from_status="new",
                to_status=created.status,
                changed_by_user_id=current_user.id,
                notes="Complaint created",
                created_at=datetime.now(UTC),
            ),
        )
        # Auto-tag 3 condition tags
        from app.services.complaint_classification_service import ComplaintClassificationService

        init_tags = ComplaintClassificationService._fallback_tags(created)
        import json

        created = ComplaintRepository.update(db, created, {"tags": json.dumps(init_tags)})

        # S2-A05: emit a duplicate_detected notification if similar reports exist.
        duplicates = DuplicateDetectionService.find_possible_duplicates(db, created)
        if duplicates:
            NotificationService.notify_duplicate_detected(db, created, len(duplicates))
        return created

    @staticmethod
    def get_complaint(db: Session, complaint_id: int) -> Complaint:
        complaint = ComplaintRepository.get_by_id(db, complaint_id)
        if not complaint:
            raise NotFoundError("Complaint not found.")
        return complaint

    @staticmethod
    def assert_can_read(complaint: Complaint, current_user: User) -> None:
        """Raise PermissionDeniedError if a citizen tries to read another user's complaint.

        Crew and Admin roles have unrestricted read access to all complaints.
        Citizens may only read complaints they reported themselves.
        """
        if (
            current_user.role == UserRole.CITIZEN.value
            and complaint.reported_by_user_id != current_user.id
        ):
            raise PermissionDeniedError("You do not have permission to access this complaint.")

    @staticmethod
    def list_complaints(db: Session, *, filters: dict | None = None) -> tuple[list[Complaint], int]:
        return ComplaintRepository.list(db, filters=filters)

    @staticmethod
    def update_complaint(
        db: Session, complaint_id: int, complaint_in: ComplaintUpdate
    ) -> Complaint:
        complaint = ComplaintService.get_complaint(db, complaint_id)
        update_data = complaint_in.model_dump(exclude_unset=True)
        status = update_data.pop("status", None)
        if status is not None:
            complaint = ComplaintService.change_status(db, complaint_id, status)
        if update_data:
            complaint = ComplaintRepository.update(db, complaint, update_data)
        return complaint

    @staticmethod
    def change_status(
        db: Session,
        complaint_id: int,
        new_status: ComplaintStatus | str,
        *,
        changed_by_user_id: int | None = None,
    ) -> Complaint:
        complaint = ComplaintService.get_complaint(db, complaint_id)
        new_status_value = new_status.value if hasattr(new_status, "value") else str(new_status)
        current_status = complaint.status
        if new_status_value == current_status:
            return complaint
        if new_status_value not in _ALLOWED_TRANSITIONS.get(current_status, set()):
            raise InvalidStateTransitionError(
                f"Cannot move complaint from '{current_status}' to '{new_status_value}'."
            )

        complaint = ComplaintRepository.update(db, complaint, {"status": new_status_value})
        if new_status_value == ComplaintStatus.RESOLVED.value:
            complaint = ComplaintRepository.update(
                db, complaint, {"resolved_at": datetime.now(UTC)}
            )
            NotificationService.notify_complaint_resolved(db, complaint)
        if new_status_value == ComplaintStatus.CANCELLED.value:
            complaint = ComplaintRepository.update(
                db, complaint, {"cancelled_at": datetime.now(UTC)}
            )

        ComplaintRepository.add_history(
            db,
            ComplaintStatusHistory(
                complaint_id=complaint.id,
                from_status=current_status,
                to_status=new_status_value,
                changed_by_user_id=changed_by_user_id or complaint.reported_by_user_id,
                notes="Status changed",
                created_at=datetime.now(UTC),
            ),
        )
        return complaint

    @staticmethod
    def cancel_complaint(
        db: Session, complaint_id: int, *, changed_by_user_id: int | None = None
    ) -> Complaint:
        complaint = ComplaintService.get_complaint(db, complaint_id)
        if complaint.status != ComplaintStatus.PENDING.value:
            raise InvalidStateTransitionError("Only pending complaints can be cancelled.")
        return ComplaintService.change_status(
            db, complaint_id, ComplaintStatus.CANCELLED, changed_by_user_id=changed_by_user_id
        )

    @staticmethod
    def verify_complaint(
        db: Session,
        complaint_id: int,
        *,
        verified_by_user_id: int,
        notes: str | None = None,
    ) -> Complaint:
        """Admin review to verify a complaint cleanup."""
        complaint = ComplaintService.get_complaint(db, complaint_id)
        current_status = complaint.status
        new_status = ComplaintStatus.VERIFIED.value
        if current_status == new_status:
            return complaint
        if new_status not in _ALLOWED_TRANSITIONS.get(current_status, set()):
            raise InvalidStateTransitionError(
                f"Cannot move complaint from '{current_status}' to '{new_status}'."
            )
        complaint = ComplaintRepository.update(db, complaint, {"status": new_status})
        ComplaintRepository.add_history(
            db,
            ComplaintStatusHistory(
                complaint_id=complaint.id,
                from_status=current_status,
                to_status=new_status,
                changed_by_user_id=verified_by_user_id,
                notes=notes or "Verified by admin review",
                created_at=datetime.now(UTC),
            ),
        )
        return complaint

    @staticmethod
    def close_complaint(
        db: Session,
        complaint_id: int,
        *,
        closed_by_user_id: int,
        notes: str | None = None,
        after_photo_url: str | None = None,
    ) -> Complaint:
        """Supervisor confirmation to close a complaint and stamp resolved_at."""
        complaint = ComplaintService.get_complaint(db, complaint_id)
        current_status = complaint.status
        new_status = ComplaintStatus.CLOSED.value
        if current_status == new_status:
            return complaint
        if new_status not in _ALLOWED_TRANSITIONS.get(current_status, set()):
            raise InvalidStateTransitionError(
                f"Cannot move complaint from '{current_status}' to '{new_status}'."
            )
        now = datetime.now(UTC)
        update_fields: dict[str, object] = {
            "status": new_status,
            "resolved_at": complaint.resolved_at or now,
        }
        complaint = ComplaintRepository.update(db, complaint, update_fields)
        ComplaintRepository.add_history(
            db,
            ComplaintStatusHistory(
                complaint_id=complaint.id,
                from_status=current_status,
                to_status=new_status,
                changed_by_user_id=closed_by_user_id,
                notes=notes or "Closed by supervisor confirmation",
                created_at=now,
            ),
        )
        NotificationService.notify_complaint_resolved(db, complaint)
        from app.services.transparency_service import TransparencyService

        TransparencyService.auto_create_post_for_complaint(
            db,
            complaint,
            closed_by_user_id=closed_by_user_id,
            after_photo_url=after_photo_url,
        )
        return complaint
