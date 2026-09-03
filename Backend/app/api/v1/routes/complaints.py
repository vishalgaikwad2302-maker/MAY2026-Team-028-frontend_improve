"""Complaint API routes."""

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_role
from app.core.exceptions import NotFoundError
from app.models.complaint import Complaint
from app.models.user import User, UserRole
from app.repositories.complaint_repository import ComplaintRepository
from app.schemas.common import Page
from app.schemas.complaint import (
    ComplaintCategory,
    ComplaintClassifyRead,
    ComplaintClose,
    ComplaintRead,
    ComplaintResolve,
    ComplaintStatus,
    ComplaintStatusHistoryRead,
    ComplaintSubmit,
    ComplaintType,
    ComplaintUpdate,
    ComplaintVerify,
    DuplicateCheckRequest,
)
from app.schemas.feedback import FeedbackCreate, FeedbackRead
from app.services.complaint_classification_service import ComplaintClassificationService
from app.services.complaint_service import ComplaintService
from app.services.duplicate_detection_service import DuplicateDetectionService
from app.services.feedback_service import FeedbackService
from app.services.upload_service import UploadRejectedError, save_upload

router = APIRouter(prefix="/complaints", tags=["Complaints"])


def _to_read_model(complaint: Complaint) -> ComplaintRead:
    return ComplaintRead.model_validate(complaint)


