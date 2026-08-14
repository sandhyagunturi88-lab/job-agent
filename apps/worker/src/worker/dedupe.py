"""Fuzzy dedupe: the same vacancy often appears on multiple boards."""

from difflib import SequenceMatcher

from jobpilot_schemas import Job

SIMILARITY_THRESHOLD = 0.92


def _key(job: Job) -> str:
    return f"{job.title} @ {job.company} | {job.location}".lower()


def dedupe(jobs: list[Job]) -> list[Job]:
    """Keep the first occurrence of near-identical (title, company, location)."""
    kept: list[Job] = []
    for job in jobs:
        key = _key(job)
        if any(
            SequenceMatcher(None, key, _key(existing)).ratio() >= SIMILARITY_THRESHOLD
            for existing in kept
        ):
            continue
        kept.append(job)
    return kept
