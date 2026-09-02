# SmartSweep API — Testing Guide

Copy-paste requests for every endpoint, with the real responses they return.
Every command below was run against a live server and the output pasted verbatim.

For the audit that produced this, see [api_testing.md](api_testing.md).

- [Start the server](#start-the-server)
- [Read this first: three gotchas](#read-this-first-three-gotchas)
- [Get a token](#get-a-token)
- [Seed reference data](#seed-reference-data)
- [Auth](#auth) · [Wards](#wards) · [Complaints](#complaints) · [Tasks](#tasks) · [Resources](#resources)
- [Error cases](#error-cases)
- [One-shot scripts](#one-shot-scripts)
- [Automated suite](#automated-suite)

---

## Start the server

```bash
cd Backend
uv run uvicorn app.main:app --reload --port 8000
```

Swagger UI is at <http://localhost:8000/docs> — you can drive everything below
from there instead, using **Authorize** to paste an access token.

All examples use:

```bash
B=http://localhost:8000/api/v1
```

```powershell
$B = "http://localhost:8000/api/v1"
```

---

## Read this first: three gotchas

**1. In PowerShell, `curl` is not curl.** It is an alias for `Invoke-WebRequest`,
which takes completely different arguments. Either call the real binary as
`curl.exe`, or use the `Invoke-RestMethod` form given alongside each example.
Every bash example here runs as-is in Git Bash or WSL.

**2. `status_value` is a query parameter on resource routes but a body field on
the complaint route.** They look symmetrical and are not:

```bash
# Complaint status -> JSON body
curl -X PATCH "$B/complaints/1/status" -H "Content-Type: application/json" -d '{"status_value":"in_progress"}'

# Resource status -> query string
curl -X PATCH "$B/resources/workers/1/status?status_value=off_duty"
```

The resource routes declare a bare enum argument, which FastAPI binds to the
query string. Sending it in the body returns 422.

**3. Wards, workers, vehicles and equipment have no create endpoint.** `init_db`
seeds users only. Those four tables start empty and must be populated directly —
see [Seed reference data](#seed-reference-data). Until you do, `/wards` and the
`/resources/*` lists correctly return `[]`.

---

## Get a token

### Seeded accounts

| Email | Password | Role |
|---|---|---|
| `citizen@smartsweep.gov` | `citizen123` | citizen |
| `anita@smartsweep.gov` | `anita123` | citizen |
| `mohammed@smartsweep.gov` | `mohammed123` | citizen |
| `crew@smartsweep.gov` | `crew123` | crew |
| `admin@smartsweep.gov` | `admin123` | admin |

### bash

```bash
B=http://localhost:8000/api/v1

login() {
  curl -s -X POST "$B/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$1\",\"password\":\"$2\"}" \
  | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])"
}

CITIZEN=$(login citizen@smartsweep.gov citizen123)
CREW=$(login crew@smartsweep.gov crew123)
ADMIN=$(login admin@smartsweep.gov admin123)
```

### PowerShell

```powershell
$B = "http://localhost:8000/api/v1"

function Get-Token($email, $password) {
  $body = @{ email = $email; password = $password } | ConvertTo-Json
  (Invoke-RestMethod -Uri "$B/auth/login" -Method Post -ContentType "application/json" -Body $body).access_token
}

$CITIZEN = Get-Token "citizen@smartsweep.gov" "citizen123"
$CREW    = Get-Token "crew@smartsweep.gov"    "crew123"
$ADMIN   = Get-Token "admin@smartsweep.gov"   "admin123"

$Hc = @{ Authorization = "Bearer $CITIZEN" }
$Hw = @{ Authorization = "Bearer $CREW" }
$Ha = @{ Authorization = "Bearer $ADMIN" }
```

Access tokens expire after 30 minutes. Re-run `login` or use
[`/auth/refresh`](#post-authrefresh).

---

## Seed reference data

Run once, with the server stopped or running (SQLite tolerates both):

```bash
cd Backend
uv run python -c "
from app.db.session import SessionLocal
from app.models.ward import Ward
from app.models.worker import Worker
from app.models.vehicle import Vehicle
from app.models.equipment import Equipment

db = SessionLocal()
ward = Ward(name='Ward 12 - Kothrud', code='W12', zone='West')
db.add(ward); db.flush()
db.add_all([
    Worker(full_name='Ramesh Kadam', employee_code='EMP-001', role_title='Sweeper', ward_id=ward.id),
    Vehicle(plate_number='MH12-AB-1234', model_name='Tata Ace Compactor', vehicle_type='compactor', ward_id=ward.id),
    Equipment(name='Industrial Broom', asset_tag='EQ-001', total_quantity=10, available_quantity=10, ward_id=ward.id),
])
db.commit()
print('seeded ward', ward.id)
db.close()
"
```

```
seeded ward 1
```

Re-running it fails on the unique constraints for `name` / `plate_number` /
`asset_tag` — change the values or delete `smartsweep.db` first.

---

## Auth

### POST /auth/register

```bash
curl -s -X POST "$B/auth/register" -H "Content-Type: application/json" -d '{
  "email": "priya@example.com",
  "full_name": "Priya Sharma",
  "password": "priya123",
  "phone": "9876543210",
  "ward_id": 1
}'
```

**201**
```json
{"email":"priya@example.com","full_name":"Priya Sharma","role":"citizen","phone":"9876543210","ward_id":1,"id":6,"is_active":true,"created_at":"...","updated_at":"..."}
```

`role` defaults to `citizen`. Password minimum is 6 characters. Registering the
same email twice returns **409** `CONFLICT`.

```powershell
$body = @{ email="priya@example.com"; full_name="Priya Sharma"; password="priya123"; phone="9876543210"; ward_id=1 } | ConvertTo-Json
Invoke-RestMethod -Uri "$B/auth/register" -Method Post -ContentType "application/json" -Body $body
```

### POST /auth/login

```bash
curl -s -X POST "$B/auth/login" -H "Content-Type: application/json" \
  -d '{"email":"admin@smartsweep.gov","password":"admin123"}'
```

**200**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1Iiwicm9sZSI6ImFkbWluIiwidHlwZSI6ImFjY2VzcyIsImlhdCI6MTc4NTQ4MzU1NCwiZXhwIjoxNzg1NDg1MzU0fQ...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

Login takes ~220 ms. That is bcrypt, and it is intentional.

### POST /auth/refresh

```bash
REFRESH=$(curl -s -X POST "$B/auth/login" -H "Content-Type: application/json" \
  -d '{"email":"admin@smartsweep.gov","password":"admin123"}' \
  | python -c "import sys,json;print(json.load(sys.stdin)['refresh_token'])")

curl -s -X POST "$B/auth/refresh" -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$REFRESH\"}"
```

**200** — a fresh token pair. Passing an *access* token here returns **401**
`Invalid token type. Refresh token required.` The check works both ways: passing
a refresh token to a protected route also gives 401.

### GET /auth/me

```bash
curl -s "$B/auth/me" -H "Authorization: Bearer $CITIZEN"
```

**200**
```json
{"email":"citizen@smartsweep.gov","full_name":"Sagnik Halder","role":"citizen","phone":null,"ward_id":null,"id":1,"is_active":true,"created_at":"2026-07-31T07:38:59","updated_at":"2026-07-31T07:38:59"}
```

### GET /auth/admin-only · GET /auth/crew-only

Role-check probes. Useful for confirming RBAC wiring from the frontend.

```bash
curl -s "$B/auth/admin-only" -H "Authorization: Bearer $ADMIN"     # 200
curl -s "$B/auth/admin-only" -H "Authorization: Bearer $CITIZEN"   # 403
curl -s "$B/auth/crew-only"  -H "Authorization: Bearer $CREW"      # 200
curl -s "$B/auth/crew-only"  -H "Authorization: Bearer $CITIZEN"   # 403
```

**200**
```json
{"message":"Admin access granted."}
```

**403**
```json
{"error":{"code":"PERMISSION_DENIED","message":"Role 'citizen' does not have permission to access this resource.","details":[],"request_id":"-"}}
```

---

## Wards

### GET /wards

```bash
curl -s "$B/wards"
```

**200**
```json
[{"name":"Ward 12 - Kothrud","code":"W12","zone":"West","description":null,"is_active":true,"id":1,"created_at":"2026-07-31T07:41:50","updated_at":"2026-07-31T07:41:50"}]
```

### GET /wards/{ward_id}

```bash
curl -s "$B/wards/1"        # 200
curl -s "$B/wards/999999"   # 404 NOT_FOUND
```

### GET /wards/me

Returns the ward attached to the calling user. Requires a token.

```bash
curl -s "$B/wards/me" -H "Authorization: Bearer $CITIZEN"
```

The five seeded demo users have `ward_id: null`, so this returns **404**:

```json
{"error":{"code":"NOT_FOUND","message":"Ward not found.","details":[],"request_id":"-"}}
```

To get a **200**, register a user with `ward_id` set (see
[POST /auth/register](#post-authregister)) and log in as them.

> This endpoint used to return **422** regardless of the token — it was shadowed
> by `/wards/{ward_id}` and never reached. Fixed by moving `/me` above the
> parameterised route.

---

## Complaints

### POST /complaints

The payload is the citizen report form shape, not the DB shape: `location`
becomes both `title` and `address`, `hazard` becomes `category`, and `coords`
splits into `latitude` / `longitude`.

```bash
curl -s -X POST "$B/complaints" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CITIZEN" \
  -d '{
    "location": "MG Road near bus stop",
    "description": "Overflowing garbage bin attracting stray dogs.",
    "hazard": "biohazard",
    "coords": {"lat": 18.5204, "lng": 73.8567}
  }'
```

**201**
```json
{"title":"MG Road near bus stop","description":"Overflowing garbage bin attracting stray dogs.","ward_id":null,"category":"biohazard","priority":null,"address":"MG Road near bus stop","latitude":18.5204,"longitude":73.8567,"photo_url":null,"id":1,"reported_by_user_id":1,"status":"pending","resolved_at":null,"cancelled_at":null,"created_at":"2026-07-31T07:39:15","updated_at":"2026-07-31T07:39:15"}
```

Only `location` and `description` are required. `ward_id` falls back to the
caller's ward when omitted. Requires a token — **401** without one.

```powershell
$body = @{
  location    = "MG Road near bus stop"
  description = "Overflowing garbage bin attracting stray dogs."
  hazard      = "biohazard"
  coords      = @{ lat = 18.5204; lng = 73.8567 }
} | ConvertTo-Json
Invoke-RestMethod -Uri "$B/complaints" -Method Post -ContentType "application/json" -Headers $Hc -Body $body
```

### GET /complaints

Paginated, with optional `search`, `status`, `ward_id`.

```bash
curl -s "$B/complaints"
curl -s "$B/complaints?status=pending&ward_id=1&page=1&page_size=5"
curl -s "$B/complaints?search=garbage"
```

**200** — the shared `Page` envelope:
```json
{
  "items": [ { "id": 1, "title": "MG Road near bus stop", "status": "pending", "...": "..." } ],
  "meta": { "page": 1, "page_size": 20, "total": 2, "total_pages": 1 }
}
```

`search` matches title, description and address (case-insensitive).
`total` is the count before pagination. `total: 0` gives `total_pages: 0`, not 1.

### GET /complaints/{id}

```bash
curl -s "$B/complaints/1"        # 200
curl -s "$B/complaints/999999"   # 404
```

### PATCH /complaints/{id}

```bash
curl -s -X PATCH "$B/complaints/1" -H "Content-Type: application/json" \
  -d '{"priority":"high","category":"biohazard"}'
```

**200** — the updated complaint. Any subset of fields is accepted. Passing
`status` here routes through the same state machine as the endpoint below, so it
can return **409**.

### PATCH /complaints/{id}/status

`status_value` goes in the **body**, embedded:

```bash
curl -s -X PATCH "$B/complaints/1/status" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CREW" \
  -d '{"status_value":"in_progress"}'
```

Legal transitions:

```
pending ──► in_progress ──► resolved
   │              │
   └──► cancelled ◄┘

resolved  = terminal
cancelled = terminal
```

Anything else returns **409**:

```bash
curl -s -X PATCH "$B/complaints/1/status" -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CREW" -d '{"status_value":"pending"}'
```

```json
{"error":{"code":"INVALID_STATE_TRANSITION","message":"Cannot move complaint from 'in_progress' to 'pending'.","details":[],"request_id":"-"}}
```

Setting the status it already has is a no-op **200**, not an error.

### POST /complaints/{id}/cancel

```bash
curl -s -X POST "$B/complaints/2/cancel" -H "Authorization: Bearer $CITIZEN"
```

**200** with `status: "cancelled"` and `cancelled_at` set. Only `pending`
complaints can be cancelled — anything else returns **409** `Only pending
complaints can be cancelled.`

### GET /complaints/{id}/history

```bash
curl -s "$B/complaints/1/history"
```

**200** — full audit trail, oldest first:
```json
[
  {"id":1,"complaint_id":1,"from_status":"new","to_status":"pending","changed_by_user_id":1,"notes":"Complaint created","created_at":"2026-07-31T07:39:15.495618"},
  {"id":3,"complaint_id":1,"from_status":"pending","to_status":"in_progress","changed_by_user_id":4,"notes":"Status changed","created_at":"2026-07-31T07:40:38.762166"}
]
```

Creation is recorded as `new -> pending`, so a brand-new complaint has exactly
one row. **404** if the complaint does not exist.

> This endpoint used to return **500** on every call — it called `.model_dump()`
> on SQLAlchemy rows. Fixed by serializing through `ComplaintStatusHistoryRead`.

### GET /complaints/{id}/duplicates

Finds other `pending` / `in_progress` complaints that look like the same report.
To see it fire, file two similar complaints at nearby coordinates:

```bash
curl -s -X POST "$B/complaints" -H "Content-Type: application/json" -H "Authorization: Bearer $CITIZEN" -d '{
  "location":"MG Road near bus stop",
  "description":"Garbage bin overflowing near the MG Road bus stop.",
  "hazard":"biohazard",
  "coords":{"lat":18.5205,"lng":73.8568}
}'

curl -s "$B/complaints/1/duplicates"
```

**200**
```json
[
  {
    "complaint": {
      "title": "MG Road near bus stop",
      "description": "Garbage bin overflowing near the MG Road bus stop.",
      "id": 2,
      "status": "pending",
      "latitude": 18.5205,
      "longitude": 73.8568,
      "...": "..."
    },
    "distance": 15.323543863800971,
    "locationScore": 1.0,
    "descScore": 0.3,
    "confidence": 0.8600000000000001
  }
]
```

`distance` is metres (`null` when either complaint lacks coordinates). Scores are
Jaccard token overlap. A match is reported when within 200 m, **or** location
similarity ≥ 0.6, **or** both scores ≥ 0.35 — see `duplicate_*` in
[app/core/config.py](app/core/config.py#L73-L80). Returns `[]` when nothing
matches.

> This endpoint used to return **500** whenever a match existed (it embedded a
> raw ORM object) while returning `200 []` when none did — so it looked healthy
> right up until the feature had something to say. Fixed by serializing the
> embedded complaint.

### GET /complaints/high-risk

```bash
curl -s "$B/complaints/high-risk?page=1&page_size=5"
```

**200**
```json
{"items":[{"id":2,"...":"..."},{"id":1,"...":"..."}],"meta":{"page":1,"page_size":5,"total":2,"total_pages":1}}
```

Selects complaints whose `category` is one of `biohazard`, `risk to children`,
`medical waste`, `mosquito breeding`, **or** whose `priority` is `high`,
`urgent`, `critical`. Filtering happens in Python over the newest 500 rows.

> This endpoint used to return **422** — shadowed by `/complaints/{complaint_id}`.
> Fixed by moving it above the parameterised route.

### POST /complaints/upload-photo

Validates the upload and echoes its metadata. It does **not** persist the file.

```bash
curl -s -X POST "$B/complaints/upload-photo" -F "photo=@sample.png;type=image/png"
```

**200**
```json
{"filename":"sample.png","content_type":"image/png","size_bytes":408}
```

Allowed: `image/jpeg`, `image/png`, `image/webp`. Max 5 MB.

```bash
curl -s -X POST "$B/complaints/upload-photo" -F "photo=@notes.txt;type=text/plain"
```

**415**
```json
{"error":{"code":"UNSUPPORTED_MEDIA_TYPE","message":"Unsupported image type.","details":[],"request_id":"-"}}
```

A file over 5 MB returns **413** `Image too large.`

```powershell
curl.exe -s -X POST "$B/complaints/upload-photo" -F "photo=@sample.png;type=image/png"
```

`Invoke-RestMethod` needs `-Form @{ photo = Get-Item .\sample.png }`, which only
exists in PowerShell 7+. On 5.1, use `curl.exe`.

---

## Tasks

### POST /tasks

Admin only.

```bash
curl -s -X POST "$B/tasks" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN" \
  -d '{
    "title": "Clear overflowing bin on MG Road",
    "description": "Dispatch compactor and two sweepers.",
    "complaint_id": 2,
    "ward_id": 1,
    "vehicle_id": 1,
    "worker_ids": [1],
    "equipment_ids": [1]
  }'
```

**201**
```json
{"title":"Clear overflowing bin on MG Road","description":"Dispatch compactor and two sweepers.","complaint_id":2,"ward_id":1,"vehicle_id":1,"status":"assigned","id":1,"assigned_by_user_id":5,"resolution_notes":null,"assigned_at":"2026-07-31T07:43:20.520370","started_at":null,"completed_at":null,"worker_ids":[1],"equipment_ids":[1],"created_at":"2026-07-31T07:43:20","updated_at":"2026-07-31T07:43:20"}
```

**Creating a task drives its linked complaint `pending → in_progress`.** So the
`complaint_id` you pass must reference a complaint that is still `pending` (or
already `in_progress`). Point it at a `resolved` or `cancelled` complaint and you
get **409** `Cannot move complaint from 'resolved' to 'in_progress'` — the task
route reporting a complaint-side conflict. Omit `complaint_id` for a standalone task.

Non-admin callers get **403**.

### GET /tasks

Crew or admin.

```bash
curl -s "$B/tasks" -H "Authorization: Bearer $CREW"      # 200
curl -s "$B/tasks" -H "Authorization: Bearer $CITIZEN"   # 403
```

### GET /tasks/{id}

```bash
curl -s "$B/tasks/1"          # 200 — note: no token required
curl -s "$B/tasks/999999"     # 404
```

### PATCH /tasks/{id}

Admin or crew.

```bash
curl -s -X PATCH "$B/tasks/1" -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CREW" \
  -d '{"status":"in_progress","resolution_notes":"Crew dispatched 09:15"}'
```

Statuses: `assigned`, `in_progress`, `completed`, `cancelled`. Passing
`worker_ids` or `equipment_ids` **replaces** the assignment set; omit them to
leave it untouched.

### POST /tasks/{id}/complete

Crew or admin.

```bash
curl -s -X POST "$B/tasks/1/complete" -H "Authorization: Bearer $CREW"
```

**200** with `status: "completed"` and `completed_at` set. Also drives the linked
complaint `in_progress → resolved`. Completing an already-completed task is a
no-op 200.

### POST /tasks/{id}/cancel

Admin only.

```bash
curl -s -X POST "$B/tasks/1/cancel" -H "Authorization: Bearer $ADMIN"
```

**200** with `status: "cancelled"`. Note this has no state guard — it will
happily cancel an already-`completed` task and does not touch the linked
complaint.

---

## Resources

All six routes require admin **or** crew. Citizens get **403**, no token gets
**401**.

### Lists

```bash
curl -s "$B/resources/workers"   -H "Authorization: Bearer $ADMIN"
curl -s "$B/resources/vehicles"  -H "Authorization: Bearer $ADMIN"
curl -s "$B/resources/equipment" -H "Authorization: Bearer $ADMIN"
```

**200**
```json
[{"full_name":"Ramesh Kadam","employee_code":"EMP-001","email":null,"phone":null,"role_title":"Sweeper","ward_id":1,"status":"available","is_active":true,"id":1,"created_at":"2026-07-31T07:41:50","updated_at":"2026-07-31T07:41:50"}]
```

### Status updates — `status_value` is a query parameter

```bash
curl -s -X PATCH "$B/resources/workers/1/status?status_value=off_duty"      -H "Authorization: Bearer $ADMIN"
curl -s -X PATCH "$B/resources/vehicles/1/status?status_value=maintenance"  -H "Authorization: Bearer $CREW"
curl -s -X PATCH "$B/resources/equipment/1/status?status_value=in_use"      -H "Authorization: Bearer $CREW"
```

**200**
```json
{"full_name":"Ramesh Kadam","employee_code":"EMP-001","email":null,"phone":null,"role_title":"Sweeper","ward_id":1,"status":"off_duty","is_active":true,"id":1,"created_at":"2026-07-31T07:41:50","updated_at":"2026-07-31T07:43:20"}
```

Valid values:

| Resource | Statuses |
|---|---|
| worker | `available`, `assigned`, `off_duty`, `unavailable` |
| vehicle | `available`, `en_route`, `on_site`, `maintenance` |
| equipment | `available`, `in_use`, `maintenance`, `retired` |

Anything else returns **422**; an unknown id returns **404**.

```powershell
Invoke-RestMethod -Uri "$B/resources/workers/1/status?status_value=off_duty" -Method Patch -Headers $Ha
```

---

## Error cases

Every non-2xx uses the same envelope, so the frontend needs one error branch:

```json
{"error": {"code": "NOT_FOUND", "message": "Complaint not found.", "details": [], "request_id": "-"}}
```

`details` is populated only on 422, one entry per bad field.

| Test | Command | Expect |
|---|---|---|
| No token | `curl -s "$B/auth/me"` | 401 `UNAUTHENTICATED` |
| Garbage token | `curl -s "$B/auth/me" -H "Authorization: Bearer abc.def.ghi"` | 401 `UNAUTHENTICATED` |
| Refresh token on protected route | `curl -s "$B/auth/me" -H "Authorization: Bearer $REFRESH"` | 401 `Invalid token type` |
| Wrong role | `curl -s "$B/tasks" -H "Authorization: Bearer $CITIZEN"` | 403 `PERMISSION_DENIED` |
| Missing row | `curl -s "$B/complaints/999999"` | 404 `NOT_FOUND` |
| Unknown path | `curl -s "$B/nope"` | 404 `NOT_FOUND` |
| Wrong method | `curl -s -X DELETE "$B/wards"` | 405 `METHOD_NOT_ALLOWED` |
| Duplicate email | register the same email twice | 409 `CONFLICT` |
| Illegal transition | `resolved` → `in_progress` | 409 `INVALID_STATE_TRANSITION` |
| Oversized upload | 6 MB image | 413 `PAYLOAD_TOO_LARGE` |
| Bad MIME | `.txt` upload | 415 `UNSUPPORTED_MEDIA_TYPE` |
| Bad field | `curl -s -X POST "$B/auth/register" -H "Content-Type: application/json" -d '{"email":"nope","full_name":"X","password":"123"}'` | 422 `VALIDATION_ERROR` |

Sample 422 with `details`:

```json
{"error":{"code":"VALIDATION_ERROR","message":"One or more fields failed validation.","details":[{"field":"email","issue":"value is not a valid email address: An email address must have an @-sign."},{"field":"password","issue":"String should have at least 6 characters"}],"request_id":"-"}}
```

In PowerShell, `Invoke-RestMethod` throws on 4xx — read the body from the
exception:

```powershell
try { Invoke-RestMethod -Uri "$B/complaints/999999" } catch { $_.ErrorDetails.Message }
```

```
{"error":{"code":"NOT_FOUND","message":"Complaint not found.","details":[],"request_id":"-"}}
```

---

## One-shot scripts

Full happy path in one go. Assumes the server is running and reference data is
seeded.

### bash

```bash
#!/usr/bin/env bash
set -euo pipefail
B=http://localhost:8000/api/v1
jqv() { python -c "import sys,json;print(json.load(sys.stdin)$1)"; }

tok() {
  curl -s -X POST "$B/auth/login" -H "Content-Type: application/json" \
    -d "{\"email\":\"$1\",\"password\":\"$2\"}" | jqv "['access_token']"
}
CITIZEN=$(tok citizen@smartsweep.gov citizen123)
CREW=$(tok crew@smartsweep.gov crew123)
ADMIN=$(tok admin@smartsweep.gov admin123)
echo "tokens acquired"

CID=$(curl -s -X POST "$B/complaints" -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CITIZEN" \
  -d '{"location":"MG Road near bus stop","description":"Overflowing garbage bin.","hazard":"biohazard","coords":{"lat":18.5204,"lng":73.8567}}' \
  | jqv "['id']")
echo "complaint $CID created"

TID=$(curl -s -X POST "$B/tasks" -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN" \
  -d "{\"title\":\"Clear bin\",\"complaint_id\":$CID,\"ward_id\":1,\"vehicle_id\":1,\"worker_ids\":[1],\"equipment_ids\":[1]}" \
  | jqv "['id']")
echo "task $TID created; complaint now $(curl -s "$B/complaints/$CID" | jqv "['status']")"

curl -s -X POST "$B/tasks/$TID/complete" -H "Authorization: Bearer $CREW" > /dev/null
echo "task completed; complaint now $(curl -s "$B/complaints/$CID" | jqv "['status']")"

echo "history:"; curl -s "$B/complaints/$CID/history" | python -m json.tool
echo "high-risk total: $(curl -s "$B/complaints/high-risk" | jqv "['meta']['total']")"
```

Expected tail:

```
tokens acquired
complaint 1 created
task 1 created; complaint now in_progress
task completed; complaint now resolved
history:
[ ... new->pending, pending->in_progress, in_progress->resolved ... ]
high-risk total: 1
```

### PowerShell

```powershell
$ErrorActionPreference = "Stop"
$B = "http://localhost:8000/api/v1"

function Get-Token($email, $password) {
  $body = @{ email = $email; password = $password } | ConvertTo-Json
  (Invoke-RestMethod -Uri "$B/auth/login" -Method Post -ContentType "application/json" -Body $body).access_token
}
$Hc = @{ Authorization = "Bearer $(Get-Token 'citizen@smartsweep.gov' 'citizen123')" }
$Hw = @{ Authorization = "Bearer $(Get-Token 'crew@smartsweep.gov'    'crew123')" }
$Ha = @{ Authorization = "Bearer $(Get-Token 'admin@smartsweep.gov'   'admin123')" }
Write-Output "tokens acquired"

$cbody = @{
  location = "MG Road near bus stop"; description = "Overflowing garbage bin."
  hazard = "biohazard"; coords = @{ lat = 18.5204; lng = 73.8567 }
} | ConvertTo-Json
$c = Invoke-RestMethod -Uri "$B/complaints" -Method Post -ContentType "application/json" -Headers $Hc -Body $cbody
Write-Output "complaint $($c.id) created"

$tbody = @{
  title = "Clear bin"; complaint_id = $c.id; ward_id = 1; vehicle_id = 1
  worker_ids = @(1); equipment_ids = @(1)
} | ConvertTo-Json
$t = Invoke-RestMethod -Uri "$B/tasks" -Method Post -ContentType "application/json" -Headers $Ha -Body $tbody
Write-Output "task $($t.id) created; complaint now $((Invoke-RestMethod -Uri "$B/complaints/$($c.id)").status)"

Invoke-RestMethod -Uri "$B/tasks/$($t.id)/complete" -Method Post -Headers $Hw | Out-Null
Write-Output "task completed; complaint now $((Invoke-RestMethod -Uri "$B/complaints/$($c.id)").status)"

Invoke-RestMethod -Uri "$B/complaints/$($c.id)/history" | ConvertTo-Json -Depth 4
Write-Output "high-risk total: $((Invoke-RestMethod -Uri "$B/complaints/high-risk").meta.total)"
```

---

## Automated suite

Two commands cover everything above without a running server.

```bash
cd Backend

# 74 assertions across all 31 routes, throwaway DB, exits 0 on success
uv run python scripts/api_smoke.py

# unit + route tests
uv run pytest -q
```

Current state:

```
CONTRACT: 74/74 passed, 0 failed
OBSERVATIONS: 9 recorded
48 passed
```

`scripts/api_smoke.py` points `DATABASE_URL` at a temp file before importing the
app, so it never touches `smartsweep.db`. Per-call results land in
`scripts/api_smoke_results.json`. Add a case by calling `check(...)` with the
status you expect, or `check(..., kind="observation")` to record behaviour
without asserting it.
