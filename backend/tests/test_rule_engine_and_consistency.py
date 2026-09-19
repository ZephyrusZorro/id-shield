"""Tests for Custom Verification Rules, Chronological Logic, and Fuzzy Name Matching."""
import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base, get_db
from app.main import app
from app.services import rule_engine


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'test_rules.db').as_posix()}",
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
        yield c
    app.dependency_overrides.clear()


# ----------------------------------------------------------- Rule Unit Tests
def test_age_eligibility_detects_underage_license_issuance():
    docs = [
        {
            "file_name": "passport.png",
            "document_type": "passport",
            "fields": {"date_of_birth": "2006-05-10"},
        },
        {
            "file_name": "license.png",
            "document_type": "driving_licence",
            "fields": {"issue_date": "2016-01-15"},  # Age 9 at issuance!
        },
    ]
    res = rule_engine.evaluate_age_eligibility(docs)
    assert res.status == "fail"
    assert res.severity == "high"
    assert "9 years old" in res.explanation


def test_age_eligibility_passes_for_adult_issuance():
    docs = [
        {
            "file_name": "passport.png",
            "document_type": "passport",
            "fields": {"date_of_birth": "1995-05-10"},
        },
        {
            "file_name": "license.png",
            "document_type": "driving_licence",
            "fields": {"issue_date": "2018-06-20"},  # Age 23
        },
    ]
    res = rule_engine.evaluate_age_eligibility(docs)
    assert res.status == "pass"


def test_date_logic_detects_inverted_expiration():
    docs = [
        {
            "file_name": "id.png",
            "document_type": "national_id",
            "fields": {
                "issue_date": "2024-01-01",
                "expiry_date": "2020-01-01",  # Expiration before issue!
            },
        }
    ]
    res = rule_engine.evaluate_date_logic(docs)
    assert res.status == "fail"
    assert "precedes" in res.explanation


def test_pan_surname_consistency_detects_mismatch():
    docs = [
        {
            "file_name": "pan.png",
            "document_type": "pan",
            "fields": {
                "document_number": "ABCPE1234F",  # 5th char is 'E'
                "full_name": "RAHUL SHARMA",     # Surname initial is 'S' != 'E'
            },
        }
    ]
    res = rule_engine.evaluate_pan_surname_consistency(docs)
    assert res.status == "fail"
    assert res.severity == "high"
    assert "expected initial 'E'" in res.explanation


def test_pan_surname_consistency_passes_matching_initial():
    docs = [
        {
            "file_name": "pan.png",
            "document_type": "pan",
            "fields": {
                "document_number": "ABCPV1234F",  # 5th char is 'V'
                "full_name": "RAHUL VERMA",      # Surname initial is 'V' == 'V'
            },
        }
    ]
    res = rule_engine.evaluate_pan_surname_consistency(docs)
    assert res.status == "pass"


def test_father_name_consistency_detects_discrepancy():
    docs = [
        {
            "file_name": "pan.png",
            "document_type": "pan",
            "fields": {"father_name": "RAMESH CHANDRA SHARMA"},
        },
        {
            "file_name": "dl.png",
            "document_type": "driving_licence",
            "fields": {"father_name": "SURESH KUMAR VERMA"},
        },
    ]
    res = rule_engine.evaluate_father_name_consistency(docs)
    assert res.status == "fail"
    assert res.severity == "high"


def test_string_similarity_and_matrix():
    # Exact match
    assert rule_engine.compute_string_similarity("Rahul Sharma", "Rahul Sharma") == 1.0
    # Inverted word order
    assert rule_engine.compute_string_similarity("Rahul Sharma", "Sharma Rahul") == 1.0
    # Minor transliteration
    sim = rule_engine.compute_string_similarity("Mohammad Ali", "Mohamed Ali")
    assert sim >= 0.85
    # Conflicting names
    assert rule_engine.compute_string_similarity("Rahul Sharma", "Vikram Singh") < 0.5



# ---------------------------------------------------- Comparison API Integration
def test_comparison_api_returns_rules_and_similarity(client):
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (100, 100), "white").save(buf, format="PNG")

    case = client.post("/api/cases", json={"case_name": "Rules Case"}).json()
    client.post(
        f"/api/cases/{case['id']}/documents",
        files=[("files", ("doc1.png", io.BytesIO(buf.getvalue()), "image/png"))],
    )

    res = client.get(f"/api/cases/{case['id']}/comparison")
    assert res.status_code == 200
    data = res.json()
    assert "rules_evaluated" in data
    assert len(data["rules_evaluated"]) >= 4
