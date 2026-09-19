"""Tests for Document Classification Stage & Preprocessing Pipeline Upgrade.

Validates:
- Aadhaar, PAN, Driving Licence, Passport, Voter ID, and Unknown classification
- Robust multi-stage preprocessing (resizing, grayscale, deskew, denoising, CLAHE, sharpening, normalization)
- Immutability of original document file
- User manual document type correction endpoint (PATCH /documents/{doc_id}/type)
- Preservation of manual classification during pipeline execution
"""
import io
import hashlib
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base, get_db
from app.db.models import Case, Document
from app.main import app
from app.services import classifier_service, preprocessing_service
from app.services.pipeline import analyze_case


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'test_v2.db').as_posix()}",
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
        c.sessionmaker = TestingSession  # type: ignore[attr-defined]
        yield c
    app.dependency_overrides.clear()


# ------------------------------------------------------------- Classification
def test_classify_aadhaar_card():
    text = "GOVERNMENT OF INDIA UNIQUE IDENTIFICATION AUTHORITY OF INDIA MERA AADHAAR 5489 1234 5678 DOB: 1990-01-01"
    doc_type, label, conf = classifier_service.classify_document(text, aspect_ratio=1.58)
    assert doc_type == "aadhaar"
    assert "Aadhaar" in label
    assert conf > 0.4


def test_classify_pan_card():
    text = "INCOME TAX DEPARTMENT GOVT. OF INDIA PERMANENT ACCOUNT NUMBER ABCDE1234F FATHER'S NAME RAHUL VERMA"
    doc_type, label, conf = classifier_service.classify_document(text, aspect_ratio=1.58)
    assert doc_type == "pan"
    assert "PAN" in label
    assert conf > 0.4


def test_classify_driving_licence():
    text = "UNION OF INDIA DRIVING LICENCE TRANSPORT DEPARTMENT AUTHORISED TO DRIVE LMV DL NO: DL-0420110012345"
    doc_type, label, conf = classifier_service.classify_document(text, aspect_ratio=1.58)
    assert doc_type == "driving_licence"
    assert "Driving Licence" in label
    assert conf > 0.4


def test_classify_voter_id():
    text = "ELECTION COMMISSION OF INDIA ELECTORAL PHOTO IDENTITY CARD ELECTOR NAME ANITA SHARMA EPIC NO: WBS1234567"
    doc_type, label, conf = classifier_service.classify_document(text, aspect_ratio=1.58)
    assert doc_type == "voter_id"
    assert "Voter ID" in label
    assert conf > 0.4


def test_classify_passport():
    text = "PASSPORT REPUBLIC OF INDIA P<INDKUMAR<<ANIL<<<<<<<<<<<<<<<<<<< TYPE P"
    doc_type, label, conf = classifier_service.classify_document(text, aspect_ratio=1.42)
    assert doc_type == "passport"
    assert "Passport" in label
    assert conf > 0.4


def test_classify_uncertain_maps_to_unknown_when_configured():
    text = "just some grocery items milk bread eggs butter"
    doc_type, label, conf = classifier_service.classify_document(
        text, default_uncertain="unknown"
    )
    assert doc_type == "unknown"
    assert label == classifier_service.UNKNOWN_LABEL


# ------------------------------------------------------------ Preprocessing
def test_preprocessing_pipeline_all_stages_and_immutability(tmp_path):
    orig_path = tmp_path / "original_id.png"
    out_path = tmp_path / "derivative_preprocessed.png"

    # Create a synthetic 1200x800 test image with some texture
    img_data = np.full((800, 1200, 3), 200, dtype=np.uint8)
    # Add text-like dark lines
    img_data[200:220, 200:800] = 30
    img_data[300:320, 200:600] = 30
    img_data[400:420, 200:700] = 30

    import cv2
    cv2.imwrite(str(orig_path), img_data)
    orig_hash_before = hashlib.sha256(orig_path.read_bytes()).hexdigest()

    meta = preprocessing_service.preprocess(
        img_data,
        out_path,
        apply_denoise=True,
        apply_clahe=True,
        apply_sharpen=True,
        apply_orientation=True,
    )

    # 1. Output derivative file exists
    assert out_path.is_file()
    # 2. Original file was completely unmodified
    orig_hash_after = hashlib.sha256(orig_path.read_bytes()).hexdigest()
    assert orig_hash_before == orig_hash_after

    # 3. Telemetry reports all executed stages
    assert meta["denoised"] is True
    assert meta["contrast_enhanced"] is True
    assert meta["sharpened"] is True
    assert any("grayscale" in s for s in meta["steps"])
    assert any("dynamic range" in s for s in meta["steps"])
    assert any("denoising" in s for s in meta["steps"])
    assert any("CLAHE" in s for s in meta["steps"])
    assert any("sharpening" in s for s in meta["steps"])


# ---------------------------------------------------- User Correction & API
def _create_sample_case(client) -> tuple[str, str]:
    from PIL import Image

    buf = io.BytesIO()
    img = Image.new("RGB", (200, 120), "white")
    img.save(buf, format="PNG")

    case = client.post("/api/cases", json={"case_name": "Test Classification"}).json()
    up = client.post(
        f"/api/cases/{case['id']}/documents",
        files=[("files", ("test_doc.png", io.BytesIO(buf.getvalue()), "image/png"))],
    ).json()
    return case["id"], up["uploaded"][0]["id"]


def test_user_can_manually_correct_document_type(client):
    case_id, doc_id = _create_sample_case(client)

    # PATCH document type to aadhaar
    patch_res = client.patch(
        f"/api/documents/{doc_id}/type",
        json={"document_type": "aadhaar"},
    )
    assert patch_res.status_code == 200
    data = patch_res.json()
    assert data["document_type"] == "aadhaar"
    assert data["type_confidence"] == 1.0
    assert data["document_type_label"] == "Aadhaar Card"

    # Also check case-scoped endpoint
    patch_res2 = client.patch(
        f"/api/cases/{case_id}/documents/{doc_id}/type",
        json={"document_type": "driving_licence"},
    )
    assert patch_res2.status_code == 200
    data2 = patch_res2.json()
    assert data2["document_type"] == "driving_licence"
    assert data2["type_confidence"] == 1.0
    assert data2["document_type_label"] == "Driving Licence"


def test_pipeline_preserves_user_corrected_document_type(client, monkeypatch):
    import app.db.base as db_base
    import app.services.pipeline as pipeline
    from app.services.ocr_service import Line, OcrResult

    monkeypatch.setattr(db_base, "SessionLocal", client.sessionmaker)

    case_id, doc_id = _create_sample_case(client)

    # User manually specifies it as voter_id
    client.patch(
        f"/api/documents/{doc_id}/type",
        json={"document_type": "voter_id"},
    )

    # Fake OCR backend so pipeline runs successfully without external tesseract
    class FakeBackend:
        engine = "mock"
        def run(self, img):
            return OcrResult(
                lines=[Line(text="Some random text", confidence=90.0, bbox=(0, 0, 10, 10), words=[])],
                engine="mock",
                mean_confidence=90.0,
                full_text="Some random text",
            )

    monkeypatch.setattr(pipeline, "get_backend", lambda: FakeBackend())

    # Run analysis synchronously
    pipeline.analyze_case(case_id)

    # Inspect document record
    doc_detail = client.get(f"/api/documents/{doc_id}").json()
    # The document type must NOT be overwritten by the classifier!
    assert doc_detail["document_type"] == "voter_id"
    assert doc_detail["type_confidence"] == 1.0
