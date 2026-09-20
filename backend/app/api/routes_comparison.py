from typing import Sequence
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import Case, CrossDocumentFinding, Document, ExtractedField, ValidationResult
from app.schemas.comparison import (
    CaseComparisonResponse,
    ComparisonFieldRow,
    ComparisonValue,
    EvidenceFusionRow,
    EvidenceGraphData,
    GraphEdge,
    GraphNode,
    OtherDocValue,
    RuleEvaluationItem,
)
from app.services.consistency_service import (
    _FIELD_LABELS,
    TYPE_SCOPED_FIELDS,
    values_agree,
)
from app.utils.normalize import names_match, normalize_address, normalize_date_str

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
    if field_name in ("date_of_birth", "issue_date", "expiry_date"):
        da, db = normalize_date_str(candidate), normalize_date_str(reference)
        if da and db:
            return da == db
    return values_agree(field_name, candidate, reference)


def _build_evidence_fusion_and_graph(
    case: Case,
    docs: Sequence[Document],
    field_rows: Sequence[ExtractedField],
    val_rows: Sequence[ValidationResult],
    rows_out: list[ComparisonFieldRow],
) -> tuple[list[EvidenceFusionRow], EvidenceGraphData]:
    """Build multi-source fusion matrix (OCR vs QR vs MRZ vs Others) and evidence graph."""
    doc_map = {d.id: d for d in docs}

    # Extract QR values from validation results
    qr_vals_by_field: dict[str, str] = {}
    for v in val_rows:
        if v.check_type.startswith("QR payload vs") and v.evidence and isinstance(v.evidence, dict):
            qr_data = v.evidence.get("qr")
            if qr_data:
                qr_str = qr_data[0] if isinstance(qr_data, list) else str(qr_data)
                if "document number" in v.check_type.lower():
                    qr_vals_by_field["document_number"] = qr_str
                elif "name" in v.check_type.lower():
                    qr_vals_by_field["full_name"] = qr_str
                elif "date of birth" in v.check_type.lower() or "dob" in v.check_type.lower():
                    qr_vals_by_field["date_of_birth"] = qr_str

    # Extract MRZ values from passport documents or MRZ validation results
    mrz_vals_by_field: dict[str, str] = {}
    for v in val_rows:
        if "mrz" in v.check_type.lower() and v.evidence and isinstance(v.evidence, dict):
            for k, val in v.evidence.items():
                if val:
                    if k in ("doc_number", "document_number", "passport_number"):
                        mrz_vals_by_field["document_number"] = str(val)
                    elif k in ("dob", "date_of_birth"):
                        mrz_vals_by_field["date_of_birth"] = str(val)
                    elif k in ("name", "full_name", "surname"):
                        mrz_vals_by_field["full_name"] = str(val)

    # Group extracted fields by document and field
    doc_field_map: dict[str, dict[str, ExtractedField]] = {}
    for r in field_rows:
        doc_field_map.setdefault(r.document_id, {})[r.field_name] = r

    fusion_matrix: list[EvidenceFusionRow] = []
    primary_fields = ["full_name", "date_of_birth", "document_number", "address", "gender"]

    for field_name in primary_fields:
        # Collect OCR values across docs
        ocr_candidates: list[tuple[str, float]] = []
        other_docs_list: list[OtherDocValue] = []

        for d in docs:
            ef = doc_field_map.get(d.id, {}).get(field_name)
            if ef:
                val = (ef.normalized_value or ef.raw_value).strip()
                conf = ef.confidence or 85.0
                ocr_candidates.append((val, conf))
                other_docs_list.append(
                    OtherDocValue(
                        doc_id=d.id,
                        doc_name=d.file_name,
                        doc_type=d.document_type,
                        value=val,
                    )
                )

        if not ocr_candidates and field_name not in qr_vals_by_field and field_name not in mrz_vals_by_field:
            continue

        label = _FIELD_LABELS.get(field_name, field_name.replace("_", " ").title())
        ocr_val = ocr_candidates[0][0] if ocr_candidates else None
        ocr_conf = round(sum(c[1] for c in ocr_candidates) / len(ocr_candidates), 1) if ocr_candidates else None

        qr_val = qr_vals_by_field.get(field_name)
        qr_conf = 98.0 if qr_val else None

        mrz_val = mrz_vals_by_field.get(field_name)
        mrz_conf = 95.0 if mrz_val else None

        # Build active sources dictionary
        sources: dict[str, str] = {}
        if ocr_val:
            sources["Printed OCR"] = ocr_val
        if qr_val:
            sources["Digital QR"] = qr_val
        if mrz_val:
            sources["Passport MRZ"] = mrz_val

        # Also add distinct document values if multiple docs exist
        if len(other_docs_list) > 1:
            for od in other_docs_list:
                src_name = f"{od.doc_name} ({od.doc_type or 'Doc'})"
                sources[src_name] = od.value

        # Majority Consensus Voting (Step 4 & 6 from workflow)
        if len(sources) <= 1:
            consensus_val = next(iter(sources.values())) if sources else None
            status = "single_source"
            conflict_summary = "Single source available for verification."
            caution = "normal"
        else:
            # Cluster values
            clusters: list[list[tuple[str, str]]] = []  # [[(source_name, value)]]
            for sname, sval in sources.items():
                placed = False
                for cluster in clusters:
                    if _agrees(field_name, sval, cluster[0][1]):
                        cluster.append((sname, sval))
                        placed = True
                        break
                if not placed:
                    clusters.append([(sname, sval)])

            clusters.sort(key=len, reverse=True)
            largest = clusters[0]
            consensus_val = largest[0][1]

            if len(clusters) == 1:
                status = "unanimous"
                conflict_summary = f"All {len(sources)} sources agree unanimously ({consensus_val})."
                caution = "normal"
            elif len(largest) >= 2 and len(clusters) == 2 and len(clusters[1]) == 1:
                # 3 sources agree, 1 differs pattern
                status = "majority_conflict"
                outlier_src, outlier_val = clusters[1][0]
                agree_srcs = ", ".join(s[0] for s in largest)
                conflict_summary = (
                    f"{len(largest)} sources agree ({agree_srcs}: '{consensus_val}'), "
                    f"1 differs ({outlier_src}: '{outlier_val}'). Potential tampering in {outlier_src}."
                )
                caution = "elevated"
            else:
                status = "mismatch"
                conflict_summary = f"Multiple conflicting sources: {'; '.join(f'{s[0]}={s[1]}' for c in clusters for s in c)}."
                caution = "high"

        # Confidence-Aware Risk adjustment
        if ocr_conf and ocr_conf < 70.0 and status != "unanimous":
            caution = "high"
            conflict_summary += " (Caution: Low OCR confidence detected)."

        fusion_matrix.append(
            EvidenceFusionRow(
                field_name=field_name,
                label=label,
                ocr_value=ocr_val,
                ocr_confidence=ocr_conf,
                qr_value=qr_val,
                qr_confidence=qr_conf,
                mrz_value=mrz_val,
                mrz_confidence=mrz_conf,
                other_docs=other_docs_list,
                consensus_value=consensus_val,
                agreement_status=status,
                conflict_summary=conflict_summary,
                caution_level=caution,
            )
        )

    # 2. Build Evidence Graph (Module 12)
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []

    # Root Person Node
    applicant_name = (
        next((r.consensus_value for r in fusion_matrix if r.field_name == "full_name" and r.consensus_value), None)
        or case.applicant_name
        or "Identity Subject"
    )
    person_status = (
        "mismatch"
        if (case.overall_risk and case.overall_risk >= 60)
        else ("warning" if (case.overall_risk and case.overall_risk >= 30) else "verified")
    )
    nodes.append(
        GraphNode(
            id="person-root",
            label=applicant_name,
            type="person",
            status=person_status,
            value=f"Risk Score: {case.overall_risk or 0}/100",
            confidence=100.0 if not case.overall_risk else float(100 - case.overall_risk),
            details={"case_id": case.id, "recommendation": case.recommendation},
        )
    )

    # Document Nodes
    for d in docs:
        doc_node_id = f"doc-{d.id}"
        doc_type_clean = (d.document_type or "Document").replace("_", " ").title()
        nodes.append(
            GraphNode(
                id=doc_node_id,
                label=f"{doc_type_clean}",
                type="document",
                status="verified" if d.processing_status == "completed" else "warning",
                value=d.file_name,
                confidence=round(d.type_confidence * 100, 0) if d.type_confidence else 90.0,
                details={"doc_id": d.id, "file_name": d.file_name, "doc_type": d.document_type},
            )
        )
        edges.append(
            GraphEdge(
                source="person-root",
                target=doc_node_id,
                label="submitted",
                status="neutral",
            )
        )

    # Field Nodes & Cross Edges
    for f in fusion_matrix:
        if not f.consensus_value:
            continue
        field_node_id = f"field-{f.field_name}"
        nodes.append(
            GraphNode(
                id=field_node_id,
                label=f"{f.label}: {f.consensus_value}",
                type="field",
                status="verified" if f.agreement_status == "unanimous" else ("mismatch" if f.agreement_status == "majority_conflict" else "warning"),
                value=f.consensus_value,
                confidence=f.ocr_confidence or 90.0,
                details={"field_name": f.field_name, "status": f.agreement_status, "caution": f.caution_level},
            )
        )

        for od in f.other_docs:
            doc_node_id = f"doc-{od.doc_id}"
            agrees = _agrees(f.field_name, od.value, f.consensus_value)
            edges.append(
                GraphEdge(
                    source=doc_node_id,
                    target=field_node_id,
                    label=od.value,
                    status="agree" if agrees else "conflict",
                )
            )

    return fusion_matrix, EvidenceGraphData(nodes=nodes, edges=edges)


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
    val_rows = db.scalars(
        select(ValidationResult).where(ValidationResult.document_id.in_(doc_by_id.keys()))
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

        def _counts_as_agree(candidate: str, cand_type: str, reference: str, ref_type: str | None = None) -> bool:
            if type_scoped and cand_type != ref_type:
                return True
            return _agrees(field_name, candidate, reference)

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

    # Also include synthetic/biometric cross-document findings (like facial_photo)
    for field_name, finding in finding_by_field.items():
        if field_name not in by_field and field_name == "facial_photo":
            label = _FIELD_LABELS.get(field_name, "Facial Photo")
            mismatched = finding.severity in ("medium", "high")
            status = "mismatch" if mismatched else "consistent"
            values = [
                ComparisonValue(
                    document_id=d.get("document_id", ""),
                    file_name=d.get("file_name", ""),
                    raw_value=d.get("value", "Face Photo"),
                    normalized_value=d.get("value", "Face Photo"),
                    confidence=100.0,
                    agrees=not mismatched,
                )
                for d in (finding.documents_involved or [])
            ]
            rows_out.append(
                ComparisonFieldRow(
                    field_name=field_name,
                    label=label,
                    status=status,
                    severity=finding.severity if mismatched else None,
                    explanation=finding.explanation,
                    values=values,
                )
            )

    from app.services import rule_engine

    docs_for_rules = []
    for d in docs:
        fields_for_doc = {
            row.field_name: (row.normalized_value or row.raw_value)
            for row in field_rows
            if row.document_id == d.id
        }
        docs_for_rules.append({
            "document_id": d.id,
            "file_name": d.file_name,
            "fields": fields_for_doc,
            "document_type": d.document_type,
        })

    rule_evals = rule_engine.run_custom_rule_engine(docs_for_rules)
    rules_out = [
        RuleEvaluationItem(
            rule_id=r.rule_id,
            rule_name=r.rule_name,
            category=r.category,
            status=r.status,
            severity=r.severity,
            confidence=r.confidence,
            explanation=r.explanation,
            evidence=r.evidence,
        )
        for r in rule_evals
    ]

    sim_matrix = rule_engine.evaluate_name_similarity_matrix(docs_for_rules)
    overall_name_sim = sim_matrix.get("overall_similarity")

    for r in rows_out:
        if r.field_name == "full_name":
            r.similarity = overall_name_sim

    rows_out.sort(key=lambda r: (r.status != "mismatch", r.field_name))

    # Multi-source fusion and evidence graph
    fusion_matrix, evidence_graph = _build_evidence_fusion_and_graph(
        case, docs, field_rows, val_rows, rows_out
    )

    return CaseComparisonResponse(
        case_id=case_id,
        fields=rows_out,
        rules_evaluated=rules_out,
        overall_name_similarity=overall_name_sim,
        fusion_matrix=fusion_matrix,
        evidence_graph=evidence_graph,
    )

