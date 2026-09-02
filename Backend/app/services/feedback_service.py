"""Feedback service — post-cleanup rating on a resolved complaint (US-24)."""

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, InvalidStateTransitionError, PermissionDeniedError
from app.models.complaint import Complaint, ComplaintStatus
from app.models.feedback import Feedback
from app.models.user import User
from app.repositories.feedback_repository import FeedbackRepository
from app.schemas.feedback import FeedbackCreate

__all__ = ["FeedbackService"]


class FeedbackService:
    @staticmethod
    def submit_feedback(
        db: Session, complaint: Complaint, current_user: User, feedback_in: FeedbackCreate
    ) -> Feedback:
        """Create the one-and-only feedback row for a resolved complaint.

        Only the citizen who reported the complaint may leave feedback on it —
        crew/admin can read feedback (via the usual complaint read rules) but
        submitting is scoped to the reporter, same as the frontend flow.
        """
        if complaint.reported_by_user_id != current_user.id:
            raise PermissionDeniedError("You can only leave feedback on your own complaint.")

        if complaint.status not in (
            ComplaintStatus.RESOLVED.value,
            ComplaintStatus.VERIFIED.value,
            ComplaintStatus.CLOSED.value,
        ):
            raise InvalidStateTransitionError(
                "Feedback can only be submitted once a complaint is resolved."
            )

        if FeedbackRepository.get_by_complaint_id(db, complaint.id):
            raise ConflictError("Feedback has already been submitted for this complaint.")

        feedback = Feedback(
            complaint_id=complaint.id,
            submitted_by_user_id=current_user.id,
            rating=feedback_in.rating,
            comment=feedback_in.comment,
        )
        return FeedbackRepository.create(db, feedback)

    @staticmethod
    def get_feedback(db: Session, complaint_id: int) -> Feedback | None:
        return FeedbackRepository.get_by_complaint_id(db, complaint_id)
