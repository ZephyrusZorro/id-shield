"""Applicant discrepancy notification service (SMS / WhatsApp / Email / Webhook).

Supports both live providers (Twilio, SMTP) and an offline high-fidelity
simulator that records and audits discrepancy notices when identity mismatches
or risk triggers are detected.
"""
from __future__ import annotations

import os
import smtplib
import uuid
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.db.models import (
    Case,
    CaseNotification,
    CrossDocumentFinding,
    Document,
    ExtractedField,
    ForensicFinding,
    ValidationResult,
)
from app.schemas.notifications import (
    DiscrepancyItem,
    NotificationOut,
    NotificationPreviewResponse,
)
from app.services.consistency_service import _FIELD_LABELS

log = get_logger("idshield.notifications")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_email_configured() -> bool:
    return bool(settings.smtp_host or os.getenv("SMTP_HOST"))


def _is_sms_configured() -> bool:
    return bool(
        settings.fast2sms_api_key
        or os.getenv("FAST2SMS_API_KEY")
        or (
            (settings.twilio_account_sid or os.getenv("TWILIO_ACCOUNT_SID"))
            and (settings.twilio_auth_token or os.getenv("TWILIO_AUTH_TOKEN"))
            and (settings.twilio_from_number or os.getenv("TWILIO_FROM_NUMBER"))
        )
    )


def _is_whatsapp_configured() -> bool:
    return bool(
        (settings.twilio_account_sid or os.getenv("TWILIO_ACCOUNT_SID"))
        and (settings.twilio_auth_token or os.getenv("TWILIO_AUTH_TOKEN"))
        and (settings.twilio_from_number or os.getenv("TWILIO_FROM_NUMBER"))
    )


def get_case_discrepancies(db: Session, case_id: str) -> list[DiscrepancyItem]:
    """Compile all cross-document conflicts, face mismatches, and validation failures."""
    items: list[DiscrepancyItem] = []

    # 1. Cross-document findings (Name, DOB, Address, Face photo, etc.)
    conflicts = db.scalars(
        select(CrossDocumentFinding).where(
            CrossDocumentFinding.case_id == case_id,
            CrossDocumentFinding.severity.in_(["medium", "high"]),
        )
    ).all()

    for c in conflicts:
        label = _FIELD_LABELS.get(c.field_name, c.field_name.replace("_", " ").title())
        docs_involved = [
            d.get("file_name", "Document")
            for d in (c.documents_involved or [])
            if isinstance(d, dict)
        ]
        items.append(
            DiscrepancyItem(
                field_name=c.field_name,
                label=label,
                severity=c.severity,
                explanation=c.explanation or f"Conflict detected in {label} across submitted documents.",
                documents_involved=docs_involved,
            )
        )

    # 2. Validation / MRZ / QR failures
    docs = db.scalars(select(Document).where(Document.case_id == case_id)).all()
    doc_map = {d.id: d.file_name for d in docs}
    if docs:
        val_failures = db.scalars(
            select(ValidationResult).where(
                ValidationResult.document_id.in_([d.id for d in docs]),
                ValidationResult.status == "fail",
            )
        ).all()
        for v in val_failures:
            doc_name = doc_map.get(v.document_id, "Document")
            items.append(
                DiscrepancyItem(
                    field_name=v.check_type.lower().replace(" ", "_"),
                    label=v.check_type,
                    severity="high",
                    explanation=f"{v.message} ({doc_name})",
                    documents_involved=[doc_name],
                )
            )

        # 3. High tampering suspicion regions
        forensics = db.scalars(
            select(ForensicFinding).where(
                ForensicFinding.document_id.in_([d.id for d in docs]),
                ForensicFinding.severity == "high",
            )
        ).all()
        for f in forensics:
            doc_name = doc_map.get(f.document_id, "Document")
            items.append(
                DiscrepancyItem(
                    field_name=f"forensic_{f.region}",
                    label=f"Visual Tampering ({f.region})",
                    severity="high",
                    explanation=f"Localized anomaly detected in {f.region} ({doc_name}): {f.explanation}",
                    documents_involved=[doc_name],
                )
            )

    return items


