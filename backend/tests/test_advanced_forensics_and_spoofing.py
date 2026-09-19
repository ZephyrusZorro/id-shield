"""Unit & integration tests for Advanced Forensics, Anti-Spoofing, and Review Workflow."""
import io
import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db import models
from app.db.base import Base, get_db
from app.main import app
from app.services import face_service, forensic_service


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


def test_copy_move_detection_on_duplicated_patch():
    """Verify that an image with cloned feature patches is detected by copy-move analysis."""
    img = np.full((600, 800, 3), 240, dtype=np.uint8)
    # Draw textured patch
    import cv2
    cv2.circle(img, (180, 200), 30, (30, 80, 190), -1)
    cv2.rectangle(img, (160, 180), (200, 220), (255, 255, 255), 2)
    cv2.putText(img, "OFFICIAL", (140, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

    # Clone exact patch to (500, 200) - shift dx = 320, dy = 0
    patch = img[150:270, 130:230].copy()
    img[150:270, 450:550] = patch

    findings = forensic_service.analyze_image(img, "national_id")
    cm_findings = [f for f in findings if f.finding_type == "copy_move_anomaly"]
    assert len(cm_findings) >= 1
    assert "duplicated visual features" in cm_findings[0].explanation


def test_metadata_tamper_detection(tmp_path):
    """Verify that images with photo editing software traces are flagged."""
    test_file = tmp_path / "edited_doc.png"
    # Write a PNG with embedded Photoshop text
    fake_header = b"\x89PNG\r\n\x1a\n" + b"x" * 100 + b"Adobe Photoshop CC 2024" + b"x" * 500
    test_file.write_bytes(fake_header)

    img = np.full((400, 600, 3), 255, dtype=np.uint8)
    findings = forensic_service.analyze_image(img, "national_id", file_path=test_file)
    meta_findings = [f for f in findings if f.finding_type == "metadata_tamper_indicator"]
    assert len(meta_findings) == 1
    assert meta_findings[0].severity == "high"
    assert "Photoshop" in meta_findings[0].explanation


def test_anti_spoofing_detects_screen_grid_moire():
    """Verify that a high-frequency grid pattern triggers screen replay detection."""
    # Synthetic moiré pattern (subpixel high-frequency sinusoidal raster)
    x = np.linspace(0, 160, 160)
    y = np.linspace(0, 160, 160)
    X, Y = np.meshgrid(x, y)
    # High frequency grid: frequency = 25 cycles across image
    screen_raster = np.sin(X * 1.5) * np.sin(Y * 1.5)
    screen_img = ((screen_raster + 1.0) * 120).astype(np.uint8)
    screen_bgr = np.stack([screen_img, screen_img, screen_img], axis=-1)

    eval_result = face_service._evaluate_anti_spoofing(screen_bgr, sharpness=80.0, contrast=50.0)
    assert eval_result["moire_intensity"] >= 4.0
    assert eval_result["status"] in ("potential_screen_replay", "screen_or_glossy_replay")
    assert eval_result["risk_score"] >= 60


def test_anti_spoofing_genuine_clean_portrait():
    """Verify that a natural optical portrait is classified as genuine."""
    # Smooth natural portrait gradient
    rng = np.random.default_rng(42)
    natural_img = np.full((160, 160, 3), 180, dtype=np.uint8)
    # Add natural soft gradients and subtle camera noise
    noise = rng.normal(0, 3, (160, 160, 3)).astype(np.int16)
    natural_img = np.clip(natural_img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    eval_result = face_service._evaluate_anti_spoofing(natural_img, sharpness=75.0, contrast=45.0)
    assert eval_result["status"] == "genuine_photo"
    assert eval_result["risk_score"] <= 20


def test_case_review_disposition_api(client):
    """Verify that officers can officially record and update review decisions."""
    db = client.sessionmaker()
    case = models.Case(
        case_number=9050,
        case_name="Review Test Case",
        status="completed",
        review_status="pending_review",
    )
    db.add(case)
    db.commit()
    case_id = case.id
    db.close()

    # 1. Submit approval
    review_payload = {
        "decision": "approved",
        "notes": "All identity checks passed. Photo matches DL and PAN.",
        "reviewer_name": "Compliance Officer A. Verma",
    }
    r = client.post(f"/api/cases/{case_id}/review", json=review_payload)
    assert r.status_code == 200
    data = r.json()
    assert data["review_status"] == "approved"
    assert data["reviewer_name"] == "Compliance Officer A. Verma"
    assert data["reviewer_notes"] == "All identity checks passed. Photo matches DL and PAN."
    assert data["reviewed_at"] is not None

    # 2. Reject decision update
    reject_payload = {
        "decision": "rejected",
        "notes": "Discovered duplicate identity hash in blacklist database.",
        "reviewer_name": "Fraud Lead K. Nair",
    }
    r = client.post(f"/api/cases/{case_id}/review", json=reject_payload)
    assert r.status_code == 200
    data = r.json()
    assert data["review_status"] == "rejected"
    assert data["reviewer_name"] == "Fraud Lead K. Nair"

    # 3. Invalid decision returns 422
    r = client.post(f"/api/cases/{case_id}/review", json={"decision": "invalid_disposition"})
    assert r.status_code == 422
