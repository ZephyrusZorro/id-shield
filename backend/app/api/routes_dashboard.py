"""Dashboard summary — always derived from stored cases, never hardcoded."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends

from app.db.base import get_db
from app.db.models import Case
from app.schemas.common import (
    DashboardSummary,
    RecentScreeningItem,
    RecentScreeningsResponse,
)

router = APIRouter()

# Recommendation values used to bucket case outcomes.
_VALID = {"verification_passed", "low_risk"}
_REVIEW = {"review_recommended", "manual_review_required", "unable_to_verify"}


def _bucket(recommendation: str | None, overall_risk: int | None) -> str:
    if recommendation is None or overall_risk is None:
        return "pending"
    rec = recommendation.strip().lower()
    if rec in _VALID:
        return "valid"
    if rec in _REVIEW and overall_risk >= 60:
        return "high_risk"
    if rec in _REVIEW:
        return "under_review"
    return "pending"


@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)) -> DashboardSummary:
    total = db.scalar(select(func.count(Case.id))) or 0
    completed = db.scalars(select(Case)).all()

    buckets = {"valid": 0, "under_review": 0, "high_risk": 0}
    risk_values: list[int] = []
    for case in completed:
        b = _bucket(case.recommendation, case.overall_risk)
        if b in buckets:
            buckets[b] += 1
        if case.overall_risk is not None:
            risk_values.append(case.overall_risk)

    avg = round(sum(risk_values) / len(risk_values), 1) if risk_values else None
    return DashboardSummary(
        total_screened=total,
        valid=buckets["valid"],
        under_review=buckets["under_review"],
        high_risk=buckets["high_risk"],
        average_risk_score=avg,
    )


@router.get("/dashboard/recent", response_model=RecentScreeningsResponse)
def recent_screenings(limit: int = 8, db: Session = Depends(get_db)) -> RecentScreeningsResponse:
    cases = (
        db.scalars(select(Case).order_by(Case.case_number.desc()).limit(limit))
        .all()
    )
    items: list[RecentScreeningItem] = []
    for case in cases:
        doc_type = next(
            (d.document_type for d in case.documents if d.document_type), None
        )
        person = next(
            (
                f.raw_value
                for d in case.documents
                for f in d.fields
                if f.field_name == "full_name"
            ),
            None,
        )
        status = "processing" if case.status != "completed" else _bucket(
            case.recommendation, case.overall_risk
        )
        items.append(
            RecentScreeningItem(
                case_id=case.id,
                case_number=case.case_number,
                case_name=case.case_name,
                document_type=doc_type,
                person_name=person,
                risk_score=case.overall_risk,
                status=status,
                created_at=case.created_at,
            )
        )
    return RecentScreeningsResponse(items=items)
