"""ID-SHIELD database entities (spec §38) + analysis stage tracking."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


# ----------------------------------------------------------------- User
class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(50), default="verifier")


# ----------------------------------------------------------------- Case
class Case(Base, TimestampMixin):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    case_number: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    case_name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(30), default="draft")
    # draft | processing | completed | failed
    overall_risk: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(String(60), nullable=True)
    applicant_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    applicant_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    applicant_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    auto_notify_on_mismatch: Mapped[bool] = mapped_column(Boolean, default=False)

    documents: Mapped[list["Document"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
    notifications: Mapped[list["CaseNotification"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )


# ------------------------------------------------------------- Document
class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    file_name: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100), default="")
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    document_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    type_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    original_path: Mapped[str] = mapped_column(String(500))
    processed_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    perceptual_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    processing_status: Mapped[str] = mapped_column(String(30), default="uploaded")
    # uploaded | processing | done | error
    ocr_engine: Mapped[str | None] = mapped_column(String(40), nullable=True)
    ocr_mean_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    case: Mapped[Case] = relationship(back_populates="documents")
    fields: Mapped[list["ExtractedField"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    validation_results: Mapped[list["ValidationResult"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    forensic_findings: Mapped[list["ForensicFinding"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


# ------------------------------------------------------- ExtractedField
class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    field_name: Mapped[str] = mapped_column(String(80), index=True)
    raw_value: Mapped[str] = mapped_column(Text, default="")
    normalized_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_region: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    document: Mapped[Document] = relationship(back_populates="fields")


# ---------------------------------------------------- ValidationResult
class ValidationResult(Base):
    __tablename__ = "validation_results"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    check_type: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20))  # pass | fail | warning | unavailable
    message: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    document: Mapped[Document] = relationship(back_populates="validation_results")


# ------------------------------------------------ CrossDocumentFinding
class CrossDocumentFinding(Base):
    __tablename__ = "cross_document_findings"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    field_name: Mapped[str] = mapped_column(String(80))
    severity: Mapped[str] = mapped_column(String(20))  # info | low | medium | high
    documents_involved: Mapped[list] = mapped_column(JSON, default=list)
    values: Mapped[dict] = mapped_column(JSON, default=dict)
    explanation: Mapped[str] = mapped_column(Text, default="")


# ----------------------------------------------------- ForensicFinding
class ForensicFinding(Base):
    __tablename__ = "forensic_findings"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    region: Mapped[str] = mapped_column(String(80))
    finding_type: Mapped[str] = mapped_column(String(120))
    severity: Mapped[str] = mapped_column(String(20))  # low | medium | high
    score: Mapped[float] = mapped_column(Float, default=0.0)
    bbox: Mapped[list | None] = mapped_column(JSON, nullable=True)  # [x, y, w, h]
    explanation: Mapped[str] = mapped_column(Text, default="")

    document: Mapped[Document] = relationship(back_populates="forensic_findings")


# ---------------------------------------------------------- RiskFactor
class RiskFactor(Base):
    __tablename__ = "risk_factors"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    factor: Mapped[str] = mapped_column(String(120))
    score: Mapped[int] = mapped_column(Integer)  # signed contribution
    direction: Mapped[str] = mapped_column(String(12))  # increase | decrease
    explanation: Mapped[str] = mapped_column(Text, default="")


# ---------------------------------------------------------------- Report
class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    content: Mapped[dict] = mapped_column(JSON, default=dict)


# -------------------------------------------------------- AnalysisStage
class AnalysisStage(Base):
    """Live pipeline stage status, polled by the processing screen."""

    __tablename__ = "analysis_stages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    order_index: Mapped[int] = mapped_column(Integer)
    stage_key: Mapped[str] = mapped_column(String(60))
    stage_label: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    # pending | running | done | warning | unavailable | error
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)


# ----------------------------------------------------- CaseNotification
class CaseNotification(Base, TimestampMixin):
    """Audit record of SMS / WhatsApp / Email discrepancy alerts sent."""

    __tablename__ = "case_notifications"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    recipient: Mapped[str] = mapped_column(String(320))
    channel: Mapped[str] = mapped_column(String(30))  # sms | whatsapp | email | webhook
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message: Mapped[str] = mapped_column(Text)
    mismatch_fields: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(30), default="sent")  # sent | delivered | simulated | failed
    trigger_type: Mapped[str] = mapped_column(String(30), default="manual")  # manual | automatic
    provider_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    case: Mapped[Case] = relationship(back_populates="notifications")
