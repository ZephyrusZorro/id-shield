"""Risk reporting endpoint — the explainable score ledger."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import Case, RiskFactor
from app.schemas.risk import RiskFactorItem, RiskReport

router = APIRouter()


@router.get("/cases/{case_id}/risk", response_model=RiskReport)
def get_case_risk(case_id: str, db: Session = Depends(get_db)) -> RiskReport:
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    factors = db.scalars(
        select(RiskFactor)
        .where(RiskFactor.case_id == case_id)
        .order_by(RiskFactor.score.desc())
    ).all()
    band = None
    if case.overall_risk is not None:
        from app.services.risk_engine import load_config, _band_for

        band, _ = _band_for(load_config(), case.overall_risk)

    return RiskReport(
        case_id=case_id,
        score=case.overall_risk,
        band=band,
        recommendation=case.recommendation,
        factors=[
            RiskFactorItem(
                factor=f.factor,
                score=f.score,
                direction=f.direction,
                explanation=f.explanation,
            )
            for f in factors
        ],
    )
