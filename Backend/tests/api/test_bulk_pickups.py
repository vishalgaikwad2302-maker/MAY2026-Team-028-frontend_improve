"""API integration tests for bulk pickup routes (S2-F04, US-31)."""

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import UserRole
from app.models.vehicle import Vehicle, VehicleStatus
from app.models.worker import Worker, WorkerStatus
from app.schemas.auth import LoginRequest
from app.schemas.user import UserCreate
from app.services.auth_service import AuthService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _register_and_login(db: Session, client: TestClient, email: str, role: UserRole) -> str:
    AuthService.register_user(
        db,
        UserCreate(email=email, password="password123", full_name="Test User", role=role),
    )
    tokens = AuthService.authenticate_user(db, LoginRequest(email=email, password="password123"))
    return tokens.access_token


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_pickup(client: TestClient, token: str, **overrides) -> int:
    payload = {"load_band": "small", "address": "12 Palm Street"}
    payload.update(overrides)
    resp = client.post("/api/v1/bulk-pickups", json=payload, headers=_auth(token))
    assert resp.status_code == status.HTTP_201_CREATED, resp.text
    return resp.json()["id"]


def _create_worker(db: Session, name: str = "Bulk Crew") -> Worker:
    worker = Worker(full_name=name, status=WorkerStatus.AVAILABLE.value, is_active=True)
    db.add(worker)
    db.commit()
    db.refresh(worker)
    return worker


