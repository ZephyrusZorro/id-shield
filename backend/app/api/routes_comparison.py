"""Cross-document comparison endpoint — the evidence matrix."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import Case, CrossDocumentFinding, Document, ExtractedField
from app.schemas.comparison import (
    CaseComparisonResponse,
    ComparisonFieldRow,
    ComparisonValue,
)
from app.services.consistency_service import (
    _FIELD_LABELS,
    TYPE_SCOPED_FIELDS,
    values_agree,
)
from app.utils.normalize import names_match, normalize_address

router = APIRouter()


def _agrees(field_name: str, candidate: str, reference: str) -> bool:
    if field_name == "full_name":
        return names_match(candidate, reference)
    if field_name == "address":
        ta = {t for t in normalize_address(candidate).split() if len(t) > 1}
        tb = {t for t in normalize_address(reference).split() if len(t) > 1}
        if not ta or not tb:
            return False
        return len(ta & tb) / min(len(ta), len(tb)) >= 0.7
    return values_agree(field_name, candidate, reference)


@router.get("/cases/{case_id}/comparison", response_model=CaseComparisonResponse)
def get_comparison(case_id: str, db: Session = Depends(get_db)) -> CaseComparisonResponse:
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")

    docs = db.scalars(select(Document).where(Document.case_id == case_id)).all()
    doc_by_id = {d.id: d for d in docs}
    field_rows = db.scalars(
        select(ExtractedField).where(ExtractedField.document_id.in_(doc_by_id.keys()))
    ).all()

    findings = db.scalars(
        select(CrossDocumentFinding).where(CrossDocumentFinding.case_id == case_id)
    ).all()
    finding_by_field = {f.field_name: f for f in findings}

    # Build per-field value lists across documents.
    by_field: dict[str, list[ExtractedField]] = {}
    for row in field_rows:
        by_field.setdefault(row.field_name, []).append(row)

    rows_out: list[ComparisonFieldRow] = []
    for field_name in sorted(by_field.keys()):
        entries = by_field[field_name]
        label = _FIELD_LABELS.get(field_name, field_name.replace("_", " ").title())
        type_scoped = field_name in TYPE_SCOPED_FIELDS

        normalized_entries = [
            (
                row,
                (row.normalized_value or row.raw_value).strip(),
                (doc_by_id[row.document_id].document_type or "other").strip().lower(),
            )
            for row in entries
        ]

        # For type-scoped fields, agreement is only judged within same-type
        # documents; cross-type values always count as "agreeing" so they
        # never render as mismatches.
        def _counts_as_agree(candidate: str, cand_type: str, reference: str, ref_type: str) -> bool:
            if type_scoped and cand_type != ref_type:
                return True
            return _agrees(field_name, candidate, reference)

        # Reference cluster = largest agreement group.
        reference_val, ref_type, reference_count = None, None, 0
        for _, norm, dtype_ in normalized_entries:
            count = sum(
                1
                for _, other, other_type in normalized_entries
                if _counts_as_agree(other, other_type, norm, dtype_)
            )
            if count > reference_count:
                reference_val, ref_type, reference_count = norm, dtype_, count

        values = [
            ComparisonValue(
                document_id=row.document_id,
                file_name=doc_by_id[row.document_id].file_name,
                raw_value=row.raw_value,
                normalized_value=row.normalized_value,
                confidence=row.confidence,
                agrees=(
                    True
                    if reference_val is None
                    else _counts_as_agree(norm, dtype_, reference_val, ref_type)
                ),
            )
            for row, norm, dtype_ in normalized_entries
        ]

        if type_scoped:
            # Same-type document count decides comparability.
            type_counts: dict[str, int] = {}
            for _, _, dtype_ in normalized_entries:
                type_counts[dtype_] = type_counts.get(dtype_, 0) + 1
            n_comparable = max(type_counts.values()) if type_counts else 0
        else:
            n_comparable = len({v.document_id for v in values})

        finding = finding_by_field.get(field_name)
        mismatched = any(not v.agrees for v in values)

        if mismatched and finding is not None and n_comparable >= 2:
            status = "mismatch"
            severity = (
                finding.severity if finding.severity in ("medium", "high") else "medium"
            )
            explanation = finding.explanation
        elif n_comparable >= 2:
            status, severity = "consistent", None
            explanation = f"{label} is consistent across all {n_comparable} comparable documents."
        else:
            status, severity = "single_source", None
            explanation = None

        rows_out.append(
            ComparisonFieldRow(
                field_name=field_name,
                label=label,
                status=status,
                severity=severity,
                explanation=explanation,
                values=values,
            )
        )

    # Mismatches first, then consistent fields.
    rows_out.sort(key=lambda r: (r.status != "mismatch", r.field_name))
    return CaseComparisonResponse(case_id=case_id, fields=rows_out)