@router.post("", response_model=ComplaintRead, status_code=status.HTTP_201_CREATED)
def create_complaint(
    complaint_in: ComplaintSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ComplaintRead:
    complaint = ComplaintService.create_complaint(db, current_user, complaint_in)
    return _to_read_model(complaint)


@router.get("", response_model=Page[ComplaintRead])
def list_complaints(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    search: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    ward_id: int | None = None,
    complaint_type: ComplaintType | None = None,
    category: ComplaintCategory | None = None,
    page: int = 1,
    page_size: int = 20,
) -> Page[ComplaintRead]:
    filters: dict = {
        "search": search,
        "status": status_filter,
        "ward_id": ward_id,
        "complaint_type": complaint_type.value if complaint_type else None,
        "category": category.value if category else None,
        "page": page,
        "page_size": page_size,
    }
    # Citizens are scoped to their own complaints only.
    if current_user.role == UserRole.CITIZEN.value:
        filters["reported_by_user_id"] = current_user.id

    items, total = ComplaintService.list_complaints(db, filters=filters)
    return Page[ComplaintRead].build(
        [_to_read_model(item) for item in items], page=page, page_size=page_size, total=total
    )


# NOTE: literal paths must stay above "/{complaint_id}". Starlette matches routes
# in registration order, so a "/high-risk" declared below the parameterised route
# would be swallowed by it and fail int coercion with a 422.


@router.get("/high-risk", response_model=Page[ComplaintRead])
def high_risk_complaints(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = 1,
    page_size: int = 20,
) -> Page[ComplaintRead]:
    items, total = ComplaintService.list_complaints(
        db,
        filters={
            "page": 1,
            "page_size": 500,
        },
    )
    high_risk_categories = {
        ComplaintCategory.RISK_TO_CHILDREN.value.lower(),
        ComplaintCategory.MOSQUITO_BREEDING.value.lower(),
    }
    high_risk = [
        item
        for item in items
        if (item.category or "").lower() in high_risk_categories
        or (item.priority or "").lower() in {"high", "urgent", "critical"}
    ]
    start = (page - 1) * page_size
    end = start + page_size
    sliced = high_risk[start:end]
    return Page[ComplaintRead].build(
        [_to_read_model(item) for item in sliced],
        page=page,
        page_size=page_size,
        total=len(high_risk),
    )


@router.post("/upload-photo")
async def upload_complaint_photo(
    photo: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    contents = await photo.read()
    try:
        url = save_upload(contents, declared_content_type=photo.content_type or "")
    except UploadRejectedError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return {
        "url": url,
        "content_type": photo.content_type,
        "size_bytes": len(contents),
    }


@router.post("/{complaint_id}/photo", response_model=ComplaintRead)
async def attach_complaint_photo(
    complaint_id: int,
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ComplaintRead:
    """Validate and attach an evidence photo to an existing complaint."""
    complaint = ComplaintService.get_complaint(db, complaint_id)
    ComplaintService.assert_can_read(complaint, current_user)
    contents = await photo.read()
    try:
        url = save_upload(contents, declared_content_type=photo.content_type or "")
    except UploadRejectedError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    complaint = ComplaintRepository.update(db, complaint, {"photo_url": url})
    return _to_read_model(complaint)


@router.post("/duplicate-check")
def duplicate_check(
    request: DuplicateCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """Return advisory matches for a complaint draft before submission."""
    draft = Complaint(
        id=0,
        title=request.location,
        description=request.description,
        latitude=(request.coords or {}).get("lat") if request.coords else None,
        longitude=(request.coords or {}).get("lng") if request.coords else None,
        ward_id=request.ward_id or current_user.ward_id,
        reported_by_user_id=current_user.id,
        status="pending",
    )
    matches = DuplicateDetectionService.find_possible_duplicates(db, draft)
    return [
        {**match, "complaint": _to_read_model(match["complaint"]).model_dump(mode="json")}
        for match in matches
    ]


@router.get("/{complaint_id}", response_model=ComplaintRead)
def get_complaint(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ComplaintRead:
    complaint = ComplaintService.get_complaint(db, complaint_id)
    ComplaintService.assert_can_read(complaint, current_user)
    return _to_read_model(complaint)


@router.patch("/{complaint_id}", response_model=ComplaintRead)
def update_complaint(
    complaint_id: int,
    complaint_in: ComplaintUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ComplaintRead:
    complaint = ComplaintService.get_complaint(db, complaint_id)
    ComplaintService.assert_can_read(complaint, current_user)
    return _to_read_model(ComplaintService.update_complaint(db, complaint_id, complaint_in))


@router.patch(
    "/{complaint_id}/status",
    response_model=ComplaintRead,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.CREW))],
)
def change_complaint_status(
    complaint_id: int,
    status_value: ComplaintStatus = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ComplaintRead:
    return _to_read_model(
        ComplaintService.change_status(
            db,
            complaint_id,
            status_value,
            changed_by_user_id=current_user.id,
        )
    )


@router.post(
    "/{complaint_id}/resolve",
    response_model=ComplaintRead,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.CREW))],
)
def resolve_complaint(
    complaint_id: int,
    resolve_in: ComplaintResolve = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ComplaintRead:
    return _to_read_model(
        ComplaintService.resolve_complaint(
            db,
            complaint_id,
            completion_photos=resolve_in.completion_photos,
            resolution_notes=resolve_in.resolution_notes,
            resolved_by_user_id=current_user.id,
        )
    )


@router.patch(
    "/{complaint_id}/verify",
    response_model=ComplaintRead,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def verify_complaint(
    complaint_id: int,
    verify_in: ComplaintVerify | None = Body(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ComplaintRead:
    return _to_read_model(
        ComplaintService.verify_complaint(
            db,
            complaint_id,
            verified_by_user_id=current_user.id,
            notes=verify_in.notes if verify_in else None,
        )
    )


@router.patch(
    "/{complaint_id}/close",
    response_model=ComplaintRead,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def close_complaint(
    complaint_id: int,
    close_in: ComplaintClose | None = Body(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ComplaintRead:
    return _to_read_model(
        ComplaintService.close_complaint(
            db,
            complaint_id,
            closed_by_user_id=current_user.id,
            notes=close_in.notes if close_in else None,
            after_photo_url=close_in.after_photo_url if close_in else None,
        )
    )


@router.post("/{complaint_id}/cancel", response_model=ComplaintRead, status_code=status.HTTP_200_OK)
def cancel_complaint(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ComplaintRead:
    return _to_read_model(
        ComplaintService.cancel_complaint(db, complaint_id, changed_by_user_id=current_user.id)
    )


@router.get("/{complaint_id}/history", response_model=list[ComplaintStatusHistoryRead])
def complaint_history(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ComplaintStatusHistoryRead]:
    complaint = ComplaintService.get_complaint(db, complaint_id)
    ComplaintService.assert_can_read(complaint, current_user)
    return [
        ComplaintStatusHistoryRead.model_validate(history)
        for history in ComplaintRepository.get_history(db, complaint_id)
    ]


@router.post(
    "/{complaint_id}/feedback", response_model=FeedbackRead, status_code=status.HTTP_201_CREATED
)
def submit_complaint_feedback(
    complaint_id: int,
    feedback_in: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FeedbackRead:
    complaint = ComplaintService.get_complaint(db, complaint_id)
    feedback = FeedbackService.submit_feedback(db, complaint, current_user, feedback_in)
    return FeedbackRead.model_validate(feedback)


@router.get("/{complaint_id}/feedback", response_model=FeedbackRead)
def get_complaint_feedback(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FeedbackRead:
    complaint = ComplaintService.get_complaint(db, complaint_id)
    ComplaintService.assert_can_read(complaint, current_user)
    feedback = FeedbackService.get_feedback(db, complaint_id)
    if not feedback:
        raise NotFoundError("No feedback has been submitted for this complaint.")
    return FeedbackRead.model_validate(feedback)


@router.post(
    "/{complaint_id}/classify",
    response_model=ComplaintClassifyRead,
    dependencies=[Depends(require_role(UserRole.CREW, UserRole.ADMIN))],
)
def classify_complaint(
    complaint_id: int,
    db: Session = Depends(get_db),
) -> ComplaintClassifyRead:
    """Classify a complaint's hazard category via Claude, falling back to keyword matching."""
    complaint = ComplaintService.get_complaint(db, complaint_id)
    result = ComplaintClassificationService.classify(db, complaint)
    return ComplaintClassifyRead(
        complaint=_to_read_model(complaint),
        category=result.category,
        tags=result.tags,
        source=result.source,
        confidence=result.confidence,
        reasoning=result.reasoning,
    )


@router.get(
    "/{complaint_id}/duplicates",
    dependencies=[Depends(require_role(UserRole.CREW, UserRole.ADMIN))],
)
def get_duplicates(
    complaint_id: int,
    db: Session = Depends(get_db),
) -> list[dict]:
    complaint = ComplaintService.get_complaint(db, complaint_id)
    matches = DuplicateDetectionService.find_possible_duplicates(db, complaint)
    # The service hands back the matched ORM row under "complaint"; convert it to
    # the read DTO so the response is JSON-serialisable.
    return [
        {**match, "complaint": _to_read_model(match["complaint"]).model_dump(mode="json")}
        for match in matches
    ]
