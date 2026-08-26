"""Document upload service — safe storage, hashing, DB records."""
import hashlib
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger, log_stage
from app.core.security import (
    UploadValidationError,
    sanitize_filename,
    validate_upload,
)
from app.db.models import Case, Document

log = get_logger("idshield.upload")

_CHUNK = 1024 * 1024


def _store_file(case_dir: Path, data: bytes, ext: str) -> tuple[str, str, int]:
    """Write bytes under the case directory. Returns (stored_name, sha256, size)."""
    stored_name = f"{uuid.uuid4().hex}{ext}"
    target = case_dir / stored_name
    digest = hashlib.sha256(data).hexdigest()
    target.write_bytes(data)
    return stored_name, digest, len(data)


async def save_upload(db: Session, case: Case, upload: UploadFile) -> Document:
    """Validate and persist one uploaded file for a case."""
    display_name = sanitize_filename(upload.filename or "upload")

    # Read up to max+1 bytes so oversize files are rejected without buffering
    # unbounded content.
    data = await upload.read(settings.max_upload_bytes + 1)
    ext = validate_upload(display_name, upload.content_type, len(data), settings.max_upload_bytes)

    case_dir = settings.upload_dir / case.id
    case_dir.mkdir(parents=True, exist_ok=True)
    stored_name, file_hash, size = _store_file(case_dir, data, ext)

    doc = Document(
        case_id=case.id,
        file_name=display_name,
        stored_name=stored_name,
        mime_type=upload.content_type or "",
        file_size=size,
        original_path=str((case_dir / stored_name).relative_to(settings.upload_dir)),
        file_hash=file_hash,
        processing_status="uploaded",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    log_stage(
        log,
        "DOCUMENT_UPLOADED",
        case_id=case.id,
        doc_id=doc.id,
        size=size,
        hash_prefix=file_hash[:12],
    )
    return doc


def delete_document(db: Session, doc: Document) -> bool:
    """Remove a document record and its stored files (best effort)."""
    try:
        path = settings.upload_dir / doc.original_path
        if path.is_file():
            path.unlink()
        # Preprocessing derivative written by the pipeline (…_processed.png).
        processed = path.with_name(path.stem + "_processed.png")
        if processed.is_file():
            processed.unlink()
    except OSError:  # pragma: no cover - best effort cleanup
        log.warning("DOCUMENT_FILE_DELETE_FAILED | doc_id=%s", doc.id)
    db.delete(doc)
    db.commit()
    log_stage(log, "DOCUMENT_DELETED", doc_id=doc.id)
    return True


def get_document_file_path(doc: Document) -> Path:
    """Resolve a document's stored file inside the upload dir (traversal-safe)."""
    from app.core.security import resolve_within

    return resolve_within(settings.upload_dir, doc.original_path)


__all__ = ["save_upload", "delete_document", "get_document_file_path", "UploadValidationError"]
