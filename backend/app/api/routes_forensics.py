"""Forensics endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import Case, Document, ForensicFinding
from app.schemas.forensics import (
    CaseForensicsResponse,
    DocumentForensicsReport,
    ForensicItem,
)
from app.services.forensic_service import overall_suspicion

router = APIRouter()

_DISCLAIMER = (
    "Visual analysis detects indicators of potential manipulation using "
    "transparent heuristics. It does not constitute proof of forgery; final "
    "determination requires human review."
)


@router.get("/cases/{case_id}/forensics", response_model=CaseForensicsResponse)
def get_case_forensics(case_id: str, db: Session = Depends(get_db)) -> CaseForensicsResponse:
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")

    docs = db.scalars(
        select(Document).where(Document.case_id == case_id)
    ).all()
    reports: list[DocumentForensicsReport] = []
    for doc in docs:
        findings = db.scalars(
            select(ForensicFinding).where(ForensicFinding.document_id == doc.id)
        ).all()
        severity, pct = overall_suspicion(f.score for f in findings)
        reports.append(
            DocumentForensicsReport(
                document_id=doc.id,
                file_name=doc.file_name,
                document_type=doc.document_type,
                overall_suspicion=severity,
                suspicion_score=pct,
                findings=[
                    ForensicItem(
                        region=f.region,
                        finding_type=f.finding_type,
                        severity=f.severity,
                        score=f.score,
                        bbox=f.bbox or [0, 0, 0, 0],
                        explanation=f.explanation,
                    )
                    for f in findings
                ],
            )
        )
    return CaseForensicsResponse(
        case_id=case_id, disclaimer=_DISCLAIMER, documents=reports
    )
