"""Intelligent Natural Language Query & Voice Assistant Service for ID-SHIELD.

Interprets free-form spoken or typed questions from elderly and general users,
extracting real answers from case data, risk factors, forensics, and consistency checks.
"""
from __future__ import annotations

import re
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Case,
    CrossDocumentFinding,
    Document,
    ExtractedField,
    ForensicFinding,
    ValidationResult,
)
from app.services.classifier_service import get_document_label


def clean_query(q: str) -> str:
    """Normalize query text, stripping punctuation and lowercase."""
    return re.sub(r"[^\w\s]", "", q.lower()).strip()


def answer_case_query(case_id: str, query: str, db: Session) -> dict[str, Any]:
    """Provide a direct, conversational answer to any user question about a specific case."""
    case = db.get(Case, case_id)
    if not case:
        return {
            "answer": "I could not find this case in the database. Please check the case number.",
            "action": None,
            "category": "not_found",
        }

    q = clean_query(query)
    docs = db.scalars(select(Document).where(Document.case_id == case_id)).all()
    fields = db.scalars(
        select(ExtractedField)
        .join(Document, ExtractedField.document_id == Document.id)
        .where(Document.case_id == case_id)
    ).all()
    conflicts = db.scalars(
        select(CrossDocumentFinding)
        .where(CrossDocumentFinding.case_id == case_id)
        .where(CrossDocumentFinding.severity.in_(["medium", "high"]))
    ).all()
    forensics = db.scalars(
        select(ForensicFinding).where(ForensicFinding.document_id.in_([d.id for d in docs]))
    ).all()
    val_fails = db.scalars(
        select(ValidationResult)
        .where(ValidationResult.document_id.in_([d.id for d in docs]))
        .where(ValidationResult.status == "fail")
    ).all()

    applicant = case.applicant_name or "the applicant"
    doc_types = [get_document_label(d.document_type) for d in docs if d.document_type]
    doc_summary = ", and ".join(doc_types) if doc_types else f"{len(docs)} documents"

    # 1. Applicant Identity / Name / Age / Father
    if any(k in q for k in ["who is", "applicant", "name of", "person", "whose", "identity"]):
        name_fields = [f.normalized_value or f.raw_value for f in fields if "name" in f.field_name.lower() and f.normalized_value]
        name_str = name_fields[0] if name_fields else applicant
        return {
            "answer": f"The applicant in this case is {name_str}. The case reference number is {case.case_number}.",
            "action": None,
            "category": "identity",
        }

    if any(k in q for k in ["father", "guardian", "parent"]):
        father_fields = [f.normalized_value or f.raw_value for f in fields if "father" in f.field_name.lower() or "guardian" in f.field_name.lower()]
        if father_fields:
            return {
                "answer": f"The father or guardian listed on the documents is {father_fields[0]}.",
                "action": "switch_tab:Documents",
                "category": "father_name",
            }
        return {
            "answer": "No father or guardian name was detected on the submitted documents.",
            "action": "switch_tab:Documents",
            "category": "father_name",
        }

    if any(k in q for k in ["birth", "dob", "born", "age", "how old"]):
        dob_fields = [f.normalized_value or f.raw_value for f in fields if "dob" in f.field_name.lower() or "birth" in f.field_name.lower()]
        if dob_fields:
            unique_dobs = list(set(dob_fields))
            if len(unique_dobs) == 1:
                return {
                    "answer": f"The date of birth listed for {applicant} is {unique_dobs[0]}.",
                    "action": "switch_tab:Documents",
                    "category": "dob",
                }
            return {
                "answer": f"There is a discrepancy in dates of birth. The documents show different dates: {', and '.join(unique_dobs)}.",
                "action": "switch_tab:Comparison",
                "category": "dob_mismatch",
            }
        return {
            "answer": "Date of birth could not be extracted from the uploaded document scans.",
            "action": "switch_tab:Documents",
            "category": "dob",
        }

    if any(k in q for k in ["address", "location", "live", "residence"]):
        addr_fields = [f.normalized_value or f.raw_value for f in fields if "address" in f.field_name.lower()]
        if addr_fields:
            return {
                "answer": f"The address extracted from the identity card is: {addr_fields[0]}.",
                "action": "switch_tab:Documents",
                "category": "address",
            }
        return {
            "answer": "Address details were not extracted from the submitted cards.",
            "action": "switch_tab:Documents",
            "category": "address",
        }

    # 2. Fraud / Fake / Tampering / Alterations / Clones
    if any(k in q for k in ["fake", "fraud", "tamper", "tampered", "alter", "altered", "edit", "edited", "photoshop", "cloned", "forged", "genuine", "authentic", "real"]):
        high_forensics = [f for f in forensics if f.severity in ("medium", "high")]
        if not high_forensics:
            return {
                "answer": f"Good news. The security scan found no visual signs of image tampering or digital editing. The document scans for {applicant} appear authentic.",
                "action": "switch_tab:Forensics",
                "category": "forensics_clean",
            }
        details = [f.explanation for f in high_forensics[:2]]
        detail_msg = ". ".join(details)
        return {
            "answer": f"Attention: our forensic scanner detected {len(high_forensics)} anomaly that may indicate digital alteration: {detail_msg}. Manual inspection is advised.",
            "action": "switch_tab:Forensics",
            "category": "forensics_flagged",
        }

    # 3. Risk Score / Safety / Band
    if any(k in q for k in ["risk", "score", "safe", "danger", "band", "rating"]):
        score = case.overall_risk if case.overall_risk is not None else "pending"
        rec = (case.recommendation or "under evaluation").replace("_", " ")
        if isinstance(score, (int, float)):
            if score < 30:
                tone = "This is a low risk case."
            elif score < 60:
                tone = "This is a moderate risk case requiring caution."
            else:
                tone = "This is a high risk case requiring thorough human review."
            return {
                "answer": f"The overall risk score is {score} out of 100. {tone} The system recommendation is {rec}.",
                "action": None,
                "category": "risk_score",
            }
        return {
            "answer": f"The risk score is currently being computed. The preliminary recommendation is {rec}.",
            "action": None,
            "category": "risk_score",
        }

    # 4. Consistency / Match / Mismatch / Conflict
    if any(k in q for k in ["match", "mismatch", "conflict", "agree", "discrepanc", "different", "wrong"]):
        if not conflicts:
            return {
                "answer": f"All personal details, including full name and dates, match consistently across all submitted documents for {applicant}.",
                "action": "switch_tab:Comparison",
                "category": "comparison_clean",
            }
        mismatched_fields = list({c.field_name.replace("_", " ") for c in conflicts})
        return {
            "answer": f"We detected mismatched information across the cards in: {', and '.join(mismatched_fields)}. The details on one document conflict with another.",
            "action": "switch_tab:Comparison",
            "category": "comparison_mismatch",
        }

    # 5. Review / Approval / Status / Decision
    if any(k in q for k in ["approve", "approved", "reject", "rejected", "status", "decision", "verdict", "officer", "signed"]):
        if getattr(case, "review_status", None) and case.review_status != "pending_review":
            status_text = case.review_status.replace("_", " ").upper()
            officer = case.reviewer_name or "A verification officer"
            notes = f" Notes left: '{case.reviewer_notes}'." if case.reviewer_notes else ""
            return {
                "answer": f"This case has been officially marked as {status_text} by {officer}.{notes}",
                "action": None,
                "category": "review_decision",
            }
        rec = (case.recommendation or "evaluating").replace("_", " ")
        return {
            "answer": f"This case is currently pending official review. The automated recommendation is {rec}. You can record an approval or rejection in the disposition card.",
            "action": None,
            "category": "review_pending",
        }

    # 6. Documents / Cards / Files Uploaded
    if any(k in q for k in ["document", "file", "card", "how many", "which id", "aadhaar", "pan", "passport", "license", "licence"]):
        if not docs:
            return {
                "answer": "No documents have been uploaded to this case yet.",
                "action": "switch_tab:Documents",
                "category": "documents_empty",
            }
        return {
            "answer": f"There are {len(docs)} document(s) uploaded for {applicant}: {doc_summary}.",
            "action": "switch_tab:Documents",
            "category": "documents_list",
        }

    # 7. Face / Photo / Biometric / Selfie
    if any(k in q for k in ["face", "photo", "picture", "selfie", "biometric", "look like"]):
        return {
            "answer": "I am opening the Face Verification tab. Here you can inspect facial portraits, biometric similarity scores, and anti-spoofing screen replay checks.",
            "action": "switch_tab:Face Verification",
            "category": "face_verification",
        }

    # 8. Report / Audit / Export
    if any(k in q for k in ["report", "audit", "download", "dossier", "export", "pdf"]):
        return {
            "answer": "Opening the verification report tab. You can view the complete compliance audit dossier here.",
            "action": "switch_tab:Report",
            "category": "report",
        }

    # 9. Navigation commands
    if any(k in q for k in ["dashboard", "home", "main"]):
        return {
            "answer": "Taking you to the main dashboard.",
            "action": "navigate:/dashboard",
            "category": "navigate_dashboard",
        }

    if any(k in q for k in ["upload", "new screen", "new case", "start"]):
        return {
            "answer": "Opening the document upload screening page.",
            "action": "navigate:/screen/new",
            "category": "navigate_upload",
        }

    if any(k in q for k in ["history", "past", "records"]):
        return {
            "answer": "Navigating to screening history.",
            "action": "navigate:/history",
            "category": "navigate_history",
        }

    # 10. Help / Guide
    if any(k in q for k in ["help", "what can you", "how to", "assist", "guide"]):
        return {
            "answer": "You can ask me questions naturally, such as: 'Is this document fake?', 'What is the risk score?', 'Do the names match?', 'Who is the applicant?', or 'Show documents'. I can also navigate between sections for you.",
            "action": None,
            "category": "help",
        }

    # 11. General Case Overview Fallback
    rec_text = (case.recommendation or "evaluating").replace("_", " ")
    score_text = f"risk score {case.overall_risk}/100" if case.overall_risk is not None else "pending risk evaluation"
    return {
        "answer": f"For case number {case.case_number} ({applicant}): we have processed {len(docs)} documents ({doc_summary}). Current status is {rec_text} with {score_text}. You can ask about tampering, mismatches, or applicant details.",
        "action": None,
        "category": "general_overview",
    }


