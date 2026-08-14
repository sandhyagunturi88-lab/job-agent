"""Source clients mapped against recorded API response shapes (no network:
httpx.MockTransport). Without credentials/watchlists every source serves mocks."""

import asyncio
import json

import httpx
from worker.sources.adzuna import AdzunaSource
from worker.sources.ats import GreenhouseSource, LeverSource
from worker.sources.reed import ReedSource

ADZUNA_FIXTURE = {
    "results": [
        {
            "id": 5001,
            "title": "Senior Python Engineer",
            "description": "Build services. This contract role is outside IR35.",
            "redirect_url": "https://www.adzuna.co.uk/jobs/details/5001",
            "company": {"display_name": "Monzo"},
            "location": {"display_name": "London, UK"},
            "salary_min": 85000.0,
            "salary_max": 105000.0,
            "contract_type": "contract",
            "contract_time": "full_time",
            "created": "2026-08-12T10:30:00Z",
        }
    ]
}

REED_FIXTURE = {
    "results": [
        {
            "jobId": 9001,
            "employerName": "Starling Bank",
            "jobTitle": "Backend Engineer",
            "locationName": "London",
            "minimumSalary": 75000,
            "maximumSalary": 95000,
            "date": "11/08/2026",
            "jobDescription": "Python microservices in a regulated environment.",
            "jobUrl": "https://www.reed.co.uk/jobs/9001",
        }
    ]
}

GREENHOUSE_FIXTURE = {
    "jobs": [
        {
            "id": 7001,
            "title": "ML Engineer",
            "absolute_url": "https://boards.greenhouse.io/deepjudge/jobs/7001",
            "location": {"name": "Remote (UK)"},
            "updated_at": "2026-08-10T09:00:00-04:00",
            "content": "&lt;p&gt;LLM retrieval systems &amp; evaluation.&lt;/p&gt;",
        }
    ]
}

LEVER_FIXTURE = [
    {
        "id": "ab12",
        "text": "Platform Engineer",
        "hostedUrl": "https://jobs.lever.co/zopa/ab12",
        "createdAt": 1786600000000,
        "categories": {"location": "London", "commitment": "Full-time"},
        "descriptionPlain": "Terraform, AWS, CI/CD. Inside IR35 engagement.",
    }
]


def _client(payload) -> httpx.AsyncClient:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=json.dumps(payload).encode())
    )
    return httpx.AsyncClient(transport=transport)


def test_adzuna_mapping():
    source = AdzunaSource("id", "key", queries=["python"], client=_client(ADZUNA_FIXTURE))
    (job,) = asyncio.run(source.fetch())
    assert job.id == "adzuna-5001"
    assert job.company == "Monzo"
    assert job.salary_min == 85000 and job.salary_max == 105000
    assert job.contract_type == "contract"
    assert job.ir35_flag is False  # "outside IR35" detected in the JD
    assert job.source == "adzuna"
    assert job.posted_at.year == 2026


def test_reed_mapping_parses_uk_date():
    source = ReedSource("key", queries=["python"], client=_client(REED_FIXTURE))
    (job,) = asyncio.run(source.fetch())
    assert job.id == "reed-9001"
    assert (job.posted_at.day, job.posted_at.month, job.posted_at.year) == (11, 8, 2026)
    assert job.salary_max == 95000


def test_greenhouse_mapping_strips_escaped_html():
    source = GreenhouseSource(["deepjudge"], client=_client(GREENHOUSE_FIXTURE))
    (job,) = asyncio.run(source.fetch())
    assert job.id == "greenhouse-7001"
    assert job.company == "Deepjudge"
    assert job.jd_text == "LLM retrieval systems & evaluation."
    assert job.location == "Remote (UK)"


def test_lever_mapping():
    source = LeverSource(["zopa"], client=_client(LEVER_FIXTURE))
    (job,) = asyncio.run(source.fetch())
    assert job.id == "lever-ab12"
    assert job.company == "Zopa"
    assert job.contract_type == "permanent"  # "Full-time" commitment
    assert job.ir35_flag is True  # "inside IR35"


def test_sources_without_credentials_serve_mocks():
    assert asyncio.run(AdzunaSource("", "").fetch())[0].id.startswith("mock-adzuna")
    assert asyncio.run(ReedSource("").fetch())[0].id.startswith("mock-reed")
    assert asyncio.run(GreenhouseSource([]).fetch())[0].id.startswith("mock-greenhouse")
