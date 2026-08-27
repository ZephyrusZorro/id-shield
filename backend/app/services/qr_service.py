"""QR / barcode payload extraction and printed-field cross-check."""
from __future__ import annotations

import json
import re

import cv2
import numpy as np


def decode_qr_payloads(image_bgr: np.ndarray) -> list[str]:
    """Decode all QR codes found on the image; returns raw payload strings."""
    detector = cv2.QRCodeDetector()
    payloads: list[str] = []
    try:
        result = detector.detectAndDecodeMulti(image_bgr)
        # OpenCV >= 4.x returns (retval, decoded_info, points[, straight_qrcode]);
        # normalize across variants.
        decoded = result[1] if isinstance(result, tuple) else None
        if decoded:
            payloads.extend(p for p in decoded if p)
    except cv2.error:  # pragma: no cover - defensive
        pass
    if not payloads:
        single, *_ = detector.detectAndDecode(image_bgr)
        if single:
            payloads.append(single)
    return payloads


def parse_payload(payload: str) -> dict | None:
    """Parse a JSON QR payload; tolerant of whitespace."""
    try:
        obj = json.loads(payload)
        return obj if isinstance(obj, dict) else None
    except (json.JSONDecodeError, ValueError):
        return None


_DOC_NO_CLEAN = re.compile(r"[^A-Z0-9\-]")


def compare_with_fields(payloads: list[dict], fields: dict[str, str]) -> list[dict]:
    """Cross-check decoded QR payloads against extracted printed fields.

    Produces ValidationDraft-shaped dicts consumed by the pipeline.
    """
    rows: list[dict] = []
    if not payloads:
        return rows

    qr_docs = [_DOC_NO_CLEAN.sub("", str(p.get("doc", "")).upper()) for p in payloads]
    qr_docs = [d for d in qr_docs if d]
    qr_names = [str(p.get("name", "")).upper().strip() for p in payloads if p.get("name")]

    printed_doc = _DOC_NO_CLEAN.sub("", (fields.get("document_number") or "").upper())
    printed_name = fields.get("full_name") or ""

    if qr_docs and printed_doc:
        match = any(qd == printed_doc for qd in qr_docs)
        rows.append(
            {
                "check_type": "QR payload vs document number",
                "status": "pass" if match else "fail",
                "message": (
                    f"QR-encoded document number matches the printed value ({printed_doc})."
                    if match
                    else (
                        f"QR/document mismatch: QR encodes {', '.join(qr_docs)} "
                        f"but the printed number reads {printed_doc}."
                    )
                ),
                "evidence": {"qr": qr_docs, "printed": printed_doc},
            }
        )

    from app.utils.normalize import names_match

    if qr_names and printed_name:
        match = any(names_match(printed_name, qn) for qn in qr_names)
        rows.append(
            {
                "check_type": "QR payload vs name",
                "status": "pass" if match else "warning",
                "message": (
                    f"Name on QR payload is consistent with the printed name."
                    if match
                    else f"QR name {qr_names} differs from printed '{printed_name}'."
                ),
                "evidence": {"qr": qr_names, "printed": printed_name},
            }
        )

    return rows
