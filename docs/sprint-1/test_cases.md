# Sprint 1 Test Cases

## Tasks & Resources

| Test ID | Endpoint | Test Type | Description / Inputs | Expected Outcome |
|---|---|---|---|---|
| TC-TSK-01 | `GET /api/v1/tasks` | Happy Path | Admin/Crew lists all tasks with valid Bearer token | HTTP 200 OK returning array of `TaskRead` items |
| TC-TSK-02 | `GET /api/v1/tasks` | Validation Failure | Request with malformed or invalid Authorization header | HTTP 401 Unauthorized with `UNAUTHENTICATED` error code |
| TC-TSK-03 | `GET /api/v1/tasks` | Auth / RBAC | Citizen role attempts to list tasks | HTTP 403 Forbidden with `PERMISSION_DENIED` error code |
| TC-TSK-04 | `GET /api/v1/tasks` | Edge Case | Admin lists tasks when database contains 0 tasks | HTTP 200 OK returning an empty list `[]` |
| TC-TSK-05 | `POST /api/v1/tasks` | Happy Path | Admin creates task with title, description, and available resources | HTTP 201 Created returning created `TaskRead` |
| TC-TSK-06 | `POST /api/v1/tasks` | Validation Failure | Create task payload missing mandatory `title` field | HTTP 422 Unprocessable Entity with `VALIDATION_ERROR` |
| TC-TSK-07 | `POST /api/v1/tasks` | Auth / RBAC | Crew role attempts to create a task (Admin-only) | HTTP 403 Forbidden with `PERMISSION_DENIED` |
| TC-TSK-08 | `POST /api/v1/tasks` | Edge Case | Admin assigns a worker/vehicle/equipment already marked as assigned | HTTP 409 Conflict with `CONFLICT` error code |
| TC-TSK-09 | `GET /api/v1/tasks/{id}` | Happy Path | Fetch existing task by numeric task ID | HTTP 200 OK returning target `TaskRead` |
| TC-TSK-10 | `GET /api/v1/tasks/{id}` | Validation Failure | Pass non-integer path parameter (e.g. `/tasks/abc`) | HTTP 422 Unprocessable Entity |
| TC-TSK-11 | `GET /api/v1/tasks/{id}` | Auth / RBAC | Request task details without Authorization header | HTTP 401 Unauthorized |
| TC-TSK-12 | `GET /api/v1/tasks/{id}` | Edge Case | Fetch non-existent task ID (e.g. `/tasks/999999`) | HTTP 404 Not Found with `NOT_FOUND` error code |
| TC-TSK-13 | `PATCH /api/v1/tasks/{id}` | Happy Path | Admin/Crew updates task title or description | HTTP 200 OK returning updated `TaskRead` |
| TC-TSK-14 | `PATCH /api/v1/tasks/{id}` | Validation Failure | Update task with invalid status string (e.g. `INVALID_VAL`) | HTTP 422 Unprocessable Entity |
| TC-TSK-15 | `PATCH /api/v1/tasks/{id}` | Auth / RBAC | Citizen role attempts to patch task details | HTTP 403 Forbidden |
| TC-TSK-16 | `PATCH /api/v1/tasks/{id}` | Edge Case | Update non-existent task ID | HTTP 404 Not Found |
| TC-TSK-17 | `POST /api/v1/tasks/{id}/complete` | Happy Path | Crew completes task; linked complaint becomes `resolved` and resources freed | HTTP 200 OK with status `completed` |
| TC-TSK-18 | `POST /api/v1/tasks/{id}/complete` | Validation Failure | Complete task with non-integer ID | HTTP 422 Unprocessable Entity |
| TC-TSK-19 | `POST /api/v1/tasks/{id}/complete` | Auth / RBAC | Citizen role attempts to complete task | HTTP 403 Forbidden |
| TC-TSK-20 | `POST /api/v1/tasks/{id}/complete` | Edge Case | Re-completing an already completed task | HTTP 200 OK idempotently returning current state |
| TC-TSK-21 | `POST /api/v1/tasks/{id}/cancel` | Happy Path | Admin cancels task; resources released to `available` | HTTP 200 OK with status `cancelled` |
| TC-TSK-22 | `POST /api/v1/tasks/{id}/cancel` | Validation Failure | Cancel task with invalid string task ID | HTTP 422 Unprocessable Entity |
| TC-TSK-23 | `POST /api/v1/tasks/{id}/cancel` | Auth / RBAC | Crew role attempts to cancel task (Admin-only) | HTTP 403 Forbidden |
| TC-TSK-24 | `POST /api/v1/tasks/{id}/cancel` | Edge Case | Cancel non-existent task ID | HTTP 404 Not Found |
| TC-RES-01 | `GET /api/v1/resources/workers` | Happy Path | Admin/Crew lists registered municipal workers | HTTP 200 OK returning list of `WorkerRead` |
| TC-RES-02 | `GET /api/v1/resources/workers` | Validation Failure | Request with invalid Authorization header format | HTTP 401 Unauthorized |
| TC-RES-03 | `GET /api/v1/resources/workers` | Auth / RBAC | Citizen role attempts to view worker directory | HTTP 403 Forbidden |
| TC-RES-04 | `GET /api/v1/resources/workers` | Edge Case | List workers when 0 workers are present in DB | HTTP 200 OK returning `[]` |
| TC-RES-05 | `PATCH /api/v1/resources/workers/{id}/status` | Happy Path | Crew updates worker status to `off_duty` via query parameter | HTTP 200 OK with updated status |
| TC-RES-06 | `PATCH /api/v1/resources/workers/{id}/status` | Validation Failure | Pass invalid status enum string to `status_value` | HTTP 422 Unprocessable Entity |
| TC-RES-07 | `PATCH /api/v1/resources/workers/{id}/status` | Auth / RBAC | Citizen role attempts to update worker status | HTTP 403 Forbidden |
| TC-RES-08 | `PATCH /api/v1/resources/workers/{id}/status` | Edge Case | Update status for non-existent worker ID | HTTP 404 Not Found |
| TC-RES-09 | `GET /api/v1/resources/vehicles` | Happy Path | Admin/Crew lists fleet vehicles | HTTP 200 OK returning list of `VehicleRead` |
| TC-RES-10 | `GET /api/v1/resources/vehicles` | Validation Failure | Request with invalid Authorization header | HTTP 401 Unauthorized |
| TC-RES-11 | `GET /api/v1/resources/vehicles` | Auth / RBAC | Citizen role attempts to list fleet vehicles | HTTP 403 Forbidden |
| TC-RES-12 | `GET /api/v1/resources/vehicles` | Edge Case | List vehicles when fleet is empty | HTTP 200 OK returning `[]` |
| TC-RES-13 | `PATCH /api/v1/resources/vehicles/{id}/status` | Happy Path | Update vehicle status to `maintenance` | HTTP 200 OK with updated status |
| TC-RES-14 | `PATCH /api/v1/resources/vehicles/{id}/status` | Validation Failure | Pass invalid vehicle status string | HTTP 422 Unprocessable Entity |
| TC-RES-15 | `PATCH /api/v1/resources/vehicles/{id}/status` | Auth / RBAC | Citizen role attempts to update vehicle status | HTTP 403 Forbidden |
| TC-RES-16 | `PATCH /api/v1/resources/vehicles/{id}/status` | Edge Case | Update status for non-existent vehicle ID | HTTP 404 Not Found |
| TC-RES-17 | `GET /api/v1/resources/equipment` | Happy Path | Admin/Crew lists equipment inventory | HTTP 200 OK returning list of `EquipmentRead` |
| TC-RES-18 | `GET /api/v1/resources/equipment` | Validation Failure | Request with invalid Authorization header | HTTP 401 Unauthorized |
| TC-RES-19 | `GET /api/v1/resources/equipment` | Auth / RBAC | Citizen role attempts to list equipment | HTTP 403 Forbidden |
| TC-RES-20 | `GET /api/v1/resources/equipment` | Edge Case | List equipment when inventory is empty | HTTP 200 OK returning `[]` |
| TC-RES-21 | `PATCH /api/v1/resources/equipment/{id}/status` | Happy Path | Update equipment status to `maintenance` | HTTP 200 OK with updated status |
| TC-RES-22 | `PATCH /api/v1/resources/equipment/{id}/status` | Validation Failure | Pass invalid equipment status string | HTTP 422 Unprocessable Entity |
| TC-RES-23 | `PATCH /api/v1/resources/equipment/{id}/status` | Auth / RBAC | Citizen role attempts to update equipment status | HTTP 403 Forbidden |
| TC-RES-24 | `PATCH /api/v1/resources/equipment/{id}/status` | Edge Case | Update status for non-existent equipment ID | HTTP 404 Not Found |
