"""Ward collection schedule API routes (S2-F04, US-32/US-33)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_role
from app.models.user import UserRole
from app.schemas.collection_schedule import (
    CollectionScheduleCreate,
    CollectionScheduleRead,
    CollectionScheduleUpdate,
    ScheduleReminderRead,
)
from app.services.collection_schedule_service import CollectionScheduleService

router = APIRouter(prefix="/schedule", tags=["Collection Schedule"])


# NOTE: literal paths must stay above "/{schedule_id}" for the same reason
# documented in complaints.py — Starlette matches routes in registration
# order, and PATCH/DELETE below use an int-typed path parameter at this level.


@router.get(
    "/reminders",
    response_model=list[ScheduleReminderRead],
    dependencies=[Depends(get_current_user)],
)
def get_schedule_reminders(
    ward_id: int, db: Session = Depends(get_db)
) -> list[ScheduleReminderRead]:
    return CollectionScheduleService.get_reminders(db, ward_id)


@router.get(
    "", response_model=list[CollectionScheduleRead], dependencies=[Depends(get_current_user)]
)
def get_ward_schedule(ward_id: int, db: Session = Depends(get_db)) -> list[CollectionScheduleRead]:
    return [
        CollectionScheduleRead.model_validate(row)
        for row in CollectionScheduleService.get_ward_schedule(db, ward_id)
    ]


@router.post(
    "",
    response_model=CollectionScheduleRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def create_schedule_row(
    schedule_in: CollectionScheduleCreate, db: Session = Depends(get_db)
) -> CollectionScheduleRead:
    return CollectionScheduleRead.model_validate(
        CollectionScheduleService.create_schedule(db, schedule_in)
    )


@router.patch(
    "/{schedule_id}",
    response_model=CollectionScheduleRead,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def update_schedule_row(
    schedule_id: int, update_in: CollectionScheduleUpdate, db: Session = Depends(get_db)
) -> CollectionScheduleRead:
    return CollectionScheduleRead.model_validate(
        CollectionScheduleService.update_schedule(db, schedule_id, update_in)
    )


@router.delete(
    "/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def delete_schedule_row(schedule_id: int, db: Session = Depends(get_db)) -> None:
    CollectionScheduleService.delete_schedule(db, schedule_id)
