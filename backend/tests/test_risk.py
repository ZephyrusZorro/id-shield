"""Risk engine tests — factor math, bands, clamping, reductions."""
from app.services import risk_engine
from app.services.risk_engine import RiskInput, evaluate, load_config


def _cfg():
    return load_config()


def _w(key: str) -> int:
    raw = _cfg()["factors"][key]
    return raw["weight"] if isinstance(raw, dict) else raw


# ------------------------------------------------------------------ basics
def test_clean_consistent_case_scores_low_with_reductions():
    result = evaluate(
        RiskInput(
            conflict_fields=[
                {"field_name": "full_name", "severity": "info"},
                {"field_name": "address", "severity": "info"},
            ],
            all_validations_pass=True,
            mrz_valid_present=True,
            has_any_evidence=True,
        )
    )
    expected = (
        _cfg()["reductions"]["name_consistent"]
        + _cfg()["reductions"]["address_consistent"]
        + _cfg()["reductions"]["mrz_valid"]
        + _cfg()["reductions"]["all_validations_pass"]
    )
    assert result["score"] == max(0, expected)
    assert result["band"] == "LOW"
    assert result["recommendation"] == "verification_passed"
    assert all(f["direction"] == "decrease" for f in result["factors"])


def test_dob_conflict_alone_lands_in_medium_band():
    dob_weight = _w("dob_mismatch")
    result = evaluate(
        RiskInput(conflict_fields=[{"field_name": "date_of_birth", "severity": "high"}],
                  has_any_evidence=True)
    )
    assert result["score"] == dob_weight
    band = next(b for b in _cfg()["bands"] if dob_weight <= b["max"])
    assert result["band"] == band["label"] == "MEDIUM"
    assert result["recommendation"] == "review_recommended"


def test_signature_style_case_reaches_high_band():
    """DOB conflict + forensic indicator + validation failure stack up."""
    result = evaluate(
        RiskInput(
            conflict_fields=[{"field_name": "date_of_birth", "severity": "high"}],
            forensic_findings=[{"severity": "medium"}],
            validation_fail_count=3,
            has_any_evidence=True,
        )
    )
    expected = min(_w("dob_mismatch") + _w("forensic_medium") + 6 * 3, 100)
    assert result["score"] == expected
    assert result["score"] >= 60 or result["band"] in ("HIGH", "CRITICAL")


def test_caps_limit_factor_stacking():
    cap = _cfg()["factors"]["forensic_high"]["cap"]
    occurrences = cap + 3
    result = evaluate(
        RiskInput(
            forensic_findings=[{"severity": "high"}] * occurrences,
            has_any_evidence=True,
        )
    )
    forensics = [f for f in result["factors"] if f["factor"] == "forensic_high"]
    assert len(forensics) == 1
    assert forensics[0]["score"] == _w("forensic_high") * cap
    assert f"{occurrences} occurrences" in forensics[0]["explanation"]


def test_score_clamped_at_100():
    huge = RiskInput(
        conflict_fields=[
            {"field_name": k, "severity": "high"}
            for k in ("date_of_birth", "full_name", "document_number", "address",
                      "gender", "nationality")
        ],
        forensic_findings=[{"severity": "high"}] * 5,
        validation_fail_count=50,
        mrz_checksum_fail=True,
        has_expired_document=True,
        has_any_evidence=True,
    )
    result = evaluate(huge)
    assert result["score"] == 100
    assert result["band"] == "CRITICAL"
    assert result["recommendation"] == "manual_review_required"


def test_no_evidence_maps_to_unable_to_verify():
    result = evaluate(RiskInput(has_any_evidence=False))
    assert result["recommendation"] == _cfg()["unable_to_verify_recommendation"]


def test_mrz_outcomes_drive_both_directions():
    fail = evaluate(RiskInput(mrz_checksum_fail=True, has_any_evidence=True))
    ok = evaluate(RiskInput(mrz_valid_present=True, has_any_evidence=True))
    assert any(f["factor"] == "mrz_checksum_fail" for f in fail["factors"])
    assert any(f["factor"] == "mrz_valid" and f["direction"] == "decrease" for f in ok["factors"])
    assert ok["score"] < fail["score"] + _w("mrz_checksum_fail")


def test_reductions_suppressed_by_gating_conflict():
    """Consistent evidence must never cancel a direct identity conflict."""
    result = evaluate(
        RiskInput(
            conflict_fields=[{"field_name": "date_of_birth", "severity": "high"}],
            forensic_findings=[{"severity": "medium"}],
            name_consistent=True,
            address_consistent=True,
            mrz_valid_present=True,
            all_validations_pass=True,
            has_any_evidence=True,
        )
    )
    expected = _w("dob_mismatch") + _w("forensic_medium")
    assert result["score"] == expected
    assert all(f["direction"] == "increase" for f in result["factors"])
    assert result["recommendation"] != "verification_passed"


def test_reductions_suppressed_by_reuse():
    """A reused submission cannot be blessed into verification_passed."""
    result = evaluate(
        RiskInput(
            duplicate_hits=1,
            mrz_valid_present=True,
            all_validations_pass=True,
            has_any_evidence=True,
        )
    )
    assert result["score"] == _w("document_reuse")
    assert all(f["direction"] == "increase" for f in result["factors"])
    assert result["recommendation"] == "review_recommended"


def test_config_is_valid_and_complete():
    cfg = _cfg()
    required_factors = {
        "dob_mismatch", "name_mismatch", "document_number_mismatch",
        "address_mismatch", "gender_nationality_mismatch", "forensic_high",
        "forensic_medium", "validation_fail_per_check", "expired_document",
        "mrz_checksum_fail",
    }
    assert required_factors <= set(cfg["factors"].keys())
    bands = sorted(cfg["bands"], key=lambda b: b["max"])
    assert bands[-1]["max"] == 100
    assert all({"max", "label", "recommendation"} <= set(b) for b in bands)


def test_field_to_factor_mapping_complete_for_known_fields():
    known_fields = {
        "date_of_birth", "full_name", "document_number", "address",
        "gender", "nationality", "facial_photo",
    }
    mapped = set(risk_engine._FIELD_FACTOR.keys())
    assert known_fields == mapped
