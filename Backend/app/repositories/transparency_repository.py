"""Transparency post + comment repositories."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.transparency import PostComment, TransparencyPost

__all__ = ["TransparencyRepository", "PostCommentRepository"]


class TransparencyRepository:
    @staticmethod
    def get_by_id(db: Session, post_id: int) -> TransparencyPost | None:
        return db.get(TransparencyPost, post_id)

    @staticmethod
    def get_by_complaint_id(db: Session, complaint_id: int) -> TransparencyPost | None:
        return db.scalar(
            select(TransparencyPost).where(TransparencyPost.complaint_id == complaint_id)
        )

    @staticmethod
    def create(db: Session, post: TransparencyPost) -> TransparencyPost:
        db.add(post)
        db.commit()
        db.refresh(post)
        return post

    @staticmethod
    def list(
        db: Session, *, filters: dict[str, Any] | None = None, page: int = 1, page_size: int = 20
    ) -> tuple[list[TransparencyPost], int]:
        filters = filters or {}
        stmt = select(TransparencyPost)

        ward_id = filters.get("ward_id")
        if ward_id is not None:
            stmt = stmt.where(TransparencyPost.ward_id == ward_id)

        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        stmt = (
            stmt.order_by(TransparencyPost.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(db.scalars(stmt).all()), total

    @staticmethod
    def increment_applause(db: Session, post: TransparencyPost) -> TransparencyPost:
        post.applause_count += 1
        db.commit()
        db.refresh(post)
        return post


class PostCommentRepository:
    @staticmethod
    def create(db: Session, comment: PostComment) -> PostComment:
        db.add(comment)
        db.commit()
        db.refresh(comment)
        return comment

    @staticmethod
    def list_by_post(db: Session, post_id: int) -> list[PostComment]:
        stmt = select(PostComment).where(PostComment.post_id == post_id)
        return list(db.scalars(stmt.order_by(PostComment.created_at.asc())).all())
