"""Forensics report schemas."""
from pydantic import BaseModel


class ForensicItem(BaseModel):
    region: str
    finding_type: str
    severity: str
    score: float
    bbox: list[int]
    explanation: str


class DocumentForensicsReport(BaseModel):
    document_id: str
    file_name: str
    document_type: str | None
    overall_suspicion: str  # low | medium | high
    suspicion_score: int  # 0-100
    findings: list[ForensicItem]


class CaseForensicsResponse(BaseModel):
    case_id: str
    disclaimer: str
    documents: list[DocumentForensicsReport]
