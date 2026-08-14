"""Ingestion source interface.

Every source (Adzuna, Reed, DWP Find a Job, public ATS boards) implements
`fetch()` and returns jobs in the ONE normalised schema (jobpilot_schemas.Job).
API keys stay behind this interface: a source without credentials returns
deterministic mock data so the whole pipeline runs before real keys exist.
"""

from typing import Protocol

import httpx
from jobpilot_schemas import Job

from worker.config import WorkerSettings


class IngestionSource(Protocol):
    name: str

    async def fetch(self) -> list[Job]: ...


def _split(csv: str) -> list[str]:
    return [item.strip() for item in csv.split(",") if item.strip()]


def get_sources(
    settings: WorkerSettings, client: httpx.AsyncClient | None = None
) -> list[IngestionSource]:
    from worker.sources.adzuna import AdzunaSource
    from worker.sources.ats import GreenhouseSource, LeverSource, WorkableSource
    from worker.sources.dwp import DWPFindAJobSource
    from worker.sources.reed import ReedSource

    return [
        AdzunaSource(
            app_id=settings.adzuna_app_id,
            app_key=settings.adzuna_app_key,
            queries=settings.queries,
            client=client,
        ),
        ReedSource(api_key=settings.reed_api_key, queries=settings.queries, client=client),
        DWPFindAJobSource(),
        GreenhouseSource(boards=_split(settings.ats_greenhouse_boards), client=client),
        LeverSource(companies=_split(settings.ats_lever_companies), client=client),
        WorkableSource(accounts=_split(settings.ats_workable_accounts), client=client),
    ]
