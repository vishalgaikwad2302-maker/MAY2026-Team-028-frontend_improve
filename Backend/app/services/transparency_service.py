"""Transparency feed service (S2-F03, US-25).

Posts are published manually by crew/admin for a resolved complaint (RBAC is
enforced at the route layer via ``require_role``); auto-generating a post when
a complaint closes is separate follow-up work (S2-A04), not implemented here.
"""

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, InvalidStateTransitionError, NotFoundError
from app.models.complaint import Complaint, ComplaintStatus
from app.models.transparency import PostComment, TransparencyPost
from app.models.user import User
from app.repositories.complaint_repository import ComplaintRepository
from app.repositories.transparency_repository import PostCommentRepository, TransparencyRepository
from app.schemas.transparency import PostCommentCreate, TransparencyPostCreate

__all__ = ["TransparencyService"]


class TransparencyService:
    @staticmethod
    def create_post(
        db: Session, current_user: User, post_in: TransparencyPostCreate
    ) -> TransparencyPost:
        ward_id = None
        complaint_id = None

        if post_in.complaint_id is not None:
            complaint = ComplaintRepository.get_by_id(db, post_in.complaint_id)
            if not complaint:
                raise NotFoundError("Complaint not found.")
            if complaint.status not in {
                ComplaintStatus.RESOLVED.value,
                ComplaintStatus.VERIFIED.value,
                ComplaintStatus.CLOSED.value,
            }:
                raise InvalidStateTransitionError(
                    "A transparency post can only be published for a resolved or closed complaint."
                )
            if TransparencyRepository.get_by_complaint_id(db, complaint.id):
                raise ConflictError("A transparency post already exists for this complaint.")
            complaint_id = complaint.id
            ward_id = complaint.ward_id

        # Take up to 3 images if provided
        images_list = post_in.images[:3] if post_in.images else None

        post = TransparencyPost(
            complaint_id=complaint_id,
            ward_id=ward_id,
            title=post_in.title,
            description=post_in.description,
            images=images_list,
            before_photo_url=post_in.before_photo_url,
            after_photo_url=post_in.after_photo_url,
            posted_by_user_id=current_user.id,
        )
        return TransparencyRepository.create(db, post)

    @staticmethod
    def auto_create_post_for_complaint(
        db: Session,
        complaint: Complaint,
        *,
        closed_by_user_id: int | None = None,
        after_photo_url: str | None = None,
    ) -> TransparencyPost | None:
        """Auto-generate a TransparencyPost when a complaint is closed (S2-A04)."""
        existing = TransparencyRepository.get_by_complaint_id(db, complaint.id)
        if existing:
            return existing

        if not after_photo_url:
            from app.models.task import Task, TaskStatus

            task = (
                db.query(Task)
                .filter(
                    Task.complaint_id == complaint.id,
                    Task.status == TaskStatus.COMPLETED.value,
                )
                .first()
            )
            if task and task.completion_photo_url:
                after_photo_url = task.completion_photo_url

        post = TransparencyPost(
            complaint_id=complaint.id,
            ward_id=complaint.ward_id,
            title=f"Cleanup: {complaint.title}",
            description=complaint.description,
            before_photo_url=complaint.photo_url,
            after_photo_url=after_photo_url,
            applause_count=0,
            posted_by_user_id=closed_by_user_id or complaint.reported_by_user_id,
        )
        return TransparencyRepository.create(db, post)

    @staticmethod
    def get_post(db: Session, post_id: int) -> TransparencyPost:
        post = TransparencyRepository.get_by_id(db, post_id)
        if not post:
            raise NotFoundError("Transparency post not found.")
        return post

    @staticmethod
    def list_posts(
        db: Session, *, ward_id: int | None = None, page: int = 1, page_size: int = 20
    ) -> tuple[list[TransparencyPost], int]:
        return TransparencyRepository.list(
            db, filters={"ward_id": ward_id}, page=page, page_size=page_size
        )

    @staticmethod
    def applaud(db: Session, post_id: int) -> TransparencyPost:
        post = TransparencyService.get_post(db, post_id)
        return TransparencyRepository.increment_applause(db, post)

    @staticmethod
    def add_comment(
        db: Session, post_id: int, current_user: User, comment_in: PostCommentCreate
    ) -> PostComment:
        TransparencyService.get_post(db, post_id)
        comment = PostComment(post_id=post_id, user_id=current_user.id, comment=comment_in.comment)
        return PostCommentRepository.create(db, comment)

    @staticmethod
    def list_comments(db: Session, post_id: int) -> list[PostComment]:
        TransparencyService.get_post(db, post_id)
        return PostCommentRepository.list_by_post(db, post_id)
