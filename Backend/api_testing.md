# SmartSweep API — Endpoint Inventory & Test Report

Every route currently registered on the v1 router, what it does, and how it behaved
when actually called.

For copy-paste requests against a running server, see [testing.md](testing.md).

| | |
|---|---|
| **Date run** | 2026-07-31 |
| **Branch** | `Nitin-Backend` |
| **Base URL** | `http://localhost:8000/api/v1` |
| **Runtime** | Python 3.14.3 · FastAPI 0.115.14 · Pydantic 2.13.4 · SQLAlchemy 2.0.51 |
| **Harness** | [scripts/api_smoke.py](scripts/api_smoke.py) |
| **Raw results** | [scripts/api_smoke_results.json](scripts/api_smoke_results.json) |

## Result summary

The first pass found **4 broken endpoints** — two returning HTTP 500, two
unreachable because a path parameter shadowed them. All four are now fixed and
re-verified; see [Defects found and fixed](#defects-found-and-fixed).

| | First pass | After fixes |
|---|---|---|
| Contract assertions run | 66 | **74** |
| Passed | 62 | **74** |
| **Failed** | **4** | **0** |
| Observations (behaviour recorded, not asserted) | 9 | 9 |
| Existing `pytest` suite | 48 passed | 48 passed |

The assertion count rose from 66 to 74 because the four repaired endpoints could
finally be tested properly — the fixes added response-shape assertions (audit
trail ordering, `Page` envelope, embedded-complaint serialization) plus two extra
`/wards/me` cases that were unreachable before.

## How to run the tests

```bash
cd Backend
uv run python scripts/api_smoke.py    # 74 assertions, exits 0 on success
uv run pytest -q                      # 48 unit + route tests
```

The harness points `DATABASE_URL` at a temp SQLite file before importing the app,
so it never touches `smartsweep.db`. It boots the app through `TestClient` (which
runs the `lifespan` hook, so `init_db` seeds the demo users), inserts one ward /
worker / vehicle / equipment row, then walks every endpoint. Exit code is 0 only
when all contract assertions pass.

`init_db` seeds **users only**. Wards, workers, vehicles and equipment have no
seed data and no create endpoint, so those lists return `[]` against a fresh
database — the harness inserts its own fixtures to exercise them meaningfully.

### Seeded demo accounts

| Email | Password | Role |
|---|---|---|
| `citizen@smartsweep.gov` | `citizen123` | citizen |
| `anita@smartsweep.gov` | `anita123` | citizen |
| `mohammed@smartsweep.gov` | `mohammed123` | citizen |
| `crew@smartsweep.gov` | `crew123` | crew |
| `admin@smartsweep.gov` | `admin123` | admin |

---

## Endpoint inventory

All rows below are the **post-fix** run. Rows marked **[was broken]** failed on
the first pass.

### Auth — [`app/api/v1/routes/auth.py`](app/api/v1/routes/auth.py)

| Method | Path | Auth | Case | Expected | Actual | |
|---|---|---|---|---|---|---|
| POST | `/auth/register` | public | new citizen | 201 | 201 | PASS |
| POST | `/auth/register` | public | duplicate email | 409 | 409 | PASS |
| POST | `/auth/register` | public | bad email / short password | 422 | 422 | PASS |
| POST | `/auth/login` | public | admin credentials | 200 | 200 | PASS |
| POST | `/auth/login` | public | crew credentials | 200 | 200 | PASS |
| POST | `/auth/login` | public | citizen credentials | 200 | 200 | PASS |
| POST | `/auth/login` | public | wrong password | 401 | 401 | PASS |
| POST | `/auth/refresh` | public | valid refresh token | 200 | 200 | PASS |
| POST | `/auth/refresh` | public | access token passed instead | 401 | 401 | PASS |
| GET | `/auth/me` | bearer | valid token | 200 | 200 | PASS |
| GET | `/auth/me` | bearer | no token | 401 | 401 | PASS |
| GET | `/auth/me` | bearer | malformed token | 401 | 401 | PASS |
| GET | `/auth/admin-only` | admin | as admin | 200 | 200 | PASS |
| GET | `/auth/admin-only` | admin | as citizen | 403 | 403 | PASS |
| GET | `/auth/crew-only` | crew+admin | as crew | 200 | 200 | PASS |
| GET | `/auth/crew-only` | crew+admin | as citizen | 403 | 403 | PASS |

Token type is enforced in both directions — `/auth/refresh` rejects an access
token and `get_current_user` rejects a refresh token. 401 vs 403 is kept
distinct, which the frontend needs in order to redirect to login on 401 but show
"not for your role" on 403.

### Wards — [`app/api/v1/routes/wards.py`](app/api/v1/routes/wards.py)

| Method | Path | Auth | Case | Expected | Actual | |
|---|---|---|---|---|---|---|
| GET | `/wards` | public | list all | 200 | 200 | PASS |
| GET | `/wards/{ward_id}` | public | existing ward | 200 | 200 | PASS |
| GET | `/wards/{ward_id}` | public | unknown id | 404 | 404 | PASS |
| GET | `/wards/me` | any role | user with a ward | 200 | 200 | PASS **[was broken]** |
| GET | `/wards/me` | any role | user with no ward | 404 | 404 | PASS *(new)* |
| GET | `/wards/me` | any role | no token | 401 | 401 | PASS *(new)* |

### Complaints — [`app/api/v1/routes/complaints.py`](app/api/v1/routes/complaints.py)

| Method | Path | Auth | Case | Expected | Actual | |
|---|---|---|---|---|---|---|
| POST | `/complaints` | bearer | valid submission | 201 | 201 | PASS |
| POST | `/complaints` | bearer | no token | 401 | 401 | PASS |
| POST | `/complaints` | bearer | missing `location` | 422 | 422 | PASS |
| GET | `/complaints` | public | default page | 200 | 200 | PASS |
| GET | `/complaints` | public | `status` + `ward_id` + paging | 200 | 200 | PASS |
| GET | `/complaints` | public | `search=garbage` | 200 | 200 | PASS |
| GET | `/complaints/{id}` | public | existing | 200 | 200 | PASS |
| GET | `/complaints/{id}` | public | unknown id | 404 | 404 | PASS |
| PATCH | `/complaints/{id}` | public | set priority + category | 200 | 200 | PASS |
| PATCH | `/complaints/{id}/status` | bearer | pending → in_progress | 200 | 200 | PASS |
| PATCH | `/complaints/{id}/status` | bearer | in_progress → pending (illegal) | 409 | 409 | PASS |
| PATCH | `/complaints/{id}/status` | bearer | in_progress → resolved | 200 | 200 | PASS |
| POST | `/complaints/{id}/cancel` | bearer | pending complaint | 200 | 200 | PASS |
| POST | `/complaints/{id}/cancel` | bearer | resolved complaint | 409 | 409 | PASS |
| GET | `/complaints/{id}/history` | public | audit trail | 200 | 200 | PASS **[was broken]** |
| — | — | — | records `new→pending→in_progress→resolved` | shape | ok | PASS *(new)* |
| — | — | — | rows carry id/from/to/changed_by/created_at | shape | ok | PASS *(new)* |
| GET | `/complaints/{id}/duplicates` | public | with a real near-match | 200 | 200 | PASS **[was broken]** |
| — | — | — | finds the near-identical report | 1 match | ok | PASS *(new)* |
| — | — | — | embeds serialized complaint, not ORM object | shape | ok | PASS *(new)* |
| GET | `/complaints/high-risk` | public | high-risk feed | 200 | 200 | PASS **[was broken]** |
| — | — | — | returns a `Page` envelope | shape | ok | PASS *(new)* |
| — | — | — | picks up biohazard / high-priority rows | 2 total | ok | PASS *(new)* |
| POST | `/complaints/upload-photo` | public | valid PNG | 200 | 200 | PASS |
| POST | `/complaints/upload-photo` | public | `application/octet-stream` | 415 | 415 | PASS |
| POST | `/complaints/upload-photo` | public | 6 MB file (cap 5 MB) | 413 | 413 | PASS |

The status state machine in `ComplaintService` is solid: `pending →
{in_progress, cancelled}`, `in_progress → {resolved, cancelled}`, and both
`resolved` and `cancelled` are terminal. Every illegal move returns 409 with
code `INVALID_STATE_TRANSITION`. Upload limits match `settings.upload_max_bytes`
(5 MB) and `settings.upload_allowed_mime_types`.

### Tasks — [`app/api/v1/routes/tasks.py`](app/api/v1/routes/tasks.py)

| Method | Path | Auth | Case | Expected | Actual | |
|---|---|---|---|---|---|---|
| POST | `/tasks` | admin | with workers + equipment + complaint | 201 | 201 | PASS |
| POST | `/tasks` | admin | as citizen | 403 | 403 | PASS |
| POST | `/tasks` | admin | no linked complaint | 201 | 201 | PASS |
| GET | `/tasks` | crew+admin | as admin | 200 | 200 | PASS |
| GET | `/tasks` | crew+admin | as crew | 200 | 200 | PASS |
| GET | `/tasks` | crew+admin | as citizen | 403 | 403 | PASS |
| GET | `/tasks/{id}` | *(none)* | existing | 200 | 200 | PASS |
| GET | `/tasks/{id}` | *(none)* | unknown id | 404 | 404 | PASS |
| PATCH | `/tasks/{id}` | admin+crew | set status in_progress | 200 | 200 | PASS |
| POST | `/tasks/{id}/complete` | crew+admin | complete | 200 | 200 | PASS |
| POST | `/tasks/{id}/cancel` | admin | assigned task | 200 | 200 | PASS |

Task creation correctly cascades: linking a task to a complaint drives that
complaint `pending → in_progress`, and completing the task drives it
`in_progress → resolved`. `worker_ids` and `equipment_ids` round-trip through the
join tables and come back on `TaskRead`.

One consequence worth knowing when writing tests: because `create_task` pushes
the linked complaint to `in_progress`, you cannot attach a task to a complaint
that is already `resolved` or `cancelled` — it returns 409. That is correct
behaviour, not a bug.

### Resources — [`app/api/v1/routes/resources.py`](app/api/v1/routes/resources.py)

| Method | Path | Auth | Case | Expected | Actual | |
|---|---|---|---|---|---|---|
| GET | `/resources/workers` | admin+crew | as admin | 200 | 200 | PASS |
| GET | `/resources/workers` | admin+crew | as citizen | 403 | 403 | PASS |
| PATCH | `/resources/workers/{id}/status` | admin+crew | `?status_value=off_duty` | 200 | 200 | PASS |
| PATCH | `/resources/workers/{id}/status` | admin+crew | invalid enum value | 422 | 422 | PASS |
| PATCH | `/resources/workers/{id}/status` | admin+crew | unknown worker | 404 | 404 | PASS |
| GET | `/resources/vehicles` | admin+crew | list | 200 | 200 | PASS |
| PATCH | `/resources/vehicles/{id}/status` | admin+crew | `?status_value=maintenance` | 200 | 200 | PASS |
| GET | `/resources/equipment` | admin+crew | list | 200 | 200 | PASS |
| GET | `/resources/equipment` | admin+crew | no token | 401 | 401 | PASS |
| PATCH | `/resources/equipment/{id}/status` | admin+crew | `?status_value=in_use` | 200 | 200 | PASS |

`status_value` on all three PATCH routes is a **query parameter**, not a body
field — it is declared as a bare enum, which FastAPI binds to the query string.
Callers must use `PATCH /resources/workers/1/status?status_value=off_duty`.

### Framework behaviour

| Method | Path | Case | Expected | Actual | |
|---|---|---|---|---|---|
| GET | `/openapi.json` | schema served | 200 | 200 | PASS |
| GET | `/docs` | Swagger UI | 200 | 200 | PASS |
| GET | `/api/v1/does-not-exist` | unknown path | 404 | 404 | PASS |
| DELETE | `/api/v1/wards` | wrong method | 405 | 405 | PASS |

Unknown paths and wrong methods come back in the shared error envelope
(`{"error": {"code", "message", "details", "request_id"}}`), not Starlette's raw
`{"detail": ...}` — `register_exception_handlers` is doing its job.

---

## Defects found and fixed

### 1. `GET /complaints/{id}/history` returned 500 on every call

```
AttributeError: 'ComplaintStatusHistory' object has no attribute 'model_dump'
  at app/api/v1/routes/complaints.py:101
```

The route called `.model_dump()` on rows returned by
`ComplaintRepository.get_history`, but that repository returns **SQLAlchemy ORM
objects**, not Pydantic models. A matching DTO already existed —
`ComplaintStatusHistoryRead` in [app/schemas/complaint.py:93](app/schemas/complaint.py#L93) —
and was simply unused. This failed 100% of the time, for any complaint.

**Fix** — declare the response model and validate through the DTO:

```python
@router.get("/{complaint_id}/history", response_model=list[ComplaintStatusHistoryRead])
def complaint_history(complaint_id: int, db: Session = Depends(get_db)) -> list[ComplaintStatusHistoryRead]:
    ComplaintService.get_complaint(db, complaint_id)
    return [
        ComplaintStatusHistoryRead.model_validate(history)
        for history in ComplaintRepository.get_history(db, complaint_id)
    ]
```

**Verified** — a complaint taken through the full lifecycle now returns its three
transitions in order, oldest first:

```json
[
  {"id":1,"complaint_id":1,"from_status":"new","to_status":"pending","changed_by_user_id":1,"notes":"Complaint created","created_at":"..."},
  {"id":2,"complaint_id":1,"from_status":"pending","to_status":"in_progress","changed_by_user_id":5,"notes":"Status changed","created_at":"..."},
  {"id":3,"complaint_id":1,"from_status":"in_progress","to_status":"resolved","changed_by_user_id":4,"notes":"Status changed","created_at":"..."}
]
```

### 2. `GET /complaints/{id}/duplicates` returned 500 whenever a duplicate was found

```
pydantic_core.PydanticSerializationError:
  Unable to serialize unknown type: <class 'app.models.complaint.Complaint'>
```

`DuplicateDetectionService.find_possible_duplicates` builds match dicts with a
raw `Complaint` ORM object under the `"complaint"` key
([duplicate_detection_service.py:71](app/services/duplicate_detection_service.py#L71)),
which FastAPI cannot serialize.

This one was **data-dependent and easy to miss**: with no duplicates the list was
empty and the endpoint returned `200 []`. It only broke on the path that matters —
when the feature actually had something to report. The harness catches it by
deliberately filing two near-identical complaints at the same coordinates.

**Fix** — convert the embedded row at the route boundary, leaving the service
free of HTTP concerns:

```python
matches = DuplicateDetectionService.find_possible_duplicates(db, complaint)
return [
    {**match, "complaint": _to_read_model(match["complaint"]).model_dump(mode="json")}
    for match in matches
]
```

**Verified** — the match now serializes, scores intact:

```json
[{"complaint":{"id":2,"status":"pending","...":"..."},"distance":15.32,"locationScore":1.0,"descScore":0.3,"confidence":0.86}]
```

### 3 & 4. `GET /wards/me` and `GET /complaints/high-risk` were unreachable

Both returned **422**, not the data they were written to serve:

```
GET /wards/me             -> 422  field "ward_id":      "unable to parse string as an integer"
GET /complaints/high-risk -> 422  field "complaint_id": "unable to parse string as an integer"
```

Starlette matches routes **in registration order**, first match wins, and both
literal paths were declared *below* their parameterised siblings:

```
GET /api/v1/wards/{ward_id}           <- registered first, swallowed "me"
GET /api/v1/wards/me                  <- never reached
GET /api/v1/complaints/{complaint_id} <- registered first, swallowed "high-risk"
GET /api/v1/complaints/high-risk      <- never reached
```

So `/wards/me` was matched as `/wards/{ward_id}` with `ward_id="me"`, which fails
int coercion → 422. Same for `high-risk`.

**Fix** — moved the literal-path handlers above the parameterised ones in
[wards.py](app/api/v1/routes/wards.py) and
[complaints.py](app/api/v1/routes/complaints.py), each with a comment recording
why the order matters so it does not regress. `/upload-photo` was moved up at the
same time; it did not collide (the only other POST under `/complaints` with an
extra segment is `/{complaint_id}/cancel`, which has two), but keeping all
literal paths together makes the constraint visible.

**Verified** — `/complaints/high-risk` now returns the `Page` envelope, and
`/wards/me` resolves against the caller's ward:

```json
{"items":[{"id":2,"...":"..."},{"id":1,"...":"..."}],"meta":{"page":1,"page_size":5,"total":2,"total_pages":1}}
```

`/wards/me` returns 404 for the five seeded demo users because they all have
`ward_id: null` — that is correct behaviour, and the harness now asserts both the
200 (user with a ward) and 404 (user without) paths.

---

## Observations — still open

Behaviour that is not a crash but is worth a decision. **None of these were
changed**, since they are design calls rather than defects.

### Endpoints reachable with no `Authorization` header

Probed each one with the header omitted entirely:

| Endpoint | Anonymous result | Reasonable? |
|---|---|---|
| `GET /wards` | 200 | Yes — public reference data |
| `GET /complaints` | 200 | Probably — but exposes every reporter's address and coordinates |
| `GET /complaints/{id}` | 200 | Same as above |
| `GET /complaints/{id}/history` | 200 | Same as above |
| `GET /complaints/{id}/duplicates` | 200 | Same as above |
| `GET /tasks/{id}` | 200 | **No** — `GET /tasks` requires crew/admin, so a citizen is blocked from the list but can read any single task by walking ids |
| `PATCH /complaints/{id}` | 200 | **No** — anyone can rewrite the title, description, ward, priority and status of any complaint |
| `POST /complaints/upload-photo` | 200 | **No** — unauthenticated upload endpoint |

The two that stand out as unintentional are `PATCH /complaints/{id}` and
`GET /tasks/{id}`. Every sibling route in those files declares an auth
dependency; these two do not, which reads like an omission rather than a
decision. `PATCH /complaints/{id}` is the more serious — it is an anonymous write
that can also drive the status state machine, since
`ComplaintService.update_complaint` forwards a `status` field into
`change_status`.

Suggested minimum: add `Depends(get_current_user)` to `GET /tasks/{id}` and
`POST /complaints/upload-photo`, and `require_role(UserRole.ADMIN, UserRole.CREW)`
to `PATCH /complaints/{id}`.

### `POST /tasks/{id}/cancel` has no state guard

Cancelling an already-`completed` task returns 200 and flips it to `cancelled`.
`TaskService.cancel_task`
([task_service.py:80-83](app/services/task_service.py#L80-L83)) writes the status
unconditionally, with none of the transition checking `ComplaintService` does.
Not a crash, but inconsistent with the complaint lifecycle, and it lets a
finished job be silently un-finished. Worth a guard that rejects cancelling from
`completed` or `cancelled`.

### JWT secret is still the placeholder

Every run logs `InsecureKeyLengthWarning: The HMAC key is 9 bytes long`. The
default `jwt_secret_key` is `"change-me"`. The production guard in
[config.py:117-129](app/core/config.py#L117-L129) blocks this when `ENV=prod`, so
deployment is protected — but nothing in dev or test sets a real key.

### No create endpoint for wards or resources

Wards, workers, vehicles and equipment can only be created by writing to the
database directly. `init_db` seeds users only. Any UI that needs to manage them,
or any test that needs fixtures, has to bypass the API — see the seed snippet in
[testing.md](testing.md#seed-reference-data).

---

## Performance

Measured in-process via `TestClient`, so these exclude network and ASGI server
overhead. 75 timed calls against SQLite:

| | Latency |
|---|---|
| Median | 2.7 ms |
| p95 | 221.5 ms |
| Max | 243.2 ms |

The p95 and max are entirely `bcrypt`. The five slowest calls are all
`/auth/register` and `/auth/login` (221–243 ms); the sixth-slowest drops to
38 ms. That is password hashing doing its job — it is *supposed* to be slow — and
is not a defect.

Excluding auth, every endpoint responds in single-digit to low-double-digit
milliseconds, including the paginated complaint list and the duplicate-detection
scan (which loads up to 500 candidate rows per call). No N+1 problems surfaced at
this data volume, though the duplicate scan is a full table walk in Python and
will need an index or a bounding-box pre-filter once complaint counts grow.

---

## Verification log

Post-fix, both suites clean:

```
$ uv run python scripts/api_smoke.py
CONTRACT: 74/74 passed, 0 failed
OBSERVATIONS: 9 recorded
$ echo $?
0

$ uv run pytest -q
48 passed in 4.88s
```

The four repaired endpoints were additionally driven by hand against a live
`uvicorn` server on a scratch database, confirming they work over real HTTP and
not only through `TestClient`. Those transcripts are the response bodies quoted
in [testing.md](testing.md).