def _derive_applicant_name(case: Case, db: Session) -> str:
    if case.applicant_name and case.applicant_name.strip():
        return case.applicant_name.strip()
    # Fallback to extracted full_name from any document
    extracted_name = db.scalar(
        select(ExtractedField.raw_value)
        .join(Document, ExtractedField.document_id == Document.id)
        .where(Document.case_id == case.id, ExtractedField.field_name == "full_name")
    )
    if extracted_name and extracted_name.strip():
        return extracted_name.strip().title()
    if case.case_name and case.case_name.strip():
        return case.case_name.strip().title()
    return "Applicant"


def generate_notification_preview(db: Session, case_id: str) -> NotificationPreviewResponse:
    """Generate pre-filled message templates and summary of mismatches for a case."""
    case = db.get(Case, case_id)
    if case is None:
        raise ValueError(f"Case {case_id} not found")

    mismatches = get_case_discrepancies(db, case_id)
    person = _derive_applicant_name(case, db)
    case_num = case.case_number

    mismatch_bullets = (
        "\n".join(f"• {m.label}: {m.explanation}" for m in mismatches)
        if mismatches
        else "• Overall identity evidence requires verification review."
    )

    mismatch_short = (
        ", ".join(m.label for m in mismatches[:3])
        + (f" and {len(mismatches)-3} more" if len(mismatches) > 3 else "")
        if mismatches
        else "verification findings"
    )

    suggested_subject = f"Action Required: Identity Verification Update (Case #{case_num})"

    sms_preview = (
        f"ID-SHIELD: Hello {person}, your identity verification (Case #{case_num}) "
        f"requires attention due to a mismatch in: {mismatch_short}. "
        f"Please check your portal or contact your verification officer to re-submit valid documents."
    )

    whatsapp_preview = (
        f"👋 *Identity Verification Notice*\n\n"
        f"Dear *{person}*,\n"
        f"We have processed your submitted documents for *Case #{case_num}*.\n\n"
        f"⚠️ *The following discrepancy was identified:*\n"
        f"{mismatch_bullets}\n\n"
        f"📌 *Next Steps:*\n"
        f"Please ensure all submitted documents contain matching personal details (matching name, date of birth, and clear face photo). Contact your verification administrator or re-upload your valid identity documents.\n\n"
        f"_ID-SHIELD Verification System_"
    )

    email_preview = (
        f"Dear {person},\n\n"
        f"Thank you for submitting your identity documents for Case #{case_num}.\n\n"
        f"During our automated document integrity and consistency screening, our system identified the following discrepancy that requires your clarification:\n\n"
        f"{mismatch_bullets}\n\n"
        f"Recommended Action:\n"
        f"1. Please review your submitted documents to ensure names, dates of birth, and document numbers are consistent.\n"
        f"2. Ensure original, high-resolution scans without glares or obscured details.\n"
        f"3. Submit replacement documents through your secure onboarding portal.\n\n"
        f"If you believe this notice was sent in error, please reach out to your verification officer.\n\n"
        f"Best regards,\n"
        f"Identity Verification Team\nID-SHIELD Platform"
    )

    return NotificationPreviewResponse(
        case_id=case.id,
        case_number=case.case_number,
        case_name=case.case_name,
        applicant_name=person,
        applicant_phone=case.applicant_phone,
        applicant_email=case.applicant_email,
        mismatches=mismatches,
        has_discrepancies=len(mismatches) > 0 or (case.overall_risk is not None and case.overall_risk >= 30),
        suggested_subject=suggested_subject,
        sms_preview=sms_preview,
        whatsapp_preview=whatsapp_preview,
        email_preview=email_preview,
        email_configured=_is_email_configured(),
        sms_configured=_is_sms_configured(),
        whatsapp_configured=_is_whatsapp_configured(),
    )


