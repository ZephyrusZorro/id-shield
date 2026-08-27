"""Analysis endpoints — start analysis, poll stage status, document detail."""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.base import get_db
from app.db.models import AnalysisStage, Case, Document, ExtractedField, ValidationResult
from app.schemas.analysis import AnalysisResponse, AnalysisStageItem, AnalyzeAccepted
from app.schemas.documents import DocumentDetail, ExtractedFieldItem
from app.schemas.validation import (
    CaseValidationsResponse,
    DocumentValidationReport,
    ValidationItem,
)
from app.services.pipeline import analyze_case
from app.services.validation_service import ValidationDraft, overall_status

router = APIRouter()


@router.post("/cases/{case_id}/analyze", response_model=AnalyzeAccepted, status_code=202)
def start_analysis(
    case_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> AnalyzeAccepted:
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    if case.status == "processing":
        raise HTTPException(
            status_code=409,
            detail="Analysis is already running for this case.",
        )
    doc_count = len(
        db.scalars(select(Document).where(Document.case_id == case_id)).all()
    )
    if doc_count == 0:
        raise HTTPException(status_code=422, detail="Case has no documents to analyze.")

    background_tasks.add_task(analyze_case, case_id)
    return AnalyzeAccepted(case_id=case_id, status="processing")


@router.get("/cases/{case_id}/analysis", response_model=AnalysisResponse)
def get_analysis(case_id: str, db: Session = Depends(get_db)) -> AnalysisResponse:
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    stages = db.scalars(
        select(AnalysisStage)
        .where(AnalysisStage.case_id == case_id)
        .order_by(AnalysisStage.order_index)
    ).all()
    return AnalysisResponse(
        case_id=case.id,
        case_status=case.status,
        stages=[
            AnalysisStageItem(
                stage_key=s.stage_key,
                stage_label=s.stage_label,
                status=s.status,
                detail=s.detail,
                duration_ms=s.duration_ms,
                order_index=s.order_index,
            )
            for s in stages
        ],
    )


@router.get("/cases/{case_id}/validations", response_model=CaseValidationsResponse)
def get_case_validations(
    case_id: str, db: Session = Depends(get_db)
) -> CaseValidationsResponse:
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    docs = db.scalars(
        select(Document)
        .options(selectinload(Document.validation_results))
        .where(Document.case_id == case_id)
    ).all()

    reports: list[DocumentValidationReport] = []
    for doc in docs:
        items = [
            ValidationItem(
                check_type=v.check_type,
                status=v.status,
                message=v.message,
                evidence=v.evidence,
            )
            for v in doc.validation_results
        ]
        has_fields = (
            db.scalar(
                select(ExtractedField.document_id).where(
                    ExtractedField.document_id == doc.id
                )
            )
            is not None
        )
        drafts = [
            ValidationDraft(i.check_type, i.status, i.message, i.evidence)
            for i in items
        ]
        reports.append(
            DocumentValidationReport(
                document_id=doc.id,
                file_name=doc.file_name,
                document_type=doc.document_type,
                overall_status=overall_status(drafts, has_fields),
                items=items,
            )
        )
    return CaseValidationsResponse(case_id=case_id, documents=reports)


@router.get("/documents/{document_id}", response_model=DocumentDetail)
def get_document(document_id: str, db: Session = Depends(get_db)) -> DocumentDetail:
    doc = db.scalar(
        select(Document)
        .options(selectinload(Document.fields))
        .where(Document.id == document_id)
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return DocumentDetail(
        id=doc.id,
        case_id=doc.case_id,
        file_name=doc.file_name,
        mime_type=doc.mime_type,
        file_size=doc.file_size,
        document_type=doc.document_type,
        type_confidence=doc.type_confidence,
        processing_status=doc.processing_status,
        has_preview=doc.mime_type.startswith("image/"),
        ocr_engine=doc.ocr_engine,
        ocr_mean_confidence=doc.ocr_mean_confidence,
        file_hash_prefix=(doc.file_hash or "")[:12] or None,
        uploaded_at=doc.created_at,
        fields=[
            ExtractedFieldItem(
                field_name=f.field_name,
                raw_value=f.raw_value,
                normalized_value=f.normalized_value,
                confidence=f.confidence,
                source_region=f.source_region,
            )
            for f in doc.fields
        ],
    )
