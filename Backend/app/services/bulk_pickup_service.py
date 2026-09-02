"""Bulk pickup service (S2-F04, US-31)."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import InvalidStateTransitionError, NotFoundError, PermissionDeniedError
from app.models.bulk_pickup import BulkPickup, BulkPickupStatus
from app.models.user import User, UserRole
from app.models.vehicle import VehicleStatus
from app.models.worker import WorkerStatus
from app.repositories.bulk_pickup_repository import BulkPickupRepository
from app.schemas.bulk_pickup import BulkPickupAssign, BulkPickupCreate, BulkPickupUpdate
from app.services.resource_service import ResourceService

__all__ = ["BulkPickupService"]


_ALLOWED_TRANSITIONS = {
    BulkPickupStatus.REQUESTED.value: {
        BulkPickupStatus.SCHEDULED.value,
        BulkPickupStatus.CANCELLED.value,
    },
    BulkPickupStatus.SCHEDULED.value: {
        BulkPickupStatus.COLLECTED.value,
        BulkPickupStatus.CANCELLED.value,
    },
    BulkPickupStatus.COLLECTED.value: set(),
    BulkPickupStatus.CANCELLED.value: set(),
}


class BulkPickupService:
    @staticmethod
    def create_pickup(db: Session, current_user: User, pickup_in: BulkPickupCreate) -> BulkPickup:
        pickup = BulkPickup(
            requested_by_user_id=current_user.id,
            ward_id=pickup_in.ward_id or current_user.ward_id,
            category=pickup_in.category.value,
            load_band=pickup_in.load_band.value,
            address=pickup_in.address,
            latitude=pickup_in.latitude,
            longitude=pickup_in.longitude,
            preferred_date=pickup_in.preferred_date,
            notes=pickup_in.notes,
            status=BulkPickupStatus.REQUESTED.value,
        )
        return BulkPickupRepository.create(db, pickup)

    @staticmethod
    def get_pickup(db: Session, pickup_id: int) -> BulkPickup:
        pickup = BulkPickupRepository.get_by_id(db, pickup_id)
        if not pickup:
            raise NotFoundError("Bulk pickup request not found.")
        return pickup

    @staticmethod
    def assert_can_read(pickup: BulkPickup, current_user: User) -> None:
        if (
            current_user.role == UserRole.CITIZEN.value
            and pickup.requested_by_user_id != current_user.id
        ):
            raise PermissionDeniedError("You do not have permission to access this pickup request.")

    @staticmethod
    def list_pickups(
        db: Session, *, filters: dict | None = None, page: int = 1, page_size: int = 20
    ) -> tuple[list[BulkPickup], int]:
        return BulkPickupRepository.list(db, filters=filters, page=page, page_size=page_size)

    @staticmethod
    def update_pickup(db: Session, pickup_id: int, update_in: BulkPickupUpdate) -> BulkPickup:
        pickup = BulkPickupService.get_pickup(db, pickup_id)
        update_data = update_in.model_dump(exclude_unset=True)
        new_status = update_data.pop("status", None)

        if new_status is not None:
            new_status_value = new_status.value if hasattr(new_status, "value") else str(new_status)
            current_status = pickup.status
            if new_status_value != current_status:
                if new_status_value not in _ALLOWED_TRANSITIONS.get(current_status, set()):
                    raise InvalidStateTransitionError(
                        f"Cannot move bulk pickup from '{current_status}' to '{new_status_value}'."
                    )
                update_data["status"] = new_status_value
                if new_status_value == BulkPickupStatus.SCHEDULED.value:
                    update_data.setdefault("scheduled_at", datetime.now(UTC))
                if new_status_value == BulkPickupStatus.COLLECTED.value:
                    update_data["collected_at"] = datetime.now(UTC)
                if new_status_value == BulkPickupStatus.CANCELLED.value:
                    update_data["cancelled_at"] = datetime.now(UTC)

        return BulkPickupRepository.update(db, pickup, update_data)

    @staticmethod
    def cancel_pickup(db: Session, pickup_id: int, current_user: User) -> BulkPickup:
        pickup = BulkPickupService.get_pickup(db, pickup_id)
        if (
            current_user.role == UserRole.CITIZEN.value
            and pickup.requested_by_user_id != current_user.id
        ):
            raise PermissionDeniedError("You do not have permission to cancel this pickup request.")

        if pickup.status not in {
            BulkPickupStatus.REQUESTED.value,
            BulkPickupStatus.SCHEDULED.value,
        }:
            raise InvalidStateTransitionError(
                "Only requested or scheduled pickups can be cancelled."
            )

        return BulkPickupRepository.update(
            db,
            pickup,
            {"status": BulkPickupStatus.CANCELLED.value, "cancelled_at": datetime.now(UTC)},
        )

    @staticmethod
    def assign_pickup(db: Session, pickup_id: int, assign_in: BulkPickupAssign) -> BulkPickup:
        pickup = BulkPickupService.get_pickup(db, pickup_id)
        if pickup.status not in {
            BulkPickupStatus.REQUESTED.value,
            BulkPickupStatus.SCHEDULED.value,
        }:
            raise InvalidStateTransitionError(
                "Only requested or scheduled pickups can be assigned a crew and vehicle."
            )

        ResourceService.check_worker_available(db, assign_in.worker_id)
        ResourceService.check_vehicle_available(db, assign_in.vehicle_id)

        update_data: dict = {
            "assigned_worker_id": assign_in.worker_id,
            "assigned_vehicle_id": assign_in.vehicle_id,
        }
        if pickup.status == BulkPickupStatus.REQUESTED.value:
            update_data["status"] = BulkPickupStatus.SCHEDULED.value
            update_data.setdefault("scheduled_at", datetime.now(UTC))

        updated = BulkPickupRepository.update(db, pickup, update_data)
        ResourceService.update_worker_status(db, assign_in.worker_id, status=WorkerStatus.ASSIGNED.value)
        ResourceService.update_vehicle_status(db, assign_in.vehicle_id, status=VehicleStatus.EN_ROUTE.value)
        return updated