def _send_live_sms_twilio(recipient: str, message: str, channel: str) -> dict:
    """Send SMS/WhatsApp via Twilio or Fast2SMS if configured."""
    fast2sms_key = settings.fast2sms_api_key or os.getenv("FAST2SMS_API_KEY")
    clean_digits = "".join(filter(str.isdigit, recipient))
    if len(clean_digits) >= 10:
        ten_digit = clean_digits[-10:]
    else:
        ten_digit = clean_digits

    if fast2sms_key and channel == "sms" and len(ten_digit) == 10:
        try:
            from urllib import request
            import json

            url = "https://www.fast2sms.com/dev/bulkV2"
            payload = json.dumps({
                "route": "q",
                "message": message,
                "language": "english",
                "flash": 0,
                "numbers": ten_digit,
            }).encode("utf-8")

            req = request.Request(url, data=payload, method="POST")
            req.add_header("authorization", fast2sms_key)
            req.add_header("Content-Type", "application/json")

            with request.urlopen(req, timeout=10) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                if res_data.get("return"):
                    return {"mode": "live", "provider": "Fast2SMS", "response": res_data}
                else:
                    log.error("FAST2SMS_API_ERROR | response=%s", res_data)
                    return {
                        "mode": "failed",
                        "provider": "Fast2SMS",
                        "error": f"Fast2SMS returned error: {res_data}",
                        "channel": channel,
                    }
        except Exception as exc:
            log.error("FAST2SMS_SEND_FAILED | err=%s", exc)
            return {
                "mode": "failed",
                "provider": "Fast2SMS",
                "error": str(exc),
                "channel": channel,
            }

    # 2. Twilio support (SMS & WhatsApp)
    account_sid = settings.twilio_account_sid or os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = settings.twilio_auth_token or os.getenv("TWILIO_AUTH_TOKEN")
    from_number = settings.twilio_from_number or os.getenv("TWILIO_FROM_NUMBER")

    if not (account_sid and auth_token and from_number):
        return {
            "mode": "simulated",
            "provider": f"ID-SHIELD Virtual Gateway ({channel.upper()} Simulation)",
            "gateway_message_id": f"sim-tw-{uuid.uuid4().hex[:12]}",
            "delivered_at": _now().isoformat(),
            "channel": channel,
            "note": f"Running in Simulation Mode. To send real {channel.upper()}, configure TWILIO credentials or FAST2SMS_API_KEY in .env",
        }

    try:
        from urllib import parse, request
        import base64

        to_num = recipient if channel == "sms" else f"whatsapp:{recipient}"
        from_num = from_number if channel == "sms" else f"whatsapp:{from_number}"

        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        data = parse.urlencode({"To": to_num, "From": from_num, "Body": message}).encode("utf-8")
        req = request.Request(url, data=data, method="POST")
        auth_header = base64.b64encode(f"{account_sid}:{auth_token}".encode("utf-8")).decode("ascii")
        req.add_header("Authorization", f"Basic {auth_header}")

        with request.urlopen(req, timeout=10) as resp:
            return {"mode": "live", "provider": "Twilio", "status_code": resp.status}
    except Exception as exc:
        log.error("TWILIO_SEND_FAILED | recipient=%s err=%s", recipient, exc)
        return {
            "mode": "failed",
            "provider": "Twilio",
            "error": f"Twilio {channel.upper()} delivery failed to {recipient}: {exc}",
            "channel": channel,
        }


def _send_live_email(recipient: str, subject: str, body: str) -> dict:
    """Send email via SMTP if configured, otherwise return simulation receipt."""
    smtp_host = settings.smtp_host or os.getenv("SMTP_HOST")
    smtp_port = settings.smtp_port or int(os.getenv("SMTP_PORT", "587"))
    smtp_user = settings.smtp_user or os.getenv("SMTP_USER")
    smtp_pass = settings.smtp_pass or os.getenv("SMTP_PASS")
    from_addr = settings.smtp_from or os.getenv("SMTP_FROM", smtp_user or "notifications@idshield.local")

    if not smtp_host:
        return {
            "mode": "simulated",
            "provider": "ID-SHIELD Virtual SMTP Gateway (Simulation Mode)",
            "gateway_message_id": f"sim-mail-{uuid.uuid4().hex[:12]}",
            "delivered_at": _now().isoformat(),
            "channel": "email",
            "note": "Running in Simulation Mode. To send real emails to inboxes, set SMTP_HOST, SMTP_USER, and SMTP_PASS in .env",
        }

    try:
        msg = MIMEMultipart()
        msg["From"] = from_addr
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=12) as server:
            server.starttls()
            if smtp_user and smtp_pass:
                clean_pass = smtp_pass.replace(" ", "").strip() if "gmail" in smtp_host.lower() else smtp_pass.strip()
                server.login(smtp_user.strip(), clean_pass)
            server.sendmail(from_addr.strip(), [recipient.strip()], msg.as_string())

        return {"mode": "live", "provider": f"SMTP ({smtp_host})", "delivered_to": recipient}
    except Exception as exc:
        log.error("SMTP_SEND_FAILED | host=%s recipient=%s err=%s", smtp_host, recipient, exc)
        return {
            "mode": "failed",
            "provider": f"SMTP ({smtp_host})",
            "error": str(exc),
            "channel": "email",
            "note": f"SMTP delivery failed to {recipient} via {smtp_host}:{smtp_port}. Check your SMTP_USER and SMTP_PASS in .env.",
        }


