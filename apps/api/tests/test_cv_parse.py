"""Deterministic CV parser: typed items, source spans, no junk from preambles."""

# ruff: noqa: RUF001 — the sample CV intentionally uses en/em dashes, as real CVs do

from app.cv_parse import parse_cv_text

SAMPLE_CV = """Jane Doe
jane@example.com · 07700 900123 · linkedin.com/in/janedoe

Skills
Python, FastAPI, PostgreSQL, AWS

Experience
Senior Engineer — Acme Fintech, 2021–present
- Cut API p95 latency 40% by adding read replicas
- Led a team of 4 engineers

Education
BSc Computer Science, University of Leeds, 2015

Certifications
AWS Certified Solutions Architect
"""


def test_kinds_and_splitting():
    items = parse_cv_text(SAMPLE_CV)
    by_kind: dict[str, list[str]] = {}
    for item in items:
        by_kind.setdefault(item.kind, []).append(item.text)

    assert set(by_kind["skill"]) == {"Python", "FastAPI", "PostgreSQL", "AWS"}
    assert any("Acme Fintech" in t for t in by_kind["role"])
    assert any("40%" in t for t in by_kind["achievement"])
    assert any("team of 4" in t for t in by_kind["achievement"])
    assert any("University of Leeds" in t for t in by_kind["education"])
    assert any("Certified" in t for t in by_kind["certification"])


def test_preamble_and_contact_lines_are_not_evidence():
    items = parse_cv_text(SAMPLE_CV)
    texts = " | ".join(i.text for i in items)
    assert "Jane Doe" not in texts
    assert "jane@example.com" not in texts
    assert "07700" not in texts


def test_ids_unique_and_source_spans_point_at_lines():
    items = parse_cv_text(SAMPLE_CV)
    assert len({i.id for i in items}) == len(items)
    assert all(i.source_span and i.source_span.startswith("line ") for i in items)


def test_headingless_cv_still_yields_items():
    items = parse_cv_text("Built a Django app used by 2,000 people\nMentored two juniors")
    assert len(items) == 2


def test_empty_text_yields_nothing():
    assert parse_cv_text("") == []
    assert parse_cv_text("\n\n  \n") == []
