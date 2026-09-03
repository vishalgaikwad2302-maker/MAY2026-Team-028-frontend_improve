"""End-to-End validation script for Crew Proof-of-Work task completion and cross-role sync.

Validates:
1. Auth for Citizen, Crew, and Admin.
2. Complaint creation and dispatch.
3. Strict proof-of-work photo validation (rejects 0 photos, rejects >3 photos).
4. RBAC security (rejects citizen resolution attempt with 403).
5. Multipart image upload under 200 KB.
6. Crew resolution with 2 completion photos and notes.
7. Direct SQLite database inspection verifying JSON array persistence.
8. Citizen retrieval of completion proof.
9. Admin audit and verification.
10. Task completion synchronization to linked complaint.
"""

import io
import sqlite3
import sys
import uuid
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import UserRole
from app.schemas.user import UserCreate
from app.services.auth_service import AuthService

def run_validation():
    print("=== STARTING CREW PROOF-OF-WORK E2E VALIDATION ===")
    client = TestClient(app)

    # 1. Auth Setup with fresh unique emails
    run_id = uuid.uuid4().hex[:8]
    citizen_email = f"cit_{run_id}@example.com"
    crew_email = f"crew_{run_id}@example.com"
    admin_email = f"admin_{run_id}@example.com"
    pwd = "SecurePassword123!"

    # Register Citizen via public HTTP endpoint
    reg_cit = client.post("/api/v1/auth/register", json={
        "full_name": "Citizen Ramesh",
        "email": citizen_email,
        "password": pwd,
    })
    assert reg_cit.status_code == 201, reg_cit.text
    log_cit = client.post("/api/v1/auth/login", json={"email": citizen_email, "password": pwd})
    cit_token = log_cit.json()["access_token"]
    cit_headers = {"Authorization": f"Bearer {cit_token}"}
    print("[OK] 1. Citizen registered and authenticated via HTTP")

    # Provision Crew and Admin accounts directly via Service (as required by system architecture)
    with SessionLocal() as db:
        AuthService.register_user(
            db,
            UserCreate(full_name="Crew Suresh", email=crew_email, password=pwd, role=UserRole.CREW),
        )
        AuthService.register_user(
            db,
            UserCreate(full_name="Supervisor Joshi", email=admin_email, password=pwd, role=UserRole.ADMIN),
        )

    log_crew = client.post("/api/v1/auth/login", json={"email": crew_email, "password": pwd})
    assert log_crew.status_code == 200, log_crew.text
    crew_token = log_crew.json()["access_token"]
    crew_headers = {"Authorization": f"Bearer {crew_token}"}
    print("[OK] 2. Crew authenticated via HTTP")

    log_admin = client.post("/api/v1/auth/login", json={"email": admin_email, "password": pwd})
    assert log_admin.status_code == 200, log_admin.text
    admin_token = log_admin.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("[OK] 3. Admin authenticated via HTTP")

    # 2. Citizen creates a complaint
    comp_res = client.post("/api/v1/complaints", json={
        "location": "Severe garbage overflow near Market Road",
        "description": "Large accumulation of commercial waste blocking footpath.",
        "category": "Garbage",
        "address": "Market Road, Ward 4",
        "latitude": 18.5204,
        "longitude": 73.8567
    }, headers=cit_headers)
    assert comp_res.status_code == 201, comp_res.text
    complaint_id = comp_res.json()["id"]
    print(f"[OK] 4. Complaint #{complaint_id} created by citizen")

    # 3. Admin moves complaint to in_progress
    prog_res = client.patch(
        f"/api/v1/complaints/{complaint_id}/status",
        json={"status_value": "in_progress"},
        headers=admin_headers
    )
    assert prog_res.status_code == 200, prog_res.text
    print(f"[OK] 5. Complaint #{complaint_id} moved to in_progress")

    # 4. Strict Validation: Empty completion_photos must fail (422)
    empty_res = client.post(
        f"/api/v1/complaints/{complaint_id}/resolve",
        json={"completion_photos": [], "resolution_notes": "Done"},
        headers=crew_headers
    )
    assert empty_res.status_code == 422, f"Expected 422 for empty photos, got {empty_res.status_code}"
    print("[OK] 6. Validation verified: 0 photos rejected with 422")

    # 5. Strict Validation: >3 completion_photos must fail (422)
    over_res = client.post(
        f"/api/v1/complaints/{complaint_id}/resolve",
        json={"completion_photos": ["/p1.jpg", "/p2.jpg", "/p3.jpg", "/p4.jpg"]},
        headers=crew_headers
    )
    assert over_res.status_code == 422, f"Expected 422 for 4 photos, got {over_res.status_code}"
    print("[OK] 7. Validation verified: 4 photos rejected with 422")

    # 6. RBAC Security: Citizen cannot resolve complaint (403)
    unauth_res = client.post(
        f"/api/v1/complaints/{complaint_id}/resolve",
        json={"completion_photos": ["/p1.jpg"]},
        headers=cit_headers
    )
    assert unauth_res.status_code == 403, f"Expected 403 for citizen resolve, got {unauth_res.status_code}"
    print("[OK] 8. RBAC verified: Citizen resolution forbidden (403)")

    # 7. Upload 2 proof photos (<200 KB each)
    tiny_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05"
        b"\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    up1 = client.post(
        "/api/v1/complaints/upload-photo",
        files={"photo": ("proof1.png", io.BytesIO(tiny_png), "image/png")},
        headers=crew_headers
    )
    assert up1.status_code == 200, up1.text
    photo1_url = up1.json()["url"]

    up2 = client.post(
        "/api/v1/complaints/upload-photo",
        files={"photo": ("proof2.png", io.BytesIO(tiny_png), "image/png")},
        headers=crew_headers
    )
    assert up2.status_code == 200, up2.text
    photo2_url = up2.json()["url"]
    print(f"[OK] 9. Crew uploaded 2 proof photos: {photo1_url}, {photo2_url}")

    # 8. Crew resolves complaint with proof photos and remarks
    res_notes = "Cleared 850kg waste. Swept and disinfected entire sidewalk."
    resolve_res = client.post(
        f"/api/v1/complaints/{complaint_id}/resolve",
        json={
            "completion_photos": [photo1_url, photo2_url],
            "resolution_notes": res_notes
        },
        headers=crew_headers
    )
    assert resolve_res.status_code == 200, resolve_res.text
    resolved_data = resolve_res.json()
    assert resolved_data["status"] == "resolved"
    assert resolved_data["completion_photos"] == [photo1_url, photo2_url]
    assert resolved_data["resolution_notes"] == res_notes
    assert resolved_data["resolved_at"] is not None
    print(f"[OK] 10. Complaint #{complaint_id} resolved with 2 proof photos & notes")

    # 9. Direct SQLite DB verification
    con = sqlite3.connect("smartsweep.db")
    cur = con.cursor()
    row = cur.execute(
        "SELECT status, completion_photos, resolution_notes, resolved_at FROM complaints WHERE id = ?",
        (complaint_id,)
    ).fetchone()
    con.close()

    assert row is not None, "Complaint row not found in DB"
    assert row[0] == "resolved", f"DB status is {row[0]}"
    assert photo1_url in row[1] and photo2_url in row[1], f"DB completion_photos missing urls: {row[1]}"
    assert row[2] == res_notes, f"DB resolution_notes mismatch: {row[2]}"
    assert row[3] is not None, "DB resolved_at timestamp is None"
    print("[OK] 11. Direct SQLite row inspection confirmed JSON completion_photos & resolution_notes")

    # 10. Citizen inspects complaint (synchronization check)
    cit_view = client.get(f"/api/v1/complaints/{complaint_id}", headers=cit_headers)
    assert cit_view.status_code == 200, cit_view.text
    cv_data = cit_view.json()
    assert cv_data["status"] == "resolved"
    assert len(cv_data["completion_photos"]) == 2
    assert cv_data["resolution_notes"] == res_notes
    print("[OK] 12. Citizen retrieval verified: proof photos & remarks returned accurately")

    # 11. Admin verifies and closes complaint
    verify_res = client.patch(
        f"/api/v1/complaints/{complaint_id}/verify",
        json={"notes": "Supervisor reviewed photographic proof. Remediation verified."},
        headers=admin_headers
    )
    assert verify_res.status_code == 200, verify_res.text
    assert verify_res.json()["status"] == "verified"
    assert verify_res.json()["completion_photos"] == [photo1_url, photo2_url]
    print("[OK] 13. Admin verified complaint after reviewing proof")

    close_res = client.patch(
        f"/api/v1/complaints/{complaint_id}/close",
        json={"notes": "Case closed officially."},
        headers=admin_headers
    )
    assert close_res.status_code == 200, close_res.text
    assert close_res.json()["status"] == "closed"
    assert close_res.json()["completion_photos"] == [photo1_url, photo2_url]
    print("[OK] 14. Admin closed complaint; proof of work persisted through final lifecycle")

    print("\n>>> ALL 14 CREW PROOF-OF-WORK E2E CHECKS PASSED WITH 100% SUCCESS! <<<")

if __name__ == "__main__":
    run_validation()
