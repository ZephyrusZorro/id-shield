"""Notification endpoints for applicant discrepancy alerts (SMS / WhatsApp / Email)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import Case, CaseNotification
from app.schemas.cases import CaseOut
from app.schemas.notifications import (
    ApplicantContactUpdate,
    NotificationOut,
    NotificationPreviewResponse,
    NotificationSendRequest,
)
from app.services import notification_service

router = APIRouter()


@router.get("/cases/{case_id}/notifications/preview", response_model=NotificationPreviewResponse)
def get_notification_preview(case_id: str, db: Session = Depends(get_db)) -> NotificationPreviewResponse:
    """Generate dynamic discrepancy message templates and mismatch summary."""
    try:
        return notification_service.generate_notification_preview(db, case_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Case not found.")


@router.post("/cases/{case_id}/notifications/send", response_model=NotificationOut, status_code=201)
def send_case_notification(
    case_id: str,
    payload: NotificationSendRequest,
    db: Session = Depends(get_db),
) -> NotificationOut:
    """Send (or simulate) a discrepancy notification directly to the applicant."""
    try:
        notification = notification_service.send_notification(
            db=db,
            case_id=case_id,
            recipient=payload.recipient,
            channel=payload.channel,
            message=payload.message,
            subject=payload.subject,
            mismatch_fields=payload.mismatch_fields,
            trigger_type="manual",
        )
        return NotificationOut.from_model(notification)
    except ValueError:
        raise HTTPException(status_code=404, detail="Case not found.")


@router.get("/cases/{case_id}/notifications", response_model=list[NotificationOut])
def list_case_notifications(case_id: str, db: Session = Depends(get_db)) -> list[NotificationOut]:
    """List all sent discrepancy notices and delivery receipts for this case."""
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")

    notifications = db.scalars(
        select(CaseNotification)
        .where(CaseNotification.case_id == case_id)
        .order_by(CaseNotification.created_at.desc())
    ).all()

    return [NotificationOut.from_model(n) for n in notifications]


@router.patch("/cases/{case_id}/applicant-contact", response_model=CaseOut)
def update_applicant_contact(
    case_id: str,
    payload: ApplicantContactUpdate,
    db: Session = Depends(get_db),
) -> CaseOut:
    """Update applicant contact details or auto-notify preference."""
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")

    if payload.applicant_name is not None:
        case.applicant_name = payload.applicant_name.strip() if payload.applicant_name else None
    if payload.applicant_phone is not None:
        case.applicant_phone = payload.applicant_phone.strip() if payload.applicant_phone else None
    if payload.applicant_email is not None:
        case.applicant_email = payload.applicant_email.strip() if payload.applicant_email else None
    if payload.auto_notify_on_mismatch is not None:
        case.auto_notify_on_mismatch = payload.auto_notify_on_mismatch

    db.commit()
    db.refresh(case)
    return CaseOut.from_model(case)
