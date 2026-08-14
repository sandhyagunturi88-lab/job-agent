"""Reed.co.uk Jobseeker API (https://www.reed.co.uk/developers/jobseeker).

GET /api/1.0/search with HTTP Basic auth (api key as username, blank password).
Search results carry a truncated description; good enough for retrieval — the
job detail endpoint can backfill full text later if needed.
"""

from datetime import UTC, datetime

import httpx
from jobpilot_schemas import Job

from worker.normalise import detect_ir35
from worker.sources._mock import mock_jobs

API_URL = "https://www.reed.co.uk/api/1.0/search"
RESULTS_TO_TAKE = 100


class ReedSource:
    name = "reed"

    def __init__(
        self,
        api_key: str,
        queries: list[str] | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key
        self.queries = queries or []
        self.client = client

    async def fetch(self) -> list[Job]:
        if not self.api_key:
            return mock_jobs("reed")

        client = self.client or httpx.AsyncClient(timeout=30)
        jobs: list[Job] = []
        for query in self.queries or ["software engineer"]:
            response = await client.get(
                API_URL,
                params={"keywords": query, "resultsToTake": RESULTS_TO_TAKE},
                auth=(self.api_key, ""),
            )
            response.raise_for_status()
            jobs.extend(self._map(r) for r in response.json().get("results", []))
        return jobs

    @staticmethod
    def _map(r: dict) -> Job:
        jd_text = r.get("jobDescription") or ""
        # Reed dates are DD/MM/YYYY
        posted = datetime.strptime(r["date"], "%d/%m/%Y").replace(tzinfo=UTC)
        return Job(
            id=f"reed-{r['jobId']}",
            title=r["jobTitle"],
            company=r.get("employerName") or "Unknown",
            location=r.get("locationName") or "UK",
            salary_min=int(r["minimumSalary"]) if r.get("minimumSalary") else None,
            salary_max=int(r["maximumSalary"]) if r.get("maximumSalary") else None,
            contract_type=None,  # search payload lacks a reliable contract field
            ir35_flag=detect_ir35(jd_text),
            source="reed",
            url=r["jobUrl"],
            jd_text=jd_text,
            posted_at=posted,
        )
