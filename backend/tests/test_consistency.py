"""Cross-document consistency engine tests."""
from app.services.consistency_service import (
    ConsistencyFinding,
    DocumentValues,
    compare_documents,
    values_agree,
)


def _doc(doc_id: str, name: str, fields: dict, document_type: str | None = None) -> DocumentValues:
    return DocumentValues(
        document_id=doc_id, file_name=name, fields=fields, document_type=document_type
    )


# ------------------------------------------------------------- comparators
def test_names_agree_across_case_and_initials():
    assert values_agree("full_name", "RAHUL SHARMA", "rahul sharma")
    assert values_agree("full_name", "R SHARMA", "RAHUL SHARMA")
    assert not values_agree("full_name", "RAHUL SHARMA", "RAHUL VERMA")


def test_address_match_tolerates_ocr_noise():
    a = "14 lakeview road pune 411001 oo i eae"  # trailing OCR noise
    b = "14 lakeview road pune 411001 since"     # trailing label leak
    assert values_agree("address", a, b)
    assert not values_agree("address", "14 lakeview road pune", "22 mg road mumbai")


def test_dates_compare_as_iso():
    assert values_agree("date_of_birth", "12/05/2001", "2001-05-12")
    assert not values_agree("date_of_birth", "2001-05-12", "1999-05-12")


def test_document_numbers_exact():
    assert values_agree("document_number", "SR1429697", "sr1429697")
    assert not values_agree("document_number", "SR1429697", "SR1429698")


# -------------------------------------------------------------- comparisons
def test_dob_mismatch_detected_with_explanation():
    docs = [
        _doc("d1", "passport_A.png", {"date_of_birth": "2001-05-12"}),
        _doc("d2", "national_id_B.png", {"date_of_birth": "2001-05-12"}),
        _doc("d3", "pan_C.png", {"date_of_birth": "1999-05-12"}),
    ]
    findings = {f.field_name: f for f in compare_documents(docs)}
    f = findings["date_of_birth"]
    assert f.severity == "high"
    assert "pan_C.png" in f.explanation and "1999-05-12" in f.explanation
    assert len(f.documents_involved) == 3


def test_consistent_fields_reported_info():
    docs = [
        _doc("d1", "A.png", {"full_name": "RAHUL SHARMA", "address": "14 lakeview road pune"}),
        _doc("d2", "B.png", {"full_name": "RAHUL SHARMA", "address": "14 lakeview road, pune"}),
    ]
    findings = compare_documents(docs)
    assert all(f.severity == "info" for f in findings)
    names = next(f for f in findings if f.field_name == "full_name")
    assert names.explanation.startswith("Name is consistent")


def test_majority_wins_reference_and_minority_flagged():
    docs = [
        _doc("d1", "A.png", {"gender": "M"}),
        _doc("d2", "B.png", {"gender": "M"}),
        _doc("d3", "C.png", {"gender": "F"}),
    ]
    findings = {f.field_name: f for f in compare_documents(docs)}
    gender = findings["gender"]
    assert gender.severity == "medium"


def test_single_document_yields_no_findings():
    assert compare_documents([_doc("d1", "A.png", {"full_name": "X"})]) == []


def test_field_in_one_doc_only_is_skipped():
    docs = [
        _doc("d1", "A.png", {"nationality": "INDIAN", "full_name": "R S"}),
        _doc("d2", "B.png", {"full_name": "R S"}),
    ]
    fields = {f.field_name for f in compare_documents(docs)}
    assert "nationality" not in fields


# ------------------------------------------------------------ type scoping
def test_doc_numbers_across_types_not_flagged():
    """A passport number vs a PAN number is NOT an inconsistency."""
    docs = [
        _doc("d1", "passport.png", {"document_number": "SR1429697"}, document_type="passport"),
        _doc("d2", "pan.png", {"document_number": "BRXPS1234K"}, document_type="pan"),
    ]
    findings = compare_documents(docs)
    assert all(f.severity == "info" for f in findings)


def test_doc_numbers_same_type_conflict_flagged():
    docs = [
        _doc("d1", "passport_A.png", {"document_number": "SR1429697"}, document_type="passport"),
        _doc("d2", "passport_B.png", {"document_number": "SR9999999"}, document_type="passport"),
    ]
    findings = {f.field_name: f for f in compare_documents(docs)}
    assert findings["document_number"].severity == "high"


def test_dob_still_compared_across_types():
    docs = [
        _doc("d1", "passport.png", {"date_of_birth": "2001-05-12"}, document_type="passport"),
        _doc("d2", "pan.png", {"date_of_birth": "1999-05-12"}, document_type="pan"),
    ]
    findings = {f.field_name: f for f in compare_documents(docs)}
    assert findings["date_of_birth"].severity == "high"
