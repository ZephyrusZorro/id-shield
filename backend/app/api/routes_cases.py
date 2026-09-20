"""Case + document REST endpoints."""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.security import UploadValidationError
from app.db.base import get_db
from app.db.models import Document
from app.schemas.cases import (
    CaseCreate,
    CaseCreated,
    CaseOut,
    CaseReviewRequest,
    DeleteResult,
    DocumentOut,
    UploadResult,
)
from app.schemas.documents import DocumentTypeUpdate
from app.services import case_service, upload_service


router = APIRouter()


@router.post("/cases", response_model=CaseCreated, status_code=201)
def create_case(payload: CaseCreate, db: Session = Depends(get_db)) -> CaseCreated:
    case = case_service.create_case(
        db=db,
        case_name=payload.case_name,
        applicant_name=payload.applicant_name,
        applicant_phone=payload.applicant_phone,
        applicant_email=payload.applicant_email,
        auto_notify_on_mismatch=payload.auto_notify_on_mismatch,
    )
    return CaseCreated(
        id=case.id,
        case_number=case.case_number,
        case_name=case.case_name,
        status=case.status,
        applicant_name=case.applicant_name,
        applicant_phone=case.applicant_phone,
        applicant_email=case.applicant_email,
        auto_notify_on_mismatch=bool(case.auto_notify_on_mismatch),
    )


@router.get("/cases", response_model=list[CaseOut])
def list_cases(
    search: str | None = None,
    outcome: str | None = None,
    sort: str = "recent",
    limit: int = 200,
    db: Session = Depends(get_db),
) -> list[CaseOut]:
    """Screening-history listing with optional search / outcome filter / sort."""
    cases = case_service.list_cases(db, limit=500)

    def _person(c) -> str | None:
        return next(
            (
                f.raw_value
                for d in c.documents
                for f in d.fields
                if f.field_name == "full_name"
            ),
            None,
        )

    if search:
        q = search.strip().lower()
        def _matches(c) -> bool:
            person = (_person(c) or "").lower()
            return (
                q in c.case_name.lower()
                or q in (c.recommendation or "").lower()
                or q in person
                or q == f"#{c.case_number}"
            )
        cases = [c for c in cases if _matches(c)]
    if outcome and outcome != "all":
        mapping = {
            "valid": {"verification_passed"},
            "review": {"review_recommended"},
            "high_risk": {"manual_review_required"},
            "unable": {"unable_to_verify"},
        }
        allowed = mapping.get(outcome)
        if allowed:
            cases = [c for c in cases if c.recommendation in allowed]

    if sort == "risk_desc":
        cases.sort(key=lambda c: c.overall_risk if c.overall_risk is not None else -1, reverse=True)
    elif sort == "risk_asc":
        cases.sort(key=lambda c: c.overall_risk if c.overall_risk is not None else 999)
    else:  # recent = descending case number
        cases.sort(key=lambda c: c.case_number, reverse=True)

    cases = cases[: max(1, min(limit, 500))]
    return [CaseOut.from_model(c, person_name=_person(c), include_documents=False) for c in cases]


@router.get("/cases/{case_id}", response_model=CaseOut)
def get_case(case_id: str, db: Session = Depends(get_db)) -> CaseOut:
    case = case_service.get_case(db, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    return CaseOut.from_model(case)


@router.post(
    "/cases/{case_id}/documents",
    response_model=UploadResult,
    status_code=201,
)
async def upload_documents(
    case_id: str,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
) -> UploadResult:
    case = case_service.get_case(db, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")

    uploaded: list[DocumentOut] = []
    failed: list[dict] = []
    for upload in files:
        try:
            doc = await upload_service.save_upload(db, case, upload)
            uploaded.append(DocumentOut.from_model(doc))
        except UploadValidationError as exc:
            failed.append({"file_name": upload.filename, "error": str(exc)})
        finally:
            await upload.close()

    if not uploaded and failed:
        raise HTTPException(status_code=422, detail={"failed": failed})
    return UploadResult(case_id=case.id, uploaded=uploaded, failed=failed)


@router.get("/documents/{document_id}/file")
def get_document_file(document_id: str, db: Session = Depends(get_db)) -> FileResponse:
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    try:
        path = upload_service.get_document_file_path(doc)
    except UploadValidationError:
        raise HTTPException(status_code=400, detail="Invalid file path.") from None
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Stored file is missing.")
    return FileResponse(path, media_type=doc.mime_type or "application/octet-stream")


@router.delete("/documents/{document_id}", response_model=DeleteResult)
def delete_document(document_id: str, db: Session = Depends(get_db)) -> DeleteResult:
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    upload_service.delete_document(db, doc)
    return DeleteResult(deleted=True)


@router.patch("/documents/{document_id}/type", response_model=DocumentOut)
@router.patch("/cases/{case_id}/documents/{document_id}/type", response_model=DocumentOut)
def update_document_type(
    document_id: str,
    payload: DocumentTypeUpdate,
    case_id: str | None = None,
    db: Session = Depends(get_db),
) -> DocumentOut:
    """Allow user/system to correct or override document type."""
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    if case_id and doc.case_id != case_id:
        raise HTTPException(status_code=404, detail="Document does not belong to specified case.")

    clean_type = payload.document_type.strip().lower().replace(" ", "_")
    doc.document_type = clean_type
    doc.type_confidence = 1.0  # Explicit manual override
    db.commit()
    db.refresh(doc)
    return DocumentOut.from_model(doc)


@router.post("/cases/{case_id}/review", response_model=CaseOut)
def submit_case_review(
    case_id: str,
    payload: CaseReviewRequest,
    db: Session = Depends(get_db),
) -> CaseOut:
    """Record an official human verifier decision (approved, rejected, needs_further_review)."""
    from datetime import datetime, timezone
    from app.core.logging import get_logger
    log = get_logger("idshield.cases")

    case = case_service.get_case(db, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")

    valid_decisions = {"approved", "rejected", "needs_further_review", "pending_review"}
    clean_decision = payload.decision.strip().lower()
    if clean_decision not in valid_decisions:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid decision '{payload.decision}'. Must be one of: {sorted(valid_decisions)}",
        )

    case.review_status = clean_decision
    case.reviewer_name = payload.reviewer_name or "Verification Officer"
    case.reviewer_notes = payload.notes or ""
    case.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(case)

    log.info(
        "CASE_REVIEW_RECORDED | case_id=%s decision=%s reviewer=%s",
        case.id, clean_decision, case.reviewer_name,
    )
    return CaseOut.from_model(case)


