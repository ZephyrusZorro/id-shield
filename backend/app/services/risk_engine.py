"""Explainable weighted risk engine.

Fuses independent evidence (cross-document conflicts, forensic indicators,
validation failures, MRZ outcomes) into a 0-100 score. Every applied weight
becomes an auditable ledger entry; the configuration lives in
risk_weights.json and is policy — not a measurement.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from app.core.config import BACKEND_DIR

WEIGHTS_PATH = Path(__file__).resolve().parents[1] / "core" / "risk_weights.json"

# CrossDocumentFinding.field_name -> risk factor key.
_FIELD_FACTOR = {
    "date_of_birth": "dob_mismatch",
    "full_name": "name_mismatch",
    "document_number": "document_number_mismatch",
    "address": "address_mismatch",
    "gender": "gender_nationality_mismatch",
    "nationality": "gender_nationality_mismatch",
    "facial_photo": "face_mismatch",
}


@lru_cache(maxsize=1)
def load_config() -> dict:
    with open(WEIGHTS_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


@dataclass
class RiskFactorDraft:
    factor: str
    score: int
    direction: str  # increase | decrease
    explanation: str


@dataclass
class RiskInput:
    """Aggregated evidence for one case."""

    conflict_fields: list[dict] = field(default_factory=list)
    # [{field_name, severity}]
    forensic_findings: list[dict] = field(default_factory=list)
    # [{severity}]
    validation_fail_count: int = 0
    has_expired_document: bool = False
    mrz_checksum_fail: bool = False
    mrz_valid_present: bool = False
    duplicate_hits: int = 0
    name_consistent: bool = False
    address_consistent: bool = False
    face_consistent: bool = False
    all_validations_pass: bool = False
    has_any_evidence: bool = False  # any OCR/validation output at all


def _factor_weight(cfg: dict, key: str) -> tuple[int, int | None]:
    raw = cfg["factors"][key]
    if isinstance(raw, dict):
        return int(raw["weight"]), raw.get("cap")
    return int(raw), None


def evaluate(inp: RiskInput) -> dict:
    cfg = load_config()
    factors: list[RiskFactorDraft] = []
    total = 0

    def add(key: str, applications: int, explanation: str) -> None:
        nonlocal total
        if applications <= 0:
            return
        weight, cap = _factor_weight(cfg, key)
        applied = min(applications, cap) if cap else applications
        contribution = weight * applied
        total += contribution
        if applications > applied:
            detail = f" ({applications} occurrences, capped at {applied})"
        elif applied > 1:
            detail = f" ({applied} occurrences)"
        else:
            detail = ""
        factors.append(
            RiskFactorDraft(
                factor=key,
                score=contribution,
                direction="increase",
                explanation=f"{explanation}{detail}",
            )
        )

    # --- increases -------------------------------------------------------
    seen_conflicts: set[str] = set()
    for c in inp.conflict_fields:
        key = _FIELD_FACTOR.get(c["field_name"])
        if key is None or c.get("severity") not in ("medium", "high"):
            continue
        seen_conflicts.add(key)
        label = c["field_name"].replace("_", " ")
        add(
            key,
            1,
            f"Cross-document conflict detected in {label}.",
        )

    forensics_high = sum(1 for f in inp.forensic_findings if f["severity"] == "high")
    forensics_medium = sum(1 for f in inp.forensic_findings if f["severity"] == "medium")
    add("forensic_high", forensics_high, "High-suspicion visual tampering indicator(s).")
    add("forensic_medium", forensics_medium, "Visual tampering indicator(s) detected.")
    add(
        "validation_fail_per_check",
        inp.validation_fail_count,
        "Structural/logical validation check(s) failed.",
    )
    if inp.has_expired_document:
        add("expired_document", 1, "At least one submitted document is expired.")
    if inp.mrz_checksum_fail:
        add("mrz_checksum_fail", 1, "MRZ checksum verification failed.")
    if inp.duplicate_hits > 0:
        add(
            "document_reuse",
            1,
            "This identity evidence was reused across submissions "
            f"({inp.duplicate_hits} match(es) found).",
        )

    # --- reductions -------------------------------------------------------
    # POLICY: reductions apply only when no gating signal exists. Direct
    # identity conflicts, high-suspicion forensic indicators and evidence
    # reuse can never be cancelled out by consistent evidence.
    has_gating_conflict = (
        bool(seen_conflicts) or forensics_high > 0 or inp.duplicate_hits > 0
    )

    def reduce(key: str, condition: bool, explanation: str) -> None:
        nonlocal total
        if not condition or has_gating_conflict:
            return
        contribution = int(cfg["reductions"][key])
        total += contribution
        factors.append(
            RiskFactorDraft(
                factor=key,
                score=contribution,
                direction="decrease",
                explanation=explanation,
            )
        )

    reduce("name_consistent", inp.name_consistent, "Name consistent across documents.")
    reduce("address_consistent", inp.address_consistent, "Address consistent across documents.")
    reduce("face_matched", inp.face_consistent, "Facial photo consistent across documents.")
    reduce("mrz_valid", inp.mrz_valid_present, "MRZ checksums verified successfully.")
    reduce(
        "all_validations_pass",
        inp.all_validations_pass and inp.validation_fail_count == 0,
        "All document validation checks passed.",
    )

    score = max(0, min(100, total))
    band, recommendation = _band_for(cfg, score)

    if not inp.has_any_evidence:
        recommendation = cfg["unable_to_verify_recommendation"]

    return {
        "score": score,
        "band": band,
        "recommendation": recommendation,
        "factors": [
            {"factor": f.factor, "score": f.score, "direction": f.direction, "explanation": f.explanation}
            for f in factors
        ],
    }


def _band_for(cfg: dict, score: int) -> tuple[str, str]:
    for band in sorted(cfg["bands"], key=lambda b: b["max"]):
        if score <= band["max"]:
            return band["label"], band["recommendation"]
    last = sorted(cfg["bands"], key=lambda b: b["max"])[-1]
    return last["label"], last["recommendation"]
