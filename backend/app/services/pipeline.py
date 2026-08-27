"""Case analysis pipeline orchestrator.

Runs stages sequentially against all documents in a case and records live
stage status (AnalysisStage rows) that the UI polls. A failing or unavailable
module degrades gracefully — partial results are preserved and surfaced.
"""
from __future__ import annotations

import time
from pathlib import Path

import cv2
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.logging import get_logger, log_stage
from app.db.models import (
    AnalysisStage,
    Case,
    CrossDocumentFinding,
    Document,
    ExtractedField,
    ForensicFinding,
    RiskFactor,
    ValidationResult,
)
from app.services import classifier_service, extraction_service  # noqa: F401
from app.services.ocr_service import OcrUnavailableError, get_backend
from app.services.preprocessing_service import load_image, preprocess

log = get_logger("idshield.pipeline")

# Note: keyword-based classification runs on OCR text, so OCR precedes
# classification in execution order.
STAGE_DEFS: list[tuple[str, str]] = [
    ("preprocess", "Image preprocessing"),
    ("ocr", "OCR extraction"),
    ("classify", "Document type detection"),
    ("fields", "Field extraction"),
    ("qrcode", "QR / barcode cross-check"),
    ("forensics", "Visual tampering analysis"),
    ("faces", "Facial photo cross-matching"),
    ("duplicates", "Reuse / duplicate scan"),
    ("validate", "Document validation & MRZ"),
    ("consistency", "Cross-document consistency"),
    ("risk", "Risk scoring"),
]

_UNAVAILABLE_MSG = (
    "OCR engine is not available in this configuration; "
    "downstream text stages were skipped."
)


class StageContext:
    """Per-run results shared across stages."""

    def __init__(self) -> None:
        self.processed: dict[str, Path] = {}
        self.ocr_text: dict[str, object] = {}
        self.ocr_available = True


def _reset_previous_analysis(db: Session, case: Case) -> None:
    db.execute(delete(AnalysisStage).where(AnalysisStage.case_id == case.id))
    db.execute(delete(CrossDocumentFinding).where(CrossDocumentFinding.case_id == case.id))
    db.execute(delete(RiskFactor).where(RiskFactor.case_id == case.id))
    case.overall_risk = None
    case.recommendation = None
    for doc in case.documents:
        db.execute(delete(ForensicFinding).where(ForensicFinding.document_id == doc.id))
        doc.document_type = None
        doc.type_confidence = None
        doc.processed_path = None
        doc.ocr_engine = None
        doc.ocr_mean_confidence = None
        doc.processing_status = "processing"
        db.execute(delete(ExtractedField).where(ExtractedField.document_id == doc.id))
        db.execute(delete(ValidationResult).where(ValidationResult.document_id == doc.id))
    db.flush()


def _run_stage(db: Session, stage_row: AnalysisStage, fn, ctx: StageContext, docs: list[Document]) -> None:
    stage_row.status = "running"
    db.commit()
    start = time.perf_counter()
    try:
        detail = fn(db, docs, ctx)
        stage_row.duration_ms = int((time.perf_counter() - start) * 1000)
        if detail is None:
            stage_row.status = "done"
            stage_row.detail = None
        else:
            stage_row.status = "warning" if detail.get("warning") else "done"
            stage_row.detail = detail.get("message")
    except OcrUnavailableError:
        stage_row.duration_ms = int((time.perf_counter() - start) * 1000)
        stage_row.status = "unavailable"
        stage_row.detail = _UNAVAILABLE_MSG
        ctx.ocr_available = False
    except Exception as exc:  # noqa: BLE001 - surface failure honestly
        log.exception("STAGE_FAILED | stage=%s", stage_row.stage_key)
        stage_row.status = "error"
        stage_row.detail = f"{type(exc).__name__}: {exc}"[:400]
    finally:
        db.commit()


