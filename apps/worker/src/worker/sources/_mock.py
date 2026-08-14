"""Deterministic mock jobs, keyed by source, until real API keys are supplied."""

from datetime import datetime, timezone

from jobpilot_schemas import Job, JobSource

_POSTED = datetime(2026, 8, 13, 6, 30, tzinfo=timezone.utc)


def mock_jobs(source: JobSource) -> list[Job]:
    return [
        Job(
            id=f"mock-{source}-1",
            title="Senior Python Engineer",
            company=f"{source.title()} Sample Co",
            location="London",
            salary_min=80000,
            salary_max=100000,
            contract_type="permanent",
            source=source,
            url=f"https://example.org/{source}/1",
            jd_text="Python, FastAPI, Postgres, AWS. Hybrid London.",
            posted_at=_POSTED,
        ),
        Job(
            id=f"mock-{source}-2",
            title="Data Engineer",
            company=f"{source.title()} Sample Co",
            location="Manchester",
            salary_min=60000,
            salary_max=75000,
            contract_type="permanent",
            source=source,
            url=f"https://example.org/{source}/2",
            jd_text="Airflow, dbt, Python, Snowflake.",
            posted_at=_POSTED,
        ),
    ]
