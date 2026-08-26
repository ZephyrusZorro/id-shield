"""Risk report schemas."""
from pydantic import BaseModel


class RiskFactorItem(BaseModel):
    factor: str
    score: int
    direction: str
    explanation: str


class RiskReport(BaseModel):
    case_id: str
    score: int | None
    band: str | None
    recommendation: str | None
    factors: list[RiskFactorItem]
