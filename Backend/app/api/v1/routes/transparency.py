"""Public transparency feed API routes (S2-F03, US-25).

Reading the feed, a post's detail, and its comments is public — no
authentication required, matching the "public transparency feed" framing.
Publishing a post is restricted to crew/admin; leaving a comment requires a
logged-in user (a comment is always attributed to one); applauding is a
public, anonymous counter bump.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_role
from app.models.user import User, UserRole
from app.schemas.common import Page
from app.schemas.transparency import (
    PostCommentCreate,
    PostCommentRead,
    TransparencyPostCreate,
    TransparencyPostRead,
)
from app.services.transparency_service import TransparencyService

router = APIRouter(prefix="/transparency", tags=["Transparency"])


@router.get("", response_model=Page[TransparencyPostRead])
def list_transparency_posts(
    db: Session = Depends(get_db),
    ward_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> Page[TransparencyPostRead]:
    items, total = TransparencyService.list_posts(
        db, ward_id=ward_id, page=page, page_size=page_size
    )
    return Page[TransparencyPostRead].build(
        [TransparencyPostRead.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post(
    "",
    response_model=TransparencyPostRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.CREW, UserRole.ADMIN))],
)
def create_transparency_post(
    post_in: TransparencyPostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TransparencyPostRead:
    post = TransparencyService.create_post(db, current_user, post_in)
    return TransparencyPostRead.model_validate(post)


@router.get("/{post_id}", response_model=TransparencyPostRead)
def get_transparency_post(post_id: int, db: Session = Depends(get_db)) -> TransparencyPostRead:
    return TransparencyPostRead.model_validate(TransparencyService.get_post(db, post_id))


@router.post("/{post_id}/applaud", response_model=TransparencyPostRead)
def applaud_transparency_post(post_id: int, db: Session = Depends(get_db)) -> TransparencyPostRead:
    return TransparencyPostRead.model_validate(TransparencyService.applaud(db, post_id))


@router.get("/{post_id}/comments", response_model=list[PostCommentRead])
def list_post_comments(post_id: int, db: Session = Depends(get_db)) -> list[PostCommentRead]:
    return [
        PostCommentRead.model_validate(comment)
        for comment in TransparencyService.list_comments(db, post_id)
    ]


@router.post(
    "/{post_id}/comments", response_model=PostCommentRead, status_code=status.HTTP_201_CREATED
)
def create_post_comment(
    post_id: int,
    comment_in: PostCommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PostCommentRead:
    comment = TransparencyService.add_comment(db, post_id, current_user, comment_in)
    return PostCommentRead.model_validate(comment)
