"""Public ATS board JSON endpoints — no API keys, just a watchlist of UK
company board slugs (config: ATS_GREENHOUSE_BOARDS / ATS_LEVER_COMPANIES /
ATS_WORKABLE_ACCOUNTS). Empty watchlist -> deterministic mock data.

- Greenhouse: boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true
- Lever:      api.lever.co/v0/postings/{company}?mode=json
- Workable:   apply.workable.com/api/v1/widget/accounts/{account}
"""

from datetime import UTC, datetime

import httpx
from jobpilot_schemas import Job

from worker.normalise import detect_ir35, strip_html
from worker.sources._mock import mock_jobs


class GreenhouseSource:
    name = "greenhouse"

    def __init__(self, boards: list[str], client: httpx.AsyncClient | None = None) -> None:
        self.boards = boards
        self.client = client

    async def fetch(self) -> list[Job]:
        if not self.boards:
            return mock_jobs("greenhouse")
        client = self.client or httpx.AsyncClient(timeout=30)
        jobs: list[Job] = []
        for board in self.boards:
            response = await client.get(
                f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs",
                params={"content": "true"},
            )
            response.raise_for_status()
            jobs.extend(self._map(board, j) for j in response.json().get("jobs", []))
        return jobs

    @staticmethod
    def _map(board: str, j: dict) -> Job:
        jd_text = strip_html(j.get("content") or "")
        return Job(
            id=f"greenhouse-{j['id']}",
            title=j["title"],
            company=j.get("company_name") or board.replace("-", " ").title(),
            location=(j.get("location") or {}).get("name") or "UK",
            contract_type=None,
            ir35_flag=detect_ir35(jd_text),
            source="greenhouse",
            url=j["absolute_url"],
            jd_text=jd_text,
            posted_at=datetime.fromisoformat(j["updated_at"]),
        )


class LeverSource:
    name = "lever"

    def __init__(self, companies: list[str], client: httpx.AsyncClient | None = None) -> None:
        self.companies = companies
        self.client = client

    async def fetch(self) -> list[Job]:
        if not self.companies:
            return mock_jobs("lever")
        client = self.client or httpx.AsyncClient(timeout=30)
        jobs: list[Job] = []
        for company in self.companies:
            response = await client.get(
                f"https://api.lever.co/v0/postings/{company}", params={"mode": "json"}
            )
            response.raise_for_status()
            jobs.extend(self._map(company, p) for p in response.json())
        return jobs

    @staticmethod
    def _map(company: str, p: dict) -> Job:
        jd_text = p.get("descriptionPlain") or strip_html(p.get("description") or "")
        categories = p.get("categories") or {}
        commitment = (categories.get("commitment") or "").lower()
        return Job(
            id=f"lever-{p['id']}",
            title=p["text"],
            company=company.replace("-", " ").title(),
            location=categories.get("location") or "UK",
            contract_type="part_time"
            if "part" in commitment
            else "contract"
            if "contract" in commitment
            else "permanent"
            if "full" in commitment
            else None,
            ir35_flag=detect_ir35(jd_text),
            source="lever",
            url=p["hostedUrl"],
            jd_text=jd_text,
            posted_at=datetime.fromtimestamp(p["createdAt"] / 1000, tz=UTC),
        )


class WorkableSource:
    name = "workable"

    def __init__(self, accounts: list[str], client: httpx.AsyncClient | None = None) -> None:
        self.accounts = accounts
        self.client = client

    async def fetch(self) -> list[Job]:
        if not self.accounts:
            return mock_jobs("workable")
        client = self.client or httpx.AsyncClient(timeout=30)
        jobs: list[Job] = []
        for account in self.accounts:
            response = await client.get(
                f"https://apply.workable.com/api/v1/widget/accounts/{account}"
            )
            response.raise_for_status()
            payload = response.json()
            company = payload.get("name") or account.title()
            jobs.extend(self._map(company, j) for j in payload.get("jobs", []))
        return jobs

    @staticmethod
    def _map(company: str, j: dict) -> Job:
        jd_text = strip_html(j.get("description") or "")
        location = ", ".join(x for x in (j.get("city"), j.get("country")) if x) or "UK"
        return Job(
            id=f"workable-{j['shortcode']}",
            title=j["title"],
            company=company,
            location=location,
            contract_type=None,
            ir35_flag=detect_ir35(jd_text),
            source="workable",
            url=j["url"],
            jd_text=jd_text,
            posted_at=datetime.fromisoformat(j["created_at"]),
        )
