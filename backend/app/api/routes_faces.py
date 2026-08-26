"""Face forensics and facial cross-matching REST endpoints."""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import get_db
from app.db.models import Case, Document
from app.schemas.faces import (
    CaseFacesResponse,
    FaceComparisonPair,
    FaceCropInfo,
    FaceMetrics,
)
from app.services import face_service
from app.services.preprocessing_service import load_image

router = APIRouter()

_DISCLAIMER = (
    "Facial verification provides explainable structural and texture similarity "
    "indicators across submitted documents. It does not constitute legal biometric "
    "identification; final determination requires human review."
)


@router.get("/cases/{case_id}/faces", response_model=CaseFacesResponse)
def get_case_faces(case_id: str, db: Session = Depends(get_db)) -> CaseFacesResponse:
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")

    docs = db.scalars(select(Document).where(Document.case_id == case_id)).all()
    face_crops: list[face_service.FaceCropResult] = []
    doc_paths: dict[str, Path] = {}
    crops_dir = settings.upload_dir / case_id / "faces"

    for doc in docs:
        src = settings.upload_dir / doc.original_path
        if not src.is_file():
            continue
        doc_paths[doc.id] = src
        try:
            image = load_image(src)
            crop_res = face_service.extract_face(
                image,
                doc_id=doc.id,
                file_name=doc.file_name,
                doc_type=doc.document_type,
                save_crop_dir=crops_dir,
            )
            if crop_res is not None:
                face_crops.append(crop_res)
        except Exception:
            continue

    comparisons = face_service.compare_document_faces(face_crops, doc_paths)

    faces_out: list[FaceCropInfo] = []
    for f in face_crops:
        crop_file = crops_dir / f"{f.document_id}_face.png"
        faces_out.append(
            FaceCropInfo(
                document_id=f.document_id,
                file_name=f.file_name,
                bbox=f.bbox,
                normalized_bbox=f.normalized_bbox,
                confidence=f.confidence,
                detection_method=f.detection_method,
                sharpness=f.sharpness,
                brightness=f.brightness,
                contrast=f.contrast,
                has_crop=crop_file.is_file(),
            )
        )

    comparisons_out: list[FaceComparisonPair] = [
        FaceComparisonPair(
            doc_a_id=c.doc_a_id,
            doc_a_name=c.doc_a_name,
            doc_b_id=c.doc_b_id,
            doc_b_name=c.doc_b_name,
            similarity_score=c.similarity_score,
            status=c.status,
            severity=c.severity,
            explanation=c.explanation,
            metrics=FaceMetrics(
                ssim_score=c.ssim_score,
                phash_similarity=c.phash_similarity,
                lbp_correlation=c.lbp_correlation,
                color_correlation=c.color_correlation,
            ),
        )
        for c in comparisons
    ]

    if not faces_out:
        overall_status = "no_faces"
    elif len(faces_out) == 1:
        overall_status = "single_face"
    elif any(c.status == "mismatch" for c in comparisons):
        overall_status = "mismatch"
    elif any(c.status == "borderline" for c in comparisons):
        overall_status = "borderline"
    else:
        overall_status = "match"

    return CaseFacesResponse(
        case_id=case_id,
        disclaimer=_DISCLAIMER,
        faces=faces_out,
        comparisons=comparisons_out,
        overall_status=overall_status,
    )


@router.get("/documents/{document_id}/face-crop")
def get_document_face_crop(document_id: str, db: Session = Depends(get_db)) -> FileResponse:
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    crop_path = settings.upload_dir / doc.case_id / "faces" / f"{doc.id}_face.png"
    if crop_path.is_file():
        return FileResponse(crop_path, media_type="image/png")

    # Generate on demand if not present
    src = settings.upload_dir / doc.original_path
    if not src.is_file():
        raise HTTPException(status_code=404, detail="Original document file not found.")

    crops_dir = settings.upload_dir / doc.case_id / "faces"
    try:
        image = load_image(src)
        res = face_service.extract_face(
            image,
            doc_id=doc.id,
            file_name=doc.file_name,
            doc_type=doc.document_type,
            save_crop_dir=crops_dir,
        )
        if res is not None and crop_path.is_file():
            return FileResponse(crop_path, media_type="image/png")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to extract face: {exc}") from exc

    raise HTTPException(status_code=404, detail="No face detected in this document.")
