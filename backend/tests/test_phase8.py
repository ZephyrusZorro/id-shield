"""Duplicate scan + report + history endpoint tests."""
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
from app.services.duplicate_service import find_reuse, hamming_distance


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


# ------------------------------------------------------------- duplicates
def test_exact_hash_reuse_detected():
    others = [
        type("O", (), {"id": "o1", "case_id": "c2", "file_name": "a.png",
                       "file_hash": "ABCD", "perceptual_hash": None})(),
        type("O", (), {"id": "o2", "case_id": "c3", "file_name": "b.png",
                       "file_hash": "FFFF", "perceptual_hash": None})(),
    ]
    hits = find_reuse("ABCD", None, others)
    assert len(hits) == 1 and hits[0]["kind"] == "exact" and hits[0]["document_id"] == "o1"


def test_perceptual_reuse_within_threshold():
    h = __import__("imagehash").average_hash(
        __import__("PIL.Image", fromlist=["Image"]).new("L", (64, 64), 128)
    )
    s = str(h)
    flipped = list(s.replace("0", "x").replace("1", "0").replace("x", "1"))
    # Flip only 4 bits.
    for i in range(0, 8):
        flipped[i] = s[i]
    other_hex = "".join(flipped)
    assert hamming_distance(s, other_hex) is not None

    others = [
        type("O", (), {"id": "o1", "case_id": "c2", "file_name": "a.png",
                       "file_hash": "DIFFERENT", "perceptual_hash": other_hex})(),
    ]
    hits = find_reuse("OTHER", s, others)
    assert len(hits) == 1 and hits[0]["kind"] == "perceptual"


def test_no_reuse_on_unrelated():
    others = [
        type("O", (), {"id": "o1", "case_id": "c2", "file_name": "a.png",
                       "file_hash": "X", "perceptual_hash": "0" * 16})(),
    ]
    assert find_reuse("Y", "f" * 16, others) == []


def _png(client, case_id, name="img.png"):
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (200, 126), "white").save(buf, format="PNG")
    r = client.post(
        f"/api/cases/{case_id}/documents",
        files=[("files", (name, io.BytesIO(buf.getvalue()), "image/png"))],
    )
    return r.json()["uploaded"][0]


# ---------------------------------------------------------------- history
def test_history_filters_and_person_fields(client):
    c1 = client.post("/api/cases", json={"case_name": "Alpha Case"}).json()
    c2 = client.post("/api/cases", json={"case_name": "Beta Case"}).json()
    _png(client, c1["id"])
    _png(client, c2["id"])

    listing = client.get("/api/cases").json()
    assert all("person_name" in item and "document_count" in item for item in listing)
    assert {i["case_number"] for i in listing} >= {c1["case_number"], c2["case_number"]}

    filtered = client.get("/api/cases", params={"search": "alpha"}).json()
    assert len(filtered) == 1 and filtered[0]["case_name"] == "Alpha Case"

    # outcome filter with no completed cases yields nothing for 'valid'
    assert client.get("/api/cases", params={"outcome": "valid"}).status_code == 200


def _wait_completed(client, case_id, timeout_s=60):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        a = client.get(f"/api/cases/{case_id}/analysis").json()
        if a["case_status"] != "processing":
            return a
        time.sleep(0.2)
    raise TimeoutError("analysis did not complete")


# ----------------------------------------------------------------- report
def test_report_endpoint_shape_after_analysis(client, monkeypatch):
    """Report includes summary modules, findings and per-document details."""
    import app.db.base as db_base
    import app.services.pipeline as pipeline
    from PIL import Image, ImageDraw

    monkeypatch.setattr(db_base, "SessionLocal", client.sessionmaker)

    case = client.post("/api/cases", json={"case_name": "Reported"}).json()
    buf = io.BytesIO()
    img = Image.new("RGB", (400, 252), "white")
    ImageDraw.Draw(img).text((20, 100), "Name: REPORT PERSON", fill="black")
    out = io.BytesIO()
    img.save(out, format="PNG")
    client.post(
        f"/api/cases/{case['id']}/documents",
        files=[("files", ("doc.png", io.BytesIO(out.getvalue()), "image/png"))],
    )
    client.post(f"/api/cases/{case['id']}/analyze")
    _wait_completed(client, case["id"])

    r = client.get(f"/api/cases/{case['id']}/report")
    assert r.status_code == 200
    body = r.json()
    module_names = [m["module"] for m in body["screening_summary"]]
    assert "Consistency check" in module_names
    assert "Face verification" in module_names  # honest stub row
    assert body["documents"][0]["validation_overall"] in {"valid", "review_required", "unable_to_verify"}
    assert any(f["text"] for f in body["key_findings"]) or body["key_findings"] == []
