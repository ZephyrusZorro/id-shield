"""Tests for applicant discrepancy notifications (SMS / WhatsApp / Email)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base, get_db
from app.db.models import Case, CrossDocumentFinding, Document, ExtractedField
from app.main import app
from app.services import notification_service


@pytest.fixture()
def test_env(tmp_path, monkeypatch):
    """Test environment with SQLite DB and mock upload dir."""
    db_file = tmp_path / "test_notifications.db"
    engine = create_engine(f"sqlite:///{db_file.as_posix()}", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(settings, "upload_dir", tmp_path / "uploads")

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield TestingSession, client
    app.dependency_overrides.clear()


def test_notification_preview_with_discrepancies(test_env):
    SessionMaker, client = test_env
    db = SessionMaker()

    case = Case(
        case_number=1050,
        case_name="Aarav Sharma Onboarding",
        applicant_name="Aarav Sharma",
        applicant_phone="+919876543210",
        applicant_email="aarav.sharma@example.com",
        status="completed",
        overall_risk=75,
    )
    db.add(case)
    db.commit()

    # Add a cross-document finding
    finding = CrossDocumentFinding(
        case_id=case.id,
        field_name="date_of_birth",
        severity="high",
        explanation="Date of birth mismatch: 1990-05-14 (Passport) vs 1992-05-14 (PAN Card)",
        documents_involved=[{"file_name": "Passport.jpg"}, {"file_name": "PAN.jpg"}],
    )
    db.add(finding)
    db.commit()
    case_id = case.id
    db.close()

    resp = client.get(f"/api/cases/{case_id}/notifications/preview")
    assert resp.status_code == 200
    data = resp.json()

    assert data["case_id"] == case.id
    assert data["applicant_name"] == "Aarav Sharma"
    assert data["applicant_phone"] == "+919876543210"
    assert data["has_discrepancies"] is True
    assert len(data["mismatches"]) == 1
    assert data["mismatches"][0]["field_name"] == "date_of_birth"
    assert "Aarav Sharma" in data["sms_preview"]
    assert "Case #1050" in data["whatsapp_preview"]
    assert "Date of birth mismatch" in data["email_preview"]


def test_notification_send_and_history(test_env):
    SessionMaker, client = test_env
    db = SessionMaker()

    case = Case(
        case_number=1051,
        case_name="Priya Patel KYC",
        applicant_name="Priya Patel",
        applicant_phone="+919123456789",
        status="completed",
        overall_risk=60,
    )
    db.add(case)
    db.commit()
    case_id = case.id
    db.close()

    # Send SMS notification
    payload = {
        "channel": "sms",
        "recipient": "+919123456789",
        "message": "Hello Priya, your KYC verification requires attention due to a document mismatch.",
        "mismatch_fields": ["date_of_birth", "full_name"],
    }
    resp = client.post(f"/api/cases/{case_id}/notifications/send", json=payload)
    assert resp.status_code == 201
    send_data = resp.json()
    assert send_data["channel"] == "sms"
    assert send_data["recipient"] == "+919123456789"
    assert send_data["status"] in ("sent", "delivered", "simulated")
    assert send_data["trigger_type"] == "manual"
    assert "provider_info" in send_data

    # List notification history
    hist_resp = client.get(f"/api/cases/{case_id}/notifications")
    assert hist_resp.status_code == 200
    history = hist_resp.json()
    assert len(history) == 1
    assert history[0]["id"] == send_data["id"]
    assert history[0]["recipient"] == "+919123456789"


def test_update_applicant_contact(test_env):
    SessionMaker, client = test_env
    db = SessionMaker()

    case = Case(
        case_number=1052,
        case_name="Test Case Contact Update",
        status="draft",
    )
    db.add(case)
    db.commit()
    case_id = case.id
    db.close()

    # Update applicant info
    patch_resp = client.patch(
        f"/api/cases/{case_id}/applicant-contact",
        json={
            "applicant_name": "Rohan Verma",
            "applicant_phone": "+919988776655",
            "applicant_email": "rohan@example.com",
            "auto_notify_on_mismatch": True,
        },
    )
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["applicant_name"] == "Rohan Verma"
    assert updated["applicant_phone"] == "+919988776655"
    assert updated["applicant_email"] == "rohan@example.com"
    assert updated["auto_notify_on_mismatch"] is True


def test_auto_notification_trigger(test_env):
    SessionMaker, _ = test_env
    db = SessionMaker()

    case = Case(
        case_number=1053,
        case_name="Auto Notify Case",
        applicant_name="Dev Singh",
        applicant_phone="+919876500000",
        auto_notify_on_mismatch=True,
        status="completed",
        overall_risk=65,
    )
    db.add(case)
    db.commit()

    finding = CrossDocumentFinding(
        case_id=case.id,
        field_name="full_name",
        severity="high",
        explanation="Name conflict across IDs: Dev Singh vs Devesh Singh",
        documents_involved=[{"file_name": "ID1.jpg"}, {"file_name": "ID2.jpg"}],
    )
    db.add(finding)
    db.commit()

    # Trigger auto notification
    notif = notification_service.trigger_auto_notification_if_enabled(db, case.id)
    assert notif is not None
    assert notif.trigger_type == "automatic"
    assert notif.recipient == "+919876500000"
    assert "Dev Singh" in notif.message
    db.close()


def test_notification_preview_provider_status_flags(test_env, monkeypatch):
    SessionMaker, client = test_env
    db = SessionMaker()

    case = Case(case_number=1054, case_name="bean", status="completed")
    db.add(case)
    db.commit()
    case_id = case.id
    db.close()

    # Baseline: no provider configured
    monkeypatch.setattr(settings, "smtp_host", None)
    monkeypatch.setattr(settings, "fast2sms_api_key", None)
    monkeypatch.setattr(settings, "twilio_account_sid", None)

    resp = client.get(f"/api/cases/{case_id}/notifications/preview")
    assert resp.status_code == 200
    data = resp.json()
    assert data["applicant_name"] == "Bean"  # capitalized properly
    assert data["email_configured"] is False
    assert data["sms_configured"] is False
    assert data["whatsapp_configured"] is False

    # When SMTP is enabled
    monkeypatch.setattr(settings, "smtp_host", "smtp.gmail.com")
    resp2 = client.get(f"/api/cases/{case_id}/notifications/preview")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["email_configured"] is True


def test_live_email_mocked_smtp(test_env, monkeypatch):
    from unittest.mock import MagicMock

    SessionMaker, client = test_env
    db = SessionMaker()

    case = Case(case_number=1055, case_name="Live Test", status="completed")
    db.add(case)
    db.commit()
    case_id = case.id
    db.close()

    monkeypatch.setattr(settings, "smtp_host", "smtp.gmail.com")
    monkeypatch.setattr(settings, "smtp_port", 587)
    monkeypatch.setattr(settings, "smtp_user", "tester@gmail.com")
    monkeypatch.setattr(settings, "smtp_pass", "secret123")
    monkeypatch.setattr(settings, "smtp_from", "tester@gmail.com")

    # Mock smtplib.SMTP
    mock_smtp_instance = MagicMock()
    mock_smtp_instance.__enter__.return_value = mock_smtp_instance
    monkeypatch.setattr("smtplib.SMTP", lambda host, port, timeout=12: mock_smtp_instance)

    payload = {
        "channel": "email",
        "recipient": "applicant@example.com",
        "subject": "Action Required: Identity Verification",
        "message": "Dear Applicant, please check your document discrepancy.",
    }
    resp = client.post(f"/api/cases/{case_id}/notifications/send", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "delivered"
    assert "SMTP (smtp.gmail.com)" in data["provider_info"]["provider"]
    assert mock_smtp_instance.starttls.called
    assert mock_smtp_instance.login.called
    assert mock_smtp_instance.sendmail.called
