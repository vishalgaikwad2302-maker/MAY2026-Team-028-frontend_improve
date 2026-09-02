"""API integration tests for task management routes (B-2)."""

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
            full_name="Test Task User",
            role=role,
        ),
    )
    tokens = AuthService.authenticate_user(db, LoginRequest(email=email, password="password123"))
    return tokens.access_token


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_sample_worker(db: Session, name: str = "John Worker") -> Worker:
    worker = Worker(full_name=name, status=WorkerStatus.AVAILABLE.value, is_active=True)
    db.add(worker)
    db.commit()
    db.refresh(worker)
    return worker


def _create_sample_vehicle(db: Session, plate: str = "KA-01-AB-1234") -> Vehicle:
    vehicle = Vehicle(
        plate_number=plate,
        model_name="Garbage Truck",
        status=VehicleStatus.AVAILABLE.value,
        is_active=True,
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


def _create_sample_equipment(db: Session, name: str = "Shovel") -> Equipment:
    equipment = Equipment(
        name=name,
        status=EquipmentStatus.AVAILABLE.value,
        available_quantity=5,
        is_active=True,
    )
    db.add(equipment)
    db.commit()
    db.refresh(equipment)
    return equipment


# ---------------------------------------------------------------------------
# 1. GET /tasks (list_tasks)
# ---------------------------------------------------------------------------


def test_list_tasks_happy_path(client: TestClient, db_session: Session):
    """Happy Path: Admin or Crew can list tasks and get a 200 response."""
    admin_token = _register_and_login(
        db_session, client, "task_admin_list@example.com", UserRole.ADMIN
    )

    # Create a task first
    client.post(
        "/api/v1/tasks",
        json={"title": "Clean Park Task", "description": "Clear garbage from central park"},
        headers=_auth(admin_token),
    )

    resp = client.get("/api/v1/tasks", headers=_auth(admin_token))
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["title"] == "Clean Park Task"


def test_list_tasks_validation_failure(client: TestClient):
    """Validation Failure: Request with malformed or invalid authorization header fails."""
    resp = client.get("/api/v1/tasks", headers={"Authorization": "Bearer invalid_token_format"})
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
    assert resp.json()["error"]["code"] == "UNAUTHENTICATED"


def test_list_tasks_rbac_failure(client: TestClient, db_session: Session):
    """Auth/RBAC Failure: Citizen role is forbidden from listing internal tasks."""
    citizen_token = _register_and_login(
        db_session, client, "task_citizen_list@example.com", UserRole.CITIZEN
    )
    resp = client.get("/api/v1/tasks", headers=_auth(citizen_token))
    assert resp.status_code == status.HTTP_403_FORBIDDEN
    assert resp.json()["error"]["code"] == "PERMISSION_DENIED"


def test_list_tasks_edge_case_empty(client: TestClient, db_session: Session):
    """Edge Case: Listing tasks when zero tasks exist returns an empty list."""
    admin_token = _register_and_login(
        db_session, client, "task_admin_empty@example.com", UserRole.ADMIN
    )
    resp = client.get("/api/v1/tasks", headers=_auth(admin_token))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == []


# ---------------------------------------------------------------------------
# 2. POST /tasks (create_task)
# ---------------------------------------------------------------------------


def test_create_task_happy_path(client: TestClient, db_session: Session):
    """Happy Path: Admin creates a task with valid payload and available resources."""
    admin_token = _register_and_login(
        db_session, client, "task_admin_create@example.com", UserRole.ADMIN
    )
    worker = _create_sample_worker(db_session, "Worker Create 1")
    vehicle = _create_sample_vehicle(db_session, "KA-02-CD-5678")

    payload = {
        "title": "Sweep Main Street",
        "description": "Debris removal along 5th avenue",
        "worker_ids": [worker.id],
        "vehicle_id": vehicle.id,
    }
    resp = client.post("/api/v1/tasks", json=payload, headers=_auth(admin_token))
    assert resp.status_code == status.HTTP_201_CREATED
    data = resp.json()
    assert data["title"] == "Sweep Main Street"
    assert data["worker_ids"] == [worker.id]
    assert data["vehicle_id"] == vehicle.id


def test_create_task_validation_failure(client: TestClient, db_session: Session):
    """Validation Failure: Omission of required field `title` yields 422."""
    admin_token = _register_and_login(
        db_session, client, "task_admin_create_val@example.com", UserRole.ADMIN
    )
    payload = {"description": "Task without title"}
    resp = client.post("/api/v1/tasks", json=payload, headers=_auth(admin_token))
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_task_rbac_failure(client: TestClient, db_session: Session):
    """Auth/RBAC Failure: Crew role cannot create new tasks (Admin only)."""
    crew_token = _register_and_login(
        db_session, client, "task_crew_create@example.com", UserRole.CREW
    )
    payload = {"title": "Unauthorized Task Creation"}
    resp = client.post("/api/v1/tasks", json=payload, headers=_auth(crew_token))
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_create_task_edge_case_unavailable_resource(client: TestClient, db_session: Session):
    """Edge Case: Creating a task with an unavailable worker returns 409 Conflict."""
    admin_token = _register_and_login(
        db_session, client, "task_admin_unavail@example.com", UserRole.ADMIN
    )
    worker = _create_sample_worker(db_session, "Busy Worker")
    # Mark worker as assigned
    worker.status = WorkerStatus.ASSIGNED.value
    db_session.commit()

    payload = {"title": "Task on busy worker", "worker_ids": [worker.id]}
    resp = client.post("/api/v1/tasks", json=payload, headers=_auth(admin_token))
    assert resp.status_code == status.HTTP_409_CONFLICT
    assert resp.json()["error"]["code"] == "CONFLICT"


# ---------------------------------------------------------------------------
# 3. GET /tasks/{task_id} (get_task)
# ---------------------------------------------------------------------------


def test_get_task_happy_path(client: TestClient, db_session: Session):
    """Happy Path: Fetching an existing task by ID returns 200 OK."""
    admin_token = _register_and_login(
        db_session, client, "task_admin_get@example.com", UserRole.ADMIN
    )
    create_resp = client.post(
        "/api/v1/tasks",
        json={"title": "Get Target Task"},
        headers=_auth(admin_token),
    )
    task_id = create_resp.json()["id"]

    resp = client.get(f"/api/v1/tasks/{task_id}", headers=_auth(admin_token))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["id"] == task_id
    assert resp.json()["title"] == "Get Target Task"


def test_get_task_validation_failure(client: TestClient, db_session: Session):
    """Validation Failure: Passing non-integer task ID returns 422 Unprocessable Entity."""
    admin_token = _register_and_login(
        db_session,
        client,
        "task_admin_get_validation@example.com",
        UserRole.ADMIN,
    )

    resp = client.get(
        "/api/v1/tasks/not-an-integer",
        headers=_auth(admin_token),
    )

    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_get_task_rbac_failure(client: TestClient, db_session: Session):
    """Auth/RBAC Failure: Citizen role is forbidden from viewing task details."""
    admin_token = _register_and_login(
        db_session, client, "task_get_owner@example.com", UserRole.ADMIN
    )
    citizen_token = _register_and_login(
        db_session, client, "task_get_citizen@example.com", UserRole.CITIZEN
    )
    create_resp = client.post(
        "/api/v1/tasks",
        json={"title": "Task for get RBAC"},
        headers=_auth(admin_token),
    )
    task_id = create_resp.json()["id"]

    resp = client.get(f"/api/v1/tasks/{task_id}", headers=_auth(citizen_token))
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_get_task_edge_case_not_found(client: TestClient, db_session: Session):
    """Edge Case: Requesting non-existent task ID returns 404 Not Found."""
    admin_token = _register_and_login(
        db_session, client, "task_admin_404@example.com", UserRole.ADMIN
    )
    resp = client.get("/api/v1/tasks/999999", headers=_auth(admin_token))
    assert resp.status_code == status.HTTP_404_NOT_FOUND
    assert resp.json()["error"]["code"] == "NOT_FOUND"


# ---------------------------------------------------------------------------
# 4. PATCH /tasks/{task_id} (update_task)
# ---------------------------------------------------------------------------


def test_update_task_happy_path(client: TestClient, db_session: Session):
    """Happy Path: Admin updates task fields successfully."""
    admin_token = _register_and_login(
        db_session, client, "task_admin_patch@example.com", UserRole.ADMIN
    )
    create_resp = client.post(
        "/api/v1/tasks",
        json={"title": "Original Title"},
        headers=_auth(admin_token),
    )
    task_id = create_resp.json()["id"]

    resp = client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"title": "Updated Title", "description": "New description"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["title"] == "Updated Title"
    assert data["description"] == "New description"


def test_update_task_validation_failure(client: TestClient, db_session: Session):
    """Validation Failure: Sending invalid status enum value returns 422."""
    admin_token = _register_and_login(
        db_session, client, "task_admin_patch_val@example.com", UserRole.ADMIN
    )
    create_resp = client.post(
        "/api/v1/tasks",
        json={"title": "Task for invalid patch"},
        headers=_auth(admin_token),
    )
    task_id = create_resp.json()["id"]

    resp = client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"status": "INVALID_STATUS_VALUE"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_update_task_rbac_failure(client: TestClient, db_session: Session):
    """Auth/RBAC Failure: Citizen and Crew roles are forbidden from updating tasks."""
    admin_token = _register_and_login(
        db_session, client, "task_patch_owner@example.com", UserRole.ADMIN
    )
    citizen_token = _register_and_login(
        db_session, client, "task_patch_citizen@example.com", UserRole.CITIZEN
    )
    crew_token = _register_and_login(
        db_session, client, "task_patch_crew@example.com", UserRole.CREW
    )

    create_resp = client.post(
        "/api/v1/tasks",
        json={"title": "Task to update"},
        headers=_auth(admin_token),
    )
    task_id = create_resp.json()["id"]

    resp = client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"title": "Hacked Title"},
        headers=_auth(citizen_token),
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN

    resp = client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"title": "Crew Updated Title"},
        headers=_auth(crew_token),
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_update_task_edge_case_not_found(client: TestClient, db_session: Session):
    """Edge Case: Updating non-existent task returns 404 Not Found."""
    admin_token = _register_and_login(
        db_session, client, "task_patch_404@example.com", UserRole.ADMIN
    )
    resp = client.patch(
        "/api/v1/tasks/999999",
        json={"title": "Non-existent task"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# 5. POST /tasks/{task_id}/complete (complete_task)
# ---------------------------------------------------------------------------


def test_complete_task_happy_path(client: TestClient, db_session: Session):
    """Happy Path: Crew or Admin completes a task successfully."""
    admin_token = _register_and_login(
        db_session, client, "task_admin_cmpl@example.com", UserRole.ADMIN
    )
    crew_token = _register_and_login(
        db_session, client, "task_crew_cmpl@example.com", UserRole.CREW
    )

    create_resp = client.post(
        "/api/v1/tasks",
        json={"title": "Task to complete"},
        headers=_auth(admin_token),
    )
    task_id = create_resp.json()["id"]

    resp = client.post(f"/api/v1/tasks/{task_id}/complete", headers=_auth(crew_token))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == "completed"


def test_complete_task_validation_failure(client: TestClient, db_session: Session):
    """Validation Failure: Non-integer task_id path parameter returns 422."""
    crew_token = _register_and_login(db_session, client, "task_cmpl_val@example.com", UserRole.CREW)
    resp = client.post("/api/v1/tasks/abc/complete", headers=_auth(crew_token))
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_complete_task_rbac_failure(client: TestClient, db_session: Session):
    """Auth/RBAC Failure: Citizen role cannot complete a task."""
    admin_token = _register_and_login(
        db_session, client, "task_cmpl_admin@example.com", UserRole.ADMIN
    )
    citizen_token = _register_and_login(
        db_session, client, "task_cmpl_cit@example.com", UserRole.CITIZEN
    )

    create_resp = client.post(
        "/api/v1/tasks",
        json={"title": "Task for citizen complete attempt"},
        headers=_auth(admin_token),
    )
    task_id = create_resp.json()["id"]

    resp = client.post(f"/api/v1/tasks/{task_id}/complete", headers=_auth(citizen_token))
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_complete_task_edge_case_idempotent(client: TestClient, db_session: Session):
    """Edge Case: Completing an already completed task returns 200 OK idempotently."""
    crew_token = _register_and_login(
        db_session, client, "task_cmpl_idem@example.com", UserRole.CREW
    )
    admin_token = _register_and_login(
        db_session, client, "task_adm_idem@example.com", UserRole.ADMIN
    )

    create_resp = client.post(
        "/api/v1/tasks",
        json={"title": "Idempotent completion task"},
        headers=_auth(admin_token),
    )
    task_id = create_resp.json()["id"]

    # First completion
    client.post(f"/api/v1/tasks/{task_id}/complete", headers=_auth(crew_token))
    # Second completion
    resp2 = client.post(f"/api/v1/tasks/{task_id}/complete", headers=_auth(crew_token))
    assert resp2.status_code == status.HTTP_200_OK
    assert resp2.json()["status"] == "completed"


def test_complete_task_with_photo_and_waste_removed(client: TestClient, db_session: Session):
    """Happy Path: Complete task with completion_photo_url and waste_removed capture."""
    admin_token = _register_and_login(
        db_session, client, "task_cmpl_photo_adm@example.com", UserRole.ADMIN
    )
    crew_token = _register_and_login(
        db_session, client, "task_cmpl_photo_crew@example.com", UserRole.CREW
    )

    create_resp = client.post(
        "/api/v1/tasks",
        json={"title": "Cleanup task with photo"},
        headers=_auth(admin_token),
    )
    task_id = create_resp.json()["id"]

    completion_payload = {
        "completion_photo_url": "/uploads/after_clean.jpg",
        "waste_removed": "1.8 Tons",
        "resolution_notes": "All debris cleared",
    }
    resp = client.post(
        f"/api/v1/tasks/{task_id}/complete",
        json=completion_payload,
        headers=_auth(crew_token),
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["status"] == "completed"
    assert data["completion_photo_url"] == "/uploads/after_clean.jpg"
    assert data["waste_removed"] == "1.8 Tons"
    assert data["resolution_notes"] == "All debris cleared"


# ---------------------------------------------------------------------------
# 6. POST /tasks/{task_id}/cancel (cancel_task)
# ---------------------------------------------------------------------------


def test_cancel_task_happy_path(client: TestClient, db_session: Session):
    """Happy Path: Admin cancels a task successfully."""
    admin_token = _register_and_login(
        db_session, client, "task_cancel_adm@example.com", UserRole.ADMIN
    )

    create_resp = client.post(
        "/api/v1/tasks",
        json={"title": "Task to cancel"},
        headers=_auth(admin_token),
    )
    task_id = create_resp.json()["id"]

    resp = client.post(f"/api/v1/tasks/{task_id}/cancel", headers=_auth(admin_token))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == "cancelled"


def test_cancel_task_validation_failure(client: TestClient, db_session: Session):
    """Validation Failure: Non-integer task_id yields 422."""
    admin_token = _register_and_login(
        db_session, client, "task_cancel_val@example.com", UserRole.ADMIN
    )
    resp = client.post("/api/v1/tasks/invalid_id/cancel", headers=_auth(admin_token))
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_cancel_task_rbac_failure(client: TestClient, db_session: Session):
    """Auth/RBAC Failure: Crew role cannot cancel a task (Admin only)."""
    admin_token = _register_and_login(
        db_session, client, "task_cncl_owner@example.com", UserRole.ADMIN
    )
    crew_token = _register_and_login(
        db_session, client, "task_cncl_crew@example.com", UserRole.CREW
    )

    create_resp = client.post(
        "/api/v1/tasks",
        json={"title": "Task crew try cancel"},
        headers=_auth(admin_token),
    )
    task_id = create_resp.json()["id"]

    resp = client.post(f"/api/v1/tasks/{task_id}/cancel", headers=_auth(crew_token))
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_cancel_task_edge_case_not_found(client: TestClient, db_session: Session):
    """Edge Case: Cancelling non-existent task returns 404 Not Found."""
    admin_token = _register_and_login(
        db_session, client, "task_cancel_404@example.com", UserRole.ADMIN
    )
    resp = client.post("/api/v1/tasks/999999/cancel", headers=_auth(admin_token))
    assert resp.status_code == status.HTTP_404_NOT_FOUND
