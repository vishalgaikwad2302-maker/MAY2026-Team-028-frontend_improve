"""Integration test for end-to-end Complaint -> Task lifecycle flow (B-4).

Tests the full state machine transition:
1. Citizen submits a complaint (Status: pending).
2. Admin assigns a task to resolve the complaint (Complaint Status -> in_progress, Task created & resources assigned).
3. Crew completes the task (Task Status -> completed, Complaint Status -> resolved, Resources freed back to available).
4. Verify complete history log and status transitions.
"""

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
    """Register a user with a given role and return an access token."""
    AuthService.register_user(
        db,
        UserCreate(
            email=email,
            password="password123",
            full_name=f"User {role.value}",
            role=role,
        ),
    )
    tokens = AuthService.authenticate_user(db, LoginRequest(email=email, password="password123"))
    return tokens.access_token


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Integration Test
# ---------------------------------------------------------------------------


def test_complaint_to_task_end_to_end_flow(client: TestClient, db_session: Session):
    """End-to-end lifecycle test from complaint submission to task completion."""

    # 1. Setup Users & Resources
    citizen_token = _register_and_login(
        db_session, client, "flow_citizen@example.com", UserRole.CITIZEN
    )
    admin_token = _register_and_login(db_session, client, "flow_admin@example.com", UserRole.ADMIN)
    crew_token = _register_and_login(db_session, client, "flow_crew@example.com", UserRole.CREW)

    worker = Worker(full_name="Flow Worker", status=WorkerStatus.AVAILABLE.value, is_active=True)
    vehicle = Vehicle(
        plate_number="KA-09-FLOW-1",
        model_name="Flow Truck",
        status=VehicleStatus.AVAILABLE.value,
        is_active=True,
    )
    equipment = Equipment(
        name="Flow Shovel",
        status=EquipmentStatus.AVAILABLE.value,
        available_quantity=5,
        is_active=True,
    )
    db_session.add_all([worker, vehicle, equipment])
    db_session.commit()
    db_session.refresh(worker)
    db_session.refresh(vehicle)
    db_session.refresh(equipment)

    # 2. Step 1: Citizen submits a complaint
    complaint_resp = client.post(
        "/api/v1/complaints",
        json={
            "location": "Flow Street 42",
            "description": "Heavy garbage overflow near park",
            "hazard": "Overflowing Bin",
        },
        headers=_auth(citizen_token),
    )
    assert complaint_resp.status_code == status.HTTP_201_CREATED
    complaint_data = complaint_resp.json()
    complaint_id = complaint_data["id"]
    assert complaint_data["status"] == "pending"

    # Verify initial history
    hist_resp = client.get(
        f"/api/v1/complaints/{complaint_id}/history", headers=_auth(citizen_token)
    )
    assert hist_resp.status_code == status.HTTP_200_OK
    assert len(hist_resp.json()) == 1
    assert hist_resp.json()[0]["to_status"] == "pending"

    # 3. Step 2: Admin assigns task linked to complaint with resources
    task_payload = {
        "title": "Clear Flow Street Overflow",
        "description": "Dispatch truck and worker to clean overflow",
        "complaint_id": complaint_id,
        "worker_ids": [worker.id],
        "vehicle_id": vehicle.id,
        "equipment_ids": [equipment.id],
    }
    task_resp = client.post("/api/v1/tasks", json=task_payload, headers=_auth(admin_token))
    assert task_resp.status_code == status.HTTP_201_CREATED
    task_data = task_resp.json()
    task_id = task_data["id"]
    assert task_data["complaint_id"] == complaint_id

    # Assert Complaint status transitioned from 'pending' -> 'in_progress'
    comp_check = client.get(f"/api/v1/complaints/{complaint_id}", headers=_auth(admin_token))
    assert comp_check.status_code == status.HTTP_200_OK
    assert comp_check.json()["status"] == "in_progress"

    # Assert Resources are now assigned/en_route/in_use
    worker_check = client.get("/api/v1/resources/workers", headers=_auth(admin_token))
    assigned_worker = next(w for w in worker_check.json() if w["id"] == worker.id)
    assert assigned_worker["status"] == "assigned"

    vehicle_check = client.get("/api/v1/resources/vehicles", headers=_auth(admin_token))
    assigned_vehicle = next(v for v in vehicle_check.json() if v["id"] == vehicle.id)
    assert assigned_vehicle["status"] == "en_route"

    # 4. Step 3: Crew completes the task
    complete_resp = client.post(f"/api/v1/tasks/{task_id}/complete", headers=_auth(crew_token))
    assert complete_resp.status_code == status.HTTP_200_OK
    assert complete_resp.json()["status"] == "completed"

    # Assert Complaint status transitioned from 'in_progress' -> 'resolved'
    comp_resolved = client.get(f"/api/v1/complaints/{complaint_id}", headers=_auth(citizen_token))
    assert comp_resolved.status_code == status.HTTP_200_OK
    assert comp_resolved.json()["status"] == "resolved"
    assert comp_resolved.json()["resolved_at"] is not None

    # Assert Resources are freed back to 'available'
    worker_freed = client.get("/api/v1/resources/workers", headers=_auth(admin_token))
    freed_w = next(w for w in worker_freed.json() if w["id"] == worker.id)
    assert freed_w["status"] == "available"

    vehicle_freed = client.get("/api/v1/resources/vehicles", headers=_auth(admin_token))
    freed_v = next(v for v in vehicle_freed.json() if v["id"] == vehicle.id)
    assert freed_v["status"] == "available"

    # 5. Step 4: Verify complete history trail
    final_hist = client.get(
        f"/api/v1/complaints/{complaint_id}/history", headers=_auth(citizen_token)
    )
    assert final_hist.status_code == status.HTTP_200_OK
    history_entries = final_hist.json()
    assert len(history_entries) == 3
    statuses = [h["to_status"] for h in history_entries]
    assert statuses == ["pending", "in_progress", "resolved"]
