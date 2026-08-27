"""Extracted field / document detail schemas."""
from datetime import datetime

from pydantic import BaseModel


class ExtractedFieldItem(BaseModel):
    field_name: str
    raw_value: str
    normalized_value: str | None
    confidence: float | None
    source_region: dict | None


class DocumentDetail(BaseModel):
    id: str
    case_id: str
    file_name: str
    mime_type: str
    file_size: int
    document_type: str | None
    type_confidence: float | None
    processing_status: str
    has_preview: bool
    ocr_engine: str | None
    ocr_mean_confidence: float | None
    file_hash_prefix: str | None
    uploaded_at: datetime
    fields: list[ExtractedFieldItem]
