"""Ward API routes."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_role
from app.core.exceptions import NotFoundError
from app.models.user import User, UserRole
from app.repositories.ward_repository import WardRepository
from app.schemas.ward import WardRead

router = APIRouter(prefix="/wards", tags=["Wards"])


def _to_read_model(ward) -> WardRead:
    return WardRead.model_validate(ward)


@router.get("", response_model=list[WardRead], status_code=status.HTTP_200_OK)
def list_wards(db: Session = Depends(get_db)) -> list[WardRead]:
    wards = WardRepository.list(db)
    return [_to_read_model(ward) for ward in wards]


# NOTE: "/me" must stay above "/{ward_id}". Starlette matches routes in
# registration order, so declaring it below would make "/wards/me" bind
# ward_id="me" and fail int coercion with a 422.


@router.get(
    "/me",
    response_model=WardRead,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role(UserRole.CITIZEN, UserRole.CREW, UserRole.ADMIN))],
)
def get_my_ward(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> WardRead:
    if current_user.ward_id is None:
        raise NotFoundError("Ward not found.")
    ward = WardRepository.get_by_id(db, current_user.ward_id)
    if ward is None:
        raise NotFoundError("Ward not found.")
    return _to_read_model(ward)


@router.get("/{ward_id}", response_model=WardRead, status_code=status.HTTP_200_OK)
def get_ward(ward_id: int, db: Session = Depends(get_db)) -> WardRead:
    ward = WardRepository.get_by_id(db, ward_id)
    if ward is None:
        raise NotFoundError("Ward not found.")
    return _to_read_model(ward)
