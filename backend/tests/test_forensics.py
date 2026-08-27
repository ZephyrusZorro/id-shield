"""Forensic analysis tests — detection, false-positive resistance, API."""
import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base, get_db
from app.db import models  # noqa: F401
from app.main import app
from app.services import forensic_service


def _doc_image() -> np.ndarray:
    """Neutral document-like image: white background + gray text rows."""
    img = np.full((630, 1000, 3), 255, dtype=np.uint8)
    for y in range(150, 500, 64):
        img[y : y + 20, 60:660] = (40, 40, 40)
        img[y + 30 : y + 34, 320:660] = (128, 128, 128)
    return img


def _paste_noise_patch(img: np.ndarray, bbox, seed: int = 7) -> None:
    x, y, w, h = bbox
    rng = np.random.default_rng(seed)
    patch = img[y : y + h, x : x + w].astype(np.int16)
    patch = np.clip(patch + rng.normal(0, 12, patch.shape).astype(np.int16), 0, 255)
    img[y : y + h, x : x + w] = patch.astype(np.uint8)


# ------------------------------------------------------------------ service
def test_clean_document_has_no_findings():
    drafts = forensic_service.analyze_image(_doc_image(), "national_id")
    assert drafts == []


def test_tampered_region_detected_with_overlapping_bbox():
    img = _doc_image()
    bbox = (315, 268, 352, 62)
    _paste_noise_patch(img, bbox)

    drafts = forensic_service.analyze_image(img, "national_id")
    assert len(drafts) >= 1

    # The top finding must overlap the manipulated strip.
    px, py, pw, ph = drafts[0].bbox
    bx, by, bw, bh = bbox
    ix = max(0, min(px + pw, bx + bw) - max(px, bx))
    iy = max(0, min(py + ph, by + bh) - max(py, by))
    assert ix > 0 and iy > 0, f"bbox {drafts[0].bbox} does not overlap {bbox}"
    assert drafts[0].severity in ("medium", "high")
    assert "not proof" in drafts[0].explanation


def test_structural_zone_findings_capped_low():
    img = np.full((630, 1000, 3), 255, dtype=np.uint8)
    # QR zone for national_id starts at (0.66, 0.62) -> (660, 390).
    _paste_noise_patch(img, (700, 430, 180, 130))

    drafts = forensic_service.analyze_image(img, "national_id")
    assert drafts, "expected a finding inside the QR zone"
    assert all(d.region == "QR zone" for d in drafts)
    assert all(d.score <= 0.25 for d in drafts)
    assert all(d.severity == "low" for d in drafts)


def test_small_images_skipped():
    assert forensic_service.analyze_image(np.full((80, 80, 3), 255, dtype=np.uint8)) == []


def test_overall_suspicion_bands():
    assert forensic_service.overall_suspicion([]) == ("low", 0)
    assert forensic_service.overall_suspicion([0.4]) == ("medium", 40)
    assert forensic_service.overall_suspicion([0.2, 0.9]) == ("high", 90)


# --------------------------------------------------------------------- API
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
        c.sessionmaker = TestingSession  # type: ignore[attr-defined]
        yield c
    app.dependency_overrides.clear()


def test_forensics_endpoint_shape(client):
    db = client.sessionmaker()
    case = models.Case(case_number=9001, case_name="F", status="completed")
    db.add(case)
    db.flush()
    doc = models.Document(
        case_id=case.id,
        file_name="x.png",
        stored_name="x.png",
        original_path="x.png",
        processing_status="done",
    )
    db.add(doc)
    db.flush()
    db.add(
        models.ForensicFinding(
            document_id=doc.id,
            region="text band",
            finding_type="chromatic_noise_anomaly",
            severity="medium",
            score=0.5,
            bbox=[10, 10, 50, 50],
            explanation="test indicator",
        )
    )
    db.commit()
    case_id, doc_id = case.id, doc.id
    db.close()

    r = client.get(f"/api/cases/{case_id}/forensics")
    assert r.status_code == 200
    body = r.json()
    assert "disclaimer" in body and "indicator" in body["disclaimer"]
    rep = body["documents"][0]
    assert rep["document_id"] == doc_id
    assert rep["overall_suspicion"] == "medium"
    assert rep["suspicion_score"] == 50
    assert rep["findings"][0]["bbox"] == [10, 10, 50, 50]
