"""Demo helpers: load the signature case and seed synthetic history.

Everything here is clearly labeled synthetic and flows through the SAME
upload/analysis code paths as real usage.
"""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Case, Document
from app.services import case_service

_DEMO_DIR = Path(__file__).parent / "assets" / "signature_case"
_SIGNATURE_FILES = [
    "passport_A_rahul_sharma.png",
    "national_id_B_rahul_sharma.png",
    "pan_C_rahul_sharma.png",
    # address proof omitted by default for the 3-minute demo flow
]


def _ensure_assets() -> None:
    if not all((_DEMO_DIR / f).is_file() for f in _SIGNATURE_FILES):
        from demo.generate_docs import signature_case_documents

        signature_case_documents(_DEMO_DIR)


def create_signature_case(db: Session) -> Case:
    """Create + populate the Rahul Sharma signature case (files only)."""
    _ensure_assets()
    case = case_service.create_case(db, "Rahul Sharma — Demo (synthetic)")

    case_dir = settings.upload_dir / case.id
    case_dir.mkdir(parents=True, exist_ok=True)
    for name in _SIGNATURE_FILES:
        src = _DEMO_DIR / name
        stored = f"{uuid.uuid4().hex}.png"
        shutil.copyfile(src, case_dir / stored)
        import hashlib

        data = (case_dir / stored).read_bytes()
        db.add(
            Document(
                case_id=case.id,
                file_name=name,
                stored_name=stored,
                mime_type="image/png",
                file_size=len(data),
                original_path=str((case_dir / stored).relative_to(settings.upload_dir)),
                file_hash=hashlib.sha256(data).hexdigest(),
                processing_status="uploaded",
            )
        )
    db.commit()
    db.refresh(case)
    return case


def get_case_or_404(db: Session, case_id: str) -> Case:
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    return case