def _stage_preprocess(db: Session, docs: list[Document], ctx: StageContext) -> dict | None:
    failures: list[str] = []
    for doc in docs:
        src = settings.upload_dir / doc.original_path
        out = src.with_name(src.stem + "_processed.png")
        try:
            image = load_image(src)
            meta = preprocess(image, out)
            ctx.processed[doc.id] = out
            doc.processed_path = str(out.relative_to(settings.upload_dir))
            log_stage(log, "PREPROCESS_DONE", doc_id=doc.id, steps=len(meta["steps"]))
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{doc.file_name}: {exc}")
    if failures:
        return {"warning": True, "message": "; ".join(failures)[:400]}
    return None


def _stage_ocr(db: Session, docs: list[Document], ctx: StageContext) -> dict | None:
    backend = get_backend()
    failures: list[str] = []
    for doc in docs:
        target = ctx.processed.get(doc.id) or (settings.upload_dir / doc.original_path)
        try:
            image = load_image(target)
            result = backend.run(image)
            ctx.ocr_text[doc.id] = result
            doc.ocr_engine = result.engine
            doc.ocr_mean_confidence = result.mean_confidence
            log_stage(log, "OCR_COMPLETED", doc_id=doc.id, lines=len(result.lines))
        except OcrUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{doc.file_name}: {exc}")
    if failures:
        return {"warning": True, "message": "; ".join(failures)[:400]}
    return None


def _stage_classify(db: Session, docs: list[Document], ctx: StageContext) -> dict | None:
    from app.services.preprocessing_service import load_image

    unknown: list[str] = []
    for doc in docs:
        aspect = None
        processed = ctx.processed.get(doc.id)
        if processed is not None:
            image = load_image(processed)
            aspect = round(image.shape[1] / image.shape[0], 2)
        ocr = ctx.ocr_text.get(doc.id)
        text = ocr.full_text if ocr is not None else ""
        type_name, label, conf = classifier_service.classify_document(text, aspect)
        doc.document_type = type_name
        doc.type_confidence = conf
        log_stage(log, "DOCUMENT_CLASSIFIED", doc_id=doc.id, type=type_name, conf=conf)
        if type_name == "other":
            unknown.append(doc.file_name)
    if unknown:
        return {
            "warning": True,
            "message": f"Type not confidently identified: {', '.join(unknown)}",
        }
    return None


def _stage_fields(db: Session, docs: list[Document], ctx: StageContext) -> dict | None:
    missing: list[str] = []
    for doc in docs:
        ocr = ctx.ocr_text.get(doc.id)
        drafts = extraction_service.extract_fields(ocr) if ocr is not None else []
        for draft in drafts:
            db.add(
                ExtractedField(
                    document_id=doc.id,
                    field_name=draft.field_name,
                    raw_value=draft.raw_value,
                    normalized_value=draft.normalized_value,
                    confidence=draft.confidence,
                    source_region=draft.source_region,
                )
            )
        if not drafts:
            missing.append(doc.file_name)
        log_stage(log, "FIELDS_EXTRACTED", doc_id=doc.id, count=len(drafts))
    if missing:
        return {
            "warning": True,
            "message": f"No structured fields extracted from: {', '.join(missing)}",
        }
    return None


def _stage_validate(db: Session, docs: list[Document], ctx: StageContext) -> dict | None:
    from app.services import validation_service

    failed = 0
    warned = 0
    for doc in docs:
        field_rows = db.scalars(
            select(ExtractedField).where(ExtractedField.document_id == doc.id)
        ).all()
        fields_map = {
            r.field_name: (r.normalized_value or r.raw_value) for r in field_rows
        }
        ocr = ctx.ocr_text.get(doc.id)
        drafts = validation_service.validate_document(
            doc.document_type, fields_map, ocr.full_text if ocr is not None else None
        )
        # Preserve rows owned by other stages (QR cross-check, duplicates).
        preserved = {"Duplicate / reuse"}
        old_rows = db.scalars(
            select(ValidationResult).where(ValidationResult.document_id == doc.id)
        ).all()
        for old in old_rows:
            if old.check_type not in preserved and not old.check_type.startswith("QR payload"):
                db.delete(old)
        for d in drafts:
            db.add(
                ValidationResult(
                    document_id=doc.id,
                    check_type=d.check_type,
                    status=d.status,
                    message=d.message,
                    evidence=d.evidence,
                )
            )
            if d.status == "fail":
                failed += 1
            elif d.status == "warning":
                warned += 1
        log_stage(
            log, "VALIDATION_COMPLETED", doc_id=doc.id,
            fails=failed, warnings=warned,
        )
    if failed or warned:
        return {
            "warning": True,
            "message": f"{failed} check(s) failed, {warned} need attention.",
        }
    return None


