"""The evidence-only guarantee: fabricated claims are blocked deterministically."""

from app.graph import stubs
from app.graph.validator import validate_tailored_cv
from jobpilot_schemas import CVChange, TailoredCV

INVENTORY = stubs.SAMPLE_INVENTORY


def _cv(*changes: CVChange) -> TailoredCV:
    return TailoredCV(job_id="job-x", changes=list(changes), full_text="")


def test_change_with_no_evidence_is_blocked():
    cv = _cv(CVChange(section="Experience", after="Led a team of 50 engineers", evidence_ids=[]))
    violations = validate_tailored_cv(cv, INVENTORY)
    assert len(violations) == 1
    assert "no evidence" in violations[0].problem


def test_unknown_evidence_id_is_blocked():
    cv = _cv(
        CVChange(section="Experience", after="Built search", evidence_ids=["inv-does-not-exist"])
    )
    violations = validate_tailored_cv(cv, INVENTORY)
    assert len(violations) == 1
    assert "inv-does-not-exist" in violations[0].problem


def test_inflated_figure_is_blocked():
    # inv-2 evidences a 40% latency cut; claiming 90% is fabrication.
    cv = _cv(
        CVChange(section="Experience", after="Cut API latency 90%", evidence_ids=["inv-2"])
    )
    violations = validate_tailored_cv(cv, INVENTORY)
    assert len(violations) == 1
    assert "90%" in violations[0].problem


def test_evidenced_change_passes():
    cv = _cv(
        CVChange(
            section="Experience",
            after="Cut p99 API latency 40% by moving hot paths to async FastAPI + Postgres",
            evidence_ids=["inv-2"],
        )
    )
    assert validate_tailored_cv(cv, INVENTORY) == []


def test_stub_tailor_output_always_validates():
    for job in stubs.SAMPLE_JOBS:
        cv = stubs.tailor(job, INVENTORY)
        assert validate_tailored_cv(cv, INVENTORY) == []
