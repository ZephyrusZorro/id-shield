"""Document type detection via keyword-signature templates + layout heuristics + regex patterns.

The template registry keeps the verification engine decoupled from any single
document format; new templates are additive.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class TemplateSpec:
    type_name: str
    label: str
    keywords: dict[str, float] = field(default_factory=dict)
    regex_patterns: tuple[str, ...] = ()
    aspect_range: tuple[float, float] | None = None  # width / height


TEMPLATES: list[TemplateSpec] = [
    TemplateSpec(
        type_name="aadhaar",
        label="Aadhaar Card",
        keywords={
            "aadhaar": 8.0,
            "uidai": 7.0,
            "mera aadhaar": 5.0,
            "unique identification": 5.0,
            "government of india": 3.0,
            "enrolment": 3.0,
            "enrolment no": 4.0,
            "vid": 3.0,
            "help@uidai.gov.in": 4.0,
            "1947": 2.0,
            "my aadhaar": 3.5,
            "year of birth": 2.5,
            "father:": 2.0,
            "husband:": 2.0,
        },
        regex_patterns=(
            r"\b[2-9]\d{3}\s\d{4}\s\d{4}\b",  # 12-digit spaced UID
            r"\b\d{4}\s\d{4}\s\d{4}\s\d{4}\b",  # 16-digit VID
        ),
        aspect_range=(1.35, 1.85),
    ),
    TemplateSpec(
        type_name="pan",
        label="PAN Card",
        keywords={
            "permanent account number": 8.0,
            "income tax": 5.0,
            "pan": 3.0,
            "cardholder": 2.0,
            "father's name": 2.5,
            "income tax department": 5.0,
            "govt. of india": 3.0,
        },
        regex_patterns=(
            r"\b[A-Za-z]{5}[0-9]{4}[A-Za-z]\b",  # Standard 10-char PAN
        ),
        aspect_range=(1.4, 2.0),
    ),
    TemplateSpec(
        type_name="driving_licence",
        label="Driving Licence",
        keywords={
            "driving licence": 7.5,
            "driving license": 7.5,
            "driver license": 7.5,
            "dl no": 4.0,
            "licence to drive": 4.0,
            "authorised to drive": 3.5,
            "transport department": 4.0,
            "union of india": 3.0,
            "blood group": 2.0,
            "valid till": 2.0,
            "motor vehicle": 3.0,
        },
        regex_patterns=(
            r"\b[A-Za-z]{2}[-\s]?\d{2}[-\s]?\d{4}[-\s]?\d{7}\b",  # Standard Indian DL format
        ),
        aspect_range=(1.3, 2.0),
    ),
    TemplateSpec(
        type_name="passport",
        label="Passport",
        keywords={
            "passport": 7.0,
            "republic of india": 4.0,
            "surname": 3.0,
            "given name": 3.0,
            "nationality": 2.5,
            "date of expiry": 2.0,
            "p<": 5.0,
            "type p": 3.0,
        },
        regex_patterns=(
            r"\bP<[A-Za-z]{3}",  # ICAO passport MRZ line 1 indicator
            r"\b[A-Za-z][0-9]{7,8}\b",
        ),
        aspect_range=(1.2, 1.8),
    ),
    TemplateSpec(
        type_name="voter_id",
        label="Voter ID (EPIC)",
        keywords={
            "election commission": 7.5,
            "electoral photo identity card": 7.0,
            "identity card": 4.0,
            "epic": 6.0,
            "elector": 4.5,
            "elector's name": 4.5,
            "voter": 4.0,
            "assembly constituency": 4.0,
            "parliamentary constituency": 4.0,
            "epic no": 5.0,
            "part no": 3.0,
        },
        regex_patterns=(
            r"\b[A-Za-z]{3}[0-9]{7}\b",  # Standard 10-char alphanumeric EPIC
        ),
        aspect_range=(1.3, 1.8),
    ),
    TemplateSpec(
        type_name="visa",
        label="Visa",
        keywords={
            "visa": 6.0,
            "entries": 2.0,
            "duration of stay": 2.0,
            "valid until": 2.0,
            "v<": 3.5,
        },
    ),
    TemplateSpec(
        type_name="national_id",
        label="National ID",
        keywords={
            "national id": 6.0,
            "identity card": 4.0,
            "id no": 2.5,
            "id number": 2.5,
            "citizen": 2.0,
            "uid": 1.5,
        },
        aspect_range=(1.3, 2.0),
    ),
    TemplateSpec(
        type_name="address_proof",
        label="Address Proof",
        keywords={
            "address proof": 6.0,
            "residing at": 3.0,
            "utility": 2.5,
            "electricity": 2.5,
            "bill": 2.0,
            "consumer no": 2.0,
        },
    ),
    TemplateSpec(
        type_name="certificate",
        label="Certificate",
        keywords={
            "certificate": 6.0,
            "degree": 2.5,
            "awarded": 2.0,
            "institute": 2.0,
            "university": 2.0,
            "has successfully completed": 3.0,
        },
    ),
]

UNKNOWN_TYPE = "unknown"
UNKNOWN_LABEL = "Unknown / Unclassified"
OTHER_TYPE = "other"
OTHER_LABEL = "Other Identity Document"
_MIN_CONFIDENCE = 0.22

DOCUMENT_TYPES = [
    "aadhaar",
    "pan",
    "driving_licence",
    "passport",
    "voter_id",
    "national_id",
    "visa",
    "address_proof",
    "certificate",
    "unknown",
    "other",
]

DOCUMENT_LABELS: dict[str, str] = {
    "aadhaar": "Aadhaar Card",
    "pan": "PAN Card",
    "driving_licence": "Driving Licence",
    "passport": "Passport",
    "voter_id": "Voter ID (EPIC)",
    "national_id": "National ID",
    "visa": "Visa",
    "address_proof": "Address Proof",
    "certificate": "Certificate",
    "unknown": "Unknown / Unclassified",
    "other": "Other Identity Document",
}


def get_document_label(doc_type: str | None) -> str:
    """Return a human-readable display label for any document type code."""
    if not doc_type:
        return UNKNOWN_LABEL
    normalized = doc_type.strip().lower()
    return DOCUMENT_LABELS.get(normalized, normalized.replace("_", " ").title())


def classify_document(
    full_text: str,
    aspect_ratio: float | None = None,
    default_uncertain: str = "other",
) -> tuple[str, str, float]:
    """Return (type_name, display_label, confidence in 0..1).

    If classification confidence is below threshold, returns the specified
    uncertain fallback (defaults to "other" for backwards compatibility,
    can be set to "unknown").
    """
    text = full_text.lower()
    best: TemplateSpec | None = None
    best_score = 0.0

    for tpl in TEMPLATES:
        score = sum(w for kw, w in tpl.keywords.items() if kw in text)

        # Regex boost for structural identifiers (PAN pattern, EPIC pattern, Aadhaar digits, etc.)
        for pattern in tpl.regex_patterns:
            if re.search(pattern, full_text, re.IGNORECASE):
                score += 4.5

        if tpl.aspect_range and aspect_ratio and tpl.aspect_range[0] <= aspect_ratio <= tpl.aspect_range[1]:
            score += 1.0

        max_possible = sum(tpl.keywords.values()) + 1.0 + (len(tpl.regex_patterns) * 4.5)
        normalized = score / max_possible
        if normalized > best_score:
            best_score = normalized
            best = tpl

    if best is None or best_score < _MIN_CONFIDENCE:
        if default_uncertain == "unknown":
            return UNKNOWN_TYPE, UNKNOWN_LABEL, round(min(best_score, _MIN_CONFIDENCE), 2)
        return OTHER_TYPE, OTHER_LABEL, round(min(best_score, _MIN_CONFIDENCE), 2)

    return best.type_name, best.label, round(min(best_score, 1.0), 2)

