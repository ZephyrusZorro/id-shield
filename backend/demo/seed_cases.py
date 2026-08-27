"""Seed a synthetic screening-history dataset for demos.

Run from backend/ with the project venv:
    python -m demo.seed_cases

All persons and documents are fictional; every case flows through the
same upload + analysis code paths as real usage.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.db.base import SessionLocal, init_db
from app.db.models import Case
from app.services import case_service
from app.services.demo_service import create_signature_case
from app.services.pipeline import analyze_case
from app.services.upload_service import save_upload

from demo.generate_docs import DocData, render_document


class _FakeUpload:
    """Minimal UploadFile stand-in for the save_upload service."""

    def __init__(self, path: Path, display_name: str | None = None):
        self.filename = display_name or path.name
        self.content_type = "image/png"
        self._data = path.read_bytes()

    async def read(self, n: int = -1):
        return self._data if n in (-1, len(self._data)) else self._data[:n]

    async def close(self):
        return None


def _make_doc(data: DocData, out_dir: Path, name: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    return render_document(data, out_dir / name)


def build_extra_assets(base: Path) -> dict[str, list[Path]]:
    base.mkdir(parents=True, exist_ok=True)
    built: dict[str, list[Path]] = {}

    # Priya Nair — fully consistent passport + national ID
    built["consistent"] = [
        _make_doc(DocData(
            doc_type="passport", title="SAMPLE REPUBLIC",
            subtitle="INTERNATIONAL PASSPORT — DEMO ISSUE",
            fields=[("Passport No", "SR7364120"), ("Surname", "NAIR"), ("Given Name", "PRIYA"),
                    ("Nationality", "INDIAN"), ("Date of Birth", "03/09/1998"),
                    ("Date of Issue", "11/06/2023"), ("Date of Expiry", "10/06/2033")],
            qr_payload={"name": "PRIYA NAIR", "doc": "SR7364120"}, photo_initials="PN",
        ), base, "passport_priya_nair.png"),
        _make_doc(DocData(
            doc_type="national_id", title="NATIONAL IDENTITY CARD",
            subtitle="SAMPLE REPUBLIC — CIVIL REGISTRY (DEMO)",
            fields=[("ID Number", "SR-2210-4487"), ("Full Name", "PRIYA NAIR"),
                    ("Date of Birth", "03/09/1998"), ("Gender", "F"),
                    ("Address", "8 GARDEN LANE MUMBAI 400001")],
            qr_payload={"name": "PRIYA NAIR", "doc": "SR-2210-4487"}, photo_initials="PN",
        ), base, "national_id_priya_nair.png"),
    ]

    # Arjun Mehta — name mismatch between ID card and PAN
    built["name_mismatch"] = [
        _make_doc(DocData(
            doc_type="national_id", title="NATIONAL IDENTITY CARD",
            subtitle="SAMPLE REPUBLIC — CIVIL REGISTRY (DEMO)",
            fields=[("ID Number", "SR-5591-2203"), ("Full Name", "ARJUN MEHTA"),
                    ("Date of Birth", "21/01/2000"), ("Gender", "M"),
                    ("Address", "22 HILL VIEW NAGPUR 440010")],
            qr_payload={"name": "ARJUN MEHTA", "doc": "SR-5591-2203"}, photo_initials="AM",
        ), base, "national_id_arjun_mehta.png"),
        _make_doc(DocData(
            doc_type="pan", title="PERMANENT ACCOUNT NUMBER",
            subtitle="DEMO TAX AUTHORITY — SAMPLE CARD",
            fields=[("PAN No", "CQZPM8821L"), ("Name", "ARJUN KUMAR"),
                    ("Date of Birth", "21/01/2000"), ("Father's Name", "RAKESH MEHTA")],
            qr_payload={"name": "ARJUN KUMAR", "doc": "CQZPM8821L"}, photo_initials="AM",
        ), base, "pan_arjun_mehta.png"),
    ]

    # Fatima Sheikh — address mismatch between ID card and address proof
    built["address_mismatch"] = [
        _make_doc(DocData(
            doc_type="national_id", title="NATIONAL IDENTITY CARD",
            subtitle="SAMPLE REPUBLIC — CIVIL REGISTRY (DEMO)",
            fields=[("ID Number", "SR-7734-9016"), ("Full Name", "FATIMA SHEIKH"),
                    ("Date of Birth", "14/03/1995"), ("Gender", "F"),
                    ("Address", "5 ROSE STREET HYDERABAD 500003")],
            qr_payload={"name": "FATIMA SHEIKH", "doc": "SR-7734-9016"}, photo_initials="FS",
        ), base, "national_id_fatima_sheikh.png"),
        _make_doc(DocData(
            doc_type="address_proof", title="ADDRESS PROOF CERTIFICATE",
            subtitle="ISSUED BY DEMO HOUSING SOCIETY — SYNTHETIC RECORD",
            fields=[("Resident Name:", "FATIMA SHEIKH"),
                    ("Residing At:", "19 LAKE BOULEVARD, DELHI 110002"),
                    ("Since:", "MARCH 2021"), ("Reference No.:", "HS/2021/00442")],
            qr_payload=None,
        ), base, "address_proof_fatima_sheikh.png"),
    ]

    # Vikram Rao — expired visa (single-document warning path)
    built["expired"] = [
        _make_doc(DocData(
            doc_type="visa", title="SAMPLE REPUBLIC — ENTRY VISA",
            subtitle="DEMO CONSULAR SERVICES",
            fields=[("Visa No", "VS9930417"), ("Name", "VIKRAM RAO"),
                    ("Nationality", "INDIAN"), ("Date of Birth", "07/12/1987"),
                    ("Date of Issue", "02/02/2024"), ("Valid Until", "01/08/2024")],
            qr_payload={"name": "VIKRAM RAO", "doc": "VS9930417"}, photo_initials="VR",
        ), base, "visa_vikram_rao.png"),
    ]
    return built


def seed() -> None:
    init_db()
    db = SessionLocal()
    loop = asyncio.new_event_loop()
    try:
        created: list[tuple[str, str]] = []

        existing = (
            db.query(Case).filter(Case.case_name.like("Rahul Sharma%")).first()
        )
        if not existing:
            case = create_signature_case(db)
            created.append((case.id, "signature"))

        assets_root = Path(__file__).parent / "assets" / "seed"
        datasets = build_extra_assets(assets_root)

        plans = [
            ("Priya Nair — Consistent Set (synthetic)", "consistent"),
            ("Arjun Mehta — Name Review (synthetic)", "name_mismatch"),
            ("Fatima Sheikh — Address Review (synthetic)", "address_mismatch"),
            ("Vikram Rao — Expired Visa (synthetic)", "expired"),
        ]
        for case_name, key in plans:
            case = case_service.create_case(db, case_name)
            for path in datasets[key]:
                loop.run_until_complete(save_upload(db, case, _FakeUpload(path)))
            created.append((case.id, key))

        # Duplicate-reuse case: the signature passport resubmitted verbatim.
        dup_case = case_service.create_case(db, "Reused Passport Scan (synthetic)")
        sig_passport = Path(__file__).parent / "assets" / "signature_case" / "passport_A_rahul_sharma.png"
        loop.run_until_complete(
            save_upload(db, dup_case, _FakeUpload(sig_passport, "passport_scan_resubmitted.png"))
        )
        created.append((dup_case.id, "duplicate"))

        for case_id, label in created:
            print(f"analyzing {label} case {case_id[:8]} …")
            analyze_case(case_id)

        print(f"Seeded {len(created)} synthetic cases.")
    finally:
        db.close()
        loop.close()


if __name__ == "__main__":
    seed()
