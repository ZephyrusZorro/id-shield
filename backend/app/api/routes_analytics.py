"""Analytics and intelligence REST endpoints."""
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.schemas.analytics import AnalyticsResponse
from app.services import analytics_service

router = APIRouter()


@router.get("/analytics", response_model=AnalyticsResponse)
def get_analytics(
    time_range: str = Query("30d", pattern="^(7d|30d|90d|all)$"),
    db: Session = Depends(get_db),
) -> AnalyticsResponse:
    """Retrieve operational intelligence, screening volume trends, risk distribution,
    discrepancy rankings, and forensic tampering metrics across screened cases.
    """
    return analytics_service.get_analytics_data(db, time_range=time_range)


@router.get("/analytics/export")
def export_analytics_csv(
    time_range: str = Query("30d", pattern="^(7d|30d|90d|all)$"),
    db: Session = Depends(get_db),
) -> Response:
    """Export screening statistics and discrepancy intelligence as a CSV document."""
    csv_content = analytics_service.generate_analytics_csv(db, time_range=time_range)
    filename = f"idshield_analytics_{time_range}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
