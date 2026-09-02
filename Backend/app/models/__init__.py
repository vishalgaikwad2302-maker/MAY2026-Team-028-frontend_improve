"""SQLAlchemy ORM models — the persistence shape of each entity."""

from app.models.bulk_pickup import (
    BulkPickup,
    BulkPickupCategory,
    BulkPickupLoadBand,
    BulkPickupStatus,
)
from app.models.collection_schedule import CollectionFrequency, CollectionSchedule
from app.models.complaint import Complaint, ComplaintStatus, ComplaintStatusHistory
from app.models.equipment import Equipment, EquipmentStatus
from app.models.feedback import Feedback
from app.models.notification import Notification, NotificationType
from app.models.task import Task, TaskStatus, task_equipment, task_workers
from app.models.transparency import PostComment, TransparencyPost
from app.models.user import User, UserRole
from app.models.vehicle import Vehicle, VehicleStatus
from app.models.ward import Ward
from app.models.worker import Worker, WorkerStatus

__all__ = [
    "BulkPickup",
    "BulkPickupCategory",
    "BulkPickupLoadBand",
    "BulkPickupStatus",
    "CollectionFrequency",
    "CollectionSchedule",
    "Complaint",
    "ComplaintStatus",
    "ComplaintStatusHistory",
    "Equipment",
    "EquipmentStatus",
    "Feedback",
    "Notification",
    "NotificationType",
    "PostComment",
    "Task",
    "TaskStatus",
    "TransparencyPost",
    "User",
    "UserRole",
    "Vehicle",
    "VehicleStatus",
    "Ward",
    "Worker",
    "WorkerStatus",
    "task_equipment",
    "task_workers",
]