def _stage_consistency(db: Session, docs: list[Document], ctx: StageContext) -> dict | None:
    from app.services import consistency_service

    db.execute(delete(CrossDocumentFinding).where(CrossDocumentFinding.case_id == docs[0].case_id))

    doc_values = []
    for doc in docs:
        rows = db.scalars(
            select(ExtractedField).where(ExtractedField.document_id == doc.id)
        ).all()
        doc_values.append(
            consistency_service.DocumentValues(
                document_id=doc.id,
                file_name=doc.file_name,
                fields={r.field_name: (r.normalized_value or r.raw_value) for r in rows},
                document_type=doc.document_type,
            )
        )

    findings = consistency_service.compare_documents(doc_values)
    for f in findings:
        db.add(
            CrossDocumentFinding(
                case_id=docs[0].case_id,
                field_name=f.field_name,
                severity=f.severity,
                documents_involved=f.documents_involved,
                values={d["document_id"]: d["value"] for d in f.documents_involved},
                explanation=f.explanation,
            )
        )
    log_stage(log, "CONSISTENCY_CHECK_COMPLETED", case_id=docs[0].case_id, findings=len(findings))

    conflicts = [f for f in findings if f.severity in ("medium", "high")]
    if len(docs) < 2:
        return {"message": "Single-document case — cross-document check not applicable."}
    if conflicts:
        return {
            "warning": True,
            "message": (
                f"{len(conflicts)} inconsistency(ies) detected across documents: "
                + ", ".join(sorted({c.field_name for c in conflicts}))
            ),
        }
    return {"message": "All shared fields are consistent across documents."}


def _stage_forensics(db: Session, docs: list[Document], ctx: StageContext) -> dict | None:
    """Analyze pristine ORIGINALS — preprocessing derivatives would inject
    their own resampling artifacts and defeat the purpose."""
    from app.services import forensic_service
    from app.services.preprocessing_service import load_image

    flagged: list[str] = []
    for doc in docs:
        src = settings.upload_dir / doc.original_path
        db.execute(delete(ForensicFinding).where(ForensicFinding.document_id == doc.id))
        try:
            image = load_image(src)
            drafts = forensic_service.analyze_image(image, doc.document_type)
        except Exception as exc:  # noqa: BLE001 - per-doc isolation
            log.warning("FORENSICS_FAILED | doc_id=%s err=%s", doc.id, exc)
            continue
        for d in drafts:
            db.add(
                ForensicFinding(
                    document_id=doc.id,
                    region=d.region,
                    finding_type=d.finding_type,
                    severity=d.severity,
                    score=d.score,
                    bbox=d.bbox,
                    explanation=d.explanation,
                )
            )
        severity, pct = forensic_service.overall_suspicion(d.score for d in drafts)
        if severity in ("medium", "high"):
            flagged.append(f"{doc.file_name} ({severity}, {pct}/100)")
        log_stage(
            log, "FORENSICS_COMPLETED", doc_id=doc.id,
            findings=len(drafts), suspicion=severity,
        )

    if flagged:
        return {
            "warning": True,
            "message": f"Suspicious region indicators in: {', '.join(flagged)}",
        }
    return {"message": "No significant tampering indicators detected."}


