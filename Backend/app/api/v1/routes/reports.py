"""Analytics and reporting API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.report import ReportsPerformanceRead, ReportsPublicRead, ReportsTrendsRead
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/trends", response_model=ReportsTrendsRead)
def get_report_trends(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ward_id: int | None = None,
) -> ReportsTrendsRead:
    """Return status breakdown, hazard breakdown, and time series trends (backs ReportsTrends.jsx)."""
    return ReportService.get_trends(db, ward_id=ward_id)


@router.get("/performance", response_model=ReportsPerformanceRead)
def get_report_performance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ward_id: int | None = None,
) -> ReportsPerformanceRead:
    """Return average resolution days, ward performance, and crew performance."""
    return ReportService.get_performance(db, ward_id=ward_id)


@router.get("/public", response_model=ReportsPublicRead)
def get_public_report_stats(
    db: Session = Depends(get_db),
) -> ReportsPublicRead:
    """Return public high-level cleanup statistics."""
    return ReportService.get_public_stats(db)
