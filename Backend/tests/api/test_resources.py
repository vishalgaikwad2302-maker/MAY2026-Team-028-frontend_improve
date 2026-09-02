"""API integration tests for resource management routes (B-3)."""

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.equipment import Equipment, EquipmentStatus
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
    """Create a user and return a valid access token."""
    AuthService.register_user(
        db,
        UserCreate(
            email=email,
            password="password123",
            full_name="Test Resource User",
            role=role,
        ),
    )
    tokens = AuthService.authenticate_user(db, LoginRequest(email=email, password="password123"))
    return tokens.access_token


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_worker(db: Session, name: str = "Worker Alpha") -> Worker:
    worker = Worker(full_name=name, status=WorkerStatus.AVAILABLE.value, is_active=True)
    db.add(worker)
    db.commit()
    db.refresh(worker)
    return worker


def _create_vehicle(db: Session, plate: str = "KA-05-EV-9999") -> Vehicle:
    vehicle = Vehicle(
        plate_number=plate,
        model_name="Sweeper Truck",
        status=VehicleStatus.AVAILABLE.value,
        is_active=True,
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


def _create_equipment(db: Session, name: str = "Broom Heavy") -> Equipment:
    equipment = Equipment(
        name=name,
        status=EquipmentStatus.AVAILABLE.value,
        available_quantity=10,
        is_active=True,
    )
    db.add(equipment)
    db.commit()
    db.refresh(equipment)
    return equipment


# ---------------------------------------------------------------------------
# 1. GET /resources/workers (list_workers)
# ---------------------------------------------------------------------------


def test_list_workers_happy_path(client: TestClient, db_session: Session):
    """Happy Path: Admin lists workers and receives 200 OK."""
    token = _register_and_login(db_session, client, "res_list_workers@example.com", UserRole.ADMIN)
    _create_worker(db_session, "Worker One")

    resp = client.get("/api/v1/resources/workers", headers=_auth(token))
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["full_name"] == "Worker One"


def test_list_workers_validation_failure(client: TestClient):
    """Validation Failure: Invalid authorization token format returns 401."""
    resp = client.get("/api/v1/resources/workers", headers={"Authorization": "Bearer bad_token"})
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
    assert resp.json()["error"]["code"] == "UNAUTHENTICATED"


def test_list_workers_rbac_failure(client: TestClient, db_session: Session):
    """Auth/RBAC Failure: Citizen and Crew roles are forbidden from viewing workers."""
    cit_token = _register_and_login(db_session, client, "res_cit_workers@example.com", UserRole.CITIZEN)
    resp = client.get("/api/v1/resources/workers", headers=_auth(cit_token))
    assert resp.status_code == status.HTTP_403_FORBIDDEN
    assert resp.json()["error"]["code"] == "PERMISSION_DENIED"

    crew_token = _register_and_login(db_session, client, "res_crew_workers@example.com", UserRole.CREW)
    resp = client.get("/api/v1/resources/workers", headers=_auth(crew_token))
    assert resp.status_code == status.HTTP_403_FORBIDDEN
    assert resp.json()["error"]["code"] == "PERMISSION_DENIED"


def test_list_workers_edge_case_empty(client: TestClient, db_session: Session):
    """Edge Case: Listing workers when no workers exist returns empty list."""
    token = _register_and_login(db_session, client, "res_empty_workers@example.com", UserRole.ADMIN)
    resp = client.get("/api/v1/resources/workers", headers=_auth(token))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == []


# ---------------------------------------------------------------------------
# 2. PATCH /resources/workers/{worker_id}/status (update_worker_status)
# ---------------------------------------------------------------------------


def test_update_worker_status_happy_path(client: TestClient, db_session: Session):
    """Happy Path: Admin updates worker status to off_duty."""
    token = _register_and_login(db_session, client, "res_w_status_hp@example.com", UserRole.ADMIN)
    worker = _create_worker(db_session, "Worker Status Test")

    resp = client.patch(
        f"/api/v1/resources/workers/{worker.id}/status?status_value=off_duty",
        headers=_auth(token),
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == "off_duty"


def test_update_worker_status_validation_failure(client: TestClient, db_session: Session):
    """Validation Failure: Invalid status enum value returns 422."""
    token = _register_and_login(db_session, client, "res_w_status_val@example.com", UserRole.ADMIN)
    worker = _create_worker(db_session, "Worker Val Test")

    resp = client.patch(
        f"/api/v1/resources/workers/{worker.id}/status?status_value=INVALID_STATUS",
        headers=_auth(token),
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_update_worker_status_rbac_failure(client: TestClient, db_session: Session):
    """Auth/RBAC Failure: Citizen and Crew roles are forbidden from updating worker status."""
    cit_token = _register_and_login(
        db_session, client, "res_w_status_rbac@example.com", UserRole.CITIZEN
    )
    worker = _create_worker(db_session, "Worker RBAC Test")

    resp = client.patch(
        f"/api/v1/resources/workers/{worker.id}/status?status_value=off_duty",
        headers=_auth(cit_token),
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN

    crew_token = _register_and_login(
        db_session, client, "res_w_status_crew_rbac@example.com", UserRole.CREW
    )
    resp = client.patch(
        f"/api/v1/resources/workers/{worker.id}/status?status_value=off_duty",
        headers=_auth(crew_token),
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_update_worker_status_edge_case_not_found(client: TestClient, db_session: Session):
    """Edge Case: Updating status of non-existent worker returns 404 Not Found."""
    token = _register_and_login(db_session, client, "res_w_status_404@example.com", UserRole.ADMIN)
    resp = client.patch(
        "/api/v1/resources/workers/999999/status?status_value=off_duty",
        headers=_auth(token),
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# 3. GET /resources/vehicles (list_vehicles)
# ---------------------------------------------------------------------------


def test_list_vehicles_happy_path(client: TestClient, db_session: Session):
    """Happy Path: Admin or Crew lists vehicles and receives 200 OK."""
    token = _register_and_login(db_session, client, "res_list_veh@example.com", UserRole.CREW)
    _create_vehicle(db_session, "KA-01-XX-1111")

    resp = client.get("/api/v1/resources/vehicles", headers=_auth(token))
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["plate_number"] == "KA-01-XX-1111"


def test_list_vehicles_validation_failure(client: TestClient):
    """Validation Failure: Missing or invalid token header returns 401."""
    resp = client.get(
        "/api/v1/resources/vehicles", headers={"Authorization": "Bearer bad_veh_token"}
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_list_vehicles_rbac_failure(client: TestClient, db_session: Session):
    """Auth/RBAC Failure: Citizen role is forbidden from viewing vehicles."""
    token = _register_and_login(db_session, client, "res_veh_rbac@example.com", UserRole.CITIZEN)
    resp = client.get("/api/v1/resources/vehicles", headers=_auth(token))
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_list_vehicles_edge_case_empty(client: TestClient, db_session: Session):
    """Edge Case: Listing vehicles when none exist returns empty list."""
    token = _register_and_login(db_session, client, "res_veh_empty@example.com", UserRole.ADMIN)
    resp = client.get("/api/v1/resources/vehicles", headers=_auth(token))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == []


# ---------------------------------------------------------------------------
# 4. PATCH /resources/vehicles/{vehicle_id}/status (update_vehicle_status)
# ---------------------------------------------------------------------------


def test_update_vehicle_status_happy_path(client: TestClient, db_session: Session):
    """Happy Path: Update vehicle status to maintenance."""
    token = _register_and_login(db_session, client, "res_v_status_hp@example.com", UserRole.CREW)
    vehicle = _create_vehicle(db_session, "KA-02-YY-2222")

    resp = client.patch(
        f"/api/v1/resources/vehicles/{vehicle.id}/status?status_value=maintenance",
        headers=_auth(token),
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == "maintenance"


def test_update_vehicle_status_validation_failure(client: TestClient, db_session: Session):
    """Validation Failure: Invalid status value returns 422."""
    token = _register_and_login(db_session, client, "res_v_status_val@example.com", UserRole.ADMIN)
    vehicle = _create_vehicle(db_session, "KA-03-ZZ-3333")

    resp = client.patch(
        f"/api/v1/resources/vehicles/{vehicle.id}/status?status_value=BROKEN",
        headers=_auth(token),
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_update_vehicle_status_rbac_failure(client: TestClient, db_session: Session):
    """Auth/RBAC Failure: Citizen role is forbidden from updating vehicle status."""
    token = _register_and_login(
        db_session, client, "res_v_status_rbac@example.com", UserRole.CITIZEN
    )
    vehicle = _create_vehicle(db_session, "KA-04-AA-4444")

    resp = client.patch(
        f"/api/v1/resources/vehicles/{vehicle.id}/status?status_value=maintenance",
        headers=_auth(token),
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_update_vehicle_status_edge_case_not_found(client: TestClient, db_session: Session):
    """Edge Case: Updating non-existent vehicle status returns 404 Not Found."""
    token = _register_and_login(db_session, client, "res_v_status_404@example.com", UserRole.ADMIN)
    resp = client.patch(
        "/api/v1/resources/vehicles/999999/status?status_value=maintenance",
        headers=_auth(token),
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# 5. GET /resources/equipment (list_equipment)
# ---------------------------------------------------------------------------


def test_list_equipment_happy_path(client: TestClient, db_session: Session):
    """Happy Path: Admin or Crew lists equipment and receives 200 OK."""
    token = _register_and_login(db_session, client, "res_list_eq@example.com", UserRole.CREW)
    _create_equipment(db_session, "Safety Helmet")

    resp = client.get("/api/v1/resources/equipment", headers=_auth(token))
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["name"] == "Safety Helmet"


def test_list_equipment_validation_failure(client: TestClient):
    """Validation Failure: Invalid authorization token format returns 401."""
    resp = client.get(
        "/api/v1/resources/equipment", headers={"Authorization": "Bearer bad_eq_token"}
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_list_equipment_rbac_failure(client: TestClient, db_session: Session):
    """Auth/RBAC Failure: Citizen role is forbidden from viewing equipment."""
    token = _register_and_login(db_session, client, "res_eq_rbac@example.com", UserRole.CITIZEN)
    resp = client.get("/api/v1/resources/equipment", headers=_auth(token))
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_list_equipment_edge_case_empty(client: TestClient, db_session: Session):
    """Edge Case: Listing equipment when none exist returns empty list."""
    token = _register_and_login(db_session, client, "res_eq_empty@example.com", UserRole.ADMIN)
    resp = client.get("/api/v1/resources/equipment", headers=_auth(token))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == []


# ---------------------------------------------------------------------------
# 6. PATCH /resources/equipment/{equipment_id}/status (update_equipment_status)
# ---------------------------------------------------------------------------


def test_update_equipment_status_happy_path(client: TestClient, db_session: Session):
    """Happy Path: Update equipment status to maintenance."""
    token = _register_and_login(db_session, client, "res_e_status_hp@example.com", UserRole.CREW)
    equipment = _create_equipment(db_session, "Trash Compactor")

    resp = client.patch(
        f"/api/v1/resources/equipment/{equipment.id}/status?status_value=maintenance",
        headers=_auth(token),
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == "maintenance"


def test_update_equipment_status_validation_failure(client: TestClient, db_session: Session):
    """Validation Failure: Invalid status value returns 422."""
    token = _register_and_login(db_session, client, "res_e_status_val@example.com", UserRole.ADMIN)
    equipment = _create_equipment(db_session, "Lawn Mower")

    resp = client.patch(
        f"/api/v1/resources/equipment/{equipment.id}/status?status_value=DESTROYED",
        headers=_auth(token),
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_update_equipment_status_rbac_failure(client: TestClient, db_session: Session):
    """Auth/RBAC Failure: Citizen role is forbidden from updating equipment status."""
    token = _register_and_login(
        db_session, client, "res_e_status_rbac@example.com", UserRole.CITIZEN
    )
    equipment = _create_equipment(db_session, "Pressure Washer")

    resp = client.patch(
        f"/api/v1/resources/equipment/{equipment.id}/status?status_value=maintenance",
        headers=_auth(token),
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_update_equipment_status_edge_case_not_found(client: TestClient, db_session: Session):
    """Edge Case: Updating status of non-existent equipment returns 404 Not Found."""
    token = _register_and_login(db_session, client, "res_e_status_404@example.com", UserRole.ADMIN)
    resp = client.patch(
        "/api/v1/resources/equipment/999999/status?status_value=maintenance",
        headers=_auth(token),
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# 7. POST /resources/workers (create_worker & onboard credentials)
# ---------------------------------------------------------------------------


def test_admin_can_onboard_worker_with_credentials(client: TestClient, db_session: Session):
    """Happy Path: Admin onboards worker; user account and worker record are provisioned."""
    token = _register_and_login(db_session, client, "admin_onboarder@example.com", UserRole.ADMIN)
    payload = {
        "full_name": "Ravi Shankar",
        "email": "ravi.crew@example.com",
        "password": "crewpassword123",
        "phone": "+91 9988776655",
        "role_title": "Sanitation Specialist",
        "employee_code": "EMP-9001",
        "status": "available",
    }
    resp = client.post("/api/v1/resources/workers", json=payload, headers=_auth(token))
    assert resp.status_code == status.HTTP_201_CREATED
    data = resp.json()
    assert data["full_name"] == "Ravi Shankar"
    assert data["email"] == "ravi.crew@example.com"
    assert data["user_id"] is not None

    # Verify that the new worker can immediately login with their provisioned credentials
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "ravi.crew@example.com", "password": "crewpassword123"},
    )
    assert login_resp.status_code == status.HTTP_200_OK
    assert "access_token" in login_resp.json()


def test_citizen_cannot_onboard_worker(client: TestClient, db_session: Session):
    """RBAC Failure: Citizen cannot onboard workers."""
    token = _register_and_login(db_session, client, "citizen_denied@example.com", UserRole.CITIZEN)
    payload = {
        "full_name": "Intruder Worker",
        "email": "intruder.crew@example.com",
        "password": "password123",
    }
    resp = client.post("/api/v1/resources/workers", json=payload, headers=_auth(token))
    assert resp.status_code == status.HTTP_403_FORBIDDEN
