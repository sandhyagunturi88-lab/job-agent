"""Reed.co.uk Jobseeker API — Basic-auth API key.

Phase 2 implements GET https://www.reed.co.uk/api/1.0/search."""

from jobpilot_schemas import Job

from worker.sources._mock import mock_jobs


class ReedSource:
    name = "reed"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def fetch(self) -> list[Job]:
        if not self.api_key:
            return mock_jobs("reed")
        raise NotImplementedError("Real Reed client lands in phase 2")
