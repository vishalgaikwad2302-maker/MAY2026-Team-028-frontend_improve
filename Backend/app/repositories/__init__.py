"""Repositories — the only layer that talks to the database."""

from app.repositories.complaint_repository import ComplaintRepository
from app.repositories.equipment_repository import EquipmentRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.repositories.vehicle_repository import VehicleRepository
from app.repositories.ward_repository import WardRepository
from app.repositories.worker_repository import WorkerRepository

__all__ = [
    "ComplaintRepository",
    "EquipmentRepository",
    "TaskRepository",
    "UserRepository",
    "VehicleRepository",
    "WardRepository",
    "WorkerRepository",
]
