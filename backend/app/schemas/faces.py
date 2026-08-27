"""Pydantic schemas for face extraction and cross-matching forensics."""
from __future__ import annotations

from pydantic import BaseModel, Field


class FaceCropInfo(BaseModel):
    document_id: str
    file_name: str
    bbox: list[int] = Field(description="[x, y, w, h] in pixel coordinates")
    normalized_bbox: list[float] = Field(description="[x, y, w, h] normalized 0..1")
    confidence: float
    detection_method: str
    sharpness: float
    brightness: float
    contrast: float
    has_crop: bool = True


class FaceMetrics(BaseModel):
    ssim_score: float
    phash_similarity: float
    lbp_correlation: float
    color_correlation: float


class FaceComparisonPair(BaseModel):
    doc_a_id: str
    doc_a_name: str
    doc_b_id: str
    doc_b_name: str
    similarity_score: int  # 0..100
    status: str  # "match" | "borderline" | "mismatch"
    severity: str  # "info" | "medium" | "high"
    explanation: str
    metrics: FaceMetrics


class CaseFacesResponse(BaseModel):
    case_id: str
    disclaimer: str
    faces: list[FaceCropInfo]
    comparisons: list[FaceComparisonPair]
    overall_status: str
