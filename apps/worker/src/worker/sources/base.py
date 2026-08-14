"""Ingestion source interface.

Every source (Adzuna, Reed, DWP Find a Job, public ATS boards) implements
`fetch()` and returns jobs in the ONE normalised schema (jobpilot_schemas.Job).
API keys stay behind this interface: a source without credentials returns
deterministic mock data so the whole pipeline runs before real keys exist.
"""

import os
from typing import Protocol

from jobpilot_schemas import Job


class IngestionSource(Protocol):
    name: str

    async def fetch(self) -> list[Job]: ...


def get_sources() -> list[IngestionSource]:
    from worker.sources.adzuna import AdzunaSource
    from worker.sources.ats import GreenhouseSource, LeverSource, WorkableSource
    from worker.sources.dwp import DWPFindAJobSource
    from worker.sources.reed import ReedSource

    return [
        AdzunaSource(
            app_id=os.environ.get("ADZUNA_APP_ID", ""),
            app_key=os.environ.get("ADZUNA_APP_KEY", ""),
        ),
        ReedSource(api_key=os.environ.get("REED_API_KEY", "")),
        DWPFindAJobSource(),
        GreenhouseSource(),
        LeverSource(),
        WorkableSource(),
    ]