def _stage_faces(db: Session, docs: list[Document], ctx: StageContext) -> dict | None:
    """Detect and cross-match facial photos across documents."""
    from app.services import face_service
    from app.services.preprocessing_service import load_image
    from app.db.models import CrossDocumentFinding, ValidationResult

    case_id = docs[0].case_id
    crops_dir = settings.upload_dir / case_id / "faces"
    crops_dir.mkdir(parents=True, exist_ok=True)

    face_crops: list[face_service.FaceCropResult] = []
    doc_paths: dict[str, Path] = {}

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
                db.add(
                    ValidationResult(
                        document_id=doc.id,
                        check_type="Face photo extraction",
                        status="pass",
                        message=(
                            f"Facial photo detected ({crop_res.detection_method.replace('_', ' ')}), "
                            f"sharpness score: {crop_res.sharpness:.1f}."
                        ),
                        evidence={
                            "bbox": crop_res.bbox,
                            "sharpness": crop_res.sharpness,
                            "contrast": crop_res.contrast,
                        },
                    )
                )
        except Exception as exc:  # noqa: BLE001
            log.warning("FACE_EXTRACTION_FAILED | doc_id=%s err=%s", doc.id, exc)

    comparisons = face_service.compare_document_faces(face_crops, doc_paths)
    for c in comparisons:
        db.add(
            CrossDocumentFinding(
                case_id=case_id,
                field_name="facial_photo",
                severity=c.severity,
                documents_involved=[
                    {"document_id": c.doc_a_id, "file_name": c.doc_a_name, "value": f"Photo ({c.doc_a_name})"},
                    {"document_id": c.doc_b_id, "file_name": c.doc_b_name, "value": f"Photo ({c.doc_b_name})"},
                ],
                values={
                    c.doc_a_id: f"{c.doc_a_name} face",
                    c.doc_b_id: f"{c.doc_b_name} face",
                },
                explanation=c.explanation,
            )
        )

    log_stage(log, "FACE_CROSSMATCH_COMPLETED", case_id=case_id, faces=len(face_crops), comparisons=len(comparisons))

    if not face_crops:
        return {"message": "No facial photos detected in submitted documents."}
    if len(face_crops) == 1:
        return {"message": f"Single facial photo detected in {face_crops[0].file_name}; cross-match requires 2+ docs."}

    mismatches = [c for c in comparisons if c.status == "mismatch"]
    borderlines = [c for c in comparisons if c.status == "borderline"]
    if mismatches:
        return {
            "warning": True,
            "message": f"Facial photo mismatch detected ({mismatches[0].similarity_score}% similarity). Review required.",
        }
    if borderlines:
        return {
            "warning": True,
            "message": f"Facial photo similarity borderline ({borderlines[0].similarity_score}% similarity). Review recommended.",
        }
    avg_score = int(sum(c.similarity_score for c in comparisons) / len(comparisons)) if comparisons else 100
    return {
        "message": f"Facial photos match across {len(face_crops)} documents (average {avg_score}% similarity).",
    }


def _stage_qrcode(db: Session, docs: list[Document], ctx: StageContext) -> dict | None:
    """Decode QR payloads from originals and cross-check against fields."""
    from app.services import qr_service
    from app.services.preprocessing_service import load_image

    checked = 0
    for doc in docs:
        field_rows = db.scalars(
            select(ExtractedField).where(ExtractedField.document_id == doc.id)
        ).all()
        if not field_rows:
            continue
        fields_map = {r.field_name: (r.normalized_value or r.raw_value) for r in field_rows}
        try:
            image = load_image(settings.upload_dir / doc.original_path)
            payloads = qr_service.decode_qr_payloads(image)
        except Exception as exc:  # noqa: BLE001
            log.warning("QR_DECODE_FAILED | doc_id=%s err=%s", doc.id, exc)
            continue
        parsed = [p for p in (qr_service.parse_payload(p) for p in payloads) if p]
        rows = qr_service.compare_with_fields(parsed, fields_map)
        db.execute(delete(ValidationResult).where(ValidationResult.document_id == doc.id, ValidationResult.check_type.like("QR payload%")))
        for r in rows:
            db.add(
                ValidationResult(
                    document_id=doc.id,
                    check_type=r["check_type"],
                    status=r["status"],
                    message=r["message"],
                    evidence=r.get("evidence"),
                )
            )
        if rows:
            checked += 1
        log_stage(log, "QR_CHECK_COMPLETED", doc_id=doc.id, payloads=len(payloads), checks=len(rows))
    if checked == 0:
        return {"message": "No QR payload / printed-field pairs to compare."}
    return None