def answer_system_query(query: str, current_path: str | None = None) -> dict[str, Any]:
    """Provide helpful answers when user is not on a specific case page."""
    q = clean_query(query)

    if any(k in q for k in ["dashboard", "home", "main"]):
        return {
            "answer": "Navigating to the main dashboard.",
            "action": "navigate:/dashboard",
            "category": "navigate",
        }

    if any(k in q for k in ["upload", "new screen", "screen document", "add case", "start"]):
        return {
            "answer": "Opening the document screening upload page.",
            "action": "navigate:/screen/new",
            "category": "navigate",
        }

    if any(k in q for k in ["history", "past", "previous", "all cases"]):
        return {
            "answer": "Opening the verification history page.",
            "action": "navigate:/history",
            "category": "navigate",
        }

    if any(k in q for k in ["report", "dossier", "audit"]):
        return {
            "answer": "Opening reports and audit compliance logs.",
            "action": "navigate:/reports",
            "category": "navigate",
        }

    if any(k in q for k in ["analytics", "trend", "statistics", "chart"]):
        return {
            "answer": "Navigating to forensic analytics.",
            "action": "navigate:/analytics",
            "category": "navigate",
        }

    words = set(q.split())

    if any(phrase in q for phrase in ["what is id shield", "about id shield", "who are you", "what is this platform"]) or ("what" in words and "idshield" in words):
        return {
            "answer": "ID-SHIELD is an explainable identity and document forensics platform. It uses multi-modal OCR, error level analysis, biometric face cross-matching, and cross-document validation to detect fraud and assist human verifiers.",
            "action": None,
            "category": "about",
        }

    if bool(words & {"hello", "hi", "hey"}) or any(phrase in q for phrase in ["good morning", "good afternoon", "good evening"]):
        return {
            "answer": "Hello! I am your ID-SHIELD voice assistant. How can I help you today? You can ask me to navigate pages, explain the system, or summarize any case.",
            "action": None,
            "category": "greeting",
        }

    if any(k in q for k in ["help", "what can you do", "how to use", "assist"]):
        return {
            "answer": "Welcome to ID-SHIELD. I am your accessible voice assistant. You can speak or type commands like 'Go to dashboard', 'Upload documents', 'Show history', or select any identity case to ask detailed questions about applicant verification and fraud detection.",
            "action": None,
            "category": "help",
        }

    # Context-aware path explanation
    path = current_path or ""
    if "/dashboard" in path:
        return {
            "answer": "You are on the dashboard. Here you can see total processed cases, high risk alerts, and recent identity verifications. Say 'Upload documents' to start a new verification.",
            "action": None,
            "category": "current_page",
        }
    if "/screen/new" in path:
        return {
            "answer": "You are on the document upload page. Enter the applicant's name, choose identity scans like Aadhaar or PAN card, and click Submit to run multi-modal tampering analysis.",
            "action": None,
            "category": "current_page",
        }
    if "/history" in path:
        return {
            "answer": "You are on the history page. You can click on any previous case to inspect its extracted fields, risk score, and tamper findings.",
            "action": None,
            "category": "current_page",
        }

    return {
        "answer": f"I heard: '{query}'. You can say 'Go to dashboard', 'Upload new documents', 'Help me', or ask any question about the current screen.",
        "action": None,
        "category": "fallback",
    }
