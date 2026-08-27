"""Structured field extraction from OCR lines (label-driven, deterministic)."""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.ocr_service import Line, OcrResult
from app.utils.normalize import normalize_address, normalize_date_str, normalize_gender, normalize_name


@dataclass
class ExtractedFieldDraft:
    field_name: str
    raw_value: str
    normalized_value: str | None
    confidence: float | None
    source_region: dict | None


@dataclass(frozen=True)
class FieldSpec:
    field_name: str
    labels: tuple[str, ...]
    kind: str  # name | date | gender | text | address
    multiline: bool = False


FIELD_SPECS: list[FieldSpec] = [
    FieldSpec("date_of_birth", ("date of birth", "dob", "birth date"), "date"),
    FieldSpec("surname_part", ("surname", "last name"), "name"),
    FieldSpec("given_names_part", ("given name", "first name"), "name"),
    FieldSpec(
        "document_number",
        (
            "document no", "passport no", "passport number", "id no", "id number",
            "card number", "pan no", "licence no", "license no", "dl no",
            "consumer no", "number",
        ),
        "text",
    ),
    FieldSpec("nationality", ("nationality",), "text"),
    FieldSpec("gender", ("gender", "sex"), "gender"),
    FieldSpec("issue_date", ("date of issue", "issue date", "issued on"), "date"),
    FieldSpec("expiry_date", ("date of expiry", "expiry date", "expires on", "valid until", "valid till"), "date"),
    FieldSpec("address", ("address", "residing at"), "address", multiline=True),
]

# Direct full-name labels (checked only when no surname/given-name parts
# exist). Multiline so letter-style docs with the value on the next line work.
_FULL_NAME_SPEC = FieldSpec(
    "full_name", ("full name", "name", "holder name", "cardholder"), "name",
    multiline=True,
)

_LABEL_PATTERN_CACHE: dict[str, re.Pattern] = {}


def _label_pattern(labels: tuple[str, ...]) -> re.Pattern:
    key = ",".join(labels)
    if key not in _LABEL_PATTERN_CACHE:
        # Longest label first so 'passport number' wins over 'number'.
        ordered = sorted(labels, key=len, reverse=True)
        joined = "|".join(re.escape(l) for l in ordered)
        _LABEL_PATTERN_CACHE[key] = re.compile(
            rf"(?:^|[\s•·|])({joined})\b\s*:?\s*(.*)$", re.IGNORECASE
        )
    return _LABEL_PATTERN_CACHE[key]


def _line_has_label_colon(labels: tuple[str, ...], text: str) -> bool:
    joined = "|".join(re.escape(l) for l in sorted(labels, key=len, reverse=True))
    return re.search(rf"\b({joined})\s*:", text, re.IGNORECASE) is not None


_ANY_LABEL_START = re.compile(
    r"^\s*("
    + "|".join(
        sorted(
            {re.escape(l) for spec in FIELD_SPECS for l in spec.labels},
            key=len,
            reverse=True,
        )
    )
    + r")\b\s*:?",
    re.IGNORECASE,
)


def _looks_like_label_line(text: str) -> bool:
    return _ANY_LABEL_START.match(text) is not None


_NAME_LABEL_NOISE = re.compile(
    r"^((full|holder|cardholder|resident|father'?s|mother'?s)?\s*name[s]?)\s*:?\s*",
    re.IGNORECASE,
)


def _strip_name_label_noise(raw: str) -> str:
    out = raw
    while True:
        stripped = _NAME_LABEL_NOISE.sub("", out).strip()
        if stripped == out or not stripped:
            return stripped
        out = stripped


_DATE_TOKEN = re.compile(r"\d{1,2}[./-]\d{1,2}[./-]\d{4}|\b\d{8}\b")


def _normalize(kind: str, raw: str) -> str | None:
    raw = raw.strip().strip(":;,")
    if not raw:
        return None
    if kind == "name":
        cleaned = _strip_name_label_noise(raw)
        cleaned = re.sub(r"[^A-Za-z\s'\-]", "", cleaned).strip()
        return normalize_name(cleaned) or None
    if kind == "date":
        # Extract the first date-shaped token so neighbouring OCR noise
        # (e.g. QR-region garble) does not break parsing.
        m = _DATE_TOKEN.search(raw)
        return normalize_date_str(m.group(0)) if m else normalize_date_str(raw)
    if kind == "gender":
        return normalize_gender(raw)
    if kind == "address":
        return normalize_address(raw) or None
    cleaned = re.sub(r"\s{2,}", " ", raw).upper()
    return cleaned or None