def _stage_risk(db: Session, docs: list[Document], ctx: StageContext) -> dict | None:
    """Fuse all evidence into the explainable case risk score."""
    from app.services import risk_engine
    from app.db.models import RiskFactor

    case_id = docs[0].case_id
    db.execute(delete(RiskFactor).where(RiskFactor.case_id == case_id))

    # Cross-document conflicts
    conflicts = db.scalars(
        select(CrossDocumentFinding).where(CrossDocumentFinding.case_id == case_id)
    ).all()
    conflict_input = [
        {"field_name": c.field_name, "severity": c.severity}
        for c in conflicts
        if c.severity in ("medium", "high")
    ]

    # Forensic findings across docs
    forensic = db.scalars(
        select(ForensicFinding).where(ForensicFinding.document_id.in_([d.id for d in docs]))
    ).all()
    forensic_input = [{"severity": f.severity} for f in forensic]

    # Validation outcomes
    val_rows = db.scalars(
        select(ValidationResult).where(ValidationResult.document_id.in_([d.id for d in docs]))
    ).all()
    fail_count = sum(1 for v in val_rows if v.status == "fail")
    has_expired = any(
        v.check_type == "Expiration status" and v.status == "warning" for v in val_rows
    )
    mrz_checksum_fail = any(
        v.check_type == "MRZ checksum" and v.status == "fail" for v in val_rows
    )
    mrz_valid_present = any(
        v.check_type == "MRZ checksum" and v.status == "pass" for v in val_rows
    )
    duplicate_hits = sum(
        1 for v in val_rows if v.check_type == "Duplicate / reuse"
    )
    name_consistent = any(
        c.field_name == "full_name" and c.severity == "info" for c in conflicts
    )
    address_consistent = any(
        c.field_name == "address" and c.severity == "info" for c in conflicts
    )
    face_consistent = any(
        c.field_name == "facial_photo" and c.severity == "info" for c in conflicts
    )
    field_counts: dict[str, int] = {}
    for d in docs:
        n = (
            db.scalar(
                select(func.count(ExtractedField.id)).where(
                    ExtractedField.document_id == d.id
                )
            )
            or 0
        )
        field_counts[d.id] = n

    # Evidence = actually extracted content (fields or successful OCR),
    # not merely structural validation rows about unreadable files.
    # Computed once for the whole case, outside the per-document loop.
    any_fields = any(v > 0 for v in field_counts.values())
    any_ocr = any(d.ocr_mean_confidence is not None for d in docs)

    inp = risk_engine.RiskInput(
        conflict_fields=conflict_input,
        forensic_findings=forensic_input,
        validation_fail_count=fail_count,
        has_expired_document=has_expired,
        mrz_checksum_fail=mrz_checksum_fail,
        mrz_valid_present=mrz_valid_present,
        duplicate_hits=duplicate_hits,
        name_consistent=name_consistent,
        address_consistent=address_consistent,
        face_consistent=face_consistent,
        all_validations_pass=(
            bool(val_rows)
            and all(v.status in ("pass", "unavailable") for v in val_rows)
        ),
        has_any_evidence=any_fields or any_ocr,
    )

    result = risk_engine.evaluate(inp)

    for f in result["factors"]:
        db.add(
            RiskFactor(
                case_id=case_id,
                factor=f["factor"],
                score=f["score"],
                direction=f["direction"],
                explanation=f["explanation"],
            )
        )

    case = db.get(Case, case_id)
    if case is not None:
        case.overall_risk = result["score"]
        case.recommendation = result["recommendation"]
    db.commit()
    log_stage(
        log, "RISK_CALCULATED", case_id=case_id,
        score=result["score"], band=result["band"],
        recommendation=result["recommendation"],
    )
    return {
        "message": (
            f"{result['band']} — score {result['score']}/100 "
            f"({result['recommendation'].replace('_', ' ')})."
        )
    }


