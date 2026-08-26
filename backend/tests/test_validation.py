"""Tests for MRZ parsing/checksums and document validation rules."""
from datetime import date, timedelta

from app.services import validation_service
from app.services.mrz_service import (
    build_td3_lines,
    compare_with_fields,
    compute_check_digit,
    parse_mrz,
    parse_td3,
)
from app.services.validation_service import ValidationDraft, overall_status

VALID_L1, VALID_L2 = build_td3_lines(
    "SHARMA", "RAHUL", "SR0421965", "SRD", "010512", "M", "330202"
)


# ------------------------------------------------------------------ MRZ math
def test_check_digit_known_vectors():
    assert compute_check_digit("012346") == "6"  # 7-3-5 weights
    assert compute_check_digit("A") == "0"  # A=10 * 7 = 70 -> 0
    assert compute_check_digit("<<<") == "0"


def test_builder_composite_matches_independent_recompute():
    """Guard against builder/parser sharing a wrong composite definition."""
    l1, l2 = build_td3_lines(
        "SHARMA", "RAHUL", "SR1429697", "SRD", "010512", "M", "340202",
        personal_number="TX97",
    )
    independent = (
        compute_check_digit(l2[0:10])
        + ""
    )
    # Recompute composite exactly as the ICAO slice defines it.
    payload = l2[0:10] + l2[13:20] + l2[21:43]
    assert compute_check_digit(payload) == l2[43]


def test_td3_roundtrip_all_checks_pass():
    mrz = parse_td3(VALID_L1, VALID_L2)
    assert mrz is not None
    assert all(v == "pass" for v in mrz.checks.values())
    assert mrz.document_number == "SR0421965"
    assert mrz.surname == "SHARMA" and mrz.given_names == "RAHUL"
    assert mrz.dob == date(2001, 5, 12)
    assert mrz.expiry == date(2033, 2, 2)


def test_corrupted_checksum_detected():
    bad = VALID_L2[:9] + ("0" if VALID_L2[9] != "0" else "1") + VALID_L2[10:]
    mrz = parse_td3(VALID_L1, bad)
    assert mrz is not None
    assert mrz.checks["document_number"] == "fail"


def test_mrz_detection_from_noisy_ocr_lines():
    lines = [
        "NATIONAL IDENTITY CARD",
        "ID NUMBER SR-8841-7723",
        VALID_L1,
        "some middle noise without fillers",
        VALID_L2,
    ]
    mrz = parse_mrz(lines)
    assert mrz is not None
    assert mrz.document_number == "SR0421965"


def test_mrz_absent_returns_none():
    assert parse_mrz(["NAME RAHUL SHARMA", "DOB 12/05/2001"]) is None


def test_mrz_field_comparison_flags_mismatch():
    mrz = parse_td3(VALID_L1, VALID_L2)
    rows = compare_with_fields(
        mrz, {"document_number": "SR9999999", "date_of_birth": "2001-05-12"}
    )
    by_type = {r["check_type"]: r for r in rows}
    assert by_type["MRZ vs printed document number"]["status"] == "fail"
    assert by_type["MRZ vs printed date of birth"]["status"] == "pass"


# ---------------------------------------------------------- validation rules
def _validate(dtype, fields, text=""):
    return {
        r.check_type: r
        for r in validation_service.validate_document(dtype, fields, text)
    }


def test_passport_with_valid_mrz_passes():
    fields = {
        "full_name": "RAHUL SHARMA",
        "document_number": "SR0421965",
        "nationality": "INDIAN",
        "date_of_birth": "2001-05-12",
        "expiry_date": "2033-02-02",
        "issue_date": "2023-02-03",
    }
    results = _validate("passport", fields, f"{VALID_L1}\n{VALID_L2}")
    assert results["Document type recognized"].status == "pass"
    assert results["Document number format"].status == "pass"
    assert results["Expiration status"].status == "pass"
    assert results["Mandatory fields"].status == "pass"
    assert results["MRZ checksum"].status == "pass"
    assert results["MRZ vs printed document number"].status == "pass"
    assert overall_status(list(results.values()), True) == "valid"


def test_expired_document_is_warning():
    expired = (date.today() - timedelta(days=30)).isoformat()
    r = _validate("visa", {"full_name": "X Y", "document_number": "V1234567", "expiry_date": expired})
    assert r["Expiration status"].status == "warning"


def test_future_dob_fails():
    future = (date.today() + timedelta(days=365)).isoformat()
    r = _validate("national_id", {"full_name": "A B", "date_of_birth": future})
    assert r["Date of birth plausibility"].status == "fail"
    assert overall_status(list(r.values()), True) == "review_required"


def test_expiry_before_issue_fails():
    r = _validate(
        "passport",
        {"full_name": "A B", "issue_date": "2030-01-01", "expiry_date": "2029-01-01"},
    )
    assert r["Issue/expiry logic"].status == "fail"


def test_pan_number_format_enforced():
    ok = _validate("pan", {"full_name": "R S", "document_number": "BRXPS1234K"})
    bad = _validate("pan", {"full_name": "R S", "document_number": "12345"})
    assert ok["Document number format"].status == "pass"
    assert bad["Document number format"].status == "fail"


def test_missing_mandatory_fields_fail():
    r = _validate("national_id", {"full_name": "A B"})
    assert r["Mandatory fields"].status == "fail"
    assert "document_number" in r["Mandatory fields"].message


def test_unable_to_verify_when_nothing_extracted():
    drafts = [ValidationDraft("X", "unavailable", "n/a")]
    assert overall_status(drafts, has_fields=False) == "unable_to_verify"
