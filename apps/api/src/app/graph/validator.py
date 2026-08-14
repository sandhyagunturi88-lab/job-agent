"""Deterministic evidence validator — the evidence-only guarantee.

No LLM involved. A tailored-CV change is valid only if:
  1. it cites at least one evidence id, and
  2. every cited id exists in the user's CV inventory, and
  3. every claim token that looks like a hard fact (numbers, e.g. "40%", "£85k",
     years) also appears in at least one cited evidence item — numbers are the
     easiest thing for an LLM to inflate, so they must be literally evidenced.

Failed validation loops the graph back to tailor_cv with the violation list
(max 2 retries), then the CV is flagged for manual edit.
"""

import re

from jobpilot_schemas import CVInventoryItem, TailoredCV, ValidationViolation

_NUMBER = re.compile(r"£?\d[\d,.]*%?")


def validate_tailored_cv(
    cv: TailoredCV, inventory: list[CVInventoryItem]
) -> list[ValidationViolation]:
    known = {item.id: item for item in inventory}
    violations: list[ValidationViolation] = []

    for idx, change in enumerate(cv.changes):
        if not change.evidence_ids:
            violations.append(
                ValidationViolation(
                    job_id=cv.job_id,
                    change_index=idx,
                    problem="Change cites no evidence from the CV inventory",
                )
            )
            continue

        unknown = [eid for eid in change.evidence_ids if eid not in known]
        if unknown:
            violations.append(
                ValidationViolation(
                    job_id=cv.job_id,
                    change_index=idx,
                    problem=f"Unknown evidence ids: {', '.join(unknown)}",
                )
            )
            continue

        evidence_text = " ".join(known[eid].text for eid in change.evidence_ids)
        evidence_numbers = set(_NUMBER.findall(evidence_text))
        for num in _NUMBER.findall(change.after):
            if num not in evidence_numbers:
                violations.append(
                    ValidationViolation(
                        job_id=cv.job_id,
                        change_index=idx,
                        problem=f"Figure '{num}' does not appear in the cited evidence",
                    )
                )

    return violations
