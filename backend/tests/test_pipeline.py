"""Pipeline integration: analysis runs, records stage status, degrades
gracefully when no OCR engine is available."""
import io
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base, get_db
from app.db import models  # noqa: F401
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
        c.sessionmaker = TestingSession  # type: ignore[attr-defined]
        yield c
    app.dependency_overrides.clear()


def _png_bytes(size: int = 300) -> bytes:
    from PIL import Image, ImageDraw

    buf = io.BytesIO()
    img = Image.new("RGB", (size, int(size * 0.63)), "white")
    d = ImageDraw.Draw(img)
    d.text((30, 200), "Name: TEST PERSON", fill="black")
    img.save(buf, format="PNG")
    return buf.getvalue()


def _create_case_with_doc(client) -> tuple[str, str]:
    case = client.post("/api/cases", json={"case_name": "Pipeline"}).json()
    up = client.post(
        f"/api/cases/{case['id']}/documents",
        files=[("files", ("doc.png", io.BytesIO(_png_bytes()), "image/png"))],
    ).json()
    return case["id"], up["uploaded"][0]["id"]


def test_analyze_without_ocr_marks_unavailable_gracefully(client, monkeypatch):
    """No OCR backend -> pipeline completes with honest 'unavailable' stages."""
    import app.db.base as db_base
    import app.services.pipeline as pipeline
    from app.services.ocr_service import OcrUnavailableError

    def ocr_service_unavailable():
        raise OcrUnavailableError("no engine")

    # The background task builds its own session; point it at the test DB.
    monkeypatch.setattr(db_base, "SessionLocal", client.sessionmaker)
    monkeypatch.setattr(pipeline, "get_backend", ocr_service_unavailable)

    case_id, doc_id = _create_case_with_doc(client)
    r = client.post(f"/api/cases/{case_id}/analyze")
    assert r.status_code == 202

    # The background task may finish after the response; poll briefly.
    detail = {"processing_status": "uploaded"}
    for _ in range(50):
        detail = client.get(f"/api/documents/{doc_id}").json()
        if detail["processing_status"] != "uploaded":
            break
        time.sleep(0.1)
    assert detail["processing_status"] in {"done", "error"}

    analysis = client.get(f"/api/cases/{case_id}/analysis").json()
    assert analysis["case_status"] == "completed"
    statuses = {s["stage_key"]: s["status"] for s in analysis["stages"]}
    assert statuses["ocr"] == "unavailable"
    assert statuses["classify"] == "unavailable"
    assert statuses["fields"] == "unavailable"
    assert statuses["validate"] == "unavailable"
    assert statuses["consistency"] == "unavailable"


def test_analysis_requires_documents(client):
    case = client.post("/api/cases", json={"case_name": "Empty"}).json()
    r = client.post(f"/api/cases/{case['id']}/analyze")
    assert r.status_code == 422


def test_risk_ledger_written_once_for_multi_document_case(client, monkeypatch):
    """Regression: risk evaluation must run once per case, not once per
    document — the ledger must never duplicate factor rows."""
    import time

    import app.db.base as db_base
    from sqlalchemy import select

    from app.db.models import RiskFactor

    monkeypatch.setattr(db_base, "SessionLocal", client.sessionmaker)

    case = client.post("/api/cases", json={"case_name": "MultiDoc Risk"}).json()
    up = client.post(
        f"/api/cases/{case['id']}/documents",
        files=[
            ("files", ("a.png", io.BytesIO(_png_bytes()), "image/png")),
            ("files", ("b.png", io.BytesIO(_png_bytes()), "image/png")),
        ],
    )
    assert up.status_code == 201
    assert len(up.json()["uploaded"]) == 2
    client.post(f"/api/cases/{case['id']}/analyze")

    analysis = {"case_status": "processing"}
    for _ in range(100):
        analysis = client.get(f"/api/cases/{case['id']}/analysis").json()
        if analysis["case_status"] != "processing":
            break
        time.sleep(0.1)
    assert analysis["case_status"] == "completed"

    db = client.sessionmaker()
    try:
        factors = db.scalars(
            select(RiskFactor).where(RiskFactor.case_id == case["id"])
        ).all()
        names = [f.factor for f in factors]
        assert len(names) == len(set(names)), f"duplicated risk factors: {names}"
    finally:
        db.close()


def test_corrupt_file_degrades_gracefully(client, monkeypatch):
    """A corrupt 'png' must not crash the pipeline: stages warn, case still
    completes, and the risk engine honestly reports unable_to_verify."""
    import time

    import app.db.base as db_base

    monkeypatch.setattr(db_base, "SessionLocal", client.sessionmaker)

    case = client.post("/api/cases", json={"case_name": "Corrupt"}).json()
    up = client.post(
        f"/api/cases/{case['id']}/documents",
        files=[("files", ("broken.png", io.BytesIO(b"this is not an image"), "image/png"))],
    )
    assert up.status_code == 201  # extension/MIME pass; content fails later
    client.post(f"/api/cases/{case['id']}/analyze")

    analysis = {"case_status": "processing"}
    for _ in range(100):
        analysis = client.get(f"/api/cases/{case['id']}/analysis").json()
        if analysis["case_status"] != "processing":
            break
        time.sleep(0.1)

    statuses = {s["stage_key"]: s["status"] for s in analysis["stages"]}
    assert statuses["preprocess"] == "warning"
    detail = client.get(f"/api/documents/{up.json()['uploaded'][0]['id']}").json()
    assert detail["fields"] == []

    report = client.get(f"/api/cases/{case['id']}/risk").json()
    assert report["recommendation"] == "unable_to_verify"


def test_document_detail_shape_after_upload(client):
    _, doc_id = _create_case_with_doc(client)
    detail = client.get(f"/api/documents/{doc_id}").json()
    for key in ("id", "file_name", "fields", "processing_status"):
        assert key in detail