def send_notification(
    db: Session,
    case_id: str,
    recipient: str,
    channel: str,
    message: str,
    subject: str | None = None,
    mismatch_fields: list[str] | None = None,
    trigger_type: str = "manual",
) -> CaseNotification:
    """Dispatch message and record audit entry in database."""
    case = db.get(Case, case_id)
    if case is None:
        raise ValueError(f"Case {case_id} not found")

    channel_norm = channel.lower().strip()
    if channel_norm in ("sms", "whatsapp"):
        provider_res = _send_live_sms_twilio(recipient, message, channel_norm)
    elif channel_norm == "email":
        subj = subject or f"Identity Verification Update (Case #{case.case_number})"
        provider_res = _send_live_email(recipient, subj, message)
    else:  # webhook / other
        provider_res = {
            "mode": "simulated",
            "provider": "ID-SHIELD Webhook Dispatcher",
            "gateway_message_id": f"sim-hook-{uuid.uuid4().hex[:12]}",
            "delivered_at": _now().isoformat(),
        }

    mode = provider_res.get("mode", "simulated")
    if mode == "live":
        status = "delivered"
    elif mode == "failed":
        status = "failed"
    else:
        status = "simulated"

    notification = CaseNotification(
        case_id=case_id,
        recipient=recipient.strip(),
        channel=channel_norm,
        subject=subject.strip() if subject else None,
        message=message.strip(),
        mismatch_fields=mismatch_fields or [],
        status=status,
        trigger_type=trigger_type,
        provider_info=provider_res,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    log.info(
        "DISCREPANCY_NOTIFICATION_%s | case_id=%s recipient=%s channel=%s trigger=%s",
        status.upper(),
        case_id,
        recipient,
        channel_norm,
        trigger_type,
    )
    return notification


def trigger_auto_notification_if_enabled(db: Session, case_id: str) -> CaseNotification | None:
    """Automatic dispatch hook if auto_notify_on_mismatch is enabled on the case."""
    case = db.get(Case, case_id)
    if case is None or not case.auto_notify_on_mismatch:
        return None

    # Check if there are any discrepancies or elevated risk
    discrepancies = get_case_discrepancies(db, case_id)
    high_risk = case.overall_risk is not None and case.overall_risk >= 30

    if not discrepancies and not high_risk:
        return None

    preview = generate_notification_preview(db, case_id)

    # Decide channel: prefer email when SMTP is configured, otherwise fall back to SMS
    email_live = _is_email_configured()
    sms_live = _is_sms_configured()

    if case.applicant_email and email_live:
        channel = "email"
        recipient = case.applicant_email
    elif case.applicant_phone and sms_live:
        channel = "sms"
        recipient = case.applicant_phone
    elif case.applicant_email:
        # Email configured or not, use it as best-effort (will be simulated if not configured)
        channel = "email"
        recipient = case.applicant_email
    elif case.applicant_phone:
        channel = "sms"
        recipient = case.applicant_phone
    else:
        log.info("AUTO_NOTIFY_SKIPPED | case_id=%s - no applicant phone or email available", case_id)
        return None

    message = preview.email_preview if channel == "email" else preview.sms_preview
    subject = preview.suggested_subject if channel == "email" else None
    mismatch_keys = [m.field_name for m in discrepancies]

    return send_notification(
        db=db,
        case_id=case_id,
        recipient=recipient,
        channel=channel,
        message=message,
        subject=subject,
        mismatch_fields=mismatch_keys,
        trigger_type="automatic",
    )
