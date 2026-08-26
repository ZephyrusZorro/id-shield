"""Tests for case creation, upload validation, and file serving."""
import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import resolve_within, sanitize_filename, validate_upload
from app.db.base import Base, get_db
from app.db import models  # noqa: F401
from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """App test client backed by a throwaway SQLite DB + upload dir."""
    engine = create_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}", connect_args={"check_same_thread": False})
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


def _png_bytes(size: int = 64) -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (size, size), (30, 60, 120)).save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------- unit tests
def test_validate_upload_rejects_bad_extension():
    with pytest.raises(Exception, match="Unsupported file type"):
        validate_upload("evil.exe", "application/octet-stream", 10, 10 * 1024 * 1024)


def test_validate_upload_rejects_empty_and_oversize():
    with pytest.raises(Exception, match="empty"):
        validate_upload("a.png", "image/png", 0, 10 * 1024 * 1024)
    with pytest.raises(Exception, match="limit"):
        validate_upload("a.png", "image/png", 999_999_999, 10 * 1024 * 1024)


def test_sanitize_filename_strips_paths():
    assert sanitize_filename("..\\..\\etc\\passwd.png") == "passwd.png"
    assert sanitize_filename("my doc (final).pdf") == "my doc _final_.pdf"


def test_resolve_within_blocks_traversal():
    base = Path("C:/base/uploads").resolve()
    with pytest.raises(Exception):
        resolve_within(base, "../../secrets.txt")
    assert resolve_within(base, "case1/file.png").is_relative_to(base)


# ------------------------------------------------------------ API tests
def test_create_case_assigns_incrementing_numbers(client):
    r1 = client.post("/api/cases", json={"case_name": "Case One"})
    r2 = client.post("/api/cases", json={"case_name": "Case Two"})
    assert r1.status_code == 201 and r2.status_code == 201
    n1, n2 = r1.json()["case_number"], r2.json()["case_number"]
    assert n2 == n1 + 1


def test_create_case_validates_name(client):
    assert client.post("/api/cases", json={"case_name": ""}).status_code == 422


def test_upload_documents_roundtrip(client):
    created = client.post("/api/cases", json={"case_name": "Upload Case"}).json()
    files = [
        ("files", ("doc_a.png", io.BytesIO(_png_bytes()), "image/png")),
        ("files", ("notes.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")),
    ]
    r = client.post(f"/api/cases/{created['id']}/documents", files=files)
    assert r.status_code == 201
    body = r.json()
    assert len(body["uploaded"]) == 2 and body["failed"] == []

    listing = client.get(f"/api/cases/{created['id']}").json()
    assert len(listing["documents"]) == 2
    png_doc = next(d for d in listing["documents"] if d["file_name"].endswith(".png"))
    assert png_doc["has_preview"] is True
    pdf_doc = next(d for d in listing["documents"] if d["file_name"].endswith(".pdf"))
    assert pdf_doc["has_preview"] is False


def test_upload_rejects_unsupported_file(client):
    created = client.post("/api/cases", json={"case_name": "Bad File"}).json()
    files = [("files", ("script.exe", io.BytesIO(b"MZ..."), "application/octet-stream"))]
    r = client.post(f"/api/cases/{created['id']}/documents", files=files)
    assert r.status_code == 422
    assert "Unsupported file type" in r.text


def test_document_file_serving(client):
    created = client.post("/api/cases", json={"case_name": "Preview"}).json()
    r = client.post(
        f"/api/cases/{created['id']}/documents",
        files=[("files", ("img.png", io.BytesIO(_png_bytes()), "image/png"))],
    )
    doc_id = r.json()["uploaded"][0]["id"]
    served = client.get(f"/api/documents/{doc_id}/file")
    assert served.status_code == 200
    assert served.headers["content-type"].startswith("image/png")


def test_unknown_document_returns_404(client):
    assert client.get("/api/documents/does-not-exist/file").status_code == 404
    assert client.delete("/api/documents/does-not-exist").status_code == 404


def test_delete_document_removes_file(client):
    created = client.post("/api/cases", json={"case_name": "Delete Me"}).json()
    r = client.post(
        f"/api/cases/{created['id']}/documents",
        files=[("files", ("img.png", io.BytesIO(_png_bytes()), "image/png"))],
    )
    doc_id = r.json()["uploaded"][0]["id"]

    assert client.delete(f"/api/documents/{doc_id}").status_code == 200
    assert client.get(f"/api/documents/{doc_id}/file").status_code == 404
