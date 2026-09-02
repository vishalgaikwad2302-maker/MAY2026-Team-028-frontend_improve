"""Analytics and reporting service."""

from collections import defaultdict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.complaint import Complaint, ComplaintStatus
from app.models.task import Task, TaskStatus
from app.models.transparency import TransparencyPost
from app.models.ward import Ward
from app.models.worker import Worker
from app.schemas.report import (
    CrewPerformance,
    HazardCount,
    ReportsPerformanceRead,
    ReportsPublicRead,
    ReportsTrendsRead,
    StatusCount,
    TimeSeriesPoint,
    TopWardStats,
    TotalsSummary,
    WardPerformance,
)


class ReportService:
    @staticmethod
    def get_trends(db: Session, *, ward_id: int | None = None) -> ReportsTrendsRead:
        stmt = select(Complaint)
        if ward_id is not None:
            stmt = stmt.where(Complaint.ward_id == ward_id)

        complaints = list(db.scalars(stmt).all())

        status_counts: dict[str, int] = defaultdict(int)
        hazard_counts: dict[str, int] = defaultdict(int)
        time_series_map: dict[str, int] = defaultdict(int)

        pending_cnt = 0
        in_progress_cnt = 0
        resolved_cnt = 0
        cancelled_cnt = 0

        for c in complaints:
            st = c.status
            status_counts[st] += 1

            if st == ComplaintStatus.PENDING.value:
                pending_cnt += 1
            elif st == ComplaintStatus.IN_PROGRESS.value:
                in_progress_cnt += 1
            elif st in (
                ComplaintStatus.RESOLVED.value,
                ComplaintStatus.VERIFIED.value,
                ComplaintStatus.CLOSED.value,
            ):
                resolved_cnt += 1
            elif st == ComplaintStatus.CANCELLED.value:
                cancelled_cnt += 1

            hazard_key = c.category if c.category else "No Hazard Flagged"
            hazard_counts[hazard_key] += 1

            if c.created_at:
                date_str = c.created_at.strftime("%Y-%m-%d")
                time_series_map[date_str] += 1

        totals = TotalsSummary(
            total=len(complaints),
            pending=pending_cnt,
            in_progress=in_progress_cnt,
            resolved=resolved_cnt,
            cancelled=cancelled_cnt,
        )

        status_breakdown = [
            StatusCount(status=k, count=v) for k, v in status_counts.items()
        ]
        hazard_breakdown = [
            HazardCount(hazard=k, count=v) for k, v in hazard_counts.items()
        ]
        time_series = [
            TimeSeriesPoint(date=k, count=v)
            for k, v in sorted(time_series_map.items(), key=lambda x: x[0])
        ]

        return ReportsTrendsRead(
            totals=totals,
            status_breakdown=status_breakdown,
            hazard_breakdown=hazard_breakdown,
            time_series=time_series,
        )

    @staticmethod
    def get_performance(db: Session, *, ward_id: int | None = None) -> ReportsPerformanceRead:
        # Fetch complaints
        c_stmt = select(Complaint)
        if ward_id is not None:
            c_stmt = c_stmt.where(Complaint.ward_id == ward_id)
        complaints = list(db.scalars(c_stmt).all())

        resolved_complaints = [
            c for c in complaints
            if c.status in (ComplaintStatus.RESOLVED.value, ComplaintStatus.VERIFIED.value, ComplaintStatus.CLOSED.value)
            and c.resolved_at is not None
            and c.created_at is not None
        ]

        total_days = 0.0
        for c in resolved_complaints:
            diff = (c.resolved_at - c.created_at).total_seconds() / (24 * 3600)
            total_days += max(0.0, diff)

        avg_resolution_days = (
            round(total_days / len(resolved_complaints), 1) if resolved_complaints else 0.0
        )

        # Ward Performance
        wards = list(db.scalars(select(Ward)).all())
        ward_perf_list: list[WardPerformance] = []

        complaints_by_ward: dict[int | None, list[Complaint]] = defaultdict(list)
        for c in complaints:
            complaints_by_ward[c.ward_id].append(c)

        for w in wards:
            w_complaints = complaints_by_ward.get(w.id, [])
            w_resolved = [
                c for c in w_complaints
                if c.status in (ComplaintStatus.RESOLVED.value, ComplaintStatus.VERIFIED.value, ComplaintStatus.CLOSED.value)
            ]
            w_res_with_time = [c for c in w_resolved if c.resolved_at is not None and c.created_at is not None]
            w_days = sum(max(0.0, (c.resolved_at - c.created_at).total_seconds() / (24 * 3600)) for c in w_res_with_time)
            w_avg_days = round(w_days / len(w_res_with_time), 1) if w_res_with_time else 0.0
            rate = round((len(w_resolved) / len(w_complaints)) * 100, 1) if w_complaints else 0.0

            ward_perf_list.append(
                WardPerformance(
                    ward_id=w.id,
                    ward_name=w.name,
                    total_complaints=len(w_complaints),
                    resolved_complaints=len(w_resolved),
                    avg_resolution_days=w_avg_days,
                    resolution_rate=rate,
                )
            )

        # Crew Performance
        workers = list(db.scalars(select(Worker)).all())
        tasks = list(db.scalars(select(Task)).all())
        crew_perf_list: list[CrewPerformance] = []

        for worker in workers:
            w_tasks = [t for t in tasks if worker in t.assigned_workers]
            w_completed = [t for t in w_tasks if t.status == TaskStatus.COMPLETED.value]
            w_rate = round((len(w_completed) / len(w_tasks)) * 100, 1) if w_tasks else 0.0

            crew_perf_list.append(
                CrewPerformance(
                    worker_id=worker.id,
                    worker_name=worker.name,
                    total_tasks_assigned=len(w_tasks),
                    completed_tasks=len(w_completed),
                    completion_rate=w_rate,
                )
            )

        return ReportsPerformanceRead(
            avg_resolution_days=avg_resolution_days,
            total_resolved=len(resolved_complaints),
            ward_performance=ward_perf_list,
            crew_performance=crew_perf_list,
        )

    @staticmethod
    def get_public_stats(db: Session) -> ReportsPublicRead:
        complaints = list(db.scalars(select(Complaint)).all())
        total = len(complaints)

        resolved_list = [
            c for c in complaints
            if c.status in (ComplaintStatus.RESOLVED.value, ComplaintStatus.VERIFIED.value, ComplaintStatus.CLOSED.value)
        ]
        resolved_cnt = len(resolved_list)
        active_cnt = total - resolved_cnt - sum(1 for c in complaints if c.status == ComplaintStatus.CANCELLED.value)

        rate = round((resolved_cnt / total) * 100, 1) if total else 0.0

        res_with_time = [c for c in resolved_list if c.resolved_at is not None and c.created_at is not None]
        total_days = sum(max(0.0, (c.resolved_at - c.created_at).total_seconds() / (24 * 3600)) for c in res_with_time)
        avg_days = round(total_days / len(res_with_time), 1) if res_with_time else 0.0

        posts_count = len(list(db.scalars(select(TransparencyPost)).all()))

        # Top wards by resolved count
        wards = list(db.scalars(select(Ward)).all())
        top_wards_list: list[TopWardStats] = []
        for w in wards:
            w_res = sum(
                1 for c in complaints
                if c.ward_id == w.id
                and c.status in (ComplaintStatus.RESOLVED.value, ComplaintStatus.VERIFIED.value, ComplaintStatus.CLOSED.value)
            )
            top_wards_list.append(TopWardStats(ward_id=w.id, name=w.name, resolved_count=w_res))

        top_wards_list.sort(key=lambda x: x.resolved_count, reverse=True)

        return ReportsPublicRead(
            total_complaints=total,
            resolved_complaints=resolved_cnt,
            active_complaints=active_cnt,
            resolution_rate=rate,
            avg_resolution_days=avg_days,
            total_cleanups_completed=posts_count,
            top_wards=top_wards_list[:5],
        )
