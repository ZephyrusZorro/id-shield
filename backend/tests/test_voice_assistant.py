"""Tests for the Voice Briefing & Oral Accessibility API."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db import models
from app.db.base import Base, get_db
from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
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
    with TestClient(app) as c:
        c.sessionmaker = TestingSession
        yield c
    app.dependency_overrides.clear()


def test_voice_brief_clean_case(client):
    """Test voice briefing generation for a clean case."""
    db = client.sessionmaker()
    case = models.Case(
        case_number=7701,
        case_name="Voice Test Clean",
        applicant_name="Sunita Devi",
        status="completed",
        recommendation="verification_passed",
    )
    db.add(case)
    db.flush()

    doc1 = models.Document(
        case_id=case.id,
        file_name="aadhaar.png",
        stored_name="aadhaar.png",
        original_path="aadhaar.png",
        document_type="aadhaar",
    )
    doc2 = models.Document(
        case_id=case.id,
        file_name="pan.png",
        stored_name="pan.png",
        original_path="pan.png",
        document_type="pan",
    )
    db.add_all([doc1, doc2])
    db.commit()
    case_id = case.id
    db.close()

    r = client.get(f"/api/cases/{case_id}/voice-brief")
    assert r.status_code == 200
    data = r.json()
    assert data["case_number"] == 7701
    assert data["applicant_name"] == "Sunita Devi"
    assert "Sunita Devi" in data["spoken_text"]
    assert "Aadhaar Card" in data["spoken_text"]
    assert "PAN Card" in data["spoken_text"]
    assert "Good news" in data["spoken_text"]
    assert not data["has_warnings"]


def test_voice_brief_with_conflicts_and_tampering(client):
    """Test voice briefing warns user gently when conflicts or forensics are flagged."""
    db = client.sessionmaker()
    case = models.Case(
        case_number=7702,
        case_name="Voice Test Mismatch",
        applicant_name="Amit Patel",
        status="completed",
        recommendation="manual_review_required",
    )
    db.add(case)
    db.flush()

    doc = models.Document(
        case_id=case.id,
        file_name="doc.png",
        stored_name="doc.png",
        original_path="doc.png",
        document_type="driving_licence",
    )
    db.add(doc)
    db.flush()

    conflict = models.CrossDocumentFinding(
        case_id=case.id,
        field_name="date_of_birth",
        severity="high",
        explanation="DOB mismatch",
    )
    forensic = models.ForensicFinding(
        document_id=doc.id,
        region="photo zone",
        finding_type="copy_move_anomaly",
        severity="high",
        score=0.8,
        bbox=[10, 10, 50, 50],
        explanation="Cloned patch",
    )
    db.add_all([conflict, forensic])
    db.commit()
    case_id = case.id
    db.close()

    r = client.get(f"/api/cases/{case_id}/voice-brief")
    assert r.status_code == 200
    data = r.json()
    assert data["has_warnings"] is True
    assert "discrepancy in date of birth" in data["spoken_text"]
    assert "security checks detected visual anomalies" in data["spoken_text"]
    assert "manual review is recommended" in data["spoken_text"]


def test_voice_query_case_questions(client):
    """Test natural language questions about fraud, applicant identity, and risk."""
    db = client.sessionmaker()
    case = models.Case(
        case_number=8801,
        case_name="Deepak Case",
        applicant_name="Deepak Sharma",
        status="completed",
        recommendation="verification_passed",
        overall_risk=12,
    )
    db.add(case)
    db.flush()

    doc = models.Document(
        case_id=case.id,
        file_name="pan_card.jpg",
        stored_name="pan_card.jpg",
        original_path="pan_card.jpg",
        document_type="pan",
    )
    db.add(doc)
    db.flush()

    field = models.ExtractedField(
        document_id=doc.id,
        field_name="full_name",
        raw_value="Deepak Sharma",
        normalized_value="Deepak Sharma",
    )
    db.add(field)
    db.commit()
    case_id = case.id
    db.close()

    # Query 1: Who is the applicant?
    r1 = client.post(
        f"/api/cases/{case_id}/voice-query",
        json={"query": "Who is the applicant for this verification?"},
    )
    assert r1.status_code == 200
    d1 = r1.json()
    assert "Deepak Sharma" in d1["answer"]
    assert d1["category"] == "identity"

    # Query 2: Is this document fake or tampered?
    r2 = client.post(
        f"/api/cases/{case_id}/voice-query",
        json={"query": "Is this document fake or altered?"},
    )
    assert r2.status_code == 200
    d2 = r2.json()
    assert "Good news" in d2["answer"]
    assert "authentic" in d2["answer"]

    # Query 3: What is the risk score?
    r3 = client.post(
        f"/api/cases/{case_id}/voice-query",
        json={"query": "What is the risk score and is it safe?"},
    )
    assert r3.status_code == 200
    d3 = r3.json()
    assert "12 out of 100" in d3["answer"]
    assert "low risk" in d3["answer"]


def test_voice_query_system_navigation(client):
    """Test general system queries and navigation commands."""
    r = client.post(
        "/api/voice-query",
        json={"query": "take me to the dashboard", "current_path": "/history"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["action"] == "navigate:/dashboard"
    assert "dashboard" in data["answer"].lower()

