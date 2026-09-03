"""End-to-End Validation Script for Transparency Feed, Database Sync, and Image Uploads."""

import io
import json
import sqlite3
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.user import UserRole
from app.schemas.user import UserCreate
from app.schemas.auth import LoginRequest
from app.services.auth_service import AuthService

def run_validation():
    print("=== Starting E2E Transparency Validation ===")
    client = TestClient(app)
    db = SessionLocal()

    # 1. Register & authenticate citizen
    email = f"validator_{sqlite3.connect('smartsweep.db').total_changes}@test.gov"
    try:
        AuthService.register_user(
            db,
            UserCreate(email=email, password="ValidPassword123!", full_name="Validation Citizen", role=UserRole.CITIZEN)
        )
    except Exception as e:
        print("Note on registration:", e)
    
    tokens = AuthService.authenticate_user(db, LoginRequest(email=email, password="ValidPassword123!"))
    token = tokens.access_token
    auth_headers = {"Authorization": f"Bearer {token}"}
    print("[OK] 1. Citizen authentication successful")

    # 2. Upload sample compressed photo
    fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200 # Valid PNG signature, ~210 bytes (under 200KB)
    upload_resp = client.post(
        "/api/v1/complaints/upload-photo",
        files={"photo": ("compressed_evidence.png", io.BytesIO(fake_png), "image/png")},
        headers=auth_headers,
    )
    assert upload_resp.status_code == 200, f"Upload failed: {upload_resp.text}"
    img_url = upload_resp.json()["url"]
    assert img_url.startswith("/uploads/"), f"Unexpected URL format: {img_url}"
    print(f"[OK] 2. Image upload validated. Saved to: {img_url}")

    # 3. Create standalone transparency post with 3 images
    img_urls = [img_url, "/uploads/simulated_2.jpg", "/uploads/simulated_3.webp"]
    post_payload = {
        "title": "E2E Verified Street Cleaning",
        "description": "Comprehensive cleanup of roadside dumping with 3 verified photos.",
        "images": img_urls,
    }
    create_resp = client.post("/api/v1/transparency", json=post_payload, headers=auth_headers)
    assert create_resp.status_code == 201, f"Post creation failed: {create_resp.text}"
    post_data = create_resp.json()
    post_id = post_data["id"]
    assert post_data["title"] == post_payload["title"]
    assert post_data["complaint_id"] is None
    assert post_data["images"] == img_urls
    print(f"[OK] 3. Standalone post created successfully with ID: {post_id}")

    # 4. Fetch feed and verify serialization
    feed_resp = client.get("/api/v1/transparency")
    assert feed_resp.status_code == 200, f"List feed failed: {feed_resp.text}"
    items = feed_resp.json()["items"]
    matching = [p for p in items if p["id"] == post_id]
    assert len(matching) == 1, "Created post not found in public feed list!"
    assert matching[0]["images"] == img_urls
    print("[OK] 4. Public feed retrieval and Pydantic serialization verified")

    # 5. Applaud post
    applaud_resp = client.post(f"/api/v1/transparency/{post_id}/applaud")
    assert applaud_resp.status_code == 200, f"Applaud failed: {applaud_resp.text}"
    assert applaud_resp.json()["applause_count"] == 1
    print("[OK] 5. Applaud interaction verified (count = 1)")

    # 6. Add comment
    comment_resp = client.post(
        f"/api/v1/transparency/{post_id}/comments",
        json={"comment": "Great work keeping the street clean!"},
        headers=auth_headers,
    )
    assert comment_resp.status_code == 201, f"Comment failed: {comment_resp.text}"
    print("[OK] 6. Citizen feedback comment verified")

    # 7. Direct Database Query via SQLite
    conn = sqlite3.connect("smartsweep.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, complaint_id, title, images, applause_count FROM transparency_posts WHERE id = ?", (post_id,))
    row = cursor.fetchone()
    assert row is not None, "Direct DB check: Row not found in smartsweep.db!"
    db_id, db_complaint_id, db_title, db_images_json, db_applauds = row
    assert db_complaint_id is None, "Direct DB check: complaint_id should be NULL!"
    assert db_title == "E2E Verified Street Cleaning"
    assert db_applauds == 1
    stored_images = json.loads(db_images_json) if isinstance(db_images_json, str) else db_images_json
    assert stored_images == img_urls, f"Stored images mismatch: {stored_images}"
    print(f"[OK] 7. Direct SQL Inspection in smartsweep.db: Row {db_id} confirmed with valid JSON images array")

    print("\n[SUCCESS] ALL 7 E2E VALIDATION CHECKS PASSED PERFECTLY!")
    db.close()
    conn.close()

if __name__ == "__main__":
    run_validation()