def _compose_full_name(
    drafts: list[ExtractedFieldDraft], lines: list[Line]
) -> None:
    """Merge surname/given-name parts into a single full_name field."""
    surname = next((d for d in drafts if d.field_name == "surname_part"), None)
    given = next((d for d in drafts if d.field_name == "given_names_part"), None)
    if surname is None and given is None:
        return

    direct = next((d for d in drafts if d.field_name == "full_name"), None)
    for part in (surname, given):
        if part is not None:
            drafts.remove(part)

    combined_norm = " ".join(
        x.normalized_value
        for x in (given, surname)
        if x is not None and x.normalized_value
    ).strip()
    combined_raw = " ".join(x.raw_value for x in (given, surname) if x is not None and x.raw_value).strip()
    confs = [x.confidence for x in (given, surname) if x is not None and x.confidence is not None]

    if direct is not None:
        # Surname+given-name parts, when both exist, are authoritative over
        # any direct capture (which may carry OCR noise from wider spans).
        if given is None or surname is None:
            return
        drafts.remove(direct)

    region = (given or surname).source_region
    drafts.append(
        ExtractedFieldDraft(
            field_name="full_name",
            raw_value=combined_raw,
            normalized_value=combined_norm or None,
            confidence=round(sum(confs) / len(confs), 1) if confs else None,
            source_region=region,
        )
    )


