"""Bulk waste pickup API routes (S2-F04, US-31)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_role
from app.models.user import User, UserRole
from app.schemas.bulk_pickup import (
    BulkPickupAssign,
    BulkPickupCreate,
    BulkPickupRead,
    BulkPickupUpdate,
)
from app.schemas.common import Page
from app.services.bulk_pickup_service import BulkPickupService

router = APIRouter(prefix="/bulk-pickups", tags=["Bulk Pickups"])


@router.post(
    "",
    response_model=BulkPickupRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.CITIZEN))],
)
def create_bulk_pickup(
    pickup_in: BulkPickupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BulkPickupRead:
    pickup = BulkPickupService.create_pickup(db, current_user, pickup_in)
    return BulkPickupRead.model_validate(pickup)


@router.get("", response_model=Page[BulkPickupRead])
def list_bulk_pickups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status_filter: str | None = None,
    ward_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> Page[BulkPickupRead]:
    filters: dict = {"status": status_filter, "ward_id": ward_id}
    # Citizens are scoped to their own pickup requests only.
    if current_user.role == UserRole.CITIZEN.value:
        filters["requested_by_user_id"] = current_user.id

    items, total = BulkPickupService.list_pickups(
        db, filters=filters, page=page, page_size=page_size
    )
    return Page[BulkPickupRead].build(
        [BulkPickupRead.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{pickup_id}", response_model=BulkPickupRead)
def get_bulk_pickup(
    pickup_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BulkPickupRead:
    pickup = BulkPickupService.get_pickup(db, pickup_id)
    BulkPickupService.assert_can_read(pickup, current_user)
    return BulkPickupRead.model_validate(pickup)


@router.patch(
    "/{pickup_id}",
    response_model=BulkPickupRead,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def update_bulk_pickup(
    pickup_id: int, update_in: BulkPickupUpdate, db: Session = Depends(get_db)
) -> BulkPickupRead:
    return BulkPickupRead.model_validate(BulkPickupService.update_pickup(db, pickup_id, update_in))


@router.post("/{pickup_id}/cancel", response_model=BulkPickupRead)
def cancel_bulk_pickup(
    pickup_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BulkPickupRead:
    return BulkPickupRead.model_validate(
        BulkPickupService.cancel_pickup(db, pickup_id, current_user)
    )


@router.post(
    "/{pickup_id}/assign",
    response_model=BulkPickupRead,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def assign_bulk_pickup(
    pickup_id: int, assign_in: BulkPickupAssign, db: Session = Depends(get_db)
) -> BulkPickupRead:
    return BulkPickupRead.model_validate(
        BulkPickupService.assign_pickup(db, pickup_id, assign_in)
    )
