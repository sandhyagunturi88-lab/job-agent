"""Adzuna API (https://developer.adzuna.com/) — UK job aggregator.

Phase 2 implements the real client: GET /v1/api/jobs/gb/search with
app_id/app_key, mapping results into the normalised Job schema."""

from jobpilot_schemas import Job

from worker.sources._mock import mock_jobs


class AdzunaSource:
    name = "adzuna"

    def __init__(self, app_id: str, app_key: str) -> None:
        self.app_id = app_id
        self.app_key = app_key

    async def fetch(self) -> list[Job]:
        if not (self.app_id and self.app_key):
            return mock_jobs("adzuna")
        raise NotImplementedError("Real Adzuna client lands in phase 2")
