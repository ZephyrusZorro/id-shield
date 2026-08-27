"""Pydantic schemas for the Analytics & Intelligence engine."""
from __future__ import annotations

from pydantic import BaseModel, Field


class AnalyticsKpis(BaseModel):
    total_cases: int = Field(description="Total cases screened in the timeframe")
    valid_count: int = Field(description="Cases passing verification")
    review_count: int = Field(description="Cases requiring manual review")
    high_risk_count: int = Field(description="Cases flagged as high risk / fraud")
    pass_rate: float = Field(description="Verification pass percentage")
    review_rate: float = Field(description="Review percentage")
    high_risk_rate: float = Field(description="High-risk flag percentage")
    average_risk_score: float = Field(description="Average risk score (0-100)")
    avg_processing_time_ms: int = Field(description="Average end-to-end processing duration in ms")
    total_documents_analyzed: int = Field(description="Total documents parsed and inspected")
    face_verifications_count: int = Field(description="Total face cross-matching checks conducted")
    face_mismatch_rate: float = Field(description="Percentage of biometric comparisons with mismatch")


class VolumeTrendPoint(BaseModel):
    date: str = Field(description="Date label (YYYY-MM-DD or formatted)")
    valid: int = Field(default=0)
    under_review: int = Field(default=0)
    high_risk: int = Field(default=0)
    total: int = Field(default=0)


class RiskDistributionBucket(BaseModel):
    tier: str = Field(description="Tier name e.g. Low, Moderate, Elevated, Critical")
    range_label: str = Field(description="Score range e.g. 0-20, 21-49, 50-74, 75-100")
    count: int = Field(default=0)
    percentage: float = Field(default=0.0)
    color: str = Field(description="Hex or tailwind color class for the tier")


class MismatchFieldStat(BaseModel):
    field_name: str = Field(description="Field name identifier e.g. date_of_birth, facial_photo")
    label: str = Field(description="Human readable field title")
    count: int = Field(default=0)
    percentage: float = Field(default=0.0)
    severity_breakdown: dict[str, int] = Field(default_factory=dict)


class DocumentTypeStat(BaseModel):
    document_type: str = Field(description="Document type key e.g. passport, pan, national_id")
    label: str = Field(description="Display label")
    count: int = Field(default=0)
    percentage: float = Field(default=0.0)
    pass_rate: float = Field(default=0.0)
    avg_confidence: float = Field(default=0.0)


class ForensicSignalStat(BaseModel):
    signal_key: str = Field(description="Signal identifier e.g. ela_anomaly, face_mismatch")
    label: str = Field(description="Display title for forensic indicator")
    category: str = Field(description="tampering | biometric | validation | security_feature")
    detected_count: int = Field(default=0)
    rate_percent: float = Field(default=0.0)
    avg_severity_score: float = Field(default=0.0)


class StageLatencyStat(BaseModel):
    stage_key: str = Field(description="Stage key e.g. ocr, forensics, faces")
    stage_label: str = Field(description="Display name for stage")
    avg_duration_ms: int = Field(default=0)
    min_duration_ms: int = Field(default=0)
    max_duration_ms: int = Field(default=0)


class IntelligenceInsight(BaseModel):
    id: str
    type: str = Field(description="risk_alert | trend | performance | quality")
    title: str
    description: str
    metric: str
    importance: str = Field(description="high | medium | info")


class AnalyticsResponse(BaseModel):
    time_range: str = Field(description="Selected filter: 7d, 30d, 90d, all")
    kpis: AnalyticsKpis
    volume_trends: list[VolumeTrendPoint]
    risk_distribution: list[RiskDistributionBucket]
    mismatch_fields: list[MismatchFieldStat]
    document_types: list[DocumentTypeStat]
    forensic_signals: list[ForensicSignalStat]
    stage_latencies: list[StageLatencyStat]
    insights: list[IntelligenceInsight]
    is_synthetic_baseline: bool = Field(
        default=False,
        description="True if baseline data points augmented sparse database for demonstration",
    )
