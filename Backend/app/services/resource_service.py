"""Resource service for worker/vehicle/equipment status updates."""

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
from app.models.equipment import Equipment, EquipmentStatus
from app.models.user import User, UserRole
from app.models.vehicle import Vehicle, VehicleStatus
from app.models.worker import Worker, WorkerStatus
from app.repositories.equipment_repository import EquipmentRepository
from app.repositories.user_repository import UserRepository
from app.repositories.vehicle_repository import VehicleRepository
from app.repositories.worker_repository import WorkerRepository
from app.schemas.resources import WorkerCreate

__all__ = ["ResourceService"]


class ResourceService:
    @staticmethod
    def create_worker(db: Session, worker_in: WorkerCreate) -> Worker:
        """Onboard a new field worker and provision an active crew User account."""
        user_id = None
        if worker_in.email:
            email = worker_in.email.strip().lower()
            existing_user = UserRepository.get_by_email(db, email)
            if existing_user:
                if existing_user.role != UserRole.CREW.value:
                    raise ConflictError(f"Email {email} is already registered with role '{existing_user.role}'.")
                user_id = existing_user.id
            else:
                raw_password = worker_in.password or "crew123"
                new_user = User(
                    email=email,
                    hashed_password=hash_password(raw_password),
                    full_name=worker_in.full_name,
                    phone=worker_in.phone,
                    role=UserRole.CREW.value,
                    ward_id=worker_in.ward_id,
                    is_active=True,
                )
                db.add(new_user)
                db.flush()
                user_id = new_user.id

        worker = Worker(
            full_name=worker_in.full_name,
            employee_code=worker_in.employee_code,
            email=worker_in.email.strip().lower() if worker_in.email else None,
            phone=worker_in.phone,
            role_title=worker_in.role_title,
            ward_id=worker_in.ward_id,
            user_id=user_id,
            status=worker_in.status.value if hasattr(worker_in.status, "value") else worker_in.status,
            is_active=worker_in.is_active,
        )
        return WorkerRepository.create(db, worker)

    @staticmethod
    def get_worker(db: Session, worker_id: int) -> Worker:
        worker = WorkerRepository.get_by_id(db, worker_id)
        if not worker:
            raise NotFoundError("Worker not found.")
        return worker

    @staticmethod
    def check_worker_available(db: Session, worker_id: int) -> Worker:
        worker = ResourceService.get_worker(db, worker_id)
        if not worker.is_active or worker.status != WorkerStatus.AVAILABLE.value:
            raise ConflictError(f"Worker {worker_id} is not available.")
        return worker

    @staticmethod
    def get_vehicle(db: Session, vehicle_id: int) -> Vehicle:
        vehicle = VehicleRepository.get_by_id(db, vehicle_id)
        if not vehicle:
            raise NotFoundError("Vehicle not found.")
        return vehicle

    @staticmethod
    def check_vehicle_available(db: Session, vehicle_id: int) -> Vehicle:
        vehicle = ResourceService.get_vehicle(db, vehicle_id)
        if not vehicle.is_active or vehicle.status != VehicleStatus.AVAILABLE.value:
            raise ConflictError(f"Vehicle {vehicle_id} is not available.")
        return vehicle

    @staticmethod
    def get_equipment(db: Session, equipment_id: int) -> Equipment:
        equipment = EquipmentRepository.get_by_id(db, equipment_id)
        if not equipment:
            raise NotFoundError("Equipment not found.")
        return equipment

    @staticmethod
    def check_equipment_available(db: Session, equipment_id: int) -> Equipment:
        equipment = ResourceService.get_equipment(db, equipment_id)
        if not equipment.is_active or equipment.status != EquipmentStatus.AVAILABLE.value:
            raise ConflictError(f"Equipment {equipment_id} is not available.")
        return equipment

    @staticmethod
    def update_worker_status(
        db: Session, worker_id: int, *, status: str | None = None, **updates
    ) -> Worker:
        worker = ResourceService.get_worker(db, worker_id)
        payload = dict(updates)
        if status is not None:
            payload["status"] = status
        return WorkerRepository.update(db, worker, payload)

    @staticmethod
    def update_vehicle_status(
        db: Session, vehicle_id: int, *, status: str | None = None, **updates
    ) -> Vehicle:
        vehicle = ResourceService.get_vehicle(db, vehicle_id)
        payload = dict(updates)
        if status is not None:
            payload["status"] = status
        return VehicleRepository.update(db, vehicle, payload)

    @staticmethod
    def update_equipment_status(
        db: Session, equipment_id: int, *, status: str | None = None, **updates
    ) -> Equipment:
        equipment = ResourceService.get_equipment(db, equipment_id)
        payload = dict(updates)
        if status is not None:
            payload["status"] = status
        return EquipmentRepository.update(db, equipment, payload)
