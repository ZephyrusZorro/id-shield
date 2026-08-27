"""Validation report schemas."""
from pydantic import BaseModel


class ValidationItem(BaseModel):
    check_type: str
    status: str
    message: str
    evidence: dict | None = None


class DocumentValidationReport(BaseModel):
    document_id: str
    file_name: str
    document_type: str | None
    overall_status: str  # valid | review_required | unable_to_verify
    items: list[ValidationItem]


class CaseValidationsResponse(BaseModel):
    case_id: str
    documents: list[DocumentValidationReport]
