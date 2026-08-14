"""Deterministic CV text → evidence inventory parser.

Deliberately NOT an LLM call (the graph's only LLM call sites are rerank and
tailor — cost control). A rules-based parse is also the honest choice for the
evidence-only guarantee: every inventory item points back at a literal span of
the uploaded CV via source_span, so the user can audit exactly what the
tailoring step is allowed to say about them.
"""

import re

from jobpilot_schemas import CVInventoryItem

MAX_ITEMS = 200

_SECTION_HEADINGS: dict[str, str] = {
    # heading keyword -> section kind hint
    "skill": "skill",
    "technolog": "skill",
    "tools": "skill",
    "experience": "role",
    "employment": "role",
    "work history": "role",
    "career": "role",
    "education": "education",
    "qualification": "education",
    "certification": "certification",
    "certificate": "certification",
    "course": "certification",
    "achievement": "achievement",
    "award": "achievement",
    "project": "achievement",
    "summary": "summary",
    "profile": "summary",
    "about": "summary",
}

_DATE_RANGE = re.compile(
    # CVs write date ranges with en/em dashes as often as hyphens
    r"\b(19|20)\d{2}\b\s*(–|—|-|to)\s*(\b(19|20)\d{2}\b|present|now|current)",  # noqa: RUF001
    re.IGNORECASE,
)
_EDUCATION_HINT = re.compile(
    r"\b(bsc|msc|ba|ma|mba|phd|beng|meng|university|college|degree|a-levels?|gcse)\b",
    re.IGNORECASE,
)
_CERT_HINT = re.compile(r"\b(certified|certification|certificate|accredit)\b", re.IGNORECASE)
_BULLET = re.compile(r"^\s*[-•*·]\s*")
_MEASURABLE = re.compile(r"£?\d[\d,.]*%?")
_CONTACT = re.compile(r"@|(\+44|07\d{3})[\s\d]{6,}|linkedin\.com|github\.com", re.IGNORECASE)


def _looks_like_heading(line: str) -> str | None:
    """A short line matching a known section name (optionally ':'-terminated)."""
    bare = line.strip().rstrip(":").strip()
    if not bare or len(bare) > 40 or _BULLET.match(line):
        return None
    lowered = bare.lower()
    for keyword, kind in _SECTION_HEADINGS.items():
        if keyword in lowered:
            return kind
    return None


def _classify(line: str, section: str | None) -> str:
    if _CERT_HINT.search(line):
        return "certification"
    if _EDUCATION_HINT.search(line) or section == "education":
        return "education"
    if _DATE_RANGE.search(line):
        return "role"
    if section == "skill":
        return "skill"
    if section == "role":
        # bullets under an experience entry are what the role achieved
        return "achievement" if _BULLET.match(line) or _MEASURABLE.search(line) else "role"
    if section == "certification":
        return "certification"
    return "achievement" if _MEASURABLE.search(line) else "skill"


def parse_cv_text(cv_text: str) -> list[CVInventoryItem]:
    """Split a pasted/uploaded CV into typed, source-referenced inventory items."""
    items: list[CVInventoryItem] = []
    section: str | None = None
    lines = cv_text.splitlines()
    # If the CV has section headings, the preamble (name, contact details) is
    # not evidence — skip until the first heading. Headingless CVs keep it all.
    has_headings = any(_looks_like_heading(line) for line in lines)

    for line_no, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or _CONTACT.search(line):
            continue
        heading = _looks_like_heading(line)
        if heading is not None:
            section = heading
            continue
        if has_headings and section is None:
            continue
        if section == "summary":
            # Marketing copy about oneself is not evidence; skip it. Facts the
            # summary repeats will appear again in the sections below.
            continue

        kind = _classify(line, section)
        if kind == "skill" and ("," in line or "·" in line):
            # "Python, FastAPI, PostgreSQL" → one auditable item per skill
            parts = [p.strip(" •·") for p in line.split(",")]
        else:
            parts = [_BULLET.sub("", line).strip()]

        for part in parts:
            if len(part) < 2:
                continue
            items.append(
                CVInventoryItem(
                    id=f"inv-{len(items) + 1}",
                    kind=kind,  # type: ignore[arg-type]
                    text=part,
                    source_span=f"line {line_no}",
                )
            )
            if len(items) >= MAX_ITEMS:
                return items
    return items
