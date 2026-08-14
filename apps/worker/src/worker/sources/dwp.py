"""DWP Find a Job (findajob.dwp.gov.uk) — public listings, no key required.

Phase 2 implements polite scraping/feed parsing within the site's terms."""

from jobpilot_schemas import Job

from worker.sources._mock import mock_jobs


class DWPFindAJobSource:
    name = "dwp_find_a_job"

    async def fetch(self) -> list[Job]:
        return mock_jobs("dwp_find_a_job")
