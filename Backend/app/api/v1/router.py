"""Aggregates all v1 resource routers into a single APIRouter."""

from fastapi import APIRouter

from app.api.v1.routes import (
    auth,
    bulk_pickups,
    complaints,
    feed,
    notifications,
    reports,
    resources,
    schedule,
    tasks,
    transparency,
    wards,
)

router = APIRouter()
router.include_router(auth.router)
router.include_router(wards.router)
router.include_router(complaints.router)
router.include_router(tasks.router)
router.include_router(resources.router)
router.include_router(notifications.router)
router.include_router(transparency.router)
router.include_router(feed.router)
router.include_router(reports.router)
router.include_router(bulk_pickups.router)
router.include_router(schedule.router)

__all__ = ["router"]
