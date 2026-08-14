from datetime import datetime, timezone

from jobpilot_schemas import Job
from worker.dedupe import dedupe
from worker.embed import chunk_jd


def _job(job_id: str, title: str, company: str, source: str = "adzuna") -> Job:
    return Job(
        id=job_id,
        title=title,
        company=company,
        location="London",
        source=source,
        url=f"https://example.org/{job_id}",
        jd_text="Python role. " * 200,
        posted_at=datetime(2026, 8, 13, tzinfo=timezone.utc),
    )


def test_near_duplicates_across_boards_are_dropped():
    jobs = [
        _job("a1", "Senior Python Engineer", "Monzo", "adzuna"),
        _job("r1", "Senior Python  Engineer", "Monzo", "reed"),  # same vacancy, other board
        _job("a2", "Data Engineer", "Monzo", "adzuna"),
    ]
    unique = dedupe(jobs)
    assert [j.id for j in unique] == ["a1", "a2"]


def test_long_jds_chunk_with_overlap():
    chunks = chunk_jd(_job("a1", "Senior Python Engineer", "Monzo"))
    assert len(chunks) > 1
    assert all(len(c) <= 1200 for c in chunks)