def _create_vehicle(db: Session, plate: str = "KA-02-BP-0001") -> Vehicle:
    vehicle = Vehicle(
        plate_number=plate,
        model_name="Mini Tipper",
        status=VehicleStatus.AVAILABLE.value,
        is_active=True,
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


# ---------------------------------------------------------------------------
# POST /bulk-pickups
# ---------------------------------------------------------------------------


def test_create_pickup_happy_path(client: TestClient, db_session: Session):
    """Happy Path: a citizen creates a bulk pickup request."""
    citizen_token = _register_and_login(
        db_session, client, "bp_citizen@example.com", UserRole.CITIZEN
    )

    resp = client.post(
        "/api/v1/bulk-pickups",
        json={"category": "e_waste", "load_band": "medium", "address": "5th Cross"},
        headers=_auth(citizen_token),
    )
    assert resp.status_code == status.HTTP_201_CREATED, resp.text
    data = resp.json()
    assert data["status"] == "requested"
    assert data["category"] == "e_waste"
    assert "fee" not in data


def test_create_pickup_validation_failure(client: TestClient, db_session: Session):
    """Validation Failure: missing required load_band returns 422."""
    citizen_token = _register_and_login(
        db_session, client, "bp_citizen_val@example.com", UserRole.CITIZEN
    )
    resp = client.post(
        "/api/v1/bulk-pickups", json={"address": "No load band"}, headers=_auth(citizen_token)
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_pickup_rbac_failure(client: TestClient, db_session: Session):
    """Auth/RBAC Failure: crew role cannot create a bulk pickup request."""
    crew_token = _register_and_login(db_session, client, "bp_crew@example.com", UserRole.CREW)
    resp = client.post(
        "/api/v1/bulk-pickups",
        json={"load_band": "small", "address": "Should fail"},
        headers=_auth(crew_token),
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_create_pickup_edge_case_defaults_category(client: TestClient, db_session: Session):
    """Edge Case: omitting category defaults to 'general'."""
    citizen_token = _register_and_login(
        db_session, client, "bp_citizen_def@example.com", UserRole.CITIZEN
    )
    resp = client.post(
        "/api/v1/bulk-pickups",
        json={"load_band": "large", "address": "Default category"},
        headers=_auth(citizen_token),
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.json()["category"] == "general"


# ---------------------------------------------------------------------------
# GET /bulk-pickups
# ---------------------------------------------------------------------------


def test_list_pickups_happy_path(client: TestClient, db_session: Session):
    """Happy Path: admin lists all pickup requests."""
    citizen_token = _register_and_login(
        db_session, client, "bp_list_citizen@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(
        db_session, client, "bp_list_admin@example.com", UserRole.ADMIN
    )
    _create_pickup(client, citizen_token)

    resp = client.get("/api/v1/bulk-pickups", headers=_auth(admin_token))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["meta"]["total"] >= 1


def test_list_pickups_requires_auth(client: TestClient):
    """Validation/Auth Failure: listing without a token returns 401."""
    resp = client.get("/api/v1/bulk-pickups")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_list_pickups_scoped_to_citizen(client: TestClient, db_session: Session):
    """Auth/RBAC: a citizen only sees their own pickup requests."""
    owner_token = _register_and_login(
        db_session, client, "bp_list_owner@example.com", UserRole.CITIZEN
    )
    other_token = _register_and_login(
        db_session, client, "bp_list_other@example.com", UserRole.CITIZEN
    )
    _create_pickup(client, owner_token)

    resp = client.get("/api/v1/bulk-pickups", headers=_auth(other_token))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["meta"]["total"] == 0


def test_list_pickups_edge_case_empty(client: TestClient, db_session: Session):
    """Edge Case: listing with zero requests returns an empty page."""
    citizen_token = _register_and_login(
        db_session, client, "bp_list_empty@example.com", UserRole.CITIZEN
    )
    resp = client.get("/api/v1/bulk-pickups", headers=_auth(citizen_token))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["items"] == []


# ---------------------------------------------------------------------------
# GET /bulk-pickups/{id}
# ---------------------------------------------------------------------------


def test_get_pickup_happy_path(client: TestClient, db_session: Session):
    """Happy Path: owner fetches their own pickup request."""
    citizen_token = _register_and_login(
        db_session, client, "bp_get_citizen@example.com", UserRole.CITIZEN
    )
    pickup_id = _create_pickup(client, citizen_token)

    resp = client.get(f"/api/v1/bulk-pickups/{pickup_id}", headers=_auth(citizen_token))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["id"] == pickup_id


def test_get_pickup_validation_failure(client: TestClient, db_session: Session):
    """Validation Failure: non-integer pickup id returns 422."""
    citizen_token = _register_and_login(
        db_session, client, "bp_get_val@example.com", UserRole.CITIZEN
    )
    resp = client.get("/api/v1/bulk-pickups/not-an-id", headers=_auth(citizen_token))
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_get_pickup_rbac_failure(client: TestClient, db_session: Session):
    """Auth/RBAC Failure: a different citizen cannot read someone else's pickup request."""
    owner_token = _register_and_login(
        db_session, client, "bp_get_owner@example.com", UserRole.CITIZEN
    )
    other_token = _register_and_login(
        db_session, client, "bp_get_other@example.com", UserRole.CITIZEN
    )
    pickup_id = _create_pickup(client, owner_token)

    resp = client.get(f"/api/v1/bulk-pickups/{pickup_id}", headers=_auth(other_token))
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_get_pickup_edge_case_not_found(client: TestClient, db_session: Session):
    """Edge Case: fetching a non-existent pickup returns 404."""
    citizen_token = _register_and_login(
        db_session, client, "bp_get_404@example.com", UserRole.CITIZEN
    )
    resp = client.get("/api/v1/bulk-pickups/999999", headers=_auth(citizen_token))
    assert resp.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# PATCH /bulk-pickups/{id}
# ---------------------------------------------------------------------------


def test_update_pickup_happy_path(client: TestClient, db_session: Session):
    """Happy Path: admin schedules a requested pickup."""
    citizen_token = _register_and_login(
        db_session, client, "bp_upd_citizen@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(
        db_session, client, "bp_upd_admin@example.com", UserRole.ADMIN
    )
    pickup_id = _create_pickup(client, citizen_token)

    resp = client.patch(
        f"/api/v1/bulk-pickups/{pickup_id}",
        json={"status": "scheduled"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == status.HTTP_200_OK, resp.text
    data = resp.json()
    assert data["status"] == "scheduled"
    assert data["scheduled_at"] is not None


def test_update_pickup_validation_failure(client: TestClient, db_session: Session):
    """Validation Failure: invalid status enum value returns 422."""
    citizen_token = _register_and_login(
        db_session, client, "bp_upd_val_citizen@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(
        db_session, client, "bp_upd_val_admin@example.com", UserRole.ADMIN
    )
    pickup_id = _create_pickup(client, citizen_token)

    resp = client.patch(
        f"/api/v1/bulk-pickups/{pickup_id}",
        json={"status": "not_a_status"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_update_pickup_rbac_failure(client: TestClient, db_session: Session):
    """Auth/RBAC Failure: a citizen or crew member cannot update pickup lifecycle status."""
    citizen_token = _register_and_login(
        db_session, client, "bp_upd_rbac@example.com", UserRole.CITIZEN
    )
    crew_token = _register_and_login(
        db_session, client, "bp_upd_crew_rbac@example.com", UserRole.CREW
    )
    pickup_id = _create_pickup(client, citizen_token)

    resp = client.patch(
        f"/api/v1/bulk-pickups/{pickup_id}",
        json={"status": "scheduled"},
        headers=_auth(citizen_token),
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN

    resp = client.patch(
        f"/api/v1/bulk-pickups/{pickup_id}",
        json={"status": "scheduled"},
        headers=_auth(crew_token),
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_update_pickup_edge_case_illegal_transition(client: TestClient, db_session: Session):
    """Edge Case: jumping straight from requested to collected returns 409 Conflict."""
    citizen_token = _register_and_login(
        db_session, client, "bp_upd_illegal@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(
        db_session, client, "bp_upd_illegal_admin@example.com", UserRole.ADMIN
    )
    pickup_id = _create_pickup(client, citizen_token)

    resp = client.patch(
        f"/api/v1/bulk-pickups/{pickup_id}",
        json={"status": "collected"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == status.HTTP_409_CONFLICT
    assert resp.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


# ---------------------------------------------------------------------------
# POST /bulk-pickups/{id}/cancel
# ---------------------------------------------------------------------------


def test_cancel_pickup_happy_path(client: TestClient, db_session: Session):
    """Happy Path: the owning citizen cancels their own requested pickup."""
    citizen_token = _register_and_login(
        db_session, client, "bp_cncl_citizen@example.com", UserRole.CITIZEN
    )
    pickup_id = _create_pickup(client, citizen_token)

    resp = client.post(f"/api/v1/bulk-pickups/{pickup_id}/cancel", headers=_auth(citizen_token))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == "cancelled"


def test_cancel_pickup_validation_failure(client: TestClient, db_session: Session):
    """Validation Failure: non-integer pickup id returns 422."""
    citizen_token = _register_and_login(
        db_session, client, "bp_cncl_val@example.com", UserRole.CITIZEN
    )
    resp = client.post("/api/v1/bulk-pickups/not-an-id/cancel", headers=_auth(citizen_token))
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_cancel_pickup_rbac_failure(client: TestClient, db_session: Session):
    """Auth/RBAC Failure: a different citizen cannot cancel someone else's pickup."""
    owner_token = _register_and_login(
        db_session, client, "bp_cncl_owner@example.com", UserRole.CITIZEN
    )
    other_token = _register_and_login(
        db_session, client, "bp_cncl_other@example.com", UserRole.CITIZEN
    )
    pickup_id = _create_pickup(client, owner_token)

    resp = client.post(f"/api/v1/bulk-pickups/{pickup_id}/cancel", headers=_auth(other_token))
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_cancel_pickup_edge_case_already_collected(client: TestClient, db_session: Session):
    """Edge Case: cancelling an already-collected pickup returns 409 Conflict."""
    citizen_token = _register_and_login(
        db_session, client, "bp_cncl_collected@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(
        db_session, client, "bp_cncl_collected_admin@example.com", UserRole.ADMIN
    )
    pickup_id = _create_pickup(client, citizen_token)
    client.patch(
        f"/api/v1/bulk-pickups/{pickup_id}",
        json={"status": "scheduled"},
        headers=_auth(admin_token),
    )
    client.patch(
        f"/api/v1/bulk-pickups/{pickup_id}",
        json={"status": "collected"},
        headers=_auth(admin_token),
    )

    resp = client.post(f"/api/v1/bulk-pickups/{pickup_id}/cancel", headers=_auth(citizen_token))
    assert resp.status_code == status.HTTP_409_CONFLICT
    assert resp.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


def test_cancel_pickup_by_admin_on_behalf(client: TestClient, db_session: Session):
    """Admin/crew can also cancel a citizen's pickup request on their behalf."""
    citizen_token = _register_and_login(
        db_session, client, "bp_cncl_admin_behalf@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(
        db_session, client, "bp_cncl_admin_behalf_admin@example.com", UserRole.ADMIN
    )
    pickup_id = _create_pickup(client, citizen_token)

    resp = client.post(f"/api/v1/bulk-pickups/{pickup_id}/cancel", headers=_auth(admin_token))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == "cancelled"


# ---------------------------------------------------------------------------
# POST /bulk-pickups/{id}/assign
# ---------------------------------------------------------------------------


def test_assign_pickup_happy_path(client: TestClient, db_session: Session):
    """Happy Path: admin assigns an available crew member and vehicle."""
    citizen_token = _register_and_login(
        db_session, client, "bp_asg_citizen@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(db_session, client, "bp_asg_admin@example.com", UserRole.ADMIN)
    pickup_id = _create_pickup(client, citizen_token)
    worker = _create_worker(db_session)
    vehicle = _create_vehicle(db_session)

    resp = client.post(
        f"/api/v1/bulk-pickups/{pickup_id}/assign",
        json={"worker_id": worker.id, "vehicle_id": vehicle.id},
        headers=_auth(admin_token),
    )
    assert resp.status_code == status.HTTP_200_OK, resp.text
    data = resp.json()
    assert data["assigned_worker_id"] == worker.id
    assert data["assigned_vehicle_id"] == vehicle.id
    assert data["status"] == "scheduled"

    db_session.refresh(worker)
    db_session.refresh(vehicle)
    assert worker.status == WorkerStatus.ASSIGNED.value
    assert vehicle.status == VehicleStatus.EN_ROUTE.value


def test_assign_pickup_validation_failure(client: TestClient, db_session: Session):
    """Validation Failure: missing vehicle_id returns 422."""
    citizen_token = _register_and_login(
        db_session, client, "bp_asg_val_citizen@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(
        db_session, client, "bp_asg_val_admin@example.com", UserRole.ADMIN
    )
    pickup_id = _create_pickup(client, citizen_token)
    worker = _create_worker(db_session, name="Val Worker")

    resp = client.post(
        f"/api/v1/bulk-pickups/{pickup_id}/assign",
        json={"worker_id": worker.id},
        headers=_auth(admin_token),
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_assign_pickup_rbac_failure(client: TestClient, db_session: Session):
    """Auth/RBAC Failure: a citizen cannot assign crew/vehicle to a pickup."""
    citizen_token = _register_and_login(
        db_session, client, "bp_asg_rbac@example.com", UserRole.CITIZEN
    )
    pickup_id = _create_pickup(client, citizen_token)
    worker = _create_worker(db_session, name="Rbac Worker")
    vehicle = _create_vehicle(db_session, plate="KA-02-BP-0002")

    resp = client.post(
        f"/api/v1/bulk-pickups/{pickup_id}/assign",
        json={"worker_id": worker.id, "vehicle_id": vehicle.id},
        headers=_auth(citizen_token),
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_assign_pickup_edge_case_unavailable_vehicle(client: TestClient, db_session: Session):
    """Edge Case: assigning a vehicle already in use returns 409 Conflict."""
    citizen_token = _register_and_login(
        db_session, client, "bp_asg_conflict_citizen@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(
        db_session, client, "bp_asg_conflict_admin@example.com", UserRole.ADMIN
    )
    pickup_id = _create_pickup(client, citizen_token)
    worker = _create_worker(db_session, name="Conflict Worker")
    vehicle = _create_vehicle(db_session, plate="KA-02-BP-0003")
    vehicle.status = VehicleStatus.MAINTENANCE.value
    db_session.commit()

    resp = client.post(
        f"/api/v1/bulk-pickups/{pickup_id}/assign",
        json={"worker_id": worker.id, "vehicle_id": vehicle.id},
        headers=_auth(admin_token),
    )
    assert resp.status_code == status.HTTP_409_CONFLICT


def test_assign_pickup_edge_case_terminal_state(client: TestClient, db_session: Session):
    """Edge Case: assigning to a cancelled pickup returns 409 Conflict."""
    citizen_token = _register_and_login(
        db_session, client, "bp_asg_terminal_citizen@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(
        db_session, client, "bp_asg_terminal_admin@example.com", UserRole.ADMIN
    )
    pickup_id = _create_pickup(client, citizen_token)
    client.post(f"/api/v1/bulk-pickups/{pickup_id}/cancel", headers=_auth(citizen_token))
    worker = _create_worker(db_session, name="Terminal Worker")
    vehicle = _create_vehicle(db_session, plate="KA-02-BP-0004")

    resp = client.post(
        f"/api/v1/bulk-pickups/{pickup_id}/assign",
        json={"worker_id": worker.id, "vehicle_id": vehicle.id},
        headers=_auth(admin_token),
    )
    assert resp.status_code == status.HTTP_409_CONFLICT
    assert resp.json()["error"]["code"] == "INVALID_STATE_TRANSITION"
