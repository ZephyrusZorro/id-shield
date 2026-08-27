"""Cross-document consistency engine.

Compares extracted fields across all documents in a case using
field-appropriate comparators over normalized values. Produces structured,
explainable findings — the core evidence-fusion signal of ID-SHIELD.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field

from app.utils.normalize import names_match, normalize_address, normalize_date_str


@dataclass
class DocumentValues:
    document_id: str
    file_name: str
    fields: dict[str, str]  # field_name -> normalized (or raw) value
    document_type: str | None = None


@dataclass
class ConsistencyFinding:
    field_name: str
    severity: str  # info | low | medium | high
    documents_involved: list[dict] = dc_field(default_factory=list)
    explanation: str = ""


_FIELD_LABELS = {
    "full_name": "Name",
    "date_of_birth": "Date of Birth",
    "document_number": "Document Number",
    "gender": "Gender",
    "nationality": "Nationality",
    "issue_date": "Date of Issue",
    "expiry_date": "Date of Expiry",
    "address": "Address",
    "facial_photo": "Facial Photo",
}

# Severity per conflicting field — drives the risk engine later.
FIELD_SEVERITY = {
    "full_name": "high",
    "date_of_birth": "high",
    "document_number": "high",
    "facial_photo": "high",
    "address": "medium",
    "gender": "medium",
    "nationality": "medium",
}

# Fields that are only meaningful between documents of the SAME type:
# a passport number and a PAN number legitimately differ.
TYPE_SCOPED_FIELDS = {"document_number", "issue_date", "expiry_date"}

def _address_tokens(value: str) -> set[str]:
    tokens = normalize_address(value).split()
    return {t for t in tokens if len(t) > 1}


def _addresses_match(a: str, b: str) -> bool:
    """Overlap-coefficient match: tolerant of OCR noise at either edge."""
    ta, tb = _address_tokens(a), _address_tokens(b)
    if not ta or not tb:
        return False
    overlap = len(ta & tb) / min(len(ta), len(tb))
    return overlap >= 0.7


def values_agree(field_name: str, a: str, b: str) -> bool:
    """Field-appropriate equivalence for normalized values."""
    if field_name == "full_name":
        return names_match(a, b)
    if field_name == "address":
        return _addresses_match(a, b)
    if field_name in ("date_of_birth", "issue_date", "expiry_date"):
        da, db = normalize_date_str(a), normalize_date_str(b)
        if da and db:
            return da == db
        return a.strip() == b.strip()
    return a.strip().upper() == b.strip().upper()


def _group_documents(field_name: str, docs: list[DocumentValues]) -> list[list[DocumentValues]]:
    """Greedy grouping into agreement clusters."""
    groups: list[list[DocumentValues]] = []
    for doc in docs:
        value = doc.fields[field_name]
        placed = False
        for group in groups:
            if values_agree(field_name, group[0].fields[field_name], value):
                group.append(doc)
                placed = True
                break
        if not placed:
            groups.append([doc])
    return groups


def _explanation(
    label: str,
    field_name: str,
    groups: list[list[DocumentValues]],
) -> str:
    parts: list[str] = []
    for group in sorted(groups, key=len, reverse=True):
        names = ", ".join(d.file_name for d in group)
        value = group[0].fields[field_name]
        parts.append(f"{names} → {value}")
    return f"{label} differs across submitted documents: {'; '.join(parts)}."


def compare_documents(docs: list[DocumentValues]) -> list[ConsistencyFinding]:
    """Compare every shared comparable field across all documents.

    Person attributes (name, DOB, address...) compare across ALL documents.
    Type-scoped fields (document numbers, issue/expiry dates) compare only
    between documents of the same detected type.
    """
    if len(docs) < 2:
        return []

    common_fields: set[str] = set()
    for doc in docs:
        common_fields.update(doc.fields.keys())

    findings: list[ConsistencyFinding] = []
    for field_name in sorted(common_fields):
        present = [d for d in docs if d.fields.get(field_name)]
        if len(present) < 2 or field_name not in _FIELD_LABELS:
            continue

        label = _FIELD_LABELS.get(field_name, field_name.replace("_", " ").title())
        severity = FIELD_SEVERITY.get(field_name, "medium")

        def _involved(group: list[DocumentValues]) -> list[dict]:
            return [
                {
                    "document_id": d.document_id,
                    "file_name": d.file_name,
                    "value": d.fields[field_name],
                }
                for d in group
            ]

        if field_name in TYPE_SCOPED_FIELDS:
            # Same-type documents only: a passport number vs a PAN number is
            # not an inconsistency.
            type_groups: dict[str, list[DocumentValues]] = {}
            for d in present:
                key = (d.document_type or "other").strip().lower()
                type_groups.setdefault(key, []).append(d)

            compared_any = False
            for type_key, group in sorted(type_groups.items()):
                if len(group) < 2:
                    continue
                compared_any = True
                clusters = _group_documents(field_name, group)
                if len(clusters) == 1:
                    findings.append(
                        ConsistencyFinding(
                            field_name=field_name,
                            severity="info",
                            documents_involved=_involved(group),
                            explanation=(
                                f"{label} is consistent across the "
                                f"{len(group)} {type_key.replace('_', ' ')} document(s)."
                            ),
                        )
                    )
                else:
                    findings.append(
                        ConsistencyFinding(
                            field_name=field_name,
                            severity=severity,
                            documents_involved=_involved(group),
                            explanation=_explanation(label, field_name, clusters),
                        )
                    )
            continue

        groups = _group_documents(field_name, present)
        if len(groups) == 1:
            findings.append(
                ConsistencyFinding(
                    field_name=field_name,
                    severity="info",
                    documents_involved=_involved(present),
                    explanation=f"{label} is consistent across all {len(present)} documents.",
                )
            )
        else:
            findings.append(
                ConsistencyFinding(
                    field_name=field_name,
                    severity=severity,
                    documents_involved=_involved(present),
                    explanation=_explanation(label, field_name, groups),
                )
            )
    return findings
