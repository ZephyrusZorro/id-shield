"""Per-document validation checks.

Syntactic/logical validity only — a document passing these checks is NOT
proven genuine. Outcomes feed the evidence model and risk engine.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.services import mrz_service
from app.services.mrz_service import MrzResult

# Fictional-but-patterned formats; intentionally strict per type.
DOC_NUMBER_PATTERNS = {
    "passport": r"^[A-Z]{1,2}[0-9]{7,8}$",
    "national_id": r"^[A-Z]{2}-[0-9]{4}-[0-9]{4}$",
    "pan": r"^[A-Z]{5}[0-9]{4}[A-Z]$",
}

MANDATORY_FIELDS = {
    "passport": ("full_name", "date_of_birth", "document_number", "nationality", "expiry_date"),
    "national_id": ("full_name", "date_of_birth", "document_number"),
    "pan": ("full_name", "date_of_birth", "document_number"),
    "driving_licence": ("full_name", "date_of_birth", "document_number"),
    "visa": ("full_name", "document_number"),
    "address_proof": ("full_name",),
    "certificate": (),
    "other": (),
}


@dataclass
class ValidationDraft:
    check_type: str
    status: str  # pass | fail | warning | unavailable
    message: str
    evidence: dict | None = None


def _parse_iso(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def validate_document(
    document_type: str | None,
    fields: dict[str, str],
    ocr_full_text: str | None,
) -> list[ValidationDraft]:
    results: list[ValidationDraft] = []
    dtype = (document_type or "other").replace(" ", "_")

    # 1. Document type recognized
    if document_type and dtype != "other":
        results.append(
            ValidationDraft("Document type recognized", "pass",
                             f"Detected type: {dtype.replace('_', ' ')}.")
        )
    else:
        results.append(
            ValidationDraft("Document type recognized", "warning",
                            "Type could not be confidently identified.")
        )

    # 2. Document number format
    doc_no = (fields.get("document_number") or "").strip().upper()
    pattern = DOC_NUMBER_PATTERNS.get(dtype)
    if not doc_no:
        if pattern:
            results.append(ValidationDraft(
                "Document number format", "fail",
                "Mandatory document number was not found."))
    elif pattern:
        import re

        if re.match(pattern, doc_no):
            results.append(ValidationDraft(
                "Document number format", "pass",
                f"'{doc_no}' matches the expected {dtype} pattern."))
        else:
            results.append(ValidationDraft(
                "Document number format", "fail",
                f"'{doc_no}' does not match the expected {dtype} pattern.",
                {"pattern": pattern}))
    else:
        results.append(ValidationDraft(
            "Document number format", "pass",
            f"Document number present ('{doc_no}'); no type-specific pattern defined."))

    # 3-4. Date of birth format + plausibility
    dob = _parse_iso(fields.get("date_of_birth"))
    today = date.today()
    if fields.get("date_of_birth") and dob is None:
        results.append(ValidationDraft(
            "Date of birth format", "fail",
            f"Could not parse date of birth '{fields.get('date_of_birth')}'."))
    elif dob is not None:
        if dob > today:
            results.append(ValidationDraft(
                "Date of birth plausibility", "fail",
                f"Date of birth {dob.isoformat()} is in the future."))
        else:
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            if age > 120:
                results.append(ValidationDraft(
                    "Date of birth plausibility", "fail",
                    f"Implied age {age} is implausible."))
            else:
                results.append(ValidationDraft(
                    "Date of birth", "pass",
                    f"Date of birth {dob.isoformat()} (age {age})."))

    # 5. Issue/expiry ordering + 6. expiration status
    issue = _parse_iso(fields.get("issue_date"))
    expiry = _parse_iso(fields.get("expiry_date"))
    if issue and expiry and expiry <= issue:
        results.append(ValidationDraft(
            "Issue/expiry logic", "fail",
            f"Expiry {expiry.isoformat()} precedes issue date {issue.isoformat()}."))
    elif issue and dob and issue < dob:
        results.append(ValidationDraft(
            "Issue/DOB logic", "fail",
            f"Issue date {issue.isoformat()} precedes date of birth."))

    if expiry:
        if expiry < today:
            results.append(ValidationDraft(
                "Expiration status", "warning",
                f"Document expired on {expiry.isoformat()}."))
        else:
            results.append(ValidationDraft(
                "Expiration status", "pass",
                f"Valid until {expiry.isoformat()}."))

    # 7. Mandatory fields
    mandatory = MANDATORY_FIELDS.get(dtype, ())
    missing = [f for f in mandatory if not fields.get(f)]
    if mandatory:
        if missing:
            results.append(ValidationDraft(
                "Mandatory fields", "fail",
                f"Missing required field(s): {', '.join(missing)}.",
                {"missing": missing}))
        else:
            results.append(ValidationDraft(
                "Mandatory fields", "pass",
                "All required fields are present."))

    # 8. MRZ (when detectable)
    mrz = mrz_service.parse_mrz((ocr_full_text or "").splitlines()) if ocr_full_text else None
    if mrz is not None:
        results.extend(
            ValidationDraft(r["check_type"], r["status"], r["message"], r.get("evidence"))
            for r in mrz_service.compare_with_fields(mrz, fields)
        )
    elif dtype == "passport":
        results.append(ValidationDraft(
            "MRZ check", "unavailable",
            "No machine-readable zone could be detected on this passport image."))

    return results


def overall_status(results: list[ValidationDraft], has_fields: bool) -> str:
    """VALID | REVIEW REQUIRED | UNABLE TO VERIFY."""
    if results and all(r.status == "unavailable" for r in results):
        return "unable_to_verify"
    if not has_fields and not any(r.status == "pass" for r in results):
        return "unable_to_verify"
    if any(r.status == "fail" for r in results):
        return "review_required"
    if any(r.status == "warning" for r in results):
        return "review_required"
    return "valid"
