"""Resource API routes."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.models.equipment import Equipment
from app.models.user import UserRole
from app.models.vehicle import Vehicle
from app.models.worker import Worker
from app.repositories.equipment_repository import EquipmentRepository
from app.repositories.vehicle_repository import VehicleRepository
from app.repositories.worker_repository import WorkerRepository
from app.schemas.resources import (
    EquipmentRead,
    EquipmentStatus,
    VehicleRead,
    VehicleStatus,
    WorkerCreate,
    WorkerRead,
    WorkerStatus,
)
from app.services.resource_service import ResourceService

router = APIRouter(prefix="/resources", tags=["Resources"])


def _to_worker_read(worker: Worker) -> WorkerRead:
    return WorkerRead.model_validate(worker)


def _to_vehicle_read(vehicle: Vehicle) -> VehicleRead:
    return VehicleRead.model_validate(vehicle)


def _to_equipment_read(equipment: Equipment) -> EquipmentRead:
    return EquipmentRead.model_validate(equipment)


@router.get(
    "/workers",
    response_model=list[WorkerRead],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def list_workers(db: Session = Depends(get_db)) -> list[WorkerRead]:
    return [_to_worker_read(worker) for worker in WorkerRepository.list(db)]


@router.post(
    "/workers",
    response_model=WorkerRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
    summary="Onboard a new field worker with login credentials",
)
def create_worker(
    worker_in: WorkerCreate, db: Session = Depends(get_db)
) -> WorkerRead:
    worker = ResourceService.create_worker(db, worker_in)
    return _to_worker_read(worker)


@router.patch(
    "/workers/{worker_id}/status",
    response_model=WorkerRead,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def update_worker_status(
    worker_id: int, status_value: WorkerStatus, db: Session = Depends(get_db)
) -> WorkerRead:
    worker = ResourceService.update_worker_status(db, worker_id, status=status_value.value)
    return _to_worker_read(worker)


@router.get(
    "/vehicles",
    response_model=list[VehicleRead],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.CREW))],
)
def list_vehicles(db: Session = Depends(get_db)) -> list[VehicleRead]:
    return [_to_vehicle_read(vehicle) for vehicle in VehicleRepository.list(db)]


@router.patch(
    "/vehicles/{vehicle_id}/status",
    response_model=VehicleRead,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.CREW))],
)
def update_vehicle_status(
    vehicle_id: int, status_value: VehicleStatus, db: Session = Depends(get_db)
) -> VehicleRead:
    vehicle = ResourceService.update_vehicle_status(db, vehicle_id, status=status_value.value)
    return _to_vehicle_read(vehicle)


@router.get(
    "/equipment",
    response_model=list[EquipmentRead],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.CREW))],
)
def list_equipment(db: Session = Depends(get_db)) -> list[EquipmentRead]:
    return [_to_equipment_read(equipment) for equipment in EquipmentRepository.list(db)]


@router.patch(
    "/equipment/{equipment_id}/status",
    response_model=EquipmentRead,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.CREW))],
)
def update_equipment_status(
    equipment_id: int,
    status_value: EquipmentStatus,
    db: Session = Depends(get_db),
) -> EquipmentRead:
    equipment = ResourceService.update_equipment_status(db, equipment_id, status=status_value.value)
    return _to_equipment_read(equipment)