def _stage_duplicates(db: Session, docs: list[Document], ctx: StageContext) -> dict | None:
    """Scan for reuse of this evidence in earlier cases."""
    from app.services import duplicate_service
    from app.services.preprocessing_service import load_image
    from app.db.models import Case as CaseModel

    total_hits = 0
    for doc in docs:
        if not doc.perceptual_hash:
            target = ctx.processed.get(doc.id) or (settings.upload_dir / doc.original_path)
            try:
                image = load_image(target)
                gray = (
                    cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                    if image.ndim == 3
                    else image
                )
                doc.perceptual_hash = duplicate_service.perceptual_hash_of(gray)
            except Exception as exc:  # noqa: BLE001
                log.warning("PHASH_FAILED | doc_id=%s err=%s", doc.id, exc)

        others = db.scalars(
            select(Document).where(Document.id != doc.id)
        ).all()
        # Exact-hash reuse only: perceptual matching is unreliable on
        # flat scan-style documents (see duplicate_service notes).
        hits = duplicate_service.find_reuse(
            doc.file_hash, doc.perceptual_hash, others, use_perceptual=False
        )

        db.execute(
            delete(ValidationResult).where(
                ValidationResult.document_id == doc.id,
                ValidationResult.check_type == "Duplicate / reuse",
            )
        )
        if hits:
            total_hits += len(hits)
            described: list[str] = []
            for h in hits[:5]:
                other_case = db.get(CaseModel, h["case_id"])
                label = f"case #{other_case.case_number}" if other_case else "another case"
                kind = "identical file" if h["kind"] == "exact" else "visually near-identical"
                described.append(f"{kind} ({label})")
            db.add(
                ValidationResult(
                    document_id=doc.id,
                    check_type="Duplicate / reuse",
                    status="warning",
                    message=(
                        f"Potential reuse detected — this document appears "
                        f"{described[0]}" + (f" and {len(hits)-1} more match(es)." if len(hits) > 1 else ".")
                    ),
                    evidence={"hits": hits},
                )
            )
        log_stage(log, "DUPLICATE_SCAN", doc_id=doc.id, hits=len(hits))

    if total_hits:
        return {
            "warning": True,
            "message": f"{total_hits} potential reuse match(es) found across cases.",
        }
    return {"message": "No reuse of this evidence found in earlier cases."}


_RUNNERS = {
    "preprocess": _stage_preprocess,
    "ocr": _stage_ocr,
    "classify": _stage_classify,
    "fields": _stage_fields,
    "qrcode": _stage_qrcode,
    "forensics": _stage_forensics,
    "faces": _stage_faces,
    "duplicates": _stage_duplicates,
    "validate": _stage_validate,
    "consistency": _stage_consistency,
    "risk": _stage_risk,
}


def analyze_case(case_id: str) -> None:
    """Entry point executed in a FastAPI background task."""
    from app.db.base import SessionLocal

    db = SessionLocal()
    try:
        case = db.scalar(
            select(Case).options(selectinload(Case.documents)).where(Case.id == case_id)
        )
        if case is None or not case.documents:
            return

        _reset_previous_analysis(db, case)
        rows = [
            AnalysisStage(case_id=case.id, order_index=i, stage_key=key, stage_label=label, status="pending")
            for i, (key, label) in enumerate(STAGE_DEFS)
        ]
        db.add_all(rows)
        case.status = "processing"
        db.commit()

        ctx = StageContext()
        for row in rows:
            # When OCR is unavailable, dependent stages are honestly marked
            # unavailable rather than pretending to run.
            if not ctx.ocr_available and row.stage_key in {"classify", "fields", "qrcode", "validate", "consistency"}:
                row.status = "unavailable"
                row.detail = _UNAVAILABLE_MSG
                db.commit()
                continue
            _run_stage(db, row, _RUNNERS[row.stage_key], ctx, case.documents)

        any_error = any(r.status == "error" for r in rows)
        for doc in case.documents:
            doc.processing_status = "done"

        case.status = "completed" if not any_error else "failed"
        db.commit()
        log_stage(log, "ANALYSIS_COMPLETED", case_id=case.id, status=case.status)
    except Exception:  # noqa: BLE001 - never leave the case stuck 'processing'
        log.exception("ANALYSIS_FAILED | case_id=%s", case_id)
        db.rollback()
        try:
            case = db.get(Case, case_id)
            if case is not None:
                case.status = "failed"
                db.commit()
        except Exception:  # pragma: no cover
            db.rollback()
    finally:
        db.close()
