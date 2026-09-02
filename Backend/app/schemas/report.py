"""Pydantic DTOs for reports and analytics endpoints."""

from pydantic import BaseModel, Field


class StatusCount(BaseModel):
    status: str
    count: int


class HazardCount(BaseModel):
    hazard: str
    count: int


class TimeSeriesPoint(BaseModel):
    date: str
    count: int


class TotalsSummary(BaseModel):
    total: int
    pending: int
    in_progress: int
    resolved: int
    cancelled: int


class ReportsTrendsRead(BaseModel):
    """Response payload for GET /reports/trends."""

    totals: TotalsSummary
    status_breakdown: list[StatusCount]
    hazard_breakdown: list[HazardCount]
    time_series: list[TimeSeriesPoint]


class WardPerformance(BaseModel):
    ward_id: int | None = None
    ward_name: str
    total_complaints: int
    resolved_complaints: int
    avg_resolution_days: float
    resolution_rate: float


class CrewPerformance(BaseModel):
    worker_id: int
    worker_name: str
    total_tasks_assigned: int
    completed_tasks: int
    completion_rate: float


class ReportsPerformanceRead(BaseModel):
    """Response payload for GET /reports/performance."""

    avg_resolution_days: float
    total_resolved: int
    ward_performance: list[WardPerformance]
    crew_performance: list[CrewPerformance]


class TopWardStats(BaseModel):
    ward_id: int | None = None
    name: str
    resolved_count: int


class ReportsPublicRead(BaseModel):
    """Response payload for GET /reports/public."""

    total_complaints: int
    resolved_complaints: int
    active_complaints: int
    resolution_rate: float
    avg_resolution_days: float
    total_cleanups_completed: int
    top_wards: list[TopWardStats]
