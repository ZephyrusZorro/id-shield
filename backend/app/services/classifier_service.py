"""Document type detection via keyword-signature templates + layout heuristics.

The template registry keeps the verification engine decoupled from any single
document format; new templates are additive.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TemplateSpec:
    type_name: str
    label: str
    keywords: dict[str, float] = field(default_factory=dict)
    aspect_range: tuple[float, float] | None = None  # width / height


TEMPLATES: list[TemplateSpec] = [
    TemplateSpec(
        type_name="passport",
        label="Passport",
        keywords={
            "passport": 6.0,
            "surname": 2.5,
            "given name": 2.5,
            "nationality": 1.5,
            "date of expiry": 1.5,
            "p<": 3.0,
            "type p": 2.0,
        },
    ),
    TemplateSpec(
        type_name="visa",
        label="Visa",
        keywords={
            "visa": 6.0,
            "entries": 2.0,
            "duration of stay": 2.0,
            "valid until": 2.0,
            "v<": 2.5,
        },
    ),
    TemplateSpec(
        type_name="national_id",
        label="National ID",
        keywords={
            "national id": 6.0,
            "identity card": 5.0,
            "id no": 2.0,
            "id number": 2.0,
            "citizen": 1.5,
            "uid": 1.5,
        },
        aspect_range=(1.3, 2.0),
    ),
    TemplateSpec(
        type_name="pan",
        label="PAN-like Document",
        keywords={
            "permanent account number": 8.0,
            "income tax": 3.0,
            "pan": 2.5,
            "cardholder": 1.5,
            "father's name": 1.5,
        },
        aspect_range=(1.4, 2.0),
    ),
    TemplateSpec(
        type_name="driving_licence",
        label="Driving Licence",
        keywords={
            "driving licence": 7.0,
            "driver license": 7.0,
            "dl no": 3.0,
            "authorised to drive": 2.5,
            "blood group": 1.0,
            "valid till": 1.5,
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

OTHER_LABEL = "Other Identity Document"
_MIN_CONFIDENCE = 0.22


def classify_document(full_text: str, aspect_ratio: float | None = None) -> tuple[str, str, float]:
    """Return (type_name, display_label, confidence in 0..1)."""
    text = full_text.lower()
    best: TemplateSpec | None = None
    best_score = 0.0

    for tpl in TEMPLATES:
        score = sum(w for kw, w in tpl.keywords.items() if kw in text)
        if tpl.aspect_range and aspect_ratio and tpl.aspect_range[0] <= aspect_ratio <= tpl.aspect_range[1]:
            score += 1.0
        max_possible = sum(tpl.keywords.values()) + 1.0
        normalized = score / max_possible
        if normalized > best_score:
            best_score = normalized
            best = tpl

    if best is None or best_score < _MIN_CONFIDENCE:
        return "other", OTHER_LABEL, round(min(best_score, _MIN_CONFIDENCE), 2)
    return best.type_name, best.label, round(min(best_score, 1.0), 2)
