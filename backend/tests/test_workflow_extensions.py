import numpy as np
import pytest
from app.services import preprocessing_service, forensic_service
from app.services.qr_service import compare_with_fields


def test_image_quality_assessment():
    # Sharp image test
    sharp_img = np.zeros((800, 1000, 3), dtype=np.uint8)
    sharp_img[::20, :] = 255
    sharp_img[:, ::20] = 255
    res = preprocessing_service.assess_image_quality(sharp_img)
    assert res["status"] in ("pass", "warning")
    assert res["sharpness"] > 0
    assert "resolution" in res

    # Blurry image test
    blur_img = np.full((300, 300, 3), 128, dtype=np.uint8)
    res_blur = preprocessing_service.assess_image_quality(blur_img)
    assert res_blur["sharpness_status"] == "poor" or res_blur["resolution_status"] == "poor"


def test_qr_dob_cross_check():
    payloads = [{"name": "AYSHA AMAL", "doc": "123456789012", "dob": "2000-06-15"}]
    matching_fields = {
        "full_name": "Aysha Amal",
        "document_number": "1234 5678 9012",
        "date_of_birth": "15/06/2000",
    }
    rows = compare_with_fields(payloads, matching_fields)
    dob_check = next((r for r in rows if "date of birth" in r["check_type"].lower()), None)
    assert dob_check is not None
    assert dob_check["status"] == "pass"

    # Mismatching DOB test (Step 4 example: QR = 2001, Printed = 2000)
    mismatch_fields = {
        "full_name": "Aysha Amal",
        "document_number": "1234 5678 9012",
        "date_of_birth": "15/06/2001",
    }
    rows_mismatch = compare_with_fields(payloads, mismatch_fields)
    dob_mismatch = next((r for r in rows_mismatch if "date of birth" in r["check_type"].lower()), None)
    assert dob_mismatch is not None
    assert dob_mismatch["status"] == "fail"
