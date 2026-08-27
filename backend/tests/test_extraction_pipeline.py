"""Tests for normalization, classification, extraction, and preprocessing."""
from pathlib import Path

import numpy as np
import pytest

from app.services import classifier_service, extraction_service
from app.services.ocr_service import Line, OcrResult, Word
from app.utils.normalize import (
    names_match,
    normalize_address,
    normalize_date_str,
    normalize_gender,
    normalize_name,
)


def _line(text: str, y: int = 100, conf: float = 95.0) -> Line:
    return Line(
        text=text,
        confidence=conf,
        bbox=(40, y, 600, 30),
        words=[Word(text=text, confidence=conf, bbox=(40, y, 100, 20))],
    )


def _ocr(lines: list[Line]) -> OcrResult:
    return OcrResult(
        lines=lines,
        engine="test",
        mean_confidence=95.0,
        full_text="\n".join(l.text for l in lines),
    )


# ------------------------------------------------------------ normalization
def test_normalize_name_folds_case_and_spaces():
    assert normalize_name("  rahul   sharma ") == "RAHUL SHARMA"
    assert normalize_name("RAHUL SHARMA") == normalize_name("rahul sharma")


def test_names_match_subset_and_distinct():
    assert names_match("Rahul Sharma", "RAHUL   SHARMA")
    assert names_match("Rahul Sharma", "R Sharma")  # initial form subset
    assert not names_match("Rahul Sharma", "Rahul Verma")


def test_normalize_dates_multi_format():
    assert normalize_date_str("12/05/2001") == "2001-05-12"
    assert normalize_date_str("02-02-2033") == "2033-02-02"
    assert normalize_date_str("2033/02/02") is None
    assert normalize_date_str("not a date") is None


def test_normalize_misc():
    assert normalize_gender("Male") == "M"
    assert normalize_gender("F") == "F"
    assert normalize_gender("x") is None
    a = normalize_address("14, Lakeview ROAD; Pune-411001")
    b = normalize_address("14 lakeview road pune 411001")
    assert a == b


# -------------------------------------------------------------- classifier
def test_classifies_passport_from_keywords():
    text = "PASSPORT SAMPLE REPUBLIC SURNAME SHARMA GIVEN NAME RAHUL NATIONALITY INDIAN DATE OF EXPIRY"
    t, l, c = classifier_service.classify_document(text)
    assert t == "passport" and c > 0.3


def test_unrecognized_text_maps_to_other():
    t, l, c = classifier_service.classify_document("random grocery list milk eggs")
    assert t == "other" and l == classifier_service.OTHER_LABEL


# -------------------------------------------------------------- extraction
def test_extract_fields_labels_and_dates():
    ocr = _ocr(
        [
            _line("HEADER TITLE BAND", y=10),
            _line("Full Name: RAHUL SHARMA", y=150),
            _line("Date of Birth 12/05/2001", y=214),
            _line("Gender M", y=278),
            _line("Passport No SR0421965", y=342),
        ]
    )
    fields = {f.field_name: f for f in extraction_service.extract_fields(ocr)}
    assert fields["full_name"].normalized_value == "RAHUL SHARMA"
    assert fields["date_of_birth"].normalized_value == "2001-05-12"
    assert fields["gender"].normalized_value == "M"
    assert fields["document_number"].normalized_value == "SR0421965"


def test_surname_given_compose_into_full_name():
    ocr = _ocr(
        [
            _line("Surname SHARMA", y=150),
            _line("Given Name RAHUL", y=214),
        ]
    )
    fields = {f.field_name: f for f in extraction_service.extract_fields(ocr)}
    assert "full_name" in fields
    assert fields["full_name"].normalized_value == "RAHUL SHARMA"
    assert "surname_part" not in fields and "given_names_part" not in fields


def test_header_title_does_not_hijack_address():
    ocr = _ocr(
        [
            _line("ADDRESS PROOF CERTIFICATE", y=20),
            _line("ISSUED BY DEMO SOCIETY", y=60),
            _line("RESIDING AT:", y=300),
            _line("14 LAKEVIEW ROAD PUNE 411001", y=340),
        ]
    )
    fields = extraction_service.extract_fields(ocr)
    addresses = [f for f in fields if f.field_name == "address"]
    assert len(addresses) == 1
    assert "lakeview" in addresses[0].normalized_value
    assert "certificate" not in addresses[0].normalized_value


def test_confidence_is_line_average_not_fabricated():
    ocr = _ocr([_line("Name RAHUL", conf=80.0)])
    fields = extraction_service.extract_fields(ocr)
    assert fields[0].confidence == 80.0


# ----------------------------------------------------------- preprocessing
def test_preprocessing_caps_resolution_and_writes_derivative(tmp_path):
    from app.services.preprocessing_service import preprocess

    big = np.full((1600, 3200, 3), 255, dtype=np.uint8)
    out = tmp_path / "proc.png"
    meta = preprocess(big, out)
    assert out.is_file()
    assert max(meta["width"], meta["height"]) <= 2000
    assert any(s.startswith("resized") for s in meta["steps"])
