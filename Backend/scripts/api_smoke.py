"""End-to-end API smoke test.

Exercises every route registered on the v1 router against a throwaway SQLite
database and prints a pass/fail table plus a JSON summary. Run with:

    uv run python scripts/api_smoke.py

Nothing here touches the real ``smartsweep.db`` — ``DATABASE_URL`` is pointed at
a temp file before ``app`` is imported.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

_TMP_DB = Path(tempfile.gettempdir()) / "smartsweep_api_smoke.db"
if _TMP_DB.exists():
    _TMP_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB.as_posix()}"
os.environ["ENV"] = "test"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.equipment import Equipment  # noqa: E402
from app.models.vehicle import Vehicle  # noqa: E402
from app.models.ward import Ward  # noqa: E402
from app.models.worker import Worker  # noqa: E402

PREFIX = "/api/v1"

RESULTS: list[dict] = []


def check(
    name: str,
    method: str,
    path: str,
    expected: int | tuple[int, ...],
    response,
    note: str = "",
    kind: str = "contract",
) -> None:
    """Record one endpoint result.

    ``kind="observation"`` records current behaviour without asserting it is
    correct — used where the API works but the design is worth flagging.
    """
    expected_set = expected if isinstance(expected, tuple) else (expected,)
    ok = response.status_code in expected_set
    try:
        body = response.json()
    except Exception:
        body = response.text[:200]
    RESULTS.append(
        {
            "name": name,
            "method": method,
            "path": path,
            "expected": list(expected_set),
            "actual": response.status_code,
            "ok": ok,
            "kind": kind,
            "ms": round(response.elapsed.total_seconds() * 1000, 1) if response.elapsed else None,
            "note": note,
            "body": body if not ok else None,
        }
    )
    flag = ("PASS" if ok else "FAIL") if kind == "contract" else "NOTE"
    print(f"[{flag}] {method:6} {path:52} -> {response.status_code} (want {list(expected_set)})")
    if not ok:
        print(f"         body: {json.dumps(body)[:400]}")
    if note:
        print(f"         note: {note}")


def check_body(name: str, ok: bool, detail: str) -> None:
    """Record a payload-shape assertion alongside the status-code results."""
    RESULTS.append(
        {
            "name": name,
            "method": "BODY",
            "path": "-",
            "expected": ["shape"],
            "actual": "ok" if ok else "mismatch",
            "ok": ok,
            "kind": "contract",
            "ms": None,
            "note": detail,
            "body": None if ok else detail,
        }
    )
    print(f"[{'PASS' if ok else 'FAIL'}] BODY   {name:52} -> {detail}")


def seed_reference_data() -> dict[str, int]:
    """init_db seeds users only; wards/workers/vehicles/equipment are added here."""
    db = SessionLocal()
    try:
        ward = Ward(
            name="Ward 12 - Kothrud", code="W12", zone="West", description="Smoke test ward"
        )
        db.add(ward)
        db.flush()
        worker = Worker(
            full_name="Ramesh Kadam", employee_code="EMP-001", role_title="Sweeper", ward_id=ward.id
        )
        vehicle = Vehicle(
            plate_number="MH12-AB-1234",
            model_name="Tata Ace Compactor",
            vehicle_type="compactor",
            ward_id=ward.id,
        )
        equipment = Equipment(
            name="Industrial Broom",
            asset_tag="EQ-001",
            total_quantity=10,
            available_quantity=10,
            ward_id=ward.id,
        )
        db.add_all([worker, vehicle, equipment])
        db.commit()
        return {
            "ward_id": ward.id,
            "worker_id": worker.id,
            "vehicle_id": vehicle.id,
            "equipment_id": equipment.id,
        }
    finally:
        db.close()


def login(client: TestClient, email: str, password: str) -> dict[str, str]:
    resp = client.post(f"{PREFIX}/auth/login", json={"email": email, "password": password})
    resp.raise_for_status()
    return resp.json()


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def main() -> int:
    app = create_app()
    # raise_server_exceptions=False so an unhandled 500 is recorded as a failing
    # result instead of aborting the whole run.
    with TestClient(app, raise_server_exceptions=False) as client:
        ids = seed_reference_data()

        # ------------------------------------------------------------- AUTH
        print("\n=== Auth ===")
        new_user = {
            "email": "smoke.tester@smartsweep.gov",
            "full_name": "Smoke Tester",
            "password": "smoke123",
            "phone": "9999999999",
            "ward_id": ids["ward_id"],
        }
        r = client.post(f"{PREFIX}/auth/register", json=new_user)
        check("Register new citizen", "POST", "/auth/register", 201, r)

        r = client.post(f"{PREFIX}/auth/register", json=new_user)
        check("Register duplicate email rejected", "POST", "/auth/register", 409, r)

        r = client.post(
            f"{PREFIX}/auth/register",
            json={"email": "not-an-email", "full_name": "X", "password": "123"},
        )
        check("Register invalid payload rejected", "POST", "/auth/register", 422, r)

        r = client.post(
            f"{PREFIX}/auth/login", json={"email": "admin@smartsweep.gov", "password": "admin123"}
        )
        check("Login admin (seeded)", "POST", "/auth/login", 200, r)
        admin = r.json()

        r = client.post(
            f"{PREFIX}/auth/login", json={"email": "crew@smartsweep.gov", "password": "crew123"}
        )
        check("Login crew (seeded)", "POST", "/auth/login", 200, r)
        crew = r.json()

        r = client.post(
            f"{PREFIX}/auth/login",
            json={"email": "citizen@smartsweep.gov", "password": "citizen123"},
        )
        check("Login citizen (seeded)", "POST", "/auth/login", 200, r)
        citizen = r.json()

        r = client.post(
            f"{PREFIX}/auth/login", json={"email": "admin@smartsweep.gov", "password": "wrong"}
        )
        check("Login wrong password rejected", "POST", "/auth/login", 401, r)

        r = client.post(f"{PREFIX}/auth/refresh", json={"refresh_token": admin["refresh_token"]})
        check("Refresh with valid refresh token", "POST", "/auth/refresh", 200, r)

        r = client.post(f"{PREFIX}/auth/refresh", json={"refresh_token": admin["access_token"]})
        check("Refresh rejects access token", "POST", "/auth/refresh", 401, r)

        r = client.get(f"{PREFIX}/auth/me", headers=bearer(admin["access_token"]))
        check("Get own profile", "GET", "/auth/me", 200, r)

        r = client.get(f"{PREFIX}/auth/me")
        check("Profile without token rejected", "GET", "/auth/me", 401, r)

        r = client.get(f"{PREFIX}/auth/me", headers=bearer("garbage.token.value"))
        check("Profile with malformed token rejected", "GET", "/auth/me", 401, r)

        r = client.get(f"{PREFIX}/auth/admin-only", headers=bearer(admin["access_token"]))
        check("Admin-only as admin", "GET", "/auth/admin-only", 200, r)

        r = client.get(f"{PREFIX}/auth/admin-only", headers=bearer(citizen["access_token"]))
        check("Admin-only as citizen forbidden", "GET", "/auth/admin-only", 403, r)

        r = client.get(f"{PREFIX}/auth/crew-only", headers=bearer(crew["access_token"]))
        check("Crew-only as crew", "GET", "/auth/crew-only", 200, r)

        r = client.get(f"{PREFIX}/auth/crew-only", headers=bearer(citizen["access_token"]))
        check("Crew-only as citizen forbidden", "GET", "/auth/crew-only", 403, r)

        # ------------------------------------------------------------ WARDS
        print("\n=== Wards ===")
        r = client.get(f"{PREFIX}/wards")
        check("List wards", "GET", "/wards", 200, r)

        r = client.get(f"{PREFIX}/wards/{ids['ward_id']}")
        check("Get ward by id", "GET", "/wards/{ward_id}", 200, r)

        r = client.get(f"{PREFIX}/wards/999999")
        check("Get unknown ward -> 404", "GET", "/wards/{ward_id}", 404, r)

        # The registered smoke user has ward_id set; the seeded demo users do not.
        smoke = login(client, new_user["email"], new_user["password"])
        r = client.get(f"{PREFIX}/wards/me", headers=bearer(smoke["access_token"]))
        check("Get my ward", "GET", "/wards/me", 200, r, note="route-order sensitive")

        r = client.get(f"{PREFIX}/wards/me", headers=bearer(admin["access_token"]))
        check("Get my ward when user has none -> 404", "GET", "/wards/me", 404, r)

        r = client.get(f"{PREFIX}/wards/me")
        check("Get my ward without token rejected", "GET", "/wards/me", 401, r)

        # ------------------------------------------------------- COMPLAINTS
        print("\n=== Complaints ===")
        payload = {
            "location": "MG Road near bus stop",
            "description": "Overflowing garbage bin attracting stray dogs.",
            "hazard": "biohazard",
            "coords": {"lat": 18.5204, "lng": 73.8567},
            "ward_id": ids["ward_id"],
        }
        r = client.post(
            f"{PREFIX}/complaints", json=payload, headers=bearer(citizen["access_token"])
        )
        check("Create complaint", "POST", "/complaints", 201, r)
        complaint_id = r.json().get("id") if r.status_code == 201 else None

        r = client.post(f"{PREFIX}/complaints", json=payload)
        check("Create complaint unauthenticated rejected", "POST", "/complaints", 401, r)

        r = client.post(
            f"{PREFIX}/complaints",
            json={"description": "no location"},
            headers=bearer(citizen["access_token"]),
        )
        check("Create complaint invalid payload rejected", "POST", "/complaints", 422, r)

        # second complaint used for cancel + duplicate detection
        dup_payload = dict(
            payload, description="Garbage bin overflowing near the MG Road bus stop."
        )
        r = client.post(
            f"{PREFIX}/complaints", json=dup_payload, headers=bearer(citizen["access_token"])
        )
        check("Create near-duplicate complaint", "POST", "/complaints", 201, r)
        dup_id = r.json().get("id") if r.status_code == 201 else None

        r = client.get(f"{PREFIX}/complaints")
        check("List complaints (paged)", "GET", "/complaints", 200, r)

        r = client.get(
            f"{PREFIX}/complaints",
            params={"status": "pending", "ward_id": ids["ward_id"], "page": 1, "page_size": 5},
        )
        check("List complaints with filters", "GET", "/complaints?filters", 200, r)

        r = client.get(f"{PREFIX}/complaints", params={"search": "garbage"})
        check("List complaints with search", "GET", "/complaints?search", 200, r)

        if complaint_id:
            r = client.get(f"{PREFIX}/complaints/{complaint_id}")
            check("Get complaint by id", "GET", "/complaints/{id}", 200, r)

        r = client.get(f"{PREFIX}/complaints/999999")
        check("Get unknown complaint -> 404", "GET", "/complaints/{id}", 404, r)

        if complaint_id:
            r = client.patch(
                f"{PREFIX}/complaints/{complaint_id}",
                json={"priority": "high", "category": "biohazard"},
            )
            check("Update complaint fields", "PATCH", "/complaints/{id}", 200, r)

            r = client.patch(
                f"{PREFIX}/complaints/{complaint_id}/status",
                json={"status_value": "in_progress"},
                headers=bearer(crew["access_token"]),
            )
            check(
                "Change status pending -> in_progress", "PATCH", "/complaints/{id}/status", 200, r
            )

            r = client.patch(
                f"{PREFIX}/complaints/{complaint_id}/status",
                json={"status_value": "pending"},
                headers=bearer(crew["access_token"]),
            )
            check(
                "Illegal transition in_progress -> pending rejected",
                "PATCH",
                "/complaints/{id}/status",
                409,
                r,
            )

            r = client.patch(
                f"{PREFIX}/complaints/{complaint_id}/status",
                json={"status_value": "resolved"},
                headers=bearer(crew["access_token"]),
            )
            check(
                "Change status in_progress -> resolved", "PATCH", "/complaints/{id}/status", 200, r
            )

            r = client.post(
                f"{PREFIX}/complaints/{complaint_id}/cancel",
                headers=bearer(citizen["access_token"]),
            )
            check("Cancel resolved complaint rejected", "POST", "/complaints/{id}/cancel", 409, r)

            r = client.get(f"{PREFIX}/complaints/{complaint_id}/history")
            check("Complaint status history", "GET", "/complaints/{id}/history", 200, r)
            if r.status_code == 200:
                rows = r.json()
                transitions = [f"{h.get('from_status')}->{h.get('to_status')}" for h in rows]
                check_body(
                    "History records the full audit trail",
                    transitions
                    == ["new->pending", "pending->in_progress", "in_progress->resolved"],
                    " | ".join(transitions) or "empty",
                )
                check_body(
                    "History rows carry required fields",
                    all(
                        {
                            "id",
                            "complaint_id",
                            "from_status",
                            "to_status",
                            "changed_by_user_id",
                            "created_at",
                        }
                        <= set(h)
                        for h in rows
                    ),
                    f"{len(rows)} rows",
                )

            r = client.get(f"{PREFIX}/complaints/{complaint_id}/duplicates")
            check("Duplicate detection", "GET", "/complaints/{id}/duplicates", 200, r)
            if r.status_code == 200:
                matches = r.json()
                check_body(
                    "Duplicate scan found the near-identical report",
                    len(matches) >= 1,
                    f"{len(matches)} match(es)",
                )
                check_body(
                    "Match embeds a serialized complaint, not an ORM object",
                    bool(matches)
                    and isinstance(matches[0].get("complaint"), dict)
                    and "id" in matches[0]["complaint"],
                    f"keys={sorted(matches[0])}" if matches else "no matches to inspect",
                )

        if dup_id:
            r = client.post(
                f"{PREFIX}/complaints/{dup_id}/cancel", headers=bearer(citizen["access_token"])
            )
            check("Cancel pending complaint", "POST", "/complaints/{id}/cancel", 200, r)

        r = client.get(f"{PREFIX}/complaints/high-risk")
        check(
            "High-risk complaints feed",
            "GET",
            "/complaints/high-risk",
            200,
            r,
            note="route-order sensitive",
        )
        if r.status_code == 200:
            body = r.json()
            check_body(
                "High-risk returns a Page envelope",
                isinstance(body, dict) and {"items", "meta"} <= set(body),
                f"keys={sorted(body) if isinstance(body, dict) else type(body).__name__}",
            )
            check_body(
                "High-risk picks up the biohazard/high-priority complaint",
                bool(body.get("items")),
                f"{body.get('meta', {}).get('total')} total",
            )

        png = b"\x89PNG\r\n\x1a\n" + b"0" * 512
        r = client.post(
            f"{PREFIX}/complaints/upload-photo", files={"photo": ("bin.png", png, "image/png")}
        )
        check("Upload valid photo", "POST", "/complaints/upload-photo", 200, r)

        r = client.post(
            f"{PREFIX}/complaints/upload-photo",
            files={"photo": ("evil.exe", b"MZ", "application/octet-stream")},
        )
        check("Upload disallowed MIME rejected", "POST", "/complaints/upload-photo", 415, r)

        r = client.post(
            f"{PREFIX}/complaints/upload-photo",
            files={"photo": ("huge.png", b"0" * (6 * 1024 * 1024), "image/png")},
        )
        check("Upload oversized photo rejected", "POST", "/complaints/upload-photo", 413, r)

        # ------------------------------------------------------------ TASKS
        print("\n=== Tasks ===")
        # Creating a task drives its linked complaint pending -> in_progress, so
        # it needs a complaint that is still pending.
        r = client.post(
            f"{PREFIX}/complaints",
            json=dict(
                payload,
                location="Sinhagad Road drain",
                description="Blocked storm drain overflowing onto footpath.",
            ),
            headers=bearer(citizen["access_token"]),
        )
        task_complaint_id = r.json().get("id") if r.status_code == 201 else None

        task_payload = {
            "title": "Clear overflowing bin on MG Road",
            "description": "Dispatch compactor and two sweepers.",
            "complaint_id": task_complaint_id,
            "ward_id": ids["ward_id"],
            "vehicle_id": ids["vehicle_id"],
            "worker_ids": [ids["worker_id"]],
            "equipment_ids": [ids["equipment_id"]],
        }
        r = client.post(f"{PREFIX}/tasks", json=task_payload, headers=bearer(admin["access_token"]))
        check("Create task as admin", "POST", "/tasks", 201, r)
        task_id = r.json().get("id") if r.status_code == 201 else None

        r = client.post(
            f"{PREFIX}/tasks", json=task_payload, headers=bearer(citizen["access_token"])
        )
        check("Create task as citizen forbidden", "POST", "/tasks", 403, r)

        r = client.get(f"{PREFIX}/tasks", headers=bearer(admin["access_token"]))
        check("List tasks as admin", "GET", "/tasks", 200, r)

        r = client.get(f"{PREFIX}/tasks", headers=bearer(crew["access_token"]))
        check("List tasks as crew", "GET", "/tasks", 200, r)

        r = client.get(f"{PREFIX}/tasks", headers=bearer(citizen["access_token"]))
        check("List tasks as citizen forbidden", "GET", "/tasks", 403, r)

        if task_id:
            r = client.get(f"{PREFIX}/tasks/{task_id}", headers=bearer(crew["access_token"]))
            check("Get task by id", "GET", "/tasks/{id}", 200, r)

            r = client.patch(
                f"{PREFIX}/tasks/{task_id}",
                json={"status": "in_progress"},
                headers=bearer(crew["access_token"]),
            )
            check("Update task status as crew", "PATCH", "/tasks/{id}", 200, r)

            r = client.post(
                f"{PREFIX}/tasks/{task_id}/complete", headers=bearer(crew["access_token"])
            )
            check("Complete task as crew", "POST", "/tasks/{id}/complete", 200, r)

            r = client.post(
                f"{PREFIX}/tasks/{task_id}/cancel", headers=bearer(admin["access_token"])
            )
            check(
                "Cancel an already-completed task",
                "POST",
                "/tasks/{id}/cancel",
                200,
                r,
                note="succeeds — cancel_task has no state-machine guard, unlike complaint cancel",
                kind="observation",
            )

        r = client.get(f"{PREFIX}/tasks/999999")
        check("Get unknown task -> 404", "GET", "/tasks/{id}", 404, r)

        # second task, unlinked from any complaint, purely for the cancel happy path
        r = client.post(
            f"{PREFIX}/tasks",
            json=dict(task_payload, title="Second sweep pass", complaint_id=None),
            headers=bearer(admin["access_token"]),
        )
        check("Create task with no linked complaint", "POST", "/tasks", 201, r)
        cancel_task_id = r.json().get("id") if r.status_code == 201 else None
        if cancel_task_id:
            r = client.post(
                f"{PREFIX}/tasks/{cancel_task_id}/cancel", headers=bearer(admin["access_token"])
            )
            check("Cancel assigned task", "POST", "/tasks/{id}/cancel", 200, r)

        # -------------------------------------------------------- RESOURCES
        print("\n=== Resources ===")
        r = client.get(f"{PREFIX}/resources/workers", headers=bearer(admin["access_token"]))
        check("List workers", "GET", "/resources/workers", 200, r)

        r = client.get(f"{PREFIX}/resources/workers", headers=bearer(citizen["access_token"]))
        check("List workers as citizen forbidden", "GET", "/resources/workers", 403, r)

        r = client.patch(
            f"{PREFIX}/resources/workers/{ids['worker_id']}/status",
            params={"status_value": "off_duty"},
            headers=bearer(admin["access_token"]),
        )
        check("Update worker status", "PATCH", "/resources/workers/{id}/status", 200, r)

        r = client.patch(
            f"{PREFIX}/resources/workers/{ids['worker_id']}/status",
            params={"status_value": "teleported"},
            headers=bearer(admin["access_token"]),
        )
        check("Invalid worker status rejected", "PATCH", "/resources/workers/{id}/status", 422, r)

        r = client.patch(
            f"{PREFIX}/resources/workers/999999/status",
            params={"status_value": "available"},
            headers=bearer(admin["access_token"]),
        )
        check("Update unknown worker -> 404", "PATCH", "/resources/workers/{id}/status", 404, r)

        r = client.get(f"{PREFIX}/resources/vehicles", headers=bearer(admin["access_token"]))
        check("List vehicles", "GET", "/resources/vehicles", 200, r)

        r = client.patch(
            f"{PREFIX}/resources/vehicles/{ids['vehicle_id']}/status",
            params={"status_value": "maintenance"},
            headers=bearer(crew["access_token"]),
        )
        check("Update vehicle status", "PATCH", "/resources/vehicles/{id}/status", 200, r)

        r = client.get(f"{PREFIX}/resources/equipment", headers=bearer(admin["access_token"]))
        check("List equipment", "GET", "/resources/equipment", 200, r)

        r = client.patch(
            f"{PREFIX}/resources/equipment/{ids['equipment_id']}/status",
            params={"status_value": "in_use"},
            headers=bearer(crew["access_token"]),
        )
        check("Update equipment status", "PATCH", "/resources/equipment/{id}/status", 200, r)

        r = client.get(f"{PREFIX}/resources/equipment")
        check("Resources without token rejected", "GET", "/resources/equipment", 401, r)

        # ---------------------------------------------------- AUTH SURFACE
        # Which endpoints answer with no Authorization header at all. Recorded
        # as observations: these are unguarded by design or by omission, and the
        # report says which is which.
        print("\n=== Auth surface (no Authorization header) ===")
        for label, method, url in [
            ("List complaints", "GET", f"{PREFIX}/complaints"),
            ("Get complaint by id", "GET", f"{PREFIX}/complaints/{complaint_id}"),
            ("Update complaint", "PATCH", f"{PREFIX}/complaints/{complaint_id}"),
            ("Complaint history", "GET", f"{PREFIX}/complaints/{complaint_id}/history"),
            ("Complaint duplicates", "GET", f"{PREFIX}/complaints/{complaint_id}/duplicates"),
            ("Upload photo", "POST", f"{PREFIX}/complaints/upload-photo"),
            ("List wards", "GET", f"{PREFIX}/wards"),
            ("Get task by id", "GET", f"{PREFIX}/tasks/{task_id}"),
        ]:
            if method == "GET":
                r = client.get(url)
            elif method == "PATCH":
                r = client.patch(url, json={"priority": "low"})
            else:
                r = client.post(url, files={"photo": ("x.png", b"\x89PNG\r\n\x1a\n", "image/png")})
            check(
                f"Anonymous: {label}",
                method,
                url.replace(PREFIX, ""),
                401,
                r,
                note=(
                    "reachable without a token"
                    if r.status_code != 401
                    else "correctly requires a token"
                ),
                kind="observation",
            )

        # ------------------------------------------------------- INFRA/DOCS
        print("\n=== Docs & error envelope ===")
        r = client.get("/openapi.json")
        check("OpenAPI schema served", "GET", "/openapi.json", 200, r)

        r = client.get("/docs")
        check("Swagger UI served", "GET", "/docs", 200, r)

        r = client.get(f"{PREFIX}/does-not-exist")
        check("Unknown path -> enveloped 404", "GET", "/{unknown}", 404, r)

        r = client.delete(f"{PREFIX}/wards")
        check("Wrong method -> 405", "DELETE", "/wards", 405, r)

    contract = [x for x in RESULTS if x["kind"] == "contract"]
    observations = [x for x in RESULTS if x["kind"] == "observation"]
    passed = sum(1 for x in contract if x["ok"])
    total = len(contract)
    print(f"\n{'=' * 70}\nCONTRACT: {passed}/{total} passed, {total - passed} failed")
    print(f"OBSERVATIONS: {len(observations)} recorded\n{'=' * 70}")
    for x in contract:
        if not x["ok"]:
            where = f"{x['method']} {x['path']}"
            print(f"FAILED: {x['name']} ({where}) expected {x['expected']} got {x['actual']}")
    for x in observations:
        if not x["ok"]:
            print(f"NOTE:   {x['name']} ({x['method']} {x['path']}) -> {x['actual']} — {x['note']}")

    out = Path(__file__).resolve().parent / "api_smoke_results.json"
    out.write_text(json.dumps(RESULTS, indent=2, default=str), encoding="utf-8")
    print(f"\nJSON results -> {out}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
