"""Conservative extraction of explicitly written notice facts."""

from __future__ import annotations

import re
from dataclasses import dataclass

_MONTHS = (
    r"January|February|March|April|May|June|July|August|September|"
    r"October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
)

_NUMBER_WORD = (
    r"\d{1,3}|one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|fifteen|twenty|thirty|forty|sixty|ninety"
)

_DATE_PATTERNS = (
    re.compile(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b"),
    re.compile(r"\b\d{4}-\d{1,2}-\d{1,2}\b"),
    re.compile(rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{_MONTHS})\.?,?\s+\d{{4}}\b", re.I),
    re.compile(rf"\b(?:{_MONTHS})\.?\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{4}}\b", re.I),
)

_AMOUNT_PATTERN = re.compile(
    r"(?:(?:Rs\.?|INR|₹)\s*[\d,]+(?:\.\d{1,2})?(?:\s*(?:lakh|lakhs|crore|crores))?)",
    re.I,
)

_REFERENCE_PATTERN = re.compile(
    r"\b(?:"
    r"Ref(?:erence)?\s*(?:(?:No\.?|Number|#)\s*[:\-]?|[:\-])\s*"
    r"|(?:Notice|Case|File)\s*(?:No\.?|Number|#)\s*[:\-]?\s*"
    r")([A-Z0-9][A-Z0-9./_-]{2,})\b",
    re.I,
)

_PARTY_PATTERN = re.compile(
    r"^\s*(?:To|From|Landlord|Tenant|Owner|Tenant\s+Name|Landlord\s+Name|"
    r"Name\s+of\s+(?:the\s+)?(?:Tenant|Landlord))\s*"
    r"(?:[:\-,]\s*|\n\s*)([^\n]+?)\s*$",
    re.I | re.M,
)

_DEADLINE_PATTERNS = (
    re.compile(
        rf"\b(?:within|before|by|on\s+or\s+before|no\s+later\s+than|"
        rf"not\s+later\s+than|latest\s+by)\s+(?:the\s+)?"
        rf"(?:{_NUMBER_WORD})"
        rf"(?:\s*\(\s*(?:{_NUMBER_WORD})\s*\))?"
        r"\s+(?:working\s+)?(?:days?|weeks?|months?|years?)"
        r"(?:\s+(?:of|from|after)\s+[^.;\n]{1,100})?",
        re.I,
    ),
    re.compile(
        rf"\b(?:by|on\s+or\s+before|no\s+later\s+than|not\s+later\s+than|"
        rf"latest\s+by|before)\s+(?:the\s+)?"
        rf"(?:\d{{1,2}}(?:st|nd|rd|th)?\s+)?(?:{_MONTHS})\.?\s+"
        rf"\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{4}}\b",
        re.I,
    ),
    re.compile(
        rf"\b(?:by|on\s+or\s+before|no\s+later\s+than|not\s+later\s+than|"
        rf"latest\s+by|before)\s+(?:the\s+)?"
        rf"\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{_MONTHS})\.?,?\s+\d{{4}}\b",
        re.I,
    ),
    re.compile(
        r"\b(?:by|on\s+or\s+before|no\s+later\s+than|not\s+later\s+than|"
        r"latest\s+by|before)\s+(?:the\s+)?"
        r"(?:\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{4}-\d{1,2}-\d{1,2})\b",
        re.I,
    ),
)


@dataclass(frozen=True)
class NoticeFacts:
    dates: tuple[str, ...]
    amounts: tuple[str, ...]
    parties: tuple[str, ...]
    reference_numbers: tuple[str, ...]
    deadline_language: tuple[str, ...]

    @property
    def has_facts(self) -> bool:
        return any(
            (
                self.dates,
                self.amounts,
                self.parties,
                self.reference_numbers,
                self.deadline_language,
            )
        )


def _clean(value: str) -> str:
    return " ".join(value.split()).strip(" \t\r\n,;.")


def _unique_matches(patterns, text: str) -> tuple[str, ...]:
    found: list[tuple[int, str]] = []
    for pattern in patterns:
        for match in pattern.finditer(text):
            value = _clean(match.group(0))
            if value:
                found.append((match.start(), value))

    seen: set[str] = set()
    ordered: list[str] = []
    for _, value in sorted(found, key=lambda item: item[0]):
        key = value.casefold()
        if key not in seen:
            seen.add(key)
            ordered.append(value)
    return tuple(ordered)


def _party_names(text: str) -> tuple[str, ...]:
    names: list[str] = []
    seen: set[str] = set()
    for match in _PARTY_PATTERN.finditer(text):
        name = _clean(match.group(1))
        if not name:
            continue
        key = name.casefold()
        if key not in seen:
            seen.add(key)
            names.append(name)
    return tuple(names)


def _reference_numbers(text: str) -> tuple[str, ...]:
    numbers: list[str] = []
    seen: set[str] = set()
    for match in _REFERENCE_PATTERN.finditer(text):
        value = _clean(match.group(1))
        if len(value) < 3:
            continue
        key = value.casefold()
        if key not in seen:
            seen.add(key)
            numbers.append(value)
    return tuple(numbers)


def extract_notice_facts(text: str) -> NoticeFacts:
    """Extract only facts that appear explicitly in the notice text.

    This function never calculates a deadline, infers a missing date, or
    converts relative language into a calendar date.
    """

    source = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    if not source.strip():
        return NoticeFacts((), (), (), (), ())

    return NoticeFacts(
        dates=_unique_matches(_DATE_PATTERNS, source),
        amounts=_unique_matches((_AMOUNT_PATTERN,), source),
        parties=_party_names(source),
        reference_numbers=_reference_numbers(source),
        deadline_language=_unique_matches(_DEADLINE_PATTERNS, source),
    )
