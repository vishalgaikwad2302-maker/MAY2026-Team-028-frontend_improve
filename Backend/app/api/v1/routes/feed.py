"""Public feed API routes (S2-F03, US-25).

Provides /feed, /feed/{id}/applaud, and /feed/{id}/comments endpoints.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.common import Page
from app.schemas.transparency import (
    PostCommentCreate,
    PostCommentRead,
    TransparencyPostRead,
)
from app.services.transparency_service import TransparencyService

router = APIRouter(prefix="/feed", tags=["Feed"])


@router.get("", response_model=Page[TransparencyPostRead])
def list_feed_posts(
    db: Session = Depends(get_db),
    ward_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> Page[TransparencyPostRead]:
    """Return paginated public feed posts with optional ward filter."""
    items, total = TransparencyService.list_posts(
        db, ward_id=ward_id, page=page, page_size=page_size
    )
    return Page[TransparencyPostRead].build(
        [TransparencyPostRead.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{post_id}", response_model=TransparencyPostRead)
def get_feed_post(post_id: int, db: Session = Depends(get_db)) -> TransparencyPostRead:
    """Return a single feed post by ID."""
    return TransparencyPostRead.model_validate(TransparencyService.get_post(db, post_id))


@router.post("/{post_id}/applaud", response_model=TransparencyPostRead)
def applaud_feed_post(post_id: int, db: Session = Depends(get_db)) -> TransparencyPostRead:
    """Public endpoint to bump applaud counter on a feed post."""
    return TransparencyPostRead.model_validate(TransparencyService.applaud(db, post_id))


@router.get("/{post_id}/comments", response_model=list[PostCommentRead])
def list_feed_post_comments(post_id: int, db: Session = Depends(get_db)) -> list[PostCommentRead]:
    """Return list of comments on a feed post."""
    return [
        PostCommentRead.model_validate(comment)
        for comment in TransparencyService.list_comments(db, post_id)
    ]


@router.post(
    "/{post_id}/comments", response_model=PostCommentRead, status_code=status.HTTP_201_CREATED
)
def create_feed_post_comment(
    post_id: int,
    comment_in: PostCommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PostCommentRead:
    """Add a comment to a feed post (requires auth)."""
    comment = TransparencyService.add_comment(db, post_id, current_user, comment_in)
    return PostCommentRead.model_validate(comment)

