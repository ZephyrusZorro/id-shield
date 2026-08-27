"""MRZ (Machine Readable Zone) parsing and ICAO 7-3-5 checksum validation.

Implements TD3 (passport, 2x44) parsing deterministically. A valid checksum
only proves structural consistency of the MRZ itself — NOT legal
authenticity of the document.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

_WEIGHTS = (7, 3, 5)


def compute_check_digit(value: str) -> str:
    """ICAO 9303 7-3-5 check digit. Digits count as themselves, A=10..Z=35,
    '<'=0."""
    total = 0
    for i, ch in enumerate(value):
        if ch.isdigit():
            v = int(ch)
        elif "A" <= ch <= "Z":
            v = ord(ch) - ord("A") + 10
        elif ch == "<":
            v = 0
        else:
            raise ValueError(f"Invalid MRZ character: {ch!r}")
        total += v * _WEIGHTS[i % 3]
    return str(total % 10)


@dataclass
class MrzResult:
    doc_code: str
    issuing_state: str
    surname: str
    given_names: str
    document_number: str
    nationality: str
    dob_raw: str
    dob: date | None
    sex: str
    expiry_raw: str
    expiry: date | None
    personal_number: str
    raw_lines: list[str] = field(default_factory=list)
    checks: dict[str, str] = field(default_factory=dict)  # pass | fail


def resolve_yyymmdd(raw: str, kind: str = "dob") -> date | None:
    """Resolve a YYMMDD MRZ date to a full date.

    - DOB uses the ICAO sliding window: yy greater than the current two-digit
      year belongs to the 1900s.
    - Expiry allows far-future dates: only years beyond current+50 fall back
      to the 1900s.
    """
    if not re.fullmatch(r"\d{6}", raw or ""):
        return None
    yy, mm, dd = int(raw[:2]), int(raw[2:4]), int(raw[4:6])
    cur = date.today().year % 100
    threshold = cur if kind == "dob" else cur + 50
    century = 1900 if yy > threshold else 2000
    try:
        return date(century + yy, mm, dd)
    except ValueError:
        return None


def _clean(value: str) -> str:
    """Strip fillers; collapse degenerate repeated-char runs produced by OCR
    misreading filler rows (e.g. 'KKKKKK')."""
    value = value.replace("<", " ").strip()
    value = re.sub(r"(.)\1{2,}", r"\1", value)
    return value.strip()


def parse_td3(line1: str, line2: str) -> MrzResult | None:
    """Parse a TD3 MRZ (2 lines x 44 characters). Returns None on structure error.

    OCR frequently confuses 0/O, 1/I, 5/S, 8/B, 2/Z inside MRZ zones. If the
    direct parse fails its checksums, a constrained homoglyph-repair pass is
    attempted and accepted only when it yields more passing checks.
    """
    result = _parse_td3_raw(line1, line2)
    repaired = _parse_td3_raw(_repair_homoglyphs(line1), _repair_homoglyphs(line2))
    if repaired is not None:
        if result is None:
            return repaired
        if sum(v == "pass" for v in repaired.checks.values()) > sum(
            v == "pass" for v in result.checks.values()
        ):
            return repaired
    return result


_HOMOGLYPHS = str.maketrans({"O": "0", "I": "1", "S": "5", "B": "8", "Z": "2"})


def _repair_homoglyphs(line: str) -> str:
    return line.translate(_HOMOGLYPHS)


def _parse_td3_raw(line1: str, line2: str) -> MrzResult | None:
    line1, line2 = line1.upper(), line2.upper()
    if len(line1) != 44 or len(line2) != 44:
        return None

    def check(payload: str, digit: str) -> str:
        try:
            return "pass" if compute_check_digit(payload) == digit else "fail"
        except ValueError:
            return "fail"

    doc_number_raw = line2[0:9]
    doc_check = check(doc_number_raw, line2[9])
    dob_raw = line2[13:19]
    dob_check = check(dob_raw, line2[19])
    expiry_raw = line2[21:27]
    exp_check = check(expiry_raw, line2[27])
    personal_raw = line2[28:42]
    per_check = check(personal_raw, line2[42])
    composite = check(line2[0:10] + line2[13:20] + line2[21:43], line2[43])

    result = MrzResult(
        doc_code=_clean(line1[0:2]) or "P",
        issuing_state=_clean(line1[2:5]),
        surname=_clean(line1[5:].split("<<")[0]),
        given_names=_clean("<<".join(line1[5:].split("<<")[1:])),
        document_number=doc_number_raw.replace("<", "").strip(),
        nationality=_clean(line2[10:13]),
        dob_raw=dob_raw,
        dob=resolve_yyymmdd(dob_raw, kind="dob"),
        sex=line2[20],
        expiry_raw=expiry_raw,
        expiry=resolve_yyymmdd(expiry_raw, kind="expiry"),
        personal_number=personal_raw.replace("<", " ").strip(),
        checks={
            "document_number": doc_check,
            "date_of_birth": dob_check,
            "expiry_date": exp_check,
            "personal_number": per_check,
            "composite": composite,
        },
    )
    result.raw_lines = [line1, line2]
    # Sanity gate: a misdetected block usually fails everything at once.
    if all(v == "fail" for v in result.checks.values()):
        return None
    return result


_MRZ_CHAR = re.compile(r"^[A-Z0-9<]+$")


def parse_mrz(text_lines: list[str]) -> MrzResult | None:
    """Detect and parse an MRZ from arbitrary OCR lines.

    Candidate lines contain multiple filler '<' chars; the best TD3 pair is
    chosen by length proximity to 44 after space removal.
    """
    candidates: list[tuple[int, str]] = []
    for idx, raw in enumerate(text_lines):
        compact = re.sub(r"\s+", "", raw).upper()
        if len(compact) >= 30 and compact.count("<") >= 5 and _MRZ_CHAR.match(compact):
            candidates.append((idx, compact))
    if len(candidates) < 2:
        return None

    best: MrzResult | None = None
    best_score = 0.0
    for a in range(len(candidates)):
        for b in range(a + 1, min(a + 4, len(candidates))):
            l1, l2 = candidates[a][1], candidates[b][1]
            length_score = 1 - (abs(len(l1) - 44) + abs(len(l2) - 44)) / 44
            if length_score <= 0.3:
                continue
            parsed = parse_td3(l1.ljust(44, "<")[:44], l2.ljust(44, "<")[:44])
            if parsed is None:
                continue
            passed = sum(1 for v in parsed.checks.values() if v == "pass")
            score = length_score * 0.5 + passed / len(parsed.checks) * 0.5
            if score > best_score:
                best_score = score
                best = parsed
    return best if best_score > 0.55 else None


def build_td3_lines(
    surname: str,
    given_names: str,
    document_number: str,
    nationality: str,
    dob_yyMMdd: str,
    sex: str,
    expiry_yyMMdd: str,
    issuing_state: str = "SRD",
    personal_number: str = "",
) -> tuple[str, str]:
    """Construct checksum-valid TD3 lines (used by the synthetic generator)."""
    name_field = f"{surname}<<{given_names}".upper()
    line1 = f"P<{issuing_state}{name_field}".replace(" ", "<")
    line1 = line1 + "<" * (44 - len(line1))

    doc_field = f"{document_number.upper():<9}".replace(" ", "<")[:9]
    personal_field = f"{personal_number.upper():<14}".replace(" ", "<")[:14]

    cd_doc = compute_check_digit(doc_field)
    cd_dob = compute_check_digit(dob_yyMMdd)
    cd_exp = compute_check_digit(expiry_yyMMdd)
    cd_per = compute_check_digit(personal_field)

    # ICAO TD3 composite covers doc+check, dob+check, expiry+check and
    # personal+check — nationality and sex are NOT part of it.
    composite_payload = (
        doc_field + cd_doc + dob_yyMMdd + cd_dob + expiry_yyMMdd + cd_exp
        + personal_field + cd_per
    )
    line2 = (
        doc_field + cd_doc
        + nationality.upper()
        + dob_yyMMdd + cd_dob
        + sex.upper()
        + expiry_yyMMdd + cd_exp
        + personal_field + cd_per
        + compute_check_digit(composite_payload)
    )
    return line1[:44], line2[:44]


def compare_with_fields(mrz: MrzResult, fields: dict[str, str]) -> list[dict]:
    """Cross-check MRZ values against OCR-extracted printed fields."""
    rows: list[dict] = []

    failed = [k for k, v in mrz.checks.items() if v != "pass"]
    rows.append(
        {
            "check_type": "MRZ checksum",
            "status": "pass" if not failed else "fail",
            "message": (
                "All MRZ check digits are structurally valid."
                if not failed
                else f"MRZ check digit failure(s): {', '.join(failed)}."
            ),
            "evidence": {"checks": mrz.checks},
        }
    )

    printed_doc = fields.get("document_number")
    if printed_doc:
        match = printed_doc.strip().upper() == mrz.document_number.upper()
        rows.append(
            {
                "check_type": "MRZ vs printed document number",
                "status": "pass" if match else "fail",
                "message": (
                    f"Document number matches MRZ ({mrz.document_number})."
                    if match
                    else f"Mismatch: printed '{printed_doc}' vs MRZ '{mrz.document_number}'."
                ),
                "evidence": {"printed": printed_doc, "mrz": mrz.document_number},
            }
        )

    printed_dob = fields.get("date_of_birth")
    if printed_dob and mrz.dob:
        match = printed_dob == mrz.dob.isoformat()
        rows.append(
            {
                "check_type": "MRZ vs printed date of birth",
                "status": "pass" if match else "fail",
                "message": (
                    f"Date of birth matches MRZ ({mrz.dob.isoformat()})."
                    if match
                    else f"Mismatch: printed {printed_dob} vs MRZ {mrz.dob.isoformat()}."
                ),
                "evidence": {"printed": printed_dob, "mrz": mrz.dob.isoformat()},
            }
        )

    printed_name = fields.get("full_name")
    from app.utils.normalize import names_match

    if printed_name:
        mrz_name = f"{mrz.given_names} {mrz.surname}".strip()
        match = names_match(printed_name, mrz_name)
        rows.append(
            {
                "check_type": "MRZ vs printed name",
                "status": "pass" if match else "warning",
                "message": (
                    f"Name consistent with MRZ ({mrz_name})."
                    if match
                    else f"Name differs from MRZ: printed '{printed_name}' vs MRZ '{mrz_name}'."
                ),
                "evidence": {"printed": printed_name, "mrz": mrz_name},
            }
        )
    return rows
