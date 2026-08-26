"""Analysis pipeline schemas."""
from pydantic import BaseModel


class AnalysisStageItem(BaseModel):
    stage_key: str
    stage_label: str
    status: str
    detail: str | None
    duration_ms: int | None
    order_index: int


class AnalysisResponse(BaseModel):
    case_id: str
    case_status: str
    stages: list[AnalysisStageItem]


class AnalyzeAccepted(BaseModel):
    case_id: str
    status: str
