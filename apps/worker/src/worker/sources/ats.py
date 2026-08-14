"""Public ATS board JSON endpoints — no keys required.

- Greenhouse: https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true
- Lever:      https://api.lever.co/v0/postings/{company}?mode=json
- Workable:   https://apply.workable.com/api/v1/widget/accounts/{account}

Phase 2 maintains a watchlist of UK company boards and implements the clients."""

from jobpilot_schemas import Job

from worker.sources._mock import mock_jobs


class GreenhouseSource:
    name = "greenhouse"

    async def fetch(self) -> list[Job]:
        return mock_jobs("greenhouse")


class LeverSource:
    name = "lever"

    async def fetch(self) -> list[Job]:
        return mock_jobs("lever")


class WorkableSource:
    name = "workable"

    async def fetch(self) -> list[Job]:
        return mock_jobs("workable")
