"""Voice Assistant & Accessible Oral Briefing REST endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import (
    Case,
    CrossDocumentFinding,
    Document,
    ForensicFinding,
    ValidationResult,
)
from app.schemas.cases import CaseOut
from app.services.classifier_service import get_document_label
from pydantic import BaseModel

router = APIRouter()


class VoiceBriefResponse(BaseModel):
    case_id: str
    case_number: int
    applicant_name: str
    spoken_text: str
    summary_bullets: list[str]
    risk_level: str
    recommendation: str
    has_warnings: bool
    risk_score: int | None = None


@router.get("/cases/{case_id}/voice-brief", response_model=VoiceBriefResponse)
def get_case_voice_brief(case_id: str, db: Session = Depends(get_db)) -> VoiceBriefResponse:
    """Generate a friendly, spoken-word case briefing tailored for elderly accessibility."""
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")

    docs = db.scalars(select(Document).where(Document.case_id == case_id)).all()
    conflicts = db.scalars(
        select(CrossDocumentFinding)
        .where(CrossDocumentFinding.case_id == case_id)
        .where(CrossDocumentFinding.severity.in_(["medium", "high"]))
    ).all()
    forensics = db.scalars(
        select(ForensicFinding).where(ForensicFinding.document_id.in_([d.id for d in docs]))
    ).all()
    val_fails = db.scalars(
        select(ValidationResult)
        .where(ValidationResult.document_id.in_([d.id for d in docs]))
        .where(ValidationResult.status == "fail")
    ).all()

    applicant = case.applicant_name or "the applicant"
    doc_labels = [get_document_label(d.document_type) for d in docs if d.document_type]
    doc_str = ", and ".join(doc_labels) if doc_labels else f"{len(docs)} documents"

    # Assemble sentences with friendly, clear tone
    sentences: list[str] = [
        f"Hello. Here is the identity verification briefing for case number {case.case_number}, for {applicant}."
    ]
    bullets: list[str] = []

    if not docs:
        sentences.append("No documents have been uploaded to this case yet.")
        bullets.append("No documents uploaded yet.")
    else:
        sentences.append(f"We have processed {len(docs)} identity document: {doc_str}." if len(docs) == 1 else f"We have processed {len(docs)} identity documents: {doc_str}.")
        bullets.append(f"Processed {len(docs)} documents ({doc_str})")

    # Discrepancies check
    has_conflicts = len(conflicts) > 0
    if not has_conflicts and docs:
        sentences.append("Good news. Personal details such as the full name and date of birth match consistently across the submitted cards.")
        bullets.append("Personal identity details match across documents.")
    elif has_conflicts:
        conflict_fields = list({c.field_name.replace('_', ' ') for c in conflicts})
        fields_text = ", and ".join(conflict_fields)
        sentences.append(f"Please note: we noticed a discrepancy in {fields_text}. The information on one card does not match the other.")
        bullets.append(f"Mismatched fields detected: {fields_text}")

    # Forensic tampering check
    high_forensics = [f for f in forensics if f.severity in ("medium", "high")]
    if not high_forensics and docs:
        sentences.append("The security scan shows the document images appear authentic and free from digital tampering.")
        bullets.append("No image tampering or pixel editing detected.")
    elif high_forensics:
        sentences.append("Our security checks detected visual anomalies such as possible digital editing or cloned pixels that require careful human inspection.")
        bullets.append(f"Detected {len(high_forensics)} visual forensic indicator(s) of potential alteration.")

    # Validation check
    if val_fails:
        sentences.append("Some document formatting rules or mandatory security numbers did not validate successfully.")
        bullets.append(f"{len(val_fails)} format validation check(s) flagged.")

    # Review status check
    if getattr(case, "review_status", None) and case.review_status != "pending_review":
        status_readable = case.review_status.replace("_", " ")
        reviewer = case.reviewer_name or "A verification officer"
        sentences.append(f"This case has been officially marked as {status_readable} by {reviewer}.")
        bullets.append(f"Official review disposition: {status_readable.upper()} by {reviewer}")
    else:
        rec = case.recommendation or "evaluating"
        if rec == "verification_passed":
            sentences.append("Overall, this verification has passed all automated criteria.")
            bullets.append("Automated recommendation: Verification Passed.")
        elif rec == "review_recommended":
            sentences.append("The system recommends a routine review by an officer.")
            bullets.append("Automated recommendation: Review Recommended.")
        else:
            sentences.append("Because of the flagged items, manual review is recommended before approving this application.")
            bullets.append("Automated recommendation: Manual Review Required.")

    sentences.append("You can speak commands like 'show documents', 'check tampering', or 'approve application' at any time.")

    spoken_text = " ".join(sentences)
    has_warnings = has_conflicts or len(high_forensics) > 0 or len(val_fails) > 0

    return VoiceBriefResponse(
        case_id=case.id,
        case_number=case.case_number,
        applicant_name=applicant,
        spoken_text=spoken_text,
        summary_bullets=bullets,
        risk_level=case.recommendation or "normal",
        recommendation=case.recommendation or "verification_passed",
        has_warnings=has_warnings,
        risk_score=case.overall_risk,
    )


class VoiceQueryRequest(BaseModel):
    query: str
    current_path: str | None = None


class VoiceQueryResponse(BaseModel):
    answer: str
    action: str | None = None
    category: str | None = None


@router.post("/cases/{case_id}/voice-query", response_model=VoiceQueryResponse)
def query_case_voice(
    case_id: str,
    payload: VoiceQueryRequest,
    db: Session = Depends(get_db),
) -> VoiceQueryResponse:
    """Intelligently answer any spoken or typed question regarding a verification case."""
    from app.services.voice_assistant_service import answer_case_query

    result = answer_case_query(case_id=case_id, query=payload.query, db=db)
    return VoiceQueryResponse(
        answer=result["answer"],
        action=result.get("action"),
        category=result.get("category"),
    )


@router.post("/voice-query", response_model=VoiceQueryResponse)
def query_system_voice(payload: VoiceQueryRequest) -> VoiceQueryResponse:
    """Intelligently answer system navigation, guidance, or help questions."""
    from app.services.voice_assistant_service import answer_system_query

    result = answer_system_query(query=payload.query, current_path=payload.current_path)
    return VoiceQueryResponse(
        answer=result["answer"],
        action=result.get("action"),
        category=result.get("category"),
    )

