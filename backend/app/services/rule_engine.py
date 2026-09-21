"""Custom Rule & Cross-Document Verification Engine.

Provides explainable multi-document integrity, chronological, and forensic
cross-checks:
1. Age Eligibility Rule: Minimum age at document issuance (e.g. DL >= 18).
2. Date Logic Rule: Issue date vs Expiry date, no future dates.
3. PAN Surname Consistency Rule: PAN character 5 vs applicant's surname.
4. Father/Spouse Name Consistency Rule: Cross-checks parental name consistency.
5. Name Fuzzy Similarity Rule: Quantified 0-100% similarity score across documents.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.utils.normalize import names_match, normalize_date_str, normalize_name


@dataclass
class RuleEvaluationResult:
    rule_id: str
    rule_name: str
    category: str  # identity | chronological | cross_document | structural
    status: str  # pass | warning | fail | not_applicable
    severity: str  # info | low | medium | high
    confidence: float
    explanation: str
    evidence: dict[str, Any] = field(default_factory=dict)


def compute_string_similarity(a: str, b: str) -> float:
    """Return similarity ratio (0.0 to 1.0) between two strings with token sorting."""
    norm_a = normalize_name(a)
    norm_b = normalize_name(b)
    if not norm_a or not norm_b:
        return 0.0
    if norm_a == norm_b:
        return 1.0

    # Direct sequence matcher
    direct = difflib.SequenceMatcher(None, norm_a, norm_b).ratio()

    # Token-sorted comparison (handles "Rahul Kumar Sharma" vs "Sharma Rahul Kumar")
    tokens_a = " ".join(sorted(norm_a.split()))
    tokens_b = " ".join(sorted(norm_b.split()))
    token_sorted = difflib.SequenceMatcher(None, tokens_a, tokens_b).ratio()

    return round(max(direct, token_sorted), 2)


def evaluate_age_eligibility(docs: list[dict[str, Any]]) -> RuleEvaluationResult:
    """Verifies that applicant was at least 18 years old when age-restricted IDs were issued."""
    # Find DOB across any document
    dob_str: str | None = None
    for d in docs:
        if d.get("fields", {}).get("date_of_birth"):
            dob_str = d["fields"]["date_of_birth"]
            break

    if not dob_str:
        return RuleEvaluationResult(
            rule_id="RULE-AGE-001",
            rule_name="Minimum Age at Document Issuance",
            category="chronological",
            status="not_applicable",
            severity="info",
            confidence=1.0,
            explanation="No Date of Birth available across submitted documents to verify age eligibility.",
        )

    dob = date.fromisoformat(normalize_date_str(dob_str) or dob_str)

    # Check age-restricted document types: DL, Voter ID, Passport
    restricted_types = {"driving_licence", "voter_id"}
    underage_violations = []

    for d in docs:
        dtype = (d.get("document_type") or "").strip().lower()
        issue_str = d.get("fields", {}).get("issue_date")
        if dtype in restricted_types and issue_str:
            norm_issue = normalize_date_str(issue_str) or issue_str
            try:
                issue_date = date.fromisoformat(norm_issue)
                # Compute age at issue date
                age_at_issue = (
                    issue_date.year
                    - dob.year
                    - ((issue_date.month, issue_date.day) < (dob.month, dob.day))
                )
                if age_at_issue < 18:
                    underage_violations.append({
                        "file_name": d.get("file_name", "Document"),
                        "document_type": dtype,
                        "age_at_issue": age_at_issue,
                        "issue_date": str(issue_date),
                        "dob": str(dob),
                    })
            except ValueError:
                continue

    if underage_violations:
        viol = underage_violations[0]
        return RuleEvaluationResult(
            rule_id="RULE-AGE-001",
            rule_name="Minimum Age at Document Issuance",
            category="chronological",
            status="fail",
            severity="high",
            confidence=0.95,
            explanation=(
                f"Applicant was only {viol['age_at_issue']} years old at the issuance of "
                f"{viol['file_name']} ({viol['document_type'].replace('_', ' ').title()}), "
                f"violating statutory minimum age requirement (18+)."
            ),
            evidence={"violations": underage_violations},
        )

    return RuleEvaluationResult(
        rule_id="RULE-AGE-001",
        rule_name="Minimum Age at Document Issuance",
        category="chronological",
        status="pass",
        severity="info",
        confidence=1.0,
        explanation="Applicant age at issuance meets or exceeds regulatory minimum requirements (18+).",
    )


def evaluate_date_logic(docs: list[dict[str, Any]]) -> RuleEvaluationResult:
    """Verifies chronological sequence: issue date <= expiry date and no future issue dates."""
    today = date.today()
    issues = []

    for d in docs:
        fields = d.get("fields", {})
        file_name = d.get("file_name", "Document")
        issue_str = fields.get("issue_date")
        expiry_str = fields.get("expiry_date")
        dob_str = fields.get("date_of_birth")

        if dob_str:
            norm_dob = normalize_date_str(dob_str)
            if norm_dob and date.fromisoformat(norm_dob) > today:
                issues.append(f"{file_name}: Date of birth ({norm_dob}) is in the future.")

        if issue_str:
            norm_issue = normalize_date_str(issue_str)
            if norm_issue and date.fromisoformat(norm_issue) > today:
                issues.append(f"{file_name}: Issue date ({norm_issue}) is in the future.")

        if issue_str and expiry_str:
            norm_issue = normalize_date_str(issue_str)
            norm_exp = normalize_date_str(expiry_str)
            if norm_issue and norm_exp:
                iss_d = date.fromisoformat(norm_issue)
                exp_d = date.fromisoformat(norm_exp)
                if exp_d <= iss_d:
                    issues.append(
                        f"{file_name}: Expiration date ({norm_exp}) precedes or equals issue date ({norm_issue})."
                    )

    if issues:
        return RuleEvaluationResult(
            rule_id="RULE-CHRONO-001",
            rule_name="Chronological Date Integrity",
            category="chronological",
            status="fail",
            severity="high",
            confidence=0.98,
            explanation=f"Chronological inconsistencies detected: {'; '.join(issues)}",
            evidence={"issues": issues},
        )

    return RuleEvaluationResult(
        rule_id="RULE-CHRONO-001",
        rule_name="Chronological Date Integrity",
        category="chronological",
        status="pass",
        severity="info",
        confidence=1.0,
        explanation="All dates (birth, issuance, expiration) conform to a valid chronological sequence.",
    )


def evaluate_pan_surname_consistency(docs: list[dict[str, Any]]) -> RuleEvaluationResult:
    """Verifies that the 5th character of an individual PAN matches the first letter of their surname."""
    pan_doc = None
    pan_number = None

    for d in docs:
        dtype = (d.get("document_type") or "").strip().lower()
        doc_no = d.get("fields", {}).get("document_number", "")
        if (dtype == "pan" or re.match(r"^[A-Za-z]{5}[0-9]{4}[A-Za-z]$", doc_no)) and len(doc_no) == 10:
            pan_doc = d
            pan_number = doc_no.upper()
            break

    if not pan_number:
        return RuleEvaluationResult(
            rule_id="RULE-PAN-001",
            rule_name="PAN 5th-Character Surname Check",
            category="structural",
            status="not_applicable",
            severity="info",
            confidence=1.0,
            explanation="No PAN card available to evaluate 5th-character surname checksum.",
        )

    # In Indian PAN, 4th char indicates entity (P=Person, C=Company, etc.). 5th char is surname initial.
    char_4 = pan_number[3]
    char_5 = pan_number[4]

    non_individual_entities = {"C", "H", "F", "A", "T", "B", "L", "J", "G"}
    if char_4 in non_individual_entities:
        # Non-individual PAN (Company, Firm, Trust, etc.)
        return RuleEvaluationResult(
            rule_id="RULE-PAN-001",
            rule_name="PAN 5th-Character Surname Check",
            category="structural",
            status="not_applicable",
            severity="info",
            confidence=1.0,
            explanation=f"PAN entity type indicator is '{char_4}' (non-individual entity); surname check omitted.",
        )


    # Find surname from any document
    surname = None
    for d in docs:
        fields = d.get("fields", {})
        if fields.get("surname_part"):
            surname = fields["surname_part"].strip().upper()
            break
        elif fields.get("full_name"):
            parts = fields["full_name"].strip().split()
            if len(parts) > 1:
                surname = parts[-1].upper()
                break

    if not surname:
        return RuleEvaluationResult(
            rule_id="RULE-PAN-001",
            rule_name="PAN 5th-Character Surname Check",
            category="structural",
            status="warning",
            severity="low",
            confidence=0.7,
            explanation=f"PAN is {pan_number} (expected surname initial '{char_5}'), but no distinct surname could be parsed.",
            evidence={"pan": pan_number, "expected_surname_initial": char_5},
        )

    surname_initial = surname[0].upper()
    if surname_initial == char_5:
        return RuleEvaluationResult(
            rule_id="RULE-PAN-001",
            rule_name="PAN 5th-Character Surname Check",
            category="structural",
            status="pass",
            severity="info",
            confidence=0.95,
            explanation=f"PAN 5th character '{char_5}' matches the first letter of surname '{surname}'.",
            evidence={"pan": pan_number, "surname": surname, "matched_char": char_5},
        )
    else:
        return RuleEvaluationResult(
            rule_id="RULE-PAN-001",
            rule_name="PAN 5th-Character Surname Check",
            category="structural",
            status="fail",
            severity="high",
            confidence=0.92,
            explanation=(
                f"PAN 5th character '{char_5}' does not match applicant surname '{surname}' "
                f"(expected initial '{char_5}', but found '{surname_initial}')."
            ),
            evidence={"pan": pan_number, "surname": surname, "expected_char": char_5, "actual_char": surname_initial},
        )


def evaluate_father_name_consistency(docs: list[dict[str, Any]]) -> RuleEvaluationResult:
    """Verifies consistency of Father's / Spouse's name across documents."""
    father_entries = []
    for d in docs:
        fn = d.get("fields", {}).get("father_name")
        if fn:
            father_entries.append({
                "document_id": d.get("document_id"),
                "file_name": d.get("file_name", "Document"),
                "value": fn,
            })

    if len(father_entries) < 2:
        return RuleEvaluationResult(
            rule_id="RULE-FATHER-001",
            rule_name="Parental/Guardian Name Consistency",
            category="identity",
            status="not_applicable",
            severity="info",
            confidence=1.0,
            explanation="Fewer than two documents contain Father/Guardian name fields.",
        )

    ref = father_entries[0]["value"]
    mismatches = []
    for entry in father_entries[1:]:
        if not names_match(ref, entry["value"]):
            sim = compute_string_similarity(ref, entry["value"])
            if sim < 0.75:
                mismatches.append(f"{entry['file_name']} ('{entry['value']}') vs {father_entries[0]['file_name']} ('{ref}')")

    if mismatches:
        return RuleEvaluationResult(
            rule_id="RULE-FATHER-001",
            rule_name="Parental/Guardian Name Consistency",
            category="identity",
            status="fail",
            severity="high",
            confidence=0.9,
            explanation=f"Parental name discrepancy detected across documents: {'; '.join(mismatches)}.",
            evidence={"entries": father_entries},
        )

    return RuleEvaluationResult(
        rule_id="RULE-FATHER-001",
        rule_name="Parental/Guardian Name Consistency",
        category="identity",
        status="pass",
        severity="info",
        confidence=0.95,
        explanation=f"Parental/Guardian name '{ref}' is consistent across all {len(father_entries)} reporting documents.",
        evidence={"entries": father_entries},
    )


def evaluate_name_similarity_matrix(docs: list[dict[str, Any]]) -> dict[str, Any]:
    """Generates pairwise similarity metrics across all document names."""
    names_with_docs = [
        (d.get("file_name", "Document"), d.get("fields", {}).get("full_name"))
        for d in docs
        if d.get("fields", {}).get("full_name")
    ]

    if len(names_with_docs) < 2:
        return {"overall_similarity": 1.0, "pairs": []}

    pairs = []
    total_sim = 0.0
    count = 0

    for i in range(len(names_with_docs)):
        for j in range(i + 1, len(names_with_docs)):
            name_a = names_with_docs[i][1]
            name_b = names_with_docs[j][1]
            sim = compute_string_similarity(name_a, name_b)
            pairs.append({
                "doc_a": names_with_docs[i][0],
                "name_a": name_a,
                "doc_b": names_with_docs[j][0],
                "name_b": name_b,
                "similarity": sim,
            })
            total_sim += sim
            count += 1

    return {
        "overall_similarity": round(total_sim / max(count, 1), 2),
        "pairs": pairs,
    }


def run_custom_rule_engine(docs: list[dict[str, Any]]) -> list[RuleEvaluationResult]:
    """Executes the full suite of verification rules against case documents."""
    return [
        evaluate_pan_surname_consistency(docs),
        evaluate_age_eligibility(docs),
        evaluate_date_logic(docs),
        evaluate_father_name_consistency(docs),
    ]
