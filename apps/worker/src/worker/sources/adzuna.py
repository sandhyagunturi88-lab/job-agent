"""Adzuna API (https://developer.adzuna.com/) — UK job aggregator.

GET /v1/api/jobs/gb/search/{page} with app_id/app_key. Without credentials the
source serves deterministic mock data so the pipeline runs before keys exist.
"""

from datetime import datetime

import httpx
from jobpilot_schemas import Job

from worker.normalise import detect_ir35, map_adzuna_contract
from worker.sources._mock import mock_jobs

API_BASE = "https://api.adzuna.com/v1/api/jobs/gb/search"
RESULTS_PER_PAGE = 50


class AdzunaSource:
    name = "adzuna"

    def __init__(
        self,
        app_id: str,
        app_key: str,
        queries: list[str] | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.app_id = app_id
        self.app_key = app_key
        self.queries = queries or []
        self.client = client

    async def fetch(self) -> list[Job]:
        if not (self.app_id and self.app_key):
            return mock_jobs("adzuna")

        client = self.client or httpx.AsyncClient(timeout=30)
        jobs: list[Job] = []
        for query in self.queries or ["software engineer"]:
            response = await client.get(
                f"{API_BASE}/1",
                params={
                    "app_id": self.app_id,
                    "app_key": self.app_key,
                    "what": query,
                    "results_per_page": RESULTS_PER_PAGE,
                    "content-type": "application/json",
                },
            )
            response.raise_for_status()
            jobs.extend(self._map(r) for r in response.json().get("results", []))
        return jobs

    @staticmethod
    def _map(r: dict) -> Job:
        jd_text = r.get("description") or ""
        return Job(
            id=f"adzuna-{r['id']}",
            title=r["title"],
            company=(r.get("company") or {}).get("display_name") or "Unknown",
            location=(r.get("location") or {}).get("display_name") or "UK",
            salary_min=int(r["salary_min"]) if r.get("salary_min") else None,
            salary_max=int(r["salary_max"]) if r.get("salary_max") else None,
            contract_type=map_adzuna_contract(r.get("contract_type"), r.get("contract_time")),
            ir35_flag=detect_ir35(jd_text),
            source="adzuna",
            url=r["redirect_url"],
            jd_text=jd_text,
            posted_at=datetime.fromisoformat(r["created"]),
        )
