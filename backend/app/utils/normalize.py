"""Deterministic value normalization for cross-document comparison."""
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

_WHITESPACE = re.compile(r"\s+")
_NON_ALNUM = re.compile(r"[^a-z0-9 ]")

DATE_FORMATS = [
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d.%m.%Y",
    "%d %b %Y",
    "%d %B %Y",
    "%Y-%m-%d",
    "%d%m%Y",  # MRZ style DDMMYYYY — last resort
]


def normalize_name(value: str) -> str:
    """Uppercase, accent-folded, single-spaced name. Not overly aggressive:
    genuinely different names must remain distinct."""
    folded = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return _WHITESPACE.sub(" ", folded).strip().upper()


def normalize_address(value: str) -> str:
    """Token-normalized address: casefolded, punctuation removed."""
    lowered = value.lower()
    cleaned = _NON_ALNUM.sub(" ", lowered)
    return _WHITESPACE.sub(" ", cleaned).strip()


def parse_date(value: str) -> date | None:
    candidate = _WHITESPACE.sub(" ", value).strip().strip(":.;,")
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(candidate, fmt).date()
        except ValueError:
            continue
    return None


def normalize_date_str(value: str) -> str | None:
    """Parse a printed date and return ISO 'YYYY-MM-DD', or None if unparseable."""
    parsed = parse_date(value)
    return parsed.isoformat() if parsed else None


def normalize_gender(value: str) -> str | None:
    v = value.strip().upper()
    if v.startswith("M"):
        return "M"
    if v.startswith("F"):
        return "F"
    return None


def _tokens_subset(a: set[str], b: set[str]) -> bool:
    """True if every token in `a` matches some token in `b` exactly or by
    initial (single-letter tokens compare on first character)."""

    def matches(x: str, y: str) -> bool:
        if x == y:
            return True
        return (len(x) == 1 or len(y) == 1) and x[:1] == y[:1]

    return bool(a) and all(any(matches(t, u) for u in b) for t in a)


def names_match(a: str, b: str) -> bool:
    """Exact normalized equality OR compatible partial forms (initials /
    missing middle names), but never fuzzy-matched into a different identity."""
    na, nb = normalize_name(a), normalize_name(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    ta, tb = set(na.split()), set(nb.split())
    return _tokens_subset(ta, tb) or _tokens_subset(tb, ta)