def extract_fields(ocr_result: OcrResult) -> list[ExtractedFieldDraft]:
    """Run label-driven extraction over ordered OCR lines."""
    specs = [*FIELD_SPECS]
    # Direct full-name labels are only consulted when no parts were found;
    # try them last so 'surname'/'given name' win on passport-style layouts.
    drafts: list[ExtractedFieldDraft] = []
    lines = ocr_result.lines

    def match_spec(spec: FieldSpec) -> bool:
        # Approximate document height from line extents to identify the
        # header/title band, where labels are unreliable.
        approx_height = (
            max((l.bbox[1] + l.bbox[3]) for l in lines) if lines else 0
        )
        for idx, line in enumerate(lines):
            m = _label_pattern(spec.labels).search(line.text)
            if not m:
                continue
            if line.bbox[1] + line.bbox[3] / 2 < approx_height * 0.13:
                continue  # header/title band
            value_part = m.group(2).strip()

            # If the label has no value on the same line, check the next line
            if not value_part and idx + 1 < len(lines):
                next_line = lines[idx + 1]
                if not _looks_like_label_line(next_line.text) and next_line.text.count("<") < 3:
                    value_part = next_line.text.strip()

            if spec.multiline:
                # Consume up to two follow lines until another labeled line
                # begins. OCR frequently drops colons, so label detection —
                # not punctuation — is the stop condition.
                extra: list[str] = []
                for follow in lines[idx + 1 : idx + 3]:
                    if _looks_like_label_line(follow.text):
                        break
                    if follow.text.count("<") >= 3 or re.match(
                        r"^[A-Z]\s*<[A-Z]*", follow.text
                    ):
                        break  # MRZ block — never part of a printed field
                    extra.append(follow.text.strip())
                value_part = " ".join([value_part] + extra).strip()

            normalized = _normalize(spec.kind, value_part)
            if normalized is None:
                continue
            region = {"x": line.bbox[0], "y": line.bbox[1], "w": line.bbox[2], "h": line.bbox[3]}
            drafts.append(
                ExtractedFieldDraft(
                    field_name=spec.field_name,
                    raw_value=value_part[:500],
                    normalized_value=normalized,
                    confidence=round(line.confidence, 1),
                    source_region=region,
                )
            )
            return True
        return False

    for spec in specs:
        match_spec(spec)
    match_spec(_FULL_NAME_SPEC)

    _compose_full_name(drafts, lines)

    # ---- Fallback Pattern Extraction (PAN, Aadhaar, Passport, Dates) ----
    existing_fields = {d.field_name for d in drafts}

    # 1. Document Number Patterns (e.g. Indian PAN, Aadhaar, Passport, DL)
    if "document_number" not in existing_fields:
        for line in lines:
            text = line.text.strip()
            # PAN Card pattern: ABCDE1234F
            pan_match = re.search(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", text)
            if pan_match:
                drafts.append(
                    ExtractedFieldDraft(
                        field_name="document_number",
                        raw_value=pan_match.group(0),
                        normalized_value=pan_match.group(0).upper(),
                        confidence=round(line.confidence, 1),
                        source_region={"x": line.bbox[0], "y": line.bbox[1], "w": line.bbox[2], "h": line.bbox[3]},
                    )
                )
                existing_fields.add("document_number")
                break

            # Aadhaar 12-digit pattern: XXXX XXXX XXXX
            aadhaar_match = re.search(r"\b\d{4}\s\d{4}\s\d{4}\b", text)
            if aadhaar_match:
                drafts.append(
                    ExtractedFieldDraft(
                        field_name="document_number",
                        raw_value=aadhaar_match.group(0),
                        normalized_value=aadhaar_match.group(0).replace(" ", ""),
                        confidence=round(line.confidence, 1),
                        source_region={"x": line.bbox[0], "y": line.bbox[1], "w": line.bbox[2], "h": line.bbox[3]},
                    )
                )
                existing_fields.add("document_number")
                break

    # 2. Date of Birth Pattern Fallback (e.g. DOB: DD/MM/YYYY or standalone date near 'DOB'/'Birth'/'जन्म')
    if "date_of_birth" not in existing_fields:
        for line in lines:
            text = line.text.strip()
            if re.search(r"(dob|birth|born|जन्म|yob)", text, re.IGNORECASE):
                date_m = _DATE_TOKEN.search(text)
                if date_m:
                    norm = normalize_date_str(date_m.group(0))
                    if norm:
                        drafts.append(
                            ExtractedFieldDraft(
                                field_name="date_of_birth",
                                raw_value=date_m.group(0),
                                normalized_value=norm,
                                confidence=round(line.confidence, 1),
                                source_region={"x": line.bbox[0], "y": line.bbox[1], "w": line.bbox[2], "h": line.bbox[3]},
                            )
                        )
                        existing_fields.add("date_of_birth")
                        break

    # 3. MRZ (Machine Readable Zone) Auto-Extraction Fallback for Passports
    from app.services.mrz_service import parse_mrz
    mrz = parse_mrz([l.text for l in lines])
    if mrz is not None:
        if "document_number" not in existing_fields and mrz.document_number:
            drafts.append(
                ExtractedFieldDraft(
                    field_name="document_number",
                    raw_value=mrz.document_number,
                    normalized_value=mrz.document_number.upper(),
                    confidence=95.0,
                    source_region=None,
                )
            )
            existing_fields.add("document_number")
        if "date_of_birth" not in existing_fields and mrz.dob:
            drafts.append(
                ExtractedFieldDraft(
                    field_name="date_of_birth",
                    raw_value=mrz.dob.isoformat(),
                    normalized_value=mrz.dob.isoformat(),
                    confidence=95.0,
                    source_region=None,
                )
            )
            existing_fields.add("date_of_birth")
        if "expiry_date" not in existing_fields and mrz.expiry:
            drafts.append(
                ExtractedFieldDraft(
                    field_name="expiry_date",
                    raw_value=mrz.expiry.isoformat(),
                    normalized_value=mrz.expiry.isoformat(),
                    confidence=95.0,
                    source_region=None,
                )
            )
            existing_fields.add("expiry_date")
        if "nationality" not in existing_fields and mrz.nationality:
            drafts.append(
                ExtractedFieldDraft(
                    field_name="nationality",
                    raw_value=mrz.nationality,
                    normalized_value=mrz.nationality.upper(),
                    confidence=95.0,
                    source_region=None,
                )
            )
            existing_fields.add("nationality")
        if "gender" not in existing_fields and mrz.sex in ("M", "F"):
            drafts.append(
                ExtractedFieldDraft(
                    field_name="gender",
                    raw_value=mrz.sex,
                    normalized_value=normalize_gender(mrz.sex),
                    confidence=95.0,
                    source_region=None,
                )
            )
            existing_fields.add("gender")
        if "full_name" not in existing_fields:
            mrz_full = f"{mrz.given_names} {mrz.surname}".strip()
            if mrz_full:
                drafts.append(
                    ExtractedFieldDraft(
                        field_name="full_name",
                        raw_value=mrz_full,
                        normalized_value=normalize_name(mrz_full),
                        confidence=95.0,
                        source_region=None,
                    )
                )
                existing_fields.add("full_name")

    return drafts

