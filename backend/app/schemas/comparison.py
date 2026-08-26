"""Cross-document comparison response schemas."""
from pydantic import BaseModel


class ComparisonValue(BaseModel):
    document_id: str
    file_name: str
    raw_value: str
    normalized_value: str | None
    confidence: float | None
    agrees: bool  # agrees with the majority/reference cluster


class ComparisonFieldRow(BaseModel):
    field_name: str
    label: str
    status: str  # consistent | mismatch | single_source
    severity: str | None  # high | medium when mismatched
    explanation: str | None = None
    values: list[ComparisonValue]


class CaseComparisonResponse(BaseModel):
    case_id: str
    fields: list[ComparisonFieldRow]
