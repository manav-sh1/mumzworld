"""Lightweight input parser — extracts structured params from raw queries."""
from __future__ import annotations

import re

from backend.gift_finder.schemas import ParsedParams

# Age patterns: "6-month-old", "6 months", "newborn", "toddler", "3-year-old"
_AGE_MONTH_RE = re.compile(r"(\d{1,3})\s*[-–]?\s*months?\s*[-–]?\s*old|(\d{1,3})\s*months?", re.I)
_AGE_YEAR_RE = re.compile(r"(\d{1,2})\s*[-–]?\s*years?\s*[-–]?\s*old|(\d{1,2})\s*years?", re.I)
_BUDGET_RE = re.compile(
    r"(?:under|below|budget|less than|max|maximum|up to)?\s*(\d[\d,]*)\s*(?:aed|درهم|dirhams?)",
    re.I,
)
_BUDGET_AR_RE = re.compile(r"(?:ميزانية|أقل من|تحت)\s*(\d[\d,]*)", re.I)

_AGE_KEYWORDS: dict[str, int] = {
    "newborn": 0,
    "مولود": 0,
    "حديث الولادة": 0,
    "infant": 3,
    "toddler": 18,
    "طفل صغير": 18,
}

_OCCASION_KEYWORDS = [
    "birthday", "baby shower", "eid", "christmas", "عيد ميلاد",
    "عيد", "حفلة", "مناسبة", "shower", "just because",
]


def detect_language(text: str) -> str:
    """Return 'ar' if ≥30 % of characters are Arabic, else 'en'."""
    arabic_count = sum(1 for ch in text if "\u0600" <= ch <= "\u06FF")
    ratio = arabic_count / max(len(text), 1)
    return "ar" if ratio >= 0.3 else "en"


def _extract_age(text: str) -> int | None:
    lower = text.lower()
    for keyword, months in _AGE_KEYWORDS.items():
        if keyword in lower:
            return months
    m = _AGE_MONTH_RE.search(text)
    if m:
        return int(m.group(1) or m.group(2))
    m = _AGE_YEAR_RE.search(text)
    if m:
        return int(m.group(1) or m.group(2)) * 12
    return None


def _extract_budget(text: str) -> float | None:
    for pattern in (_BUDGET_RE, _BUDGET_AR_RE):
        m = pattern.search(text)
        if m:
            return float(m.group(1).replace(",", ""))
    return None


def _extract_occasion(text: str) -> str | None:
    lower = text.lower()
    for kw in _OCCASION_KEYWORDS:
        if kw in lower:
            return kw
    return None


def parse_query(raw: str) -> ParsedParams:
    """Extract structured parameters from a natural-language gift query."""
    return ParsedParams(
        age_months=_extract_age(raw),
        budget_aed=_extract_budget(raw),
        occasion=_extract_occasion(raw),
        interests=raw,
        language=detect_language(raw),
    )
