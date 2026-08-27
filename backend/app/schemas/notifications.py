"""Notification schemas for applicant discrepancy alerts (SMS / WhatsApp / Email)."""
from datetime import datetime
from pydantic import BaseModel, Field


class DiscrepancyItem(BaseModel):
    field_name: str
    label: str
    severity: str
    explanation: str
    documents_involved: list[str] = Field(default_factory=list)


class NotificationPreviewResponse(BaseModel):
    case_id: str
    case_number: int
    case_name: str
    applicant_name: str | None = None
    applicant_phone: str | None = None
    applicant_email: str | None = None
    mismatches: list[DiscrepancyItem] = Field(default_factory=list)
    has_discrepancies: bool = False
    suggested_subject: str = ""
    sms_preview: str = ""
    whatsapp_preview: str = ""
    email_preview: str = ""
    email_configured: bool = False
    sms_configured: bool = False
    whatsapp_configured: bool = False


class NotificationSendRequest(BaseModel):
    channel: str = Field(default="sms", pattern="^(sms|whatsapp|email|webhook)$")
    recipient: str = Field(min_length=3, max_length=320)
    subject: str | None = None
    message: str = Field(min_length=5)
    mismatch_fields: list[str] = Field(default_factory=list)


class NotificationOut(BaseModel):
    id: str
    case_id: str
    recipient: str
    channel: str
    subject: str | None = None
    message: str
    mismatch_fields: list[str] = Field(default_factory=list)
    status: str
    trigger_type: str
    created_at: datetime
    provider_info: dict | None = None

    @classmethod
    def from_model(cls, n) -> "NotificationOut":
        return cls(
            id=n.id,
            case_id=n.case_id,
            recipient=n.recipient,
            channel=n.channel,
            subject=n.subject,
            message=n.message,
            mismatch_fields=n.mismatch_fields or [],
            status=n.status,
            trigger_type=n.trigger_type,
            created_at=n.created_at,
            provider_info=n.provider_info,
        )


class ApplicantContactUpdate(BaseModel):
    applicant_name: str | None = None
    applicant_phone: str | None = None
    applicant_email: str | None = None
    auto_notify_on_mismatch: bool | None = None
