"""Normalisation helpers shared by all ingestion sources."""

import html
import re

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t]+")
_OUTSIDE_IR35 = re.compile(r"outside\s+ir\s?35", re.IGNORECASE)
_INSIDE_IR35 = re.compile(r"inside\s+ir\s?35", re.IGNORECASE)


def strip_html(text: str) -> str:
    """Greenhouse ships HTML-escaped HTML; Lever/Workable ship HTML. Flatten to text."""
    unescaped = html.unescape(text)
    no_tags = _TAG.sub(" ", unescaped)
    return "\n".join(_WS.sub(" ", line).strip() for line in no_tags.splitlines() if line.strip())


def detect_ir35(jd_text: str) -> bool | None:
    """ir35_flag semantics: True = inside IR35, False = outside IR35, None = unknown.

    Only meaningful for contract roles; JDs that state it usually say
    "outside IR35" / "inside IR35" verbatim.
    """
    if _OUTSIDE_IR35.search(jd_text):
        return False
    if _INSIDE_IR35.search(jd_text):
        return True
    return None


def map_adzuna_contract(contract_type: str | None, contract_time: str | None) -> str | None:
    """Adzuna splits contract kind (permanent/contract) from hours (full/part time)."""
    if contract_time == "part_time":
        return "part_time"
    if contract_type in ("permanent", "contract"):
        return contract_type
    return None
