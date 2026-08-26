"""Case and document API schemas."""
from datetime import datetime

from pydantic import BaseModel, Field


class CaseCreate(BaseModel):
    case_name: str = Field(min_length=1, max_length=200)


class DocumentOut(BaseModel):
    id: str
    file_name: str
    mime_type: str
    file_size: int
    document_type: str | None
    type_confidence: float | None
    processing_status: str
    has_preview: bool

    @classmethod
    def from_model(cls, doc) -> "DocumentOut":
        return cls(
            id=doc.id,
            file_name=doc.file_name,
            mime_type=doc.mime_type,
            file_size=doc.file_size,
            document_type=doc.document_type,
            type_confidence=doc.type_confidence,
            processing_status=doc.processing_status,
            has_preview=doc.mime_type.startswith("image/"),
        )


class CaseOut(BaseModel):
    id: str
    case_number: int
    case_name: str
    status: str
    overall_risk: int | None
    recommendation: str | None
    person_name: str | None
    document_count: int
    created_at: datetime
    documents: list[DocumentOut] | None = None

    @classmethod
    def from_model(cls, case, person_name: str | None = None, include_documents: bool = True) -> "CaseOut":
        return cls(
            id=case.id,
            case_number=case.case_number,
            case_name=case.case_name,
            status=case.status,
            overall_risk=case.overall_risk,
            recommendation=case.recommendation,
            person_name=person_name,
            document_count=len(case.documents),
            created_at=case.created_at,
            documents=[DocumentOut.from_model(d) for d in case.documents] if include_documents else None,
        )


class CaseCreated(BaseModel):
    id: str
    case_number: int
    case_name: str
    status: str


class UploadResult(BaseModel):
    case_id: str
    uploaded: list[DocumentOut]
    failed: list[dict]


class DeleteResult(BaseModel):
    deleted: bool
